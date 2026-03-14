import cv2
import time
import math
import os
import tempfile
import threading
import queue
from collections import deque
from datetime import datetime
import torch
import numpy as np
from PIL import Image
from common.model_utils import load_video_mae_model
import gc
import requests
import cloudinary
import cloudinary.uploader
from common.config import CLOUDINARY_CONFIG

cloudinary.config(**CLOUDINARY_CONFIG)

# Anomaly clip limits (free tier safe)
MAX_CLIP_SECONDS = 30
MIN_CLIP_SECONDS = 5
CLIP_RECORD_THRESHOLD = 0.70  # Only record clips at email-alert level


class StreamManager:
    
    def __init__(self, model_path, device, use_fp16, threshold):

        self.model_path = model_path
        self.device = device
        self.use_fp16 = use_fp16
        self.threshold = threshold
        
        # Model state
        self.model = None
        self.processor = None
        
        # Active feeds storage
        self.feeds = {}  # {source_id: CameraFeed}
        self.lock = threading.Lock()
        
        # Global threat scores per feed
        self.threat_scores = {}
        
        # Uploaded anomaly clips across all feeds
        self.anomaly_clips = []
        self.clips_lock = threading.Lock()
        
        print("StreamManager initialized")
    
    def start_feed(self, source, source_id, name="Camera"):
        with self.lock:
            if source_id in self.feeds:
                print(f"Feed {source_id} already running")
                return False
            
            try:
                # 0. Request Forensic Service to release GPU
                try:
                    requests.post('http://localhost:5001/api/release', timeout=0.5)
                except:
                    pass # Ignore if forensic service is offline

                if self.model is None:
                    print(f"Loading AI Model for {name}...")
                    self.model, self.processor = load_video_mae_model(self.model_path, self.device, self.use_fp16)

                feed = CameraFeed(
                    source=source,
                    source_id=source_id,
                    name=name,
                    model=self.model,
                    processor=self.processor,
                    device=self.device,
                    use_fp16=self.use_fp16,
                    threshold=self.threshold,
                    score_callback=self._update_score,
                    clip_callback=self.add_clip
                )
                self.feeds[source_id] = feed
                self.threat_scores[source_id] = {
                    'score': 0.0,
                    'status': 'INITIALIZING',
                    'timestamp': datetime.now().isoformat(),
                    'name': name
                }
                feed.start()
                print(f"Started feed: {name} (ID: {source_id})")
                return True
            except Exception as e:
                print(f"Failed to start feed {source_id}: {e}")
                return False
    
    def stop_feed(self, source_id):
        """Stop a camera feed."""
        with self.lock:
            if source_id in self.feeds:
                self.feeds[source_id].stop()
                del self.feeds[source_id]
                if source_id in self.threat_scores:
                    del self.threat_scores[source_id]
                print(f"Stopped feed: {source_id}")
                if not self.feeds:
                    print("No active feeds. Unloading model to free GPU...")
                    self.model = None
                    self.processor = None
                    torch.cuda.empty_cache()
                    gc.collect()
                
                return True
            return False
    
    def stop_all_feeds(self):
        """Stop all active feeds."""
        with self.lock:
            for feed in list(self.feeds.values()):
                feed.stop()
            self.feeds.clear()
            self.threat_scores.clear()
            print("All feeds stopped")
    
    def get_frame_generator(self, source_id):
        if source_id not in self.feeds:
            return None
        return self.feeds[source_id].generate_mjpeg()
    
    def get_scores(self):
        """Get current threat scores for all feeds."""
        return dict(self.threat_scores)
    
    def get_score(self, source_id):
        """Get threat score for a specific feed."""
        return self.threat_scores.get(source_id, {
            'score': 0.0,
            'status': 'OFFLINE',
            'timestamp': None
        })
    
    def is_feed_active(self, source_id):
        """Check if a feed is currently active."""
        return source_id in self.feeds
    
    def _update_score(self, source_id, score, status):
        """Callback to update threat score (thread-safe)."""
        with self.lock:
            if source_id in self.threat_scores:
                self.threat_scores[source_id] = {
                    'score': score,
                    'status': status,
                    'timestamp': datetime.now().isoformat(),
                    'name': self.threat_scores[source_id].get('name', 'Camera')
                }
    
    def add_clip(self, clip_info):
        """Store an uploaded anomaly clip."""
        with self.clips_lock:
            self.anomaly_clips.append(clip_info)
    
    def get_clips(self):
        """Return all uploaded anomaly clips."""
        with self.clips_lock:
            return list(self.anomaly_clips)


class CameraFeed:
    
    def __init__(self, source, source_id, name, model, processor, device, use_fp16, threshold, score_callback, clip_callback=None):
        self.source = source
        self.source_id = source_id
        self.name = name
        self.model = model
        self.processor = processor
        self.device = device
        self.use_fp16 = use_fp16
        self.threshold = threshold
        self.score_callback = score_callback
        self.clip_callback = clip_callback
        
        # Thread control
        self.running = False
        self.capture_thread = None
        self.ai_thread = None
        self.upload_thread = None
        
        # Frame storage
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
        # AI sampling buffer (16 frames for VideoMAE)
        self.ai_buffer = deque(maxlen=16)
        self.ai_buffer_lock = threading.Lock()
        
        # Current threat score
        self.current_score = 0.0
        self.current_status = "INITIALIZING"

        self.score_history = deque(maxlen=3)
        self.prev_frame_gray = None
        self.motion_threshold = 0.003
        self.min_contour_area = 1000
        self.prev_motion_ratio = 0.0
        self.peak_score = 0.0
        self.peak_time = 0.0
        
        # OpenCV capture
        self.cap = None
        self.inference_counter = 4
        
        # Anomaly clip recording (non-blocking)
        self.anomaly_recording = False
        self.anomaly_frames = []
        self.anomaly_start_time = None
        self.anomaly_peak_score = 0.0
        self.upload_queue = queue.Queue()
        
    def start(self):
        """Start the camera feed threads."""
        self.running = True
        
        # Initialize capture
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            raise ValueError(f"Failed to open video source: {self.source}")
        
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Start capture thread (visual frames at 30 FPS)
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        # Start AI inference thread (Smart Sampling)
        self.ai_thread = threading.Thread(target=self._ai_loop, daemon=True)
        self.ai_thread.start()
        
        # Background thread for clip uploads (never blocks AI loop)
        self.upload_thread = threading.Thread(target=self._upload_loop, daemon=True)
        self.upload_thread.start()
        
        print(f"Camera feed started: {self.name}")
    
    def stop(self):
        """Stop the camera feed."""
        self.running = False
        self._finalize_clip()
        self.upload_queue.put(None)  # Signal upload thread to exit
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        if self.ai_thread:
            self.ai_thread.join(timeout=2.0)
        if self.upload_thread:
            self.upload_thread.join(timeout=5.0)
        if self.cap:
            self.cap.release()
        print(f"Camera feed stopped: {self.name}")
    
    def _capture_loop(self):
        target_fps = 30
        frame_interval = 1.0 / target_fps
        
        while self.running:
            start_time = time.time()
            
            try:
                ret, frame = self.cap.read()
                if not ret:
                    print(f"Lost connection to {self.name}, attempting reconnect...")
                    time.sleep(1.0)
                    self.cap.release()
                    self.cap = cv2.VideoCapture(self.source)
                    if not self.cap.isOpened():
                        time.sleep(2.0)
                    continue
                
                with self.frame_lock:
                    self.current_frame = frame.copy()
                
            except Exception as e:
                print(f"Capture error on {self.name}: {e}")
                time.sleep(0.5)
                continue
            
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _ai_loop(self):
        """AI sampling loop - captures 1 frame every 0.1s, runs inference every 16 frames."""
        sample_interval = 0.1  # 10 FPS sampling for AI
        
        while self.running:
            start_time = time.time()
            
            try:
                with self.frame_lock:
                    if self.current_frame is not None:
                        frame = self.current_frame.copy()
                    else:
                        time.sleep(0.05)
                        continue
                
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                
                with self.ai_buffer_lock:
                    self.ai_buffer.append(pil_img)
                    
                    if len(self.ai_buffer) == 16:
                        self.inference_counter += 1
                        
                        if self.inference_counter >= 4:
                            frames_to_process = list(self.ai_buffer) # Copy buffer
                            self.inference_counter = 0 # Reset counter
                            
                            self._run_inference(frames_to_process, frame)
                
                # Record frames for anomaly clip at AI loop rate (~10 FPS)
                if self.anomaly_recording:
                    self.anomaly_frames.append(frame.copy())
                
            except Exception as e:
                print(f"AI loop error on {self.name}: {e}")
            
            elapsed = time.time() - start_time
            sleep_time = max(0, sample_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _detect_motion(self, current_frame):
        gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        if self.prev_frame_gray is None:
            self.prev_frame_gray = gray
            return 1.0
            
        frame_delta = cv2.absdiff(self.prev_frame_gray, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        changed_pixels = cv2.countNonZero(thresh)
        total_pixels = gray.shape[0] * gray.shape[1]
        motion_ratio = changed_pixels / total_pixels
        
        self.prev_frame_gray = gray
        
        if motion_ratio <= self.motion_threshold:
            return 0.0
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        significant_motion = any(cv2.contourArea(c) > self.min_contour_area for c in contours)
        
        return motion_ratio if significant_motion else 0.0
    
    def _run_inference(self, frames, current_frame_cv):
        try:
            motion_ratio = self._detect_motion(current_frame_cv)
            
            if motion_ratio == 0.0:
                self.prev_motion_ratio = 0.0
                self.score_history.append(0.0)
                
                now = time.time()
                if now - self.peak_time < 4.0 and self.peak_score > 0:
                    final_score = self.peak_score * max(0, 1.0 - (now - self.peak_time) / 4.0)
                else:
                    final_score = sum(self.score_history) / len(self.score_history) if self.score_history else 0.0
                    self.peak_score = 0.0
                
                self.current_score = round(final_score, 4)
                self.current_status = "SECURE" if final_score < self.threshold else ("CRITICAL" if final_score > 0.55 else "WARNING")
                self.score_callback(self.source_id, self.current_score, self.current_status)
                return

            inputs = self.processor(frames, return_tensors="pt").pixel_values.to(self.device)
            if self.use_fp16:
                inputs = inputs.half()
            
            mask = self._generate_mask(1, 1568, 0.75)
            
            with torch.no_grad():
                outputs = self.model(inputs, bool_masked_pos=mask)
                loss = outputs.loss.item()
                if not math.isfinite(loss):
                    loss = 1.0
            
            motion_boost = 1.0
            if motion_ratio > 0.02:
                motion_boost = 1.0 + min(motion_ratio * 5, 0.4)
            
            motion_accel = motion_ratio - self.prev_motion_ratio
            accel_boost = 1.0
            if motion_accel > 0.015:
                accel_boost = 1.0 + min(motion_accel * 10, 0.5)
            
            self.prev_motion_ratio = motion_ratio
            
            boosted_loss = min(loss * motion_boost * accel_boost, 1.0)
            
            self.score_history.append(boosted_loss)
            current_max = max(self.score_history)
            
            now = time.time()
            if current_max > self.peak_score:
                self.peak_score = current_max
                self.peak_time = now
            
            if now - self.peak_time < 4.0:
                final_score = max(current_max, self.peak_score * max(0, 1.0 - (now - self.peak_time) / 4.0))
            else:
                final_score = current_max
                self.peak_score = current_max
                self.peak_time = now
            
            self.current_score = round(final_score, 4)
            
            if final_score > 0.55:
                self.current_status = "CRITICAL"
            elif final_score > self.threshold:
                self.current_status = "WARNING"
            else:
                self.current_status = "SECURE"
            
            self.score_callback(self.source_id, self.current_score, self.current_status)
            
            # Anomaly clip recording (lightweight — just appends frame reference)
            self._handle_clip_recording(current_frame_cv)
            
            print(f"[{self.name}] Score: {self.current_score:.4f} (Raw: {loss:.4f}, Motion: {motion_ratio:.4f}, Boost: {motion_boost:.2f}x, Accel: {accel_boost:.2f}x) | {self.current_status}")
            
        except Exception as e:
            print(f"Inference error on {self.name}: {e}")
            self.current_status = "ERROR"
            self.score_callback(self.source_id, 0.0, "ERROR")
    
    def _generate_mask(self, batch_size, seq_length, ratio=0.75):
        """Generate mask for VideoMAE model."""
        num_masked = int(seq_length * ratio)
        mask = torch.hstack([
            torch.ones(batch_size, num_masked),
            torch.zeros(batch_size, seq_length - num_masked)
        ])
        ids_shuffle = torch.argsort(torch.rand(batch_size, seq_length), dim=1)
        return torch.gather(mask, dim=1, index=ids_shuffle).bool().to(self.device)
    
    def generate_mjpeg(self):
        while self.running:
            try:
                with self.frame_lock:
                    if self.current_frame is None:
                        time.sleep(0.033)
                        continue
                    frame = self.current_frame.copy()
                
                frame = self._annotate_frame(frame)
                
                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not ret:
                    continue
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                
            except Exception as e:
                print(f"MJPEG stream error: {e}")
                time.sleep(0.1)
    
    def _annotate_frame(self, frame):
        """Add threat score overlay to frame."""
        height, width = frame.shape[:2]
        
        colors = {
            'SECURE': (0, 200, 100),      # Green
            'WARNING': (0, 165, 255),      # Orange
            'CRITICAL': (0, 0, 255),       # Red
            'INITIALIZING': (255, 255, 0), # Cyan
            'ERROR': (128, 128, 128)       # Gray
        }
        color = colors.get(self.current_status, (255, 255, 255))
        
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (width, 50), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
        
        status_text = f"{self.current_status}"
        cv2.putText(frame, status_text, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 
                    0.9, color, 2, cv2.LINE_AA)
        
        score_text = f"Score: {self.current_score:.3f}"
        text_size = cv2.getTextSize(score_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        cv2.putText(frame, score_text, (width - text_size[0] - 10, 35), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        
        cv2.rectangle(overlay, (0, height - 30), (width, height), (0, 0, 0), -1)
        frame_bottom = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
        cv2.putText(frame, f"{self.name}", (10, height - 8), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, timestamp, (width - 80, height - 8), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
        
        if self.current_status == "CRITICAL":
            pulse = int(128 + 127 * math.sin(time.time() * 6))  # Pulsing effect
            cv2.rectangle(frame, (2, 2), (width - 2, height - 2), (0, 0, pulse), 3)
        
        return frame

    def _handle_clip_recording(self, frame):
        """Start/stop clip recording based on anomaly status."""
        is_critical = self.current_score >= CLIP_RECORD_THRESHOLD
        
        if is_critical and not self.anomaly_recording:
            self.anomaly_recording = True
            self.anomaly_frames = []
            self.anomaly_start_time = time.time()
            self.anomaly_peak_score = self.current_score
            print(f"[{self.name}] Anomaly clip recording started")
        
        if self.anomaly_recording:
            self.anomaly_peak_score = max(self.anomaly_peak_score, self.current_score)
            elapsed = time.time() - self.anomaly_start_time
            if not is_critical or elapsed >= MAX_CLIP_SECONDS:
                self._finalize_clip()
    
    def _finalize_clip(self):
        """Queue the recorded clip for background upload."""
        if not self.anomaly_recording or not self.anomaly_frames:
            self.anomaly_recording = False
            return
        
        elapsed = time.time() - self.anomaly_start_time
        self.anomaly_recording = False
        
        if elapsed < MIN_CLIP_SECONDS:
            print(f"[{self.name}] Clip too short ({elapsed:.1f}s), discarding")
            self.anomaly_frames = []
            return
        
        # Hand off to background upload thread
        clip_data = {
            'frames': self.anomaly_frames,
            'duration': round(elapsed, 1),
            'peak_score': self.anomaly_peak_score,
            'timestamp': datetime.now().isoformat(),
            'source_id': self.source_id,
            'name': self.name
        }
        self.anomaly_frames = []
        self.upload_queue.put(clip_data)
        print(f"[{self.name}] Clip queued for upload ({clip_data['duration']}s, peak: {clip_data['peak_score']:.3f})")
    
    def _upload_loop(self):
        """Background thread: writes clips to temp file and uploads to Cloudinary."""
        while True:
            clip_data = self.upload_queue.get()
            if clip_data is None:
                break  # Shutdown signal
            
            try:
                frames = clip_data['frames']
                if not frames:
                    continue
                
                h, w = frames[0].shape[:2]
                clip_fps = 10  # Matches AI loop sampling rate
                
                # Write to temp file
                tmp_path = os.path.join(tempfile.gettempdir(), f"alertrix_clip_{int(time.time())}.mp4")
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                writer = cv2.VideoWriter(tmp_path, fourcc, clip_fps, (w, h))
                
                for f in frames:
                    writer.write(f)
                writer.release()
                
                # Upload to Cloudinary
                print(f"[{clip_data['name']}] Uploading anomaly clip to Cloudinary...")
                result = cloudinary.uploader.upload(
                    tmp_path,
                    resource_type="video",
                    folder="alertrix_anomaly_clips"
                )
                url = result.get('secure_url', '')
                # Add H.264 transcoding for browser playback (mp4v isn't web-compatible)
                url = url.replace('/upload/', '/upload/vc_h264/')
                print(f"[{clip_data['name']}] Clip uploaded: {url}")
                
                # Notify StreamManager
                if self.clip_callback:
                    self.clip_callback({
                        'url': url,
                        'source_id': clip_data['source_id'],
                        'camera_name': clip_data['name'],
                        'duration': clip_data['duration'],
                        'peak_score': clip_data['peak_score'],
                        'timestamp': clip_data['timestamp']
                    })
                
                # Cleanup temp file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
            except Exception as e:
                print(f"[{clip_data.get('name', '?')}] Clip upload failed: {e}")


DEMO_CAMERAS = [
    {"id": "cam_lobby", "name": "Main Lobby", "source": "rtsp://example.com/lobby", "location": "Building A, Floor 1"},
    {"id": "cam_parking", "name": "Parking Lot", "source": "rtsp://example.com/parking", "location": "Basement Level"},
    {"id": "cam_hallway", "name": "East Hallway", "source": "rtsp://example.com/hallway", "location": "Building A, Floor 2"},
    {"id": "cam_entrance", "name": "Main Entrance", "source": "rtsp://example.com/entrance", "location": "Building A, Ground"},
]
