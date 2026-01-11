"""
Alertrix Backend - FastAPI Application
Spatiotemporal Anomaly Detection System
"""

import asyncio
import random
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

app = FastAPI(
    title="Alertrix API",
    description="Spatiotemporal Anomaly Detection System Backend",
    version="1.0.0"
)

# CORS Configuration - Allow frontend on localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store for uploaded videos
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "online", "message": "Alertrix API is running"}


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time anomaly score streaming.
    Sends a random anomaly_score (0.0-1.0) every 100ms for testing.
    """
    await websocket.accept()
    try:
        while True:
            # Generate dummy anomaly score for testing
            anomaly_data = {
                "anomaly_score": round(random.uniform(0.0, 1.0), 4),
                "timestamp": asyncio.get_event_loop().time(),
                "status": "monitoring"
            }
            await websocket.send_json(anomaly_data)
            await asyncio.sleep(0.1)  # 100ms interval
    except WebSocketDisconnect:
        print("Client disconnected from WebSocket")
    except Exception as e:
        print(f"WebSocket error: {e}")


@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """
    POST endpoint to accept video file uploads.
    Saves the uploaded video to the uploads directory.
    """
    try:
        # Validate file type
        allowed_extensions = [".mp4", ".avi", ".mov", ".mkv", ".webm"]
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid file type. Allowed: {allowed_extensions}"}
            )
        
        # Save file
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        return {
            "message": "Video uploaded successfully",
            "filename": file.filename,
            "path": file_path,
            "size": len(content)
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
