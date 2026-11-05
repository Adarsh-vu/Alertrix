# Alertrix – Autonomous Spatiotemporal Video Anomaly Detection System

An AI-powered video surveillance platform that combines deep learning, computer vision and real-time monitoring to identify potentially anomalous activities in CCTV footage.

## Overview

Traditional CCTV systems primarily record video footage, leaving security personnel responsible for continuously monitoring multiple camera feeds and identifying suspicious activities manually.

**Alertrix** aims to transform passive video surveillance into an intelligent monitoring system. It uses a fine-tuned VideoMAE transformer model to identify deviations from learned normal behaviour patterns in video streams. The system combines AI-based anomaly scoring with OpenCV motion analysis to provide contextual threat detection.

Alertrix supports both real-time camera monitoring and forensic analysis of previously recorded video footage through a web-based dashboard.

## Key Features

- **Real-Time Video Monitoring:** Monitor multiple camera feeds through a unified dashboard with continuously updated anomaly scores.
- **AI-Based Anomaly Detection:** Uses a fine-tuned VideoMAE transformer model and masked reconstruction loss to identify unusual spatiotemporal patterns.
- **Motion-Adaptive Scoring:** Combines AI inference with OpenCV-based motion detection and contour analysis to contextualize anomaly scores.
- **Forensic Video Analysis:** Process uploaded video footage through a dedicated analysis service and generate timeline-based anomaly information.
- **Automated Alerting:** Sends HTML-formatted email notifications through SMTP and provides browser-based text-to-speech alerts.
- **Automated Evidence Capture:** Captures video clips associated with critical anomaly events and uploads them to Cloudinary.
- **Incident Management:** Maintains camera configurations, personnel information and incident records using Firebase Firestore.
- **GPU Resource Management:** Uses on-demand model loading and unloading to manage GPU resources across the two backend services.

## System Architecture

Alertrix follows a decoupled architecture consisting of a React frontend, two Flask backend services, an AI inference engine and cloud services.

### Architecture Components

| Component | Responsibility |
|---|---|
| React + Vite Frontend | Monitoring dashboard, camera management, threat visualization and video analysis interface |
| Live Monitoring Service | Handles live camera streams, MJPEG streaming, inference and alert dispatching |
| Forensic Analysis Service | Processes uploaded video footage and manages GPU resources during analysis |
| VideoMAE AI Engine | Performs masked video reconstruction and generates anomaly scores |
| OpenCV | Handles frame processing, motion detection and contour analysis |
| Firebase | Authentication and persistent application data |
| Cloudinary | Cloud storage and H.264 transcoding of captured anomaly clips |

### Backend Services

**Live Monitoring Service – Port 5000**

Responsible for:
- Live camera feed processing.
- MJPEG video streaming.
- Real-time AI inference.
- Camera and user management.
- Alert dispatching.

**Forensic Analysis Service – Port 5001**

Responsible for:
- Uploaded video processing.
- Video anomaly analysis.
- Timeline-based analysis results.
- GPU resource management.

## AI Detection Approach

Alertrix uses **VideoMAE (Video Masked Autoencoder)**, a transformer-based video representation learning model.

The system uses a self-supervised masked reconstruction approach:

1. A video is divided into clips containing 16 frames.
2. Approximately 90% of the spatiotemporal patches are masked.
3. The model attempts to reconstruct the masked portions of the video.
4. Reconstruction loss is used as the anomaly score.
5. Higher reconstruction loss indicates a greater deviation from learned normal patterns.

The model was fine-tuned for 40 epochs using surveillance footage.

### Motion-Adaptive Scoring

To provide additional context to AI-generated anomaly scores, Alertrix integrates OpenCV-based motion analysis.

Background subtraction and contour analysis are used to estimate physical motion within a scene. This information is incorporated into the anomaly scoring process to suppress false positives in static scenes and increase sensitivity to significant motion.

## Alert and Evidence Workflow

When an anomaly score exceeds the configured threshold, the system follows an alert and evidence-capture workflow:

1. Check the anomaly score against the configured threshold.
2. Verify the alert cooldown to prevent repeated notifications.
3. Classify the threat level.
4. Dispatch an HTML-formatted email notification.
5. Generate a browser-based voice announcement.
6. Capture the relevant video clip and upload it to Cloudinary.

A 30-second cooldown mechanism is used to reduce repeated alerts during sustained anomaly events.

## Technology Stack

| Category | Technologies |
|---|---|
| Frontend | React.js, Vite |
| Backend | Python, Flask |
| Deep Learning | PyTorch, Hugging Face Transformers |
| AI Model | VideoMAE |
| Computer Vision | OpenCV |
| Database | Firebase Firestore |
| Authentication | Firebase Authentication |
| Cloud Storage | Cloudinary |
| Streaming | MJPEG, Socket.IO |
| Notifications | SMTP, Web Speech API |
| Video Processing | H.264 transcoding |

## Performance

The project report records the following experimental performance figures:

- **Inference latency:** Below 55 ms per inference with FP16 GPU optimization.
- **Live streaming performance:** 30 FPS.

These are reported experimental results and may vary depending on hardware, video input and deployment configuration.

## Repository Structure

The repository contains the frontend, backend services and shared application components.

```text
Alertrix/
├── .agent/
├── backend/
├── backend_forensic/
├── backend_live/
├── common/
├── frontend/
├── data_prep.py
└── .gitignore
```

## Running the Project

Alertrix requires separate frontend and backend configuration.

The general setup involves:

1. Installing the required Python dependencies for the backend services.
2. Installing frontend dependencies using the Node.js package manager.
3. Configuring Firebase Authentication and Firestore.
4. Configuring Cloudinary and SMTP credentials.
5. Providing the required fine-tuned VideoMAE model weights.
6. Configuring a CUDA-compatible NVIDIA GPU for the intended GPU-accelerated inference workflow.
7. Starting the live monitoring service, forensic analysis service and frontend.

**Important:** The repository's `.gitignore` excludes model-weight files such as `.pth` and `.pt`, datasets and some local resources. These assets are not necessarily included in the GitHub repository. The original model weights and external service credentials must be supplied separately. Exact installation commands and configuration values should be verified against the available source files before attempting deployment.

## Project Scope and Limitations

Alertrix focuses on anomaly detection in fixed-camera surveillance environments.

The current project scope does not include:

- Facial recognition.
- Real-time individual identity recognition.
- General-purpose object identification.
- Legal compliance auditing.

The system is intended to assist security personnel with anomaly identification and monitoring, rather than replace human investigation or decision-making.

## Future Scope

Potential improvements identified for the project include:

- Edge-device deployment.
- Further optimization of inference performance.
- Expansion of surveillance scenarios and anomaly detection capabilities.

## Author

**Adarsh V U**

MCA Project – Department of Computer Applications  
Rajiv Gandhi Institute of Technology, Kottayam

## License

No license has been specified for this repository. Please contact the repository owner regarding reuse or distribution.
