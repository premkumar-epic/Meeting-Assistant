# AI-Powered Meeting Assistant

A privacy-focused, local-first meeting assistant that normalizes meeting recordings, transcribes speech using Whisper, generates recursive summaries using BART, and parses action items and entities using spaCy. **All models execute locally on your CPU—your data never leaves your device.**

## Key Features
* 🔒 **100% Privacy**: Offline execution with local database persistence (SQLite). No external third-party API keys required.
* ⚡ **CTranslate2 Acceleration**: Integrated with `faster-whisper` for **4x - 8x speedups** on standard CPUs.
* 🔄 **Real-Time Progress Tracking**: Background pipeline processing with active status and progress updates polled by the React frontend.
* 📝 **Long-Text Summarization**: Tokenizer-aware recursive hierarchical chunking (BART) to summarize hours-long transcripts without truncation limits.
* ✅ **Entity & Task Parsing**: Automatically extracts named entities (`PERSON`, `ORG`, `DATE`) and matches commitment phrases to assign action items.
* 🧪 **Production Grade**: Full automated unit and integration test suite with **90% coverage**.

---

## Repository Structure
* [`backend/`](file:///home/premkumar/PROJECTS/AI-Powered-Meeting_Assistant/backend): FastAPI server containing pipelines, services, and tests.
* [`client/`](file:///home/premkumar/PROJECTS/AI-Powered-Meeting_Assistant/client): React client dashboard powered by Vite.
* [`samples/`](file:///home/premkumar/PROJECTS/AI-Powered-Meeting_Assistant/samples): Sample audio recordings used during ASR verification.
* [`run.sh`](file:///home/premkumar/PROJECTS/AI-Powered-Meeting_Assistant/run.sh): Unified single-command startup script.
* [`project.md`](file:///home/premkumar/PROJECTS/AI-Powered-Meeting_Assistant/project.md): Project roadmap, DoD checklist, and detailed engineering execution log.

---

## Setup & Execution Guide

### Prerequisites
Make sure the following system dependencies are installed and available on your PATH:
* **FFmpeg** (Required for audio format normalization)
* **Node.js** (Required to run the Vite React dev client)
* **Python 3.10+** (Required for backend pipelines)

### 1. One-Click Bootstrap & Launch
We have created a unified script to manage dependency installation and launch both servers concurrently. In the root directory, simply run:

```bash
./run.sh
```

This script will automatically:
1. Validate your system prerequisites (`ffmpeg`, `node`, `python3`).
2. Run `npm install` for frontend packages if missing.
3. Start the FastAPI backend server on `http://localhost:8000`.
4. Start the Vite React client dev server on `http://localhost:5173`.
5. Gracefully terminate both processes when you press `Ctrl+C`.

---

### 2. Offline Model Pre-Caching (Optional)
If you want to use the application in a completely air-gapped environment without internet access, run the caching script beforehand:

```bash
cd backend
source .venv/bin/activate
python scripts/bootstrap_models.py
```
This script pre-downloads and caches all model weights (`faster-whisper`, `sshleifer/distilbart-cnn-12-6` tokenizer/weights, and spaCy language packs) to local cache directories.

---

### 3. Backend Verification & Tests
To run verification scripts or backend tests:

```bash
cd backend
source .venv/bin/activate

# Run verification script on transcription
python scripts/verify_transcription.py ../samples/tedx.mp3 --segments-json ../samples/tedx_segments.json

# Run verification script on summarization
python scripts/verify_summarization.py ../samples/tedx_segments.json

# Execute the complete automated test suite (34 unit and API tests)
pytest tests/ -v

# Execute tests with full coverage report
pytest --cov=app tests/
```
# Meeting-Assistant
