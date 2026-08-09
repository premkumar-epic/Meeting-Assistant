from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_FILE = Path(__file__).resolve().parents[2] / "model_config.json"

DEFAULT_CONFIG = {
    "asr_provider": "faster-whisper",
    "asr_model": "base",
    "summarizer_model": "sshleifer/distilbart-cnn-12-6",
    "llm_model": "Qwen/Qwen2.5-0.5B-Instruct"
}


def get_model_config() -> dict[str, str]:
    """Retrieve the active model configuration from JSON or return defaults."""
    if not CONFIG_FILE.exists():
        save_model_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            config = json.load(f)
            # Ensure all keys exist
            for k, v in DEFAULT_CONFIG.items():
                if k not in config or config[k] is None or config[k] == "":
                    config[k] = v
            return config
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_model_config(config: dict[str, str]) -> None:
    """Save the selected active models to local persistent config file."""
    # Validate keys
    sanitized = {}
    for k in ["asr_provider", "asr_model", "summarizer_model", "llm_model"]:
        val = config.get(k)
        if val is None or val == "":
            sanitized[k] = DEFAULT_CONFIG[k]
        else:
            sanitized[k] = val
    
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(sanitized, f, indent=2)
    
    # Trigger model cache clearing across services to ensure the new model is loaded next
    clear_model_caches()


def clear_model_caches() -> None:
    """Clear memory caches in transcription, summarization, and chat engines to trigger reload."""
    try:
        from app.services import transcriber, summarizer, chat_engine
        
        # Clear transcriber cache
        transcriber._MODEL_CACHE.clear()
        
        # Clear summarizer pipeline cache
        summarizer._SUMMARIZER_CACHE.clear()
        
        # Clear chat engine cache
        chat_engine._CHAT_PIPELINE = None
        
        print("[INFO] Model memory caches cleared successfully for hot-swap.", flush=True)
    except Exception as e:
        print(f"[WARNING] Failed to clear model caches: {e}", flush=True)
