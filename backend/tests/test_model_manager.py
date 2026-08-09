from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from app.services.model_manager import get_all_models_status, get_download_status, download_model_background


@patch("app.services.model_manager.get_system_specs")
@patch("app.services.model_manager.get_model_config")
@patch("app.services.model_manager.is_whisper_model_cached")
@patch("app.services.model_manager.is_hf_model_cached")
def test_get_all_models_status(mock_hf, mock_whisper, mock_config, mock_specs):
    # Setup mock returns
    mock_specs.return_value = {
        "ram_gb": 16.0,
        "cpu_count": 8,
        "gpu_available": False,
        "gpu_name": None,
        "recommendation_tier": "medium"
    }
    mock_config.return_value = {
        "asr_provider": "faster-whisper",
        "asr_model": "base",
        "summarizer_model": "sshleifer/distilbart-cnn-12-6",
        "llm_model": "Qwen/Qwen2.5-0.5B-Instruct"
    }
    mock_whisper.return_value = True
    mock_hf.return_value = False
    
    status = get_all_models_status()
    
    assert status["specs"]["ram_gb"] == 16.0
    assert status["active_config"]["asr_model"] == "base"
    
    # Verify recommendations based on medium specs
    asr_base = next(m for m in status["asr"] if m["id"] == "base")
    assert asr_base["recommended"] is True
    assert asr_base["active"] is True
    
    asr_tiny = next(m for m in status["asr"] if m["id"] == "tiny")
    assert asr_tiny["recommended"] is False


def test_get_download_status_non_existent():
    # If not active and not cached
    status = get_download_status("non-existent-model")
    assert status["status"] == "not_started"
    assert status["progress"] == 0


@patch("app.services.model_manager.urllib.request.urlretrieve")
@patch("huggingface_hub.snapshot_download")
@patch("transformers.AutoTokenizer.from_pretrained")
def test_download_model_background_asr(mock_tokenizer, mock_snapshot, mock_urlretrieve):
    download_model_background("asr", "tiny")
    
    status = get_download_status("tiny")
    assert status["status"] == "completed"
    assert status["progress"] == 100
