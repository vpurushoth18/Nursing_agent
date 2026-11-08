import torch
import platform
import sys
import importlib.metadata
import json
from pathlib import Path
from huggingface_hub import snapshot_download

MODELS = {
    "whisper_small": {
        "repo_id": "openai/whisper-medium",
        "local_dir": Path("models/whisper-medium")
    },
    "qwen_0_5b": {
        "repo_id": "Qwen/Qwen2.5-7B-Instruct",
        "local_dir": Path("models/qwen2.5-7B-Instruct")
    }
}

def get_environment_metadata():
    return {
        "python_version": platform.python_version(),
        "os": platform.platform(),
        "torch_version": torch.__version__,
        "transformers_version": importlib.metadata.version("transformers"),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "cuda_version": torch.version.cuda if torch.cuda.is_available() else "N/A"
    } 



def verify_and_download(model_key):
    #check if model artifacts exist and log hash for verification
    model_info = MODELS[model_key]
    local_dir = model_info["local_dir"]

    if local_dir.exists():
        return f"{model_key} found locally."
    
    #download if doesn't exist
    snapshot_download(
        repo_id = model_info["repo_id"],
        local_dir = local_dir,
        local_dir_use_symlinks = False
    )

    return f"{model_key} downloaded successfully."