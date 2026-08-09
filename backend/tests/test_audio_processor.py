import pytest
import subprocess
from unittest.mock import patch, MagicMock
from app.services.audio_processor import normalize_audio

@patch("app.services.audio_processor.Path.exists")
@patch("app.services.audio_processor.Path.is_file")
def test_normalize_audio_invalid_extension(mock_is_file, mock_exists):
    mock_exists.return_value = True
    mock_is_file.return_value = True
    # Verify file extensions guardrail
    with pytest.raises(ValueError, match="Unsupported audio format"):
        normalize_audio("file.txt")


def test_normalize_audio_file_not_found():
    # Verify input existence check
    with pytest.raises(FileNotFoundError):
        normalize_audio("non_existent_file.mp3")

@patch("app.services.audio_processor.Path.exists")
@patch("app.services.audio_processor.Path.is_file")
@patch("subprocess.run")
def test_normalize_audio_success(mock_run, mock_is_file, mock_exists, tmp_path):
    mock_exists.return_value = True
    mock_is_file.return_value = True
    
    output_wav = tmp_path / "output.wav"
    res = normalize_audio("test.mp3", output_path=str(output_wav))
    
    assert res == str(output_wav)
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "ffmpeg" in args
    assert "-i" in args
    assert "test.mp3" in args
    assert str(output_wav) in args

@patch("app.services.audio_processor.Path.exists")
@patch("app.services.audio_processor.Path.is_file")
@patch("subprocess.run")
def test_normalize_audio_failure(mock_run, mock_is_file, mock_exists, tmp_path):
    mock_exists.return_value = True
    mock_is_file.return_value = True
    mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr="FFmpeg execution error")
    
    output_wav = tmp_path / "output.wav"
    with pytest.raises(RuntimeError, match="Failed to export normalized audio"):
        normalize_audio("test.mp3", output_path=str(output_wav))


@patch("app.services.audio_processor.Path.exists")
@patch("app.services.audio_processor.Path.is_file")
@patch("app.services.audio_processor.create_temp_dir")
@patch("app.services.audio_processor.build_temp_file_path")
@patch("subprocess.run")
def test_normalize_audio_default_output(mock_run, mock_build_path, mock_create_dir, mock_is_file, mock_exists, tmp_path):
    mock_exists.return_value = True
    mock_is_file.return_value = True
    mock_create_dir.return_value = tmp_path
    mock_build_path.return_value = tmp_path / "normalized_abc.wav"
    
    res = normalize_audio("test.mp3", output_path=None)
    
    assert res == str(tmp_path / "normalized_abc.wav")
    mock_run.assert_called_once()
    mock_create_dir.assert_called_once_with(prefix="normalized_audio_")
    mock_build_path.assert_called_once_with(temp_dir=tmp_path, suffix=".wav", prefix="normalized")

