from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ASRSettings:
    provider: str = os.getenv("MEETING_ASR_PROVIDER", "faster-whisper")
    model_name: str = os.getenv("MEETING_ASR_MODEL", "base")
    window_seconds: int = int(os.getenv("MEETING_ASR_WINDOW_SECONDS", "30"))
    overlap_seconds: int = int(os.getenv("MEETING_ASR_OVERLAP_SECONDS", "2"))



@dataclass(frozen=True)
class SummarizerSettings:
    model_name: str = os.getenv("MEETING_SUMMARIZER_MODEL", "sshleifer/distilbart-cnn-12-6")
    max_chunk_tokens: int = int(os.getenv("MEETING_SUMMARIZER_MAX_CHUNK_TOKENS", "800"))
    min_summary_length: int = int(os.getenv("MEETING_SUMMARIZER_MIN_LENGTH", "30"))
    max_summary_length: int = int(os.getenv("MEETING_SUMMARIZER_MAX_LENGTH", "150"))


@dataclass(frozen=True)
class LLMSettings:
    model_name: str = os.getenv("MEETING_LLM_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
    max_new_tokens: int = int(os.getenv("MEETING_LLM_MAX_NEW_TOKENS", "256"))
    temperature: float = float(os.getenv("MEETING_LLM_TEMPERATURE", "0.1"))


ASR_SETTINGS = ASRSettings()
SUMMARIZER_SETTINGS = SummarizerSettings()
LLM_SETTINGS = LLMSettings()


