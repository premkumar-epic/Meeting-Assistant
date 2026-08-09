from __future__ import annotations

import os
import urllib.request
from pathlib import Path
from typing import Any
import torch

from app.utils.system_specs import get_system_specs
from app.services.config_manager import get_model_config, save_model_config

# Global tracker for active downloads
_DOWNLOAD_JOBS: dict[str, dict[str, Any]] = {}

# Constants for Whisper download URLs
WHISPER_URLS = {
    "tiny": "https://openaipublic.azureedge.net/main/whisper/models/651470b05b866e49711653f2b1d7d540994d66531d819f84d650013d28334301/tiny.pt",
    "base": "https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b240efebe5d0972e66a397dbd66a0dc21e6cd145c33e22124728838b7/base.pt",
    "small": "https://openaipublic.azureedge.net/main/whisper/models/9ecf77965fb9b9355f1e565fd2008103859d61413d29d81ebd235914616fd28d/small.pt"
}


def is_hf_model_cached(model_id: str) -> bool:
    """Check if a Hugging Face model repo is cached locally in ~/.cache/huggingface/hub/."""
    hf_cache_dir = Path(os.path.expanduser("~/.cache/huggingface/hub"))
    formatted_id = f"models--{model_id.replace('/', '--')}"
    model_dir = hf_cache_dir / formatted_id
    if not model_dir.exists():
        return False
    snapshots_dir = model_dir / "snapshots"
    if not snapshots_dir.exists():
        return False
    # Check if any snapshot directory has downloaded files
    try:
        for snapshot in snapshots_dir.iterdir():
            if snapshot.is_dir() and any(snapshot.iterdir()):
                return True
    except Exception:
        pass
    return False


def is_whisper_model_cached(model_name: str) -> bool:
    """Check if a standard OpenAI Whisper model file exists locally in ~/.cache/whisper/."""
    whisper_dir = Path(os.getenv("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))) / "whisper"
    model_file = whisper_dir / f"{model_name}.pt"
    return model_file.exists()


def get_all_models_status() -> dict[str, Any]:
    """Retrieve system specs and supported models listing with caching/recommendation status."""
    specs = get_system_specs()
    config = get_model_config()
    tier = specs["recommendation_tier"]
    
    # 1. ASR Models
    asr_models = [
        {
            "id": "tiny",
            "name": "Whisper Tiny (Fastest)",
            "size": "75 MB",
            "tier": "low",
            "description": "Lowest RAM usage, fastest processing speed on old CPUs.",
            "recommended": tier == "low",
            "cached": is_whisper_model_cached("tiny") or is_hf_model_cached("Systran/faster-whisper-tiny"),
            "active": config["asr_model"] == "tiny"
        },
        {
            "id": "base",
            "name": "Whisper Base (Balanced)",
            "size": "140 MB",
            "tier": "medium",
            "description": "Good balance of speed and accuracy. Default choice.",
            "recommended": tier == "medium",
            "cached": is_whisper_model_cached("base") or is_hf_model_cached("Systran/faster-whisper-base"),
            "active": config["asr_model"] == "base"
        },
        {
            "id": "small",
            "name": "Whisper Small (High Precision)",
            "size": "460 MB",
            "tier": "high",
            "description": "Higher transcription accuracy, but runs slower on standard CPUs.",
            "recommended": tier == "high",
            "cached": is_whisper_model_cached("small") or is_hf_model_cached("Systran/faster-whisper-small"),
            "active": config["asr_model"] == "small"
        }
    ]
    
    # 2. Summarizer Models
    summarizer_models = [
        {
            "id": "sshleifer/distilbart-cnn-12-6",
            "name": "DistilBART (Default)",
            "size": "1.1 GB",
            "tier": "low",
            "description": "Distilled BART model, fast CPU execution with excellent summary coverage.",
            "recommended": tier in ("low", "medium"),
            "cached": is_hf_model_cached("sshleifer/distilbart-cnn-12-6"),
            "active": config["summarizer_model"] == "sshleifer/distilbart-cnn-12-6"
        },
        {
            "id": "facebook/bart-large-cnn",
            "name": "BART Large (Detailed)",
            "size": "1.6 GB",
            "tier": "high",
            "description": "Larger model generating high-fidelity abstractive summaries. Needs more RAM.",
            "recommended": tier == "high",
            "cached": is_hf_model_cached("facebook/bart-large-cnn"),
            "active": config["summarizer_model"] == "facebook/bart-large-cnn"
        }
    ]
    
    # 3. Q&A LLM Models
    llm_models = [
        {
            "id": "Qwen/Qwen2.5-0.5B-Instruct",
            "name": "Qwen 2.5 0.5B (Fastest)",
            "size": "950 MB",
            "tier": "low",
            "description": "Ultra-lightweight state-of-the-art instruct model. Fast CPU chat.",
            "recommended": tier == "low",
            "cached": is_hf_model_cached("Qwen/Qwen2.5-0.5B-Instruct"),
            "active": config["llm_model"] == "Qwen/Qwen2.5-0.5B-Instruct"
        },
        {
            "id": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            "name": "TinyLlama 1.1B (Balanced)",
            "size": "2.2 GB",
            "tier": "medium",
            "description": "Small Llama-based chat model. Good conversation structure.",
            "recommended": tier == "medium",
            "cached": is_hf_model_cached("TinyLlama/TinyLlama-1.1B-Chat-v1.0"),
            "active": config["llm_model"] == "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        },
        {
            "id": "Qwen/Qwen2.5-1.5B-Instruct",
            "name": "Qwen 2.5 1.5B (Deep Reasoning)",
            "size": "3.0 GB",
            "tier": "high",
            "description": "Highly accurate question answering model. Slower on low-spec CPUs.",
            "recommended": tier == "high",
            "cached": is_hf_model_cached("Qwen/Qwen2.5-1.5B-Instruct"),
            "active": config["llm_model"] == "Qwen/Qwen2.5-1.5B-Instruct"
        }
    ]
    
    return {
        "specs": specs,
        "active_config": config,
        "asr": asr_models,
        "summarizer": summarizer_models,
        "llm": llm_models
    }


def download_model_background(model_type: str, model_id: str) -> None:
    """Download model weights in background and record live status/progress percentages."""
    try:
        _DOWNLOAD_JOBS[model_id] = {"status": "Starting download...", "progress": 5}
        
        if model_type == "asr":
            # For faster-whisper provider, pre-cache HF model weights
            # Systran maps 'tiny' to 'Systran/faster-whisper-tiny'
            hf_repo = f"Systran/faster-whisper-{model_id}"
            
            _DOWNLOAD_JOBS[model_id].update({"status": "Downloading tokenizer config...", "progress": 15})
            from transformers import AutoTokenizer
            AutoTokenizer.from_pretrained(hf_repo)
            
            _DOWNLOAD_JOBS[model_id].update({"status": "Downloading model tensors...", "progress": 40})
            from huggingface_hub import snapshot_download
            snapshot_download(repo_id=hf_repo)
            
            # Also download standard OpenAI Whisper model as fallback compatibility
            if model_id in WHISPER_URLS:
                _DOWNLOAD_JOBS[model_id].update({"status": "Downloading OpenAI Whisper weights...", "progress": 75})
                # Download using urllib urlretrieve with custom reporthook
                whisper_dir = Path(os.path.expanduser("~/.cache/whisper"))
                whisper_dir.mkdir(parents=True, exist_ok=True)
                dest = whisper_dir / f"{model_id}.pt"
                
                url = WHISPER_URLS[model_id]
                
                def reporthook(block_num, block_size, total_size):
                    downloaded = block_num * block_size
                    if total_size > 0:
                        pct = 75 + int(20 * downloaded / total_size)
                        _DOWNLOAD_JOBS[model_id].update({
                            "status": f"Downloading OpenAI Whisper weights ({int(downloaded/(1024*1024))}MB/{int(total_size/(1024*1024))}MB)...",
                            "progress": min(pct, 95)
                        })
                
                urllib.request.urlretrieve(url, str(dest), reporthook)
                
        elif model_type == "summarizer":
            _DOWNLOAD_JOBS[model_id].update({"status": "Downloading tokenizer configuration...", "progress": 15})
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            AutoTokenizer.from_pretrained(model_id)
            
            _DOWNLOAD_JOBS[model_id].update({"status": "Downloading model weights...", "progress": 40})
            AutoModelForSeq2SeqLM.from_pretrained(model_id)
            
        elif model_type == "llm":
            _DOWNLOAD_JOBS[model_id].update({"status": "Downloading tokenizer configuration...", "progress": 15})
            from transformers import AutoTokenizer, AutoModelForCausalLM
            AutoTokenizer.from_pretrained(model_id)
            
            _DOWNLOAD_JOBS[model_id].update({"status": "Downloading instruct weights...", "progress": 45})
            AutoModelForCausalLM.from_pretrained(model_id)
            
        _DOWNLOAD_JOBS[model_id].update({"status": "completed", "progress": 100})
        print(f"[INFO] Model download completed: {model_id}", flush=True)
        
    except Exception as e:
        print(f"[ERROR] Model download failed for {model_id}: {e}", flush=True)
        _DOWNLOAD_JOBS[model_id].update({"status": "failed", "progress": 0, "error": str(e)})


def get_download_status(model_id: str) -> dict[str, Any]:
    """Retrieve the progress percentage and status of a model download task."""
    job = _DOWNLOAD_JOBS.get(model_id)
    if job is None:
        # If not active but cached, return completed, otherwise not_started
        # Let's map model_id
        is_cached = False
        if model_id in ("tiny", "base", "small"):
            is_cached = is_whisper_model_cached(model_id)
        else:
            is_cached = is_hf_model_cached(model_id)
            
        if is_cached:
            return {"status": "completed", "progress": 100}
        return {"status": "not_started", "progress": 0}
    return job
