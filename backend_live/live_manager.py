import cv2
import time
import math
import threading
from collections import deque
from datetime import datetime
import torch
import numpy as np
from PIL import Image
from common.model_utils import load_video_mae_model
import gc
import requests


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
        self.threat_scores = {}  # {source_id: {'score': float, 'status': str, 'timestamp': datetime}}
        
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
                    score_callback=self._update_score
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


class CameraFeed:
    
    def __init__(self, source, source_id, name, model, processor, device, use_fp16, threshold, score_callback):
        self.source = source
        self.source_id = source_id
        self.name = name
        self.model = model
        self.processor = processor
        self.device = device
        self.use_fp16 = use_fp16
        self.threshold = threshold
        self.score_callback = score_callback
        
        # Thread control
        self.running = False
        self.capture_thread = None
        self.ai_thread = None
        
        # Frame storage
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
        # AI sampling buffer (16 frames for VideoMAE)
        self.ai_buffer = deque(maxlen=16)
        self.ai_buffer_lock = threading.Lock()
        
        # Current threat score
        self.current_score = 0.0
        self.current_status = "INITIALIZING"

        self.score_history = deque(maxlen=2)
        self.prev_frame_gray = None
        self.motion_threshold = 0.001
        
        # OpenCV capture
        self.cap = None
        self.inference_counter = 8
        
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
        
        print(f"Camera feed started: {self.name}")
    
    def stop(self):
        """Stop the camera feed."""
        self.running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        if self.ai_thread:
            self.ai_thread.join(timeout=2.0)
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
                        
                        if self.inference_counter >= 8:
                            frames_to_process = list(self.ai_buffer) # Copy buffer
                            self.inference_counter = 0 # Reset counter
                            
                            self._run_inference(frames_to_process, frame)
                
            except Exception as e:
                print(f"AI loop error on {self.name}: {e}")
            
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
            return True
            
        frame_delta = cv2.absdiff(self.prev_frame_gray, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        changed_pixels = cv2.countNonZero(thresh)
        total_pixels = gray.shape[0] * gray.shape[1]
        motion_ratio = changed_pixels / total_pixels
        
        self.prev_frame_gray = gray
        
        return motion_ratio > self.motion_threshold
    
    def _run_inference(self, frames, current_frame_cv):
        """Run VideoMAE inference on 16 frames with Motion Gating and Smoothing."""
        try:
            if not self._detect_motion(current_frame_cv):
                self.score_history.append(0.0)
                if len(self.score_history) > 4: self.score_history.popleft()
                
                avg_score = sum(self.score_history) / len(self.score_history) if self.score_history else 0.0
                self.current_score = round(avg_score, 4)
                self.current_status = "SECURE"
                
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
            
            self.score_history.append(loss)
            avg_score = sum(self.score_history) / len(self.score_history)
            
            self.current_score = round(avg_score, 4)
            
            if avg_score > 0.65:
                self.current_status = "CRITICAL"
            elif avg_score > self.threshold:
                self.current_status = "WARNING"
            else:
                self.current_status = "SECURE"
            
            self.score_callback(self.source_id, self.current_score, self.current_status)
            
            print(f"[{self.name}] Score: {self.current_score:.4f} (Raw: {loss:.4f}) | Status: {self.current_status}")
            
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


DEMO_CAMERAS = [
    {"id": "cam_lobby", "name": "Main Lobby", "source": "rtsp://example.com/lobby", "location": "Building A, Floor 1"},
    {"id": "cam_parking", "name": "Parking Lot", "source": "rtsp://example.com/parking", "location": "Basement Level"},
    {"id": "cam_hallway", "name": "East Hallway", "source": "rtsp://example.com/hallway", "location": "Building A, Floor 2"},
    {"id": "cam_entrance", "name": "Main Entrance", "source": "rtsp://example.com/entrance", "location": "Building A, Ground"},
]
