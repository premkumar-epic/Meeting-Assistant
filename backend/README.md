# Backend (FastAPI + Local AI Pipeline)

## Planned modules
- `app/services/audio_processor.py` — audio normalization to 16kHz mono WAV (ffmpeg-backed)
- `app/services/transcriber.py` — Whisper transcription with chunk overlap (ffmpeg chunk extraction)
- `app/services/summarizer.py` — BART summarization with long-text chunking
- `app/services/parser.py` — entities + action item extraction
- `app/main.py` — FastAPI endpoint wiring
- `app/schemas.py` — API request/response models

## Install (Linux/macOS)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/bootstrap_models.py
```

## System dependency
FFmpeg must be installed and available on PATH.

## Verify audio normalization (Chunk C1)

From `backend/`:

```bash
python scripts/verify_audio_normalization.py ../samples/your-audio-file.mp3
```

This verifies conversion output and prints:
- channels (expected: `1`)
- sample rate (expected: `16000`)
- sample width and duration

## Verify Whisper chunked transcription (Chunk C2)

From `backend/`:

```bash
python scripts/verify_transcription.py ../samples/your-audio-file.wav --provider openai-whisper --model base --window 30 --overlap 2
```

Optional: save merged segments to JSON

```bash
python scripts/verify_transcription.py ../samples/your-audio-file.wav --segments-json ../samples/segments.json
```

## Verify Summarization (Chunk C3)

From `backend/`:

```bash
python scripts/verify_summarization.py ../samples/segments.json
```

## Run Automated Unit & API Tests

From `backend/`:

```bash
# Run the complete test suite (pytest)
pytest tests/ -v

# Run with coverage report
pytest --cov=app tests/
```


## Swappable ASR model settings

The transcriber now supports provider/model swaps without code changes.

### Supported providers
- `openai-whisper` (default)
- `faster-whisper` (optional dependency)

### Per-run override (CLI)
```bash
python scripts/verify_transcription.py ../samples/your-audio-file.wav --provider openai-whisper --model medium
python scripts/verify_transcription.py ../samples/your-audio-file.wav --provider faster-whisper --model large-v3
```

### Environment-level defaults
```bash
export MEETING_ASR_PROVIDER=openai-whisper
export MEETING_ASR_MODEL=base
export MEETING_ASR_WINDOW_SECONDS=30
export MEETING_ASR_OVERLAP_SECONDS=2
```

### Optional install for `faster-whisper`
```bash
pip install faster-whisper
```

## Best open-source ASR options (shortlist)

1. `Whisper large-v3` / `turbo` — strongest quality baseline for multilingual/noisy speech (source: OpenAI Whisper repo/model docs).
2. `faster-whisper` — Whisper-family accuracy with lower latency/memory via CTranslate2 (source: SYSTRAN faster-whisper benchmarks).
3. `NVIDIA Parakeet TDT 0.6B` / `v3` — strong modern ASR line with high throughput and timestamps (source: NVIDIA model cards on Hugging Face).
4. `whisper.cpp` — lightweight fully offline deployment path for CPU/edge devices (source: ggml-org/whisper.cpp).
