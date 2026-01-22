import cv2
import os
import glob
import numpy as np
from pathlib import Path

# CONSTANTS
SRC_DIR = "./DataCore/Vdwnlds"
TRAIN_DIR = "./DataCore/TrainSet"
TEST_DIR = "./DataCore/TestSet"
IMG_SIZE = 224
CLIP_LEN = 16

# Keywords for auto-classification
TRAIN_KEYWORDS = ["training_videos", "train", "normal"]
TEST_KEYWORDS = ["testing_videos", "test", "anomaly", "fight", "robbery", "crime"]

def save_clip(frames, video_name, clip_count, output_folder):
    clip_name = f"{video_name}_clip_{clip_count:03d}"
    clip_path = os.path.join(output_folder, clip_name)
    os.makedirs(clip_path, exist_ok=True)
    for i, frame in enumerate(frames):
        cv2.imwrite(os.path.join(clip_path, f"{i:03d}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

def process_video_file(video_path, output_folder):
    """Handles .mp4 and .avi files (Avenue/UCF)"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened(): return 0
    video_name = Path(video_path).stem
    frames, clip_count = [], 0
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        try:
            frame = cv2.resize(frame, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frames.append(gray)
        except: continue

        if len(frames) == CLIP_LEN:
            save_clip(frames, video_name, clip_count, output_folder)
            clip_count += 1
            frames = []
    cap.release()
    return clip_count

def process_image_sequence(folder_path, output_folder):
    """Handles image folders (UCSD)"""
    images = sorted(glob.glob(os.path.join(folder_path, "*.*")))
    images = [x for x in images if x.lower().endswith(('.tif', '.jpg', '.png'))]
    if not images: return 0
    
    folder_name = os.path.basename(folder_path)
    frames, clip_count = [], 0
    for img_path in images:
        frame = cv2.imread(img_path)
        if frame is None: continue
        frame = cv2.resize(frame, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frames.append(gray)
        
        if len(frames) == CLIP_LEN:
            save_clip(frames, folder_name, clip_count, output_folder)
            clip_count += 1
            frames = []
    return clip_count

def classify_path(path):
    p = path.lower().replace('\\', '/')
    if any(k in p for k in TRAIN_KEYWORDS): return 'train'
    if any(k in p for k in TEST_KEYWORDS): return 'test'
    return 'unknown'

if __name__ == "__main__":
    print("Starting Data Prep...")
    total_clips = 0
    
    # 1. SCAN VIDEOS
    print("...Scanning Video Files (UCF/Avenue)...")
    videos = glob.glob(f"{SRC_DIR}/**/*.mp4", recursive=True) + glob.glob(f"{SRC_DIR}/**/*.avi", recursive=True)
    for v in videos:
        cat = classify_path(v)
        if cat != 'unknown':
            dest = TRAIN_DIR if cat == 'train' else TEST_DIR
            total_clips += process_video_file(v, dest)
            print(f"Processed: {os.path.basename(v)} -> {cat}")

    # 2. SCAN IMAGE FOLDERS
    print("...Scanning Image Folders (UCSD)...")
    folders = glob.glob(f"{SRC_DIR}/**/Train/*", recursive=True) + glob.glob(f"{SRC_DIR}/**/Test/*", recursive=True)
    for f in folders:
        if os.path.isdir(f):
            cat = classify_path(f)
            if cat != 'unknown':
                dest = TRAIN_DIR if cat == 'train' else TEST_DIR
                total_clips += process_image_sequence(f, dest)
                print(f"Processed: {os.path.basename(f)} -> {cat}")

    print(f"\n DONE! Total Clips Generated: {total_clips}")