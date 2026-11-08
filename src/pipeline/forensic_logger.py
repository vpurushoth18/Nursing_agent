import hashlib
import os
import sys
import torch
import platform
import json
import importlib.metadata
from pathlib import Path
from datetime import datetime

CACHE_FILE = "model_hash_cache.json"

def sha256_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

def sha256_file(path):
    hash_function = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_function.update(chunk)
    return hash_function.hexdigest()

def sha256_model(model_dir):
    """Calculates hash of a model dir, using a cache to avoid 10-minute IO bottlenecks."""
    model_dir = Path(model_dir)
    dir_str = str(model_dir)
    
    # 1. Load the cache if it exists
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
        except json.JSONDecodeError:
            pass 
            
    #check if hashed
    if dir_str in cache:
        return cache[dir_str]
        
    #calculate hash
    hashes = {}
    for p in sorted(model_dir.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(model_dir))
            try:
                hashes[rel] = sha256_file(p)
            except Exception as e:
                hashes[rel] = f"ERROR:{repr(e)}"
                
    #save result to cache
    cache[dir_str] = hashes
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=4)
        
    return hashes

def get_system_info():
    return {
        "python_version": platform.python_version(),
        "os": platform.platform(),
        "torch_version": torch.__version__,
        "transformers_version": importlib.metadata.version("transformers"),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "cuda_version": torch.version.cuda if torch.cuda.is_available() else "N/A"
    }

def create_forensic_artifact(model_path, prompt, output, transcript):
    return {
        "metadata": get_system_info(),
        "hashes": {
            "model_artifacts": sha256_model(model_path),
            "prompt": sha256_text(prompt),
            "output": sha256_text(output),
            "transcript": sha256_text(transcript)
        },
        "deterministic_settings": {
            "fp_precision": "FP32",
            "greedy_decoding": True,
            "seed": 42
        }
    }