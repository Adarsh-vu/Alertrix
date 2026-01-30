import torch
import math
import os
from transformers import VideoMAEForPreTraining, VideoMAEImageProcessor

# Constants
MODEL_TYPE = "MCG-NJU/videomae-base"

def load_video_mae_model(model_path, device, use_fp16=False):
    """
    Load the VideoMAE model from checkpoint.
    """
    print(f"Loading AI Model from {model_path}...")
    try:
        model = VideoMAEForPreTraining.from_pretrained(MODEL_TYPE)
        checkpoint = torch.load(model_path, map_location=torch.device(device))
        
        if 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
        else:
            model.load_state_dict(checkpoint)
            
        model.to(device)
        model.eval()
        
        if use_fp16 and device == 'cuda':
            model.half()
            
        processor = VideoMAEImageProcessor.from_pretrained(MODEL_TYPE)
        print(f"SUCCESS: Model Loaded on {device.upper()}! FP16={use_fp16}")
        return model, processor
    except Exception as e:
        print(f"ERROR Loading Model: {e}")
        raise e

def generate_mask(batch_size, seq_length, ratio=0.75, device='cpu'):
    """
    Generate boolean mask for VideoMAE.
    """
    num_masked = int(seq_length * ratio)
    mask = torch.hstack([
        torch.ones(batch_size, num_masked), 
        torch.zeros(batch_size, seq_length - num_masked)
    ])
    ids_shuffle = torch.argsort(torch.rand(batch_size, seq_length), dim=1)
    return torch.gather(mask, dim=1, index=ids_shuffle).bool().to(device)
