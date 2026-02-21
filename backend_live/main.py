import sys
import os
import math
import time
import random

# Add parent directory to path to import from common
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import torch
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
import cloudinary

from common.model_utils import load_video_mae_model
from common.config import CLOUDINARY_CONFIG, LIVE_THRESHOLD

# App Setup
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.config['SECRET_KEY'] = 'alertrix-secret-key-change-in-production'

# Cloudinary Setup
cloudinary.config(**CLOUDINARY_CONFIG)

# Socket.IO
try:
    from flask_socketio import SocketIO, emit
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
    SOCKETIO_ENABLED = True
    print("Live Service: SocketIO enabled")
except ImportError:
    socketio = None
    SOCKETIO_ENABLED = False
    print("Live Service: socketio missing")

# Database (Firebase)
from models import init_firebase
if init_firebase():
    print("Live Service: Firebase Connected")
else:
    print("Live Service: Firebase connection failed")

# Blueprints
from auth import auth_bp
from admin import admin_bp
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)

# Model Setup
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
USE_FP16 = DEVICE == "cuda"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "../backend/alertrix_final_epoch40.pth")

print(f"LIVE SERVICE: Initializing on {DEVICE}...")

# Stream Manager
try:
    from live_manager import StreamManager, DEMO_CAMERAS
    # Pass MODEL_PATH instead of loaded model
    stream_manager = StreamManager(MODEL_PATH, DEVICE, USE_FP16, LIVE_THRESHOLD)
    LIVE_STREAMING_ENABLED = True
    print(f"Live Manager Active (Threshold: {LIVE_THRESHOLD})")
except Exception as e:
    stream_manager = None
    LIVE_STREAMING_ENABLED = False
    print(f"Live Manager Failed: {e}")

# Alert System
try:
    from alerts import get_alert_manager
    alert_manager = get_alert_manager()
    ALERTS_ENABLED = True
except Exception as e:
    alert_manager = None
    ALERTS_ENABLED = False

# API Routes
@app.route('/health')
def health():
    return jsonify({"status": "online", "service": "live", "gpu": DEVICE})

@app.route('/api/alerts/send-email', methods=['POST'])
def send_email_alert():
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

@app.route('/video_feed/<source_id>')
def video_feed(source_id):
    if not LIVE_STREAMING_ENABLED or not stream_manager.is_feed_active(source_id):
        return jsonify({"error": "Feed unavailable"}), 404
    return Response(stream_manager.get_frame_generator(source_id), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/live/start', methods=['POST'])
def start_live_feed():
    if not LIVE_STREAMING_ENABLED: return jsonify({"error": "Service unavailable"}), 503
    data = request.get_json() or {}
    source = data.get('source', 0)
    if str(source) == "0": source = 0
    
    success = stream_manager.start_feed(source, data.get('source_id', 'webcam'), data.get('name', 'Webcam'))
    return jsonify({"status": "started"} if success else {"error": "Failed"}), 200 if success else 500

@app.route('/api/live/stop', methods=['POST'])
def stop_live_feed():
    if not LIVE_STREAMING_ENABLED: return jsonify({"error": "Service unavailable"}), 503
    source_id = request.json.get('source_id', 'webcam')
    stream_manager.stop_feed(source_id)
    return jsonify({"status": "stopped"})

@app.route('/api/live/scores')
def get_live_scores():
    if not LIVE_STREAMING_ENABLED: return jsonify({})
    return jsonify(stream_manager.get_scores())

@app.route('/api/live/status')
def get_live_status():
    if not LIVE_STREAMING_ENABLED: return jsonify({"enabled": False})
    return jsonify({
        "enabled": True,
        "active_feeds": list(stream_manager.feeds.keys()),
        "scores": stream_manager.get_scores(),
        "demo_cameras": DEMO_CAMERAS
    })

# ------------------------------------------
# DASH CAM ROUTES
# ------------------------------------------
DASHCAM_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Dash Cam")
print(f"Dash Cam folder: {DASHCAM_FOLDER} (exists: {os.path.exists(DASHCAM_FOLDER)})")

DASHCAM_VIDEOS = {
    "cam_entrance": {"file": "entrance.mp4", "name": "CAM-01 ENTRANCE", "location": "Main Entrance"},
    "cam_parking": {"file": "parking.mp4", "name": "CAM-02 PARKING", "location": "Parking Lot A"},
    "cam_hallway": {"file": "Hallway.mov", "name": "CAM-03 HALLWAY", "location": "Main Hallway"},
    "cam_exit": {"file": "exit.mp4", "name": "CAM-04 EXIT", "location": "Emergency Exit"},
}

@app.route('/api/dashcam/list')
def dashcam_list():
    """Return list of available dash cam feeds."""
    cameras = []
    for cam_id, info in DASHCAM_VIDEOS.items():
        filepath = os.path.join(DASHCAM_FOLDER, info['file'])
        cameras.append({
            "id": cam_id,
            "name": info['name'],
            "location": info['location'],
            "filename": info['file'],
            "available": os.path.exists(filepath)
        })
    return jsonify({"cameras": cameras})

@app.route('/api/dashcam/video/<filename>')
def dashcam_video(filename):
    """Serve dash cam video files with range request support."""
    filepath = os.path.join(DASHCAM_FOLDER, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "Video not found"}), 404
    
    # Determine MIME type
    mime = 'video/mp4'
    if filename.lower().endswith('.mov'):
        mime = 'video/quicktime'
    elif filename.lower().endswith('.avi'):
        mime = 'video/x-msvideo'
    
    file_size = os.path.getsize(filepath)
    
    # Handle range requests for smooth video streaming
    range_header = request.headers.get('Range')
    if range_header:
        byte_start = 0
        byte_end = file_size - 1
        
        range_match = range_header.replace('bytes=', '').split('-')
        byte_start = int(range_match[0])
        if range_match[1]:
            byte_end = int(range_match[1])
        
        content_length = byte_end - byte_start + 1
        
        def generate_range():
            with open(filepath, 'rb') as f:
                f.seek(byte_start)
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(8192, remaining)
                    data = f.read(chunk_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data
        
        response = Response(
            generate_range(),
            status=206,
            mimetype=mime,
            direct_passthrough=True
        )
        response.headers['Content-Range'] = f'bytes {byte_start}-{byte_end}/{file_size}'
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Content-Length'] = content_length
        return response
    
    return send_from_directory(DASHCAM_FOLDER, filename, mimetype=mime)

@app.route('/api/dashcam/scores')
def dashcam_scores():
    """Return simulated anomaly scores (35-55%) for dash cam feeds."""
    scores = {}
    current_time = time.time()
    for cam_id in DASHCAM_VIDEOS:
        seed = hash(cam_id) % 1000
        base = 0.45
        variation = 0.10 * math.sin(current_time * 0.3 + seed)
        jitter = random.uniform(-0.03, 0.03)
        score = max(0.35, min(0.55, base + variation + jitter))
        
        if score > 0.50:
            status = "ELEVATED"
        elif score > 0.42:
            status = "MONITORING"
        else:
            status = "NORMAL"
        
        scores[cam_id] = {
            "score": round(score, 4),
            "status": status,
            "timestamp": current_time
        }
    return jsonify(scores)

# Socket IO
if SOCKETIO_ENABLED:
    @socketio.on('connect')
    def on_connect():
        emit('connection_status', {'status': 'connected', 'service': 'live'})

    @socketio.on('start_webcam')
    def on_start_webcam():
        if LIVE_STREAMING_ENABLED:
            success = stream_manager.start_feed(0, 'webcam', 'Webcam')
            emit('webcam_status', {'status': 'started' if success else 'failed'})

    @socketio.on('stop_webcam')
    def on_stop_webcam():
        if LIVE_STREAMING_ENABLED:
            stream_manager.stop_feed('webcam')
            emit('webcam_status', {'status': 'stopped'})

if __name__ == '__main__':
    print("LIVE SERVICE STARTING ON PORT 5000")
    if SOCKETIO_ENABLED:
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    else:
        app.run(host='0.0.0.0', port=5000, debug=True)
