import sys
import os

# Add parent directory to path to import from common
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import math
import cv2
import torch
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import time

from common.model_utils import load_video_mae_model, generate_mask
from common.config import UPLOAD_THRESHOLD

# App Setup
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


# Model Setup
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
USE_FP16 = DEVICE == "cuda"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "../backend/alertrix_final_epoch40.pth")

print(f"FORENSIC SERVICE: Initializing on {DEVICE}...")

if DEVICE != "cuda":
    print("WARNING: GPU not available! Forensic analysis will be slow.")
else:
    print("FORENSIC SERVICE: GPU Detected & Locked.")

# Load Model (Global for Speed)
model = None
processor = None
try:
    print(f"Loading AI Model on {DEVICE}...")
    model, processor = load_video_mae_model(MODEL_PATH, DEVICE, USE_FP16)
except Exception as e:
    print(f"Warning: Failed to load global model (will retry on request): {e}")

# Analysis Logic
def process_video_forensic(video_path):
    global model, processor
    if model is None:
        print(f"Reloading AI Model for Analysis on {DEVICE}...")
        try:
            model, processor = load_video_mae_model(MODEL_PATH, DEVICE, USE_FP16)
        except Exception as e:
            print(f"Failed to load model: {e}")
            return []
    
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0: fps = 30.0
    
    frame_buffer = []
    anomalies = []
    current_frame = 0
    FRAME_SKIP = 3
    
    print(f"Processing video: {video_path}...")

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            current_frame += 1
            
            # Skip frames
            if current_frame % FRAME_SKIP != 0:
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)
            frame_buffer.append(pil_img)

            # Batch Inference (VideoMAE uses 16 frames)
            if len(frame_buffer) == 16:
                inputs = processor(list(frame_buffer), return_tensors="pt").pixel_values.to(DEVICE)
                if USE_FP16:
                    inputs = inputs.half()
                
                mask = generate_mask(1, 1568, 0.75, device=DEVICE)

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

                # Rolling Buffer: Keep last 8 frames for overlap
                frame_buffer = frame_buffer[8:]

    finally:
        cap.release()

    return anomalies

@app.route('/health')
def health_check():
    return jsonify({"status": "online", "service": "forensic", "gpu": DEVICE})

@app.route('/api/release', methods=['POST'])
def release_resources():
    """Unload model to free GPU for Live Service."""
    global model, processor
    try:
        if model is not None:
            print("Releasing forensic model resources...")
            del model
            del processor
            model = None
            processor = None
            torch.cuda.empty_cache()
            gc.collect()
            print("Model unloaded.")
        return jsonify({"status": "released"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reload', methods=['POST'])
def reload_resources():
    """Reload model if it was unloaded."""
    global model, processor
    try:
        if model is None:
            print("Reloading forensic model...")
            model, processor = load_video_mae_model(MODEL_PATH, DEVICE, USE_FP16)
        return jsonify({"status": "loaded"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'video' not in request.files:
        return jsonify({"error": "No video uploaded"}), 400
    
    video_file = request.files['video']
    temp_filename = "temp_forensic_upload.mp4"
    video_file.save(temp_filename)
    
    start_time = time.time()
    try:
        # 1. Run Analysis
        print("Starting Forensic Analysis...")
        inference_start = time.time()
        results = process_video_forensic(temp_filename)
        inference_time = time.time() - inference_start
        
        has_anomaly = any(r['is_anomaly'] for r in results)
        status = "ANOMALY DETECTED" if has_anomaly else "SECURE"
        
        # Cloudinary Upload REMOVED
        video_url = None 

        total_time = time.time() - start_time
        print(f"[TIMING] Inference: {inference_time:.2f}s | Total: {total_time:.2f}s")
        
        # Cleanup
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            
        return jsonify({
            "service": "forensic",
            "status": status,
            "total_threats": len(results),
            "video_url": video_url, 
            "details": results,
            "processing_time": f"{total_time:.2f}s"
        })

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("FORENSIC SERVICE STARTING ON PORT 5001")
    app.run(host='0.0.0.0', port=5001, debug=True)
