from __future__ import annotations

import json
from pathlib import Path
import subprocess
import threading
from typing import Any, Callable

import whisper

from app.config import ASR_SETTINGS
from app.utils.temp_files import build_temp_file_path, create_temp_dir, safe_rmtree, safe_unlink

SUPPORTED_ASR_PROVIDERS = {"openai-whisper", "faster-whisper"}
DEFAULT_ASR_PROVIDER = ASR_SETTINGS.provider
DEFAULT_WHISPER_MODEL = ASR_SETTINGS.model_name
DEFAULT_WINDOW_SECONDS = ASR_SETTINGS.window_seconds
DEFAULT_OVERLAP_SECONDS = ASR_SETTINGS.overlap_seconds

_MODEL_LOCK = threading.Lock()
_MODEL_CACHE: dict[str, Any] = {}


def _cache_key(provider: str, model_name: str) -> str:
    return f"{provider}:{model_name}"


def _get_openai_whisper_model(model_name: str) -> Any:
    key = _cache_key("openai-whisper", model_name)
    with _MODEL_LOCK:
        if key not in _MODEL_CACHE:
            _MODEL_CACHE[key] = whisper.load_model(model_name)
        return _MODEL_CACHE[key]


def _get_faster_whisper_model(model_name: str) -> Any:
    key = _cache_key("faster-whisper", model_name)
    with _MODEL_LOCK:
        if key in _MODEL_CACHE:
            return _MODEL_CACHE[key]

        try:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "ASR provider 'faster-whisper' requires package 'faster-whisper'. "
                "Install with: pip install faster-whisper"
            ) from exc

        # Defaulting to int8 keeps CPU usage practical for local runs.
        _MODEL_CACHE[key] = WhisperModel(model_name, compute_type="int8")
        return _MODEL_CACHE[key]


def _probe_duration_seconds(audio_path: str) -> float:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                audio_path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        duration = float(payload["format"]["duration"])
    except Exception as exc:
        raise RuntimeError(f"Failed to read audio duration for '{audio_path}': {exc}") from exc

    if duration <= 0:
        raise RuntimeError(f"Audio duration is invalid for '{audio_path}'")
    return duration


def _extract_chunk_wav(
    source_path: str, target_path: str, start_seconds: float, duration_seconds: float
) -> None:
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{start_seconds:.3f}",
                "-i",
                source_path,
                "-t",
                f"{duration_seconds:.3f}",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-acodec",
                "pcm_s16le",
                target_path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Failed to extract chunk ({start_seconds:.3f}s, {duration_seconds:.3f}s): {exc}"
        ) from exc


def _transcribe_chunk(
    provider: str, model: Any, chunk_path: str
) -> list[dict[str, float | str]]:
    if provider == "openai-whisper":
        result = model.transcribe(
            chunk_path,
            temperature=0.0,
            word_timestamps=True,
        )
        segments = result.get("segments", [])
        normalized: list[dict[str, float | str]] = []
        for segment in segments:
            normalized.append(
                {
                    "start": float(segment["start"]),
                    "end": float(segment["end"]),
                    "text": str(segment.get("text", "")).strip(),
                }
            )
        return normalized

    if provider == "faster-whisper":
        segments, _info = model.transcribe(
            chunk_path,
            beam_size=5,
            word_timestamps=True,
            condition_on_previous_text=False,
        )
        normalized = []
        for segment in segments:
            normalized.append(
                {
                    "start": float(segment.start),
                    "end": float(segment.end),
                    "text": str(segment.text).strip(),
                }
            )
        return normalized

    raise ValueError(
        f"Unsupported ASR provider '{provider}'. "
        f"Supported providers: {', '.join(sorted(SUPPORTED_ASR_PROVIDERS))}"
    )


def transcribe_audio(
    audio_path: str,
    provider: str | None = None,
    model_name: str | None = None,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
    overlap_seconds: int = DEFAULT_OVERLAP_SECONDS,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """
    Transcribe audio with sliding windows and overlap to reduce boundary truncation.
    Returns merged text and globally timed segments.
    """
    input_path = Path(audio_path)
    if not input_path.exists() or not input_path.is_file():
        raise FileNotFoundError(f"Input audio file not found: {audio_path}")

    from app.services.config_manager import get_model_config
    config = get_model_config()
    active_provider = provider or config["asr_provider"]
    active_model = model_name or config["asr_model"]

    if window_seconds <= 0:
        raise ValueError("window_seconds must be greater than 0")
    if overlap_seconds < 0:
        raise ValueError("overlap_seconds must be 0 or greater")
    if overlap_seconds >= window_seconds:
        raise ValueError("overlap_seconds must be smaller than window_seconds")
    if active_provider not in SUPPORTED_ASR_PROVIDERS:
        raise ValueError(
            f"Unsupported ASR provider '{active_provider}'. "
            f"Supported providers: {', '.join(sorted(SUPPORTED_ASR_PROVIDERS))}"
        )

    if active_provider == "openai-whisper":
        model = _get_openai_whisper_model(active_model)
    else:
        model = _get_faster_whisper_model(active_model)

    total_seconds = _probe_duration_seconds(str(input_path))
    window_seconds_float = float(window_seconds)
    overlap_seconds_float = float(overlap_seconds)
    stride_seconds = window_seconds_float - overlap_seconds_float

    import math
    if total_seconds <= window_seconds_float:
        total_chunks = 1
    else:
        total_chunks = 1 + math.ceil((total_seconds - window_seconds_float) / stride_seconds)

    chunk_dir = create_temp_dir(prefix="whisper_chunks_")
    merged_segments: list[dict[str, Any]] = []

    try:
        cursor_seconds = 0.0
        chunk_index = 0
        while cursor_seconds < total_seconds:
            chunk_start_seconds = cursor_seconds
            chunk_end_seconds = min(chunk_start_seconds + window_seconds_float, total_seconds)
            chunk_duration_seconds = chunk_end_seconds - chunk_start_seconds
            is_last_chunk = chunk_end_seconds >= total_seconds

            print(
                f"[ASR] Transcribing chunk {chunk_index + 1}/{total_chunks} "
                f"({chunk_start_seconds:.1f}s - {chunk_end_seconds:.1f}s)...",
                flush=True
            )
            if progress_callback:
                try:
                    progress_callback(chunk_index, total_chunks)
                except Exception:
                    pass

            chunk_path = build_temp_file_path(
                temp_dir=chunk_dir,
                suffix=".wav",
                prefix=f"chunk_{chunk_index}",
            )
            _extract_chunk_wav(
                source_path=str(input_path),
                target_path=str(chunk_path),
                start_seconds=chunk_start_seconds,
                duration_seconds=chunk_duration_seconds,
            )

            chunk_segments = _transcribe_chunk(active_provider, model, str(chunk_path))

            keep_until_seconds = (
                float("inf")
                if is_last_chunk
                else chunk_end_seconds - overlap_seconds_float
            )

            for segment in chunk_segments:
                global_start = chunk_start_seconds + float(segment["start"])
                if global_start >= keep_until_seconds:
                    continue

                global_end = chunk_start_seconds + float(segment["end"])
                text = str(segment["text"]).strip()
                if not text:
                    continue

                merged_segments.append(
                    {
                        "id": len(merged_segments),
                        "start": round(global_start, 3),
                        "end": round(global_end, 3),
                        "text": text,
                    }
                )

            safe_unlink(chunk_path)
            chunk_index += 1
            cursor_seconds += stride_seconds
    finally:
        safe_rmtree(chunk_dir)

    merged_text = " ".join(segment["text"] for segment in merged_segments).strip()
    return {
        "provider": active_provider,
        "model_name": active_model,
        "text": merged_text,
        "segments": merged_segments,
    }
