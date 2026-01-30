import os
import math
import cv2
import torch
import numpy as np
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from PIL import Image
from transformers import VideoMAEForPreTraining, VideoMAEImageProcessor
import cloudinary
import cloudinary.uploader

# ==========================================
# 1. CONFIGURATION
# ==========================================
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# SOCKET.IO SETUP for real-time streaming
try:
    from flask_socketio import SocketIO, emit
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
    SOCKETIO_ENABLED = True
    print("✅ SocketIO enabled for real-time streaming")
except ImportError:
    socketio = None
    SOCKETIO_ENABLED = False
    print("⚠️ flask-socketio not installed. Real-time features disabled.")
app.config['SECRET_KEY'] = 'alertrix-secret-key-change-in-production'

# FIREBASE SETUP

from models import init_firebase
firebase_ready = init_firebase()
if firebase_ready:
    print("Firebase connected successfully!")
else:
    print("WARNING: Firebase not initialized. Auth features will be limited.")

# Register blueprints
from auth import auth_bp
from admin import admin_bp
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)

# CLOUDINARY SETUP
cloudinary.config( 
  cloud_name = "dz23mrxfb", 
  api_key = "456783583454585", 
  api_secret = "kh2TWcD3kFUSefGKgeUAoU85OAs",
  secure = True
)

# AI MODEL SETUP
MODEL_PATH = os.path.join(os.path.dirname(__file__), "alertrix_final_epoch40.pth")
MODEL_TYPE = "MCG-NJU/videomae-base"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
USE_FP16 = DEVICE == "cuda" 
UPLOAD_THRESHOLD = 0.44
LIVE_THRESHOLD = 0.60   
FRAME_SKIP = 3 

# ==========================================
# 2. LOAD THE MODEL
# ==========================================
print(f"Loading AI Model from {MODEL_PATH}...")
try:
    model = VideoMAEForPreTraining.from_pretrained(MODEL_TYPE)
    checkpoint = torch.load(MODEL_PATH, map_location=torch.device(DEVICE))
    if 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint)
    model.to(DEVICE)
    model.eval()
    if USE_FP16:
        model.half()
    processor = VideoMAEImageProcessor.from_pretrained(MODEL_TYPE)
    print(f"SUCCESS: Model Loaded on {DEVICE.upper()}! FP16={USE_FP16}. Server is ready.")
except Exception as e:
    print(f"ERROR: {e}")
    print("HINT: Is the .pth file inside the backend folder?")
    exit()

# ==========================================
# 2.1 LIVE STREAM MANAGER
# ==========================================
try:
    from live_manager import StreamManager, DEMO_CAMERAS
    stream_manager = StreamManager(model, processor, DEVICE, USE_FP16, LIVE_THRESHOLD)
    LIVE_STREAMING_ENABLED = True
    print("✅ Live StreamManager initialized")
except Exception as e:
    stream_manager = None
    LIVE_STREAMING_ENABLED = False
    print(f"⚠️ Live streaming disabled: {e}")

# ==========================================
# 2.2 ALERT SYSTEM
# ==========================================
try:
    from alerts import get_alert_manager, EMAIL_CONFIG
    alert_manager = get_alert_manager()
    ALERTS_ENABLED = True
    print("✅ Alert system initialized")
except Exception as e:
    alert_manager = None
    ALERTS_ENABLED = False
    print(f"⚠️ Alert system disabled: {e}")

# ==========================================
# 3. AI PROCESSING LOGIC
# ==========================================
def generate_mask(batch_size, seq_length, ratio=0.75):
    num_masked = int(seq_length * ratio)
    mask = torch.hstack([torch.ones(batch_size, num_masked), torch.zeros(batch_size, seq_length - num_masked)])
    ids_shuffle = torch.argsort(torch.rand(batch_size, seq_length), dim=1)
    return torch.gather(mask, dim=1, index=ids_shuffle).bool().to(DEVICE)

def process_video(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0: fps = 30.0
    
    frame_buffer = []
    anomalies = []
    current_frame = 0 # Tracks real video frames
    
    print(f"Processing video for anomalies (Speedup: {FRAME_SKIP}x)...")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        current_frame += 1
        
        # Skip frames for speed optimization
        if current_frame % FRAME_SKIP != 0:
            continue

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)
        frame_buffer.append(pil_img)

        if len(frame_buffer) == 16:
            inputs = processor(list(frame_buffer), return_tensors="pt").pixel_values.to(DEVICE)
            if USE_FP16:
                inputs = inputs.half()  # Match model precision
            mask = generate_mask(1, 1568, 0.75) 

            with torch.no_grad():
                outputs = model(inputs, bool_masked_pos=mask)
                loss = outputs.loss.item()
                if not math.isfinite(loss):
                    loss = 1.0
            
            timestamp = current_frame / fps
            is_anomaly = loss > UPLOAD_THRESHOLD
            
            anomalies.append({
                "time": round(timestamp, 2),
                "score": round(loss, 4),
                "status": "Anomaly Detected" if is_anomaly else "Normal",
                "is_anomaly": is_anomaly
            })

            frame_buffer = frame_buffer[8:]

    cap.release()
    return anomalies

# ==========================================
# 4. API ROUTES
# ==========================================

# ------------------------------------------
# 4.1 LIVE STREAMING ROUTES
# ------------------------------------------
@app.route('/video_feed/<source_id>')
def video_feed(source_id):
    """
    MJPEG video stream endpoint for live camera feeds.
    
    Usage:
        <img src="http://localhost:5000/video_feed/webcam" />
    """
    if not LIVE_STREAMING_ENABLED:
        return jsonify({"error": "Live streaming not available"}), 503
    
    if not stream_manager.is_feed_active(source_id):
        return jsonify({"error": f"Feed '{source_id}' is not active"}), 404
    
    return Response(
        stream_manager.get_frame_generator(source_id),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/live/start', methods=['POST'])
def start_live_feed():
    """Start a live camera feed."""
    if not LIVE_STREAMING_ENABLED:
        return jsonify({"error": "Live streaming not available"}), 503
    
    data = request.get_json() or {}
    source_id = data.get('source_id', 'webcam')
    source = data.get('source', 0)  # 0 for webcam, or RTSP URL
    name = data.get('name', 'Webcam')
    
    # Convert source to int if it's "0" (webcam)
    if source == "0" or source == 0:
        source = 0
    
    success = stream_manager.start_feed(source, source_id, name)
    
    if success:
        return jsonify({
            "status": "started",
            "source_id": source_id,
            "feed_url": f"/video_feed/{source_id}"
        })
    else:
        return jsonify({"error": f"Failed to start feed: {source_id}"}), 500

@app.route('/api/live/stop', methods=['POST'])
def stop_live_feed():
    """Stop a live camera feed."""
    if not LIVE_STREAMING_ENABLED:
        return jsonify({"error": "Live streaming not available"}), 503
    
    data = request.get_json() or {}
    source_id = data.get('source_id', 'webcam')
    
    success = stream_manager.stop_feed(source_id)
    
    if success:
        return jsonify({"status": "stopped", "source_id": source_id})
    else:
        return jsonify({"error": f"Feed not found: {source_id}"}), 404

@app.route('/api/live/scores')
def get_live_scores():
    """Get current threat scores for all active feeds."""
    if not LIVE_STREAMING_ENABLED:
        return jsonify({"error": "Live streaming not available"}), 503
    
    return jsonify(stream_manager.get_scores())

@app.route('/api/live/status')
def get_live_status():
    """Get status of all feeds and available cameras."""
    if not LIVE_STREAMING_ENABLED:
        return jsonify({
            "enabled": False,
            "error": "Live streaming not available"
        }), 503
    
    return jsonify({
        "enabled": True,
        "active_feeds": list(stream_manager.feeds.keys()),
        "scores": stream_manager.get_scores(),
        "demo_cameras": DEMO_CAMERAS
    })

@app.route('/api/cameras')
def get_cameras():
    """Get list of available cameras (demo data for prototype)."""
    return jsonify({
        "cameras": DEMO_CAMERAS,
        "webcam_available": True
    })

# ------------------------------------------
# 4.2 ALERT API ROUTES
# ------------------------------------------
@app.route('/api/alerts/send-email', methods=['POST'])
def send_email_alert():
    """Send email alert to admin."""
    if not ALERTS_ENABLED:
        return jsonify({"error": "Alert system not available"}), 503
    
    data = request.get_json() or {}
    recipient = data.get('recipient_email')
    source_id = data.get('source_id', 'webcam')
    score = data.get('score', 0)
    camera_name = data.get('camera_name', 'Webcam')
    
    if not recipient:
        return jsonify({"error": "recipient_email is required"}), 400
    
    result = alert_manager.send_email_alert(recipient, source_id, score, camera_name)
    
    if result['success']:
        return jsonify({"status": "sent", "message": result['message']})
    else:
        return jsonify({"status": "failed", "error": result['error']}), 500

@app.route('/api/alerts/voice-text')
def get_voice_alert_text():
    """Get text for browser voice alert (TTS)."""
    if not ALERTS_ENABLED:
        return jsonify({"error": "Alert system not available"}), 503
    
    score = float(request.args.get('score', 0))
    camera_name = request.args.get('camera_name', 'camera')
    
    text = alert_manager.get_voice_alert_text(score, camera_name)
    
    return jsonify({
        "text": text,
        "should_alert": len(text) > 0,
        "score": score
    })

@app.route('/api/alerts/history')
def get_alert_history():
    """Get recent alert history."""
    if not ALERTS_ENABLED:
        return jsonify({"error": "Alert system not available"}), 503
    
    limit = int(request.args.get('limit', 50))
    history = alert_manager.get_alert_history(limit)
    
    return jsonify({
        "alerts": history,
        "count": len(history)
    })

@app.route('/api/alerts/config')
def get_alert_config():
    """Get alert configuration status."""
    return jsonify({
        "enabled": ALERTS_ENABLED,
        "email_configured": EMAIL_CONFIG.get('enabled', False) if ALERTS_ENABLED else False,
        "cooldown_seconds": alert_manager.cooldown_seconds if ALERTS_ENABLED else 30
    })


# ------------------------------------------
# 4.2 VIDEO UPLOAD ANALYSIS ROUTE
# ------------------------------------------
@app.route('/analyze', methods=['POST'])
def analyze():
    if 'video' not in request.files:
        return jsonify({"error": "No video uploaded"}), 400
    
    video_file = request.files['video']
    temp_filename = "temp_upload.mp4"
    video_file.save(temp_filename)
    
    try:
        # 1. Run AI Analysis
        results = process_video(temp_filename)
        
        has_anomaly = any(r['is_anomaly'] for r in results)
        status = "ANOMALY DETECTED" if has_anomaly else "SECURE"
        
        video_url = None

        # 2. If Anomaly -> Upload to Cloudinary
        if status == "ANOMALY DETECTED":
            print("Anomaly found! Uploading evidence to Cloud...")
            upload_response = cloudinary.uploader.upload(temp_filename, resource_type="video")
            video_url = upload_response['secure_url']
            print(f"Evidence Uploaded: {video_url}")

        # Cleanup
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            
        return jsonify({
            "status": status,
            "total_threats": len(results),
            "video_url": video_url, 
            "details": results
        })

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================================
# 5. SOCKET.IO EVENTS (Real-time control)
# ==========================================
if SOCKETIO_ENABLED:
    @socketio.on('connect')
    def handle_connect():
        print("🔌 Client connected via WebSocket")
        emit('connection_status', {'status': 'connected', 'live_enabled': LIVE_STREAMING_ENABLED})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        print("🔌 Client disconnected")
    
    @socketio.on('start_webcam')
    def handle_start_webcam():
        if LIVE_STREAMING_ENABLED:
            success = stream_manager.start_feed(0, 'webcam', 'Laptop Webcam')
            emit('webcam_status', {'status': 'started' if success else 'failed'})
    
    @socketio.on('stop_webcam')
    def handle_stop_webcam():
        if LIVE_STREAMING_ENABLED:
            stream_manager.stop_feed('webcam')
            emit('webcam_status', {'status': 'stopped'})
    
    @socketio.on('get_scores')
    def handle_get_scores():
        if LIVE_STREAMING_ENABLED:
            emit('scores_update', stream_manager.get_scores())

# ==========================================
# 6. SERVER STARTUP
# ==========================================
if __name__ == '__main__':
    print("\n" + "="*50)
    print("  ALERTRIX SERVER READY")
    print("="*50)
    print(f"  AI Model: {DEVICE.upper()} | FP16: {USE_FP16}")
    print(f"  Live Streaming: {'ENABLED' if LIVE_STREAMING_ENABLED else 'DISABLED'}")
    print(f"  API Endpoints:")
    print(f"    POST /analyze           - Video analysis")
    print(f"    GET  /video_feed/<id>   - MJPEG live stream")
    print(f"    POST /api/live/start    - Start camera feed")
    print(f"    POST /api/live/stop     - Stop camera feed")
    print(f"    GET  /api/live/scores   - Get threat scores")
    print(f"    GET  /api/live/status   - Get streaming status")
    print(f"    GET  /api/cameras       - List cameras")
    print(f"    POST /api/auth/login    - User login")
    print(f"    POST /api/auth/signup   - User signup")
    print(f"    GET  /api/admin/users   - List users (admin)")
    print("="*50 + "\n")
    
    # Use SocketIO if available, otherwise regular Flask
    if SOCKETIO_ENABLED:
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    else:
        app.run(host='0.0.0.0', port=5000, debug=True)