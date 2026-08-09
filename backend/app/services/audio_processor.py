from __future__ import annotations

from pathlib import Path
import subprocess

from app.utils.temp_files import build_temp_file_path, create_temp_dir, ensure_parent_dir

SUPPORTED_INPUT_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac"}
TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1


def normalize_audio(file_path: str, output_path: str | None = None) -> str:
    """
    Convert supported audio input into a normalized 16kHz mono PCM WAV file.
    Returns the output WAV path.
    """
    input_path = Path(file_path)
    if not input_path.exists() or not input_path.is_file():
        raise FileNotFoundError(f"Input audio file not found: {file_path}")

    suffix = input_path.suffix.lower()
    if suffix not in SUPPORTED_INPUT_EXTENSIONS:
        raise ValueError(
            f"Unsupported audio format '{suffix}'. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_INPUT_EXTENSIONS))}"
        )

    if output_path is None:
        temp_dir = create_temp_dir(prefix="normalized_audio_")
        output = build_temp_file_path(temp_dir=temp_dir, suffix=".wav", prefix="normalized")
    else:
        output = Path(output_path)
        ensure_parent_dir(output)

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(input_path),
                "-ac",
                str(TARGET_CHANNELS),
                "-ar",
                str(TARGET_SAMPLE_RATE),
                "-acodec",
                "pcm_s16le",
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to export normalized audio to '{output}': {exc}") from exc

    return str(output)
