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
import cloudinary
import cloudinary.uploader

# Anomaly clip limits (free tier safe)
MAX_CLIP_SECONDS = 30
MIN_CLIP_SECONDS = 5
CLIP_RECORD_THRESHOLD = 0.70  # Only record clips at email-alert level


class StreamManager:
    
    def __init__(self, model, processor, device, use_fp16, threshold):
        self.model = model
        self.processor = processor
        self.device = device
        self.use_fp16 = use_fp16
        self.threshold = threshold
        
        # Active feeds storage
        self.feeds = {}  # {source_id: CameraFeed}
        self.lock = threading.Lock()
        
        # Global threat scores per feed
        self.threat_scores = {}
        
        # Uploaded anomaly clips across all feeds
        self.anomaly_clips = []
        self.clips_lock = threading.Lock()
        
        print("✅ StreamManager initialized")
    
    def start_feed(self, source, source_id, name="Camera"):
        with self.lock:
            if source_id in self.feeds:
                print(f"⚠️ Feed {source_id} already running")
                return False
            
            try:
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
                print(f"✅ Started feed: {name} (ID: {source_id})")
                return True
            except Exception as e:
                print(f"❌ Failed to start feed {source_id}: {e}")
                return False
    
    def stop_feed(self, source_id):
        """Stop a camera feed."""
        with self.lock:
            if source_id in self.feeds:
                self.feeds[source_id].stop()
                del self.feeds[source_id]
                if source_id in self.threat_scores:
                    del self.threat_scores[source_id]
                print(f"🛑 Stopped feed: {source_id}")
                return True
            return False
    
    def stop_all_feeds(self):
        """Stop all active feeds."""
        with self.lock:
            for feed in list(self.feeds.values()):
                feed.stop()
            self.feeds.clear()
            self.threat_scores.clear()
            print("🛑 All feeds stopped")
    
    def get_frame_generator(self, source_id):

        if source_id not in self.feeds:
            return None
        return self.feeds[source_id].generate_mjpeg()
    
    def get_scores(self):

        return dict(self.threat_scores)
    
    def get_score(self, source_id):

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

        # Smoothing & Motion Gating
        self.score_history = deque(maxlen=4)
        self.prev_frame_gray = None
        self.motion_threshold = 0.005
        
        # OpenCV capture
        self.cap = None
        
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
        
        # Set optimal buffer size for real-time
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
        
        print(f"📹 Camera feed started: {self.name}")
    
    def stop(self):
        """Stop the camera feed."""
        self.running = False
        self._finalize_clip()
        self.upload_queue.put(None)
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        if self.ai_thread:
            self.ai_thread.join(timeout=2.0)
        if self.upload_thread:
            self.upload_thread.join(timeout=5.0)
        if self.cap:
            self.cap.release()
        print(f"📹 Camera feed stopped: {self.name}")
    
    def _capture_loop(self):
        """Main capture loop - runs at ~30 FPS."""
        target_fps = 30
        frame_interval = 1.0 / target_fps
        
        while self.running:
            start_time = time.time()
            
            try:
                ret, frame = self.cap.read()
                if not ret:
                    # Try to reconnect
                    print(f"⚠️ Lost connection to {self.name}, attempting reconnect...")
                    time.sleep(1.0)
                    self.cap.release()
                    self.cap = cv2.VideoCapture(self.source)
                    if not self.cap.isOpened():
                        time.sleep(2.0)
                    continue
                
                # Store current frame for visual streaming
                with self.frame_lock:
                    self.current_frame = frame.copy()
                
            except Exception as e:
                print(f"❌ Capture error on {self.name}: {e}")
                time.sleep(0.5)
                continue
            
            # Maintain target FPS
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
                # Get current frame for AI buffer
                with self.frame_lock:
                    if self.current_frame is not None:
                        frame = self.current_frame.copy()
                    else:
                        time.sleep(0.05)
                        continue
                
                # Convert to PIL Image for processor
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                
                # Add to AI buffer
                with self.ai_buffer_lock:
                    self.ai_buffer.append(pil_img)
                    
                    # Run inference when we have 16 frames
                    if len(self.ai_buffer) == 16:
                        frames_to_process = list(self.ai_buffer)
                        self.ai_buffer.clear()
                        
                        # Run inference in separate call to keep lock time minimal
                        self._run_inference(frames_to_process, frame)
                
                # Record frames for anomaly clip at AI loop rate (~10 FPS)
                if self.anomaly_recording:
                    self.anomaly_frames.append(frame.copy())
                
            except Exception as e:
                print(f"❌ AI loop error on {self.name}: {e}")
            
            # Maintain sampling interval
            elapsed = time.time() - start_time
            sleep_time = max(0, sample_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _detect_motion(self, current_frame):
        """Simple motion detection to filter out static scenes."""
        gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        if self.prev_frame_gray is None:
            self.prev_frame_gray = gray
            return True # Assume motion on first frame
            
        # Compute absolute difference
        frame_delta = cv2.absdiff(self.prev_frame_gray, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        
        # Dilate to fill holes
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Check "quantity" of motion
        changed_pixels = cv2.countNonZero(thresh)
        total_pixels = gray.shape[0] * gray.shape[1]
        motion_ratio = changed_pixels / total_pixels
        
        self.prev_frame_gray = gray
        
        # If changed pixels < threshold (e.g. 0.5%), assume idle
        return motion_ratio > self.motion_threshold
    
    def _run_inference(self, frames, current_frame_cv):
        """Run VideoMAE inference on 16 frames with Motion Gating and Smoothing."""
        try:
            # 1. Motion Gating: Check if there's enough motion to warrant AI Check
            if not self._detect_motion(current_frame_cv):
                # No significant motion -> Decay score towards 0
                self.score_history.append(0.0)
                if len(self.score_history) > 4: self.score_history.popleft()
                
                avg_score = sum(self.score_history) / len(self.score_history) if self.score_history else 0.0
                self.current_score = round(avg_score, 4)
                self.current_status = "SECURE"
                
                # Callback to update global scores
                self.score_callback(self.source_id, self.current_score, self.current_status)
                return

            # Prepare inputs
            inputs = self.processor(frames, return_tensors="pt").pixel_values.to(self.device)
            if self.use_fp16:
                inputs = inputs.half()
            
            # Generate mask for VideoMAE
            mask = self._generate_mask(1, 1568, 0.75)
            
            # Run inference with no_grad for memory efficiency
            with torch.no_grad():
                outputs = self.model(inputs, bool_masked_pos=mask)
                loss = outputs.loss.item()
                
                # Handle invalid loss values
                if not math.isfinite(loss):
                    loss = 1.0
            
            # 2. Score Smoothing (Moving Average)
            self.score_history.append(loss)
            avg_score = sum(self.score_history) / len(self.score_history)
            
            self.current_score = round(avg_score, 4)
            
            # 3. Status Determination
            if avg_score > 0.72:
                self.current_status = "CRITICAL"
            elif avg_score > self.threshold:
                self.current_status = "WARNING"
            else:
                self.current_status = "SECURE"
            
            # Callback to update global scores
            self.score_callback(self.source_id, self.current_score, self.current_status)
            
            # Anomaly clip recording (lightweight — just appends frame reference)
            self._handle_clip_recording(current_frame_cv)
            
            print(f"🔍 [{self.name}] Score: {self.current_score:.4f} (Raw: {loss:.4f}) | Status: {self.current_status}")
            
        except Exception as e:
            print(f"❌ Inference error on {self.name}: {e}")
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
                
                # Add threat score overlay
                frame = self._annotate_frame(frame)
                
                # Encode as JPEG
                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not ret:
                    continue
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                
            except Exception as e:
                print(f"❌ MJPEG stream error: {e}")
                time.sleep(0.1)
    
    def _annotate_frame(self, frame):
        """Add threat score overlay to frame."""
        height, width = frame.shape[:2]
        
        # Define colors based on status
        colors = {
            'SECURE': (0, 200, 100),      # Green
            'WARNING': (0, 165, 255),      # Orange
            'CRITICAL': (0, 0, 255),       # Red
            'INITIALIZING': (255, 255, 0), # Cyan
            'ERROR': (128, 128, 128)       # Gray
        }
        color = colors.get(self.current_status, (255, 255, 255))
        
        # Create semi-transparent overlay bar at top
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (width, 50), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
        
        # Add status text
        status_text = f"{self.current_status}"
        cv2.putText(frame, status_text, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 
                    0.9, color, 2, cv2.LINE_AA)
        
        # Add score text on right side
        score_text = f"Score: {self.current_score:.3f}"
        text_size = cv2.getTextSize(score_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        cv2.putText(frame, score_text, (width - text_size[0] - 10, 35), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Add camera name at bottom
        cv2.rectangle(overlay, (0, height - 30), (width, height), (0, 0, 0), -1)
        frame_bottom = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
        cv2.putText(frame, f"📹 {self.name}", (10, height - 8), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, timestamp, (width - 80, height - 8), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
        
        # Add pulsing border for CRITICAL status
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
                break
            
            try:
                frames = clip_data['frames']
                if not frames:
                    continue
                
                h, w = frames[0].shape[:2]
                clip_fps = 10  # Matches AI loop sampling rate
                
                tmp_path = os.path.join(tempfile.gettempdir(), f"alertrix_clip_{int(time.time())}.mp4")
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                writer = cv2.VideoWriter(tmp_path, fourcc, clip_fps, (w, h))
                
                for f in frames:
                    writer.write(f)
                writer.release()
                
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
                
                if self.clip_callback:
                    self.clip_callback({
                        'url': url,
                        'source_id': clip_data['source_id'],
                        'camera_name': clip_data['name'],
                        'duration': clip_data['duration'],
                        'peak_score': clip_data['peak_score'],
                        'timestamp': clip_data['timestamp']
                    })
                
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
            except Exception as e:
                print(f"[{clip_data.get('name', '?')}] Clip upload failed: {e}")


# Demo camera configurations for testing
DEMO_CAMERAS = [
    {"id": "cam_lobby", "name": "Main Lobby", "source": "rtsp://example.com/lobby", "location": "Building A, Floor 1"},
    {"id": "cam_parking", "name": "Parking Lot", "source": "rtsp://example.com/parking", "location": "Basement Level"},
    {"id": "cam_hallway", "name": "East Hallway", "source": "rtsp://example.com/hallway", "location": "Building A, Floor 2"},
    {"id": "cam_entrance", "name": "Main Entrance", "source": "rtsp://example.com/entrance", "location": "Building A, Ground"},
]
