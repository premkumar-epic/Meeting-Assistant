import pytest
import subprocess
import json
from unittest.mock import patch, MagicMock
from app.services.transcriber import transcribe_audio, _probe_duration_seconds

def test_probe_duration_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout=json.dumps({"format": {"duration": "120.5"}})
        )
        duration = _probe_duration_seconds("test.wav")
        assert duration == 120.5

def test_probe_duration_invalid_duration():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout=json.dumps({"format": {"duration": "0"}})
        )
        with pytest.raises(RuntimeError, match="Audio duration is invalid"):
            _probe_duration_seconds("test.wav")

@patch("app.services.transcriber.Path.exists")
@patch("app.services.transcriber.Path.is_file")
def test_transcribe_audio_invalid_parameters(mock_is_file, mock_exists):
    mock_exists.return_value = True
    mock_is_file.return_value = True
    
    with pytest.raises(ValueError, match="window_seconds must be greater than 0"):
        transcribe_audio("test.wav", window_seconds=0)
        
    with pytest.raises(ValueError, match="overlap_seconds must be 0 or greater"):
        transcribe_audio("test.wav", overlap_seconds=-1)
        
    with pytest.raises(ValueError, match="overlap_seconds must be smaller than window_seconds"):
        transcribe_audio("test.wav", window_seconds=10, overlap_seconds=10)


@patch("app.services.transcriber.Path.exists")
@patch("app.services.transcriber.Path.is_file")
@patch("app.services.transcriber._probe_duration_seconds")
@patch("app.services.transcriber._get_openai_whisper_model")
@patch("subprocess.run")
def test_transcribe_audio_openai_whisper(mock_run, mock_get_model, mock_probe, mock_is_file, mock_exists):
    mock_exists.return_value = True
    mock_is_file.return_value = True
    mock_probe.return_value = 45.0  # Total duration 45 seconds
    
    mock_model = MagicMock()
    # Mocking two chunks:
    # Chunk 1 (0 to 30s) -> Keep limit is 25s (window=30, overlap=5)
    # Chunk 2 (25 to 45s) -> Keep limit is inf (last chunk)
    mock_model.transcribe.side_effect = [
        {
            "segments": [
                {"start": 1.0, "end": 3.0, "text": "Hello"},
                {"start": 26.0, "end": 28.0, "text": "This should be discarded from chunk 1"}
            ]
        },
        {
            "segments": [
                {"start": 1.0, "end": 3.0, "text": "World"}  # global start: 25 + 1 = 26s
            ]
        }
    ]
    mock_get_model.return_value = mock_model
    
    result = transcribe_audio(
        "test.wav",
        provider="openai-whisper",
        model_name="base",
        window_seconds=30,
        overlap_seconds=5
    )
    
    assert result["provider"] == "openai-whisper"
    assert result["model_name"] == "base"
    assert result["text"] == "Hello World"
    assert len(result["segments"]) == 2
    assert result["segments"][0]["text"] == "Hello"
    assert result["segments"][0]["start"] == 1.0
    assert result["segments"][1]["text"] == "World"
    assert result["segments"][1]["start"] == 26.0


@patch("app.services.transcriber.Path.exists")
@patch("app.services.transcriber.Path.is_file")
@patch.dict("sys.modules", {"faster_whisper": None})
def test_transcribe_audio_faster_whisper_import_error(mock_is_file, mock_exists):
    mock_exists.return_value = True
    mock_is_file.return_value = True
    
    with pytest.raises(RuntimeError, match="ASR provider 'faster-whisper' requires package 'faster-whisper'"):
        from app.services.transcriber import _MODEL_CACHE
        _MODEL_CACHE.pop("faster-whisper:base", None)
        transcribe_audio("test.wav", provider="faster-whisper", model_name="base")


@patch("app.services.transcriber.Path.exists")
@patch("app.services.transcriber.Path.is_file")
@patch("app.services.transcriber._probe_duration_seconds")
@patch("app.services.transcriber._get_faster_whisper_model")
@patch("subprocess.run")
def test_transcribe_audio_faster_whisper_success(mock_run, mock_get_model, mock_probe, mock_is_file, mock_exists):
    mock_exists.return_value = True
    mock_is_file.return_value = True
    mock_probe.return_value = 10.0
    
    mock_model = MagicMock()
    class MockSegment:
        def __init__(self, start, end, text):
            self.start = start
            self.end = end
            self.text = text
            
    mock_model.transcribe.return_value = (
        [MockSegment(1.0, 5.0, "Hello from faster whisper")],
        None
    )
    mock_get_model.return_value = mock_model
    
    result = transcribe_audio(
        "test.wav",
        provider="faster-whisper",
        model_name="base",
        window_seconds=30,
        overlap_seconds=5
    )
    
    assert result["provider"] == "faster-whisper"
    assert result["text"] == "Hello from faster whisper"

