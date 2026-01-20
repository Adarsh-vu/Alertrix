import os
import cv2
import torch
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
from transformers import VideoMAEForPreTraining, VideoMAEImageProcessor
import cloudinary
import cloudinary.uploader

# ==========================================
# 1. CONFIGURATION
# ==========================================
app = Flask(__name__)
CORS(app)

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
DEVICE = "cpu"
THRESHOLD = 0.39

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
    processor = VideoMAEImageProcessor.from_pretrained(MODEL_TYPE)
    print("SUCCESS: Model Loaded! Server is ready.")
except Exception as e:
    print(f"ERROR: {e}")
    print("HINT: Is the .pth file inside the backend folder?")
    exit()

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
    current_frame = 0
    
    print(f"Processing video for anomalies...")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)
        frame_buffer.append(pil_img)

        if len(frame_buffer) == 16:
            inputs = processor(list(frame_buffer), return_tensors="pt").pixel_values.to(DEVICE)
            mask = generate_mask(1, 1568, 0.75) 

            with torch.no_grad():
                outputs = model(inputs, bool_masked_pos=mask)
                loss = outputs.loss.item()
            
            if loss > THRESHOLD:
                timestamp = current_frame / fps
                anomalies.append({
                    "time": round(timestamp, 2),
                    "score": round(loss, 4),
                    "status": "Anomaly Detected"
                })

            frame_buffer = frame_buffer[8:] # Stride

        current_frame += 1
    
    cap.release()
    return anomalies

# ==========================================
# 4. API ROUTES
# ==========================================
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
        status = "ANOMALY DETECTED" if len(results) > 0 else "CLEAR"
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)