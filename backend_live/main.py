import sys
import os

# Add parent directory to path to import from common
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import torch
from flask import Flask, request, jsonify, Response
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
