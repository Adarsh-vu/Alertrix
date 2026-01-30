import os

# Cloudinary Configuration
CLOUDINARY_CONFIG = {
    'cloud_name': "dz23mrxfb",
    'api_key': "456783583454585",
    'api_secret': "kh2TWcD3kFUSefGKgeUAoU85OAs",
    'secure': True
}

# Thresholds
UPLOAD_THRESHOLD = 0.44
LIVE_THRESHOLD = 0.50  # Lowered to 0.50 to catch more threats (fist, etc)

# Paths
# Assumes we are running from backend_live or backend_forensic, so model is in sibling "backend"
MODEL_FILENAME = "alertrix_final_epoch40.pth"
# We'll calculate absolute path dynamically in the apps
