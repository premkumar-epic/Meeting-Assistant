from __future__ import annotations

import os
from pathlib import Path
import uuid
import re
import shutil
from typing import Any
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app.database import init_db, save_meeting, get_all_meetings, get_meeting_by_id, delete_meeting
from app.schemas import MeetingListItem, MeetingDetailResponse, ProcessMeetingResponse, ChatQuestionRequest, ChatAnswerResponse, ActiveModelConfigRequest, ModelDownloadRequest
from app.services.audio_processor import normalize_audio, SUPPORTED_INPUT_EXTENSIONS
from app.services.transcriber import transcribe_audio, _probe_duration_seconds
from app.services.summarizer import summarize_text

from app.services.chat_engine import ask_meeting
from app.services.model_manager import get_all_models_status, download_model_background, get_download_status, is_whisper_model_cached, is_hf_model_cached
from app.services.config_manager import save_model_config
from app.utils.temp_files import create_temp_dir, build_temp_file_path, safe_rmtree

app = FastAPI(
    title="AI-Powered Meeting Assistant API",
    description="Local-first meeting analysis engine with audio processing, ASR, and summarization.",
    version="1.0.0"
)

# Enable CORS for frontend integration (Vite dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory job tracker for real-time progress polling
_JOBS: dict[str, dict[str, Any]] = {}

MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

def sanitize_filename(filename: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)

async def cleanup_old_jobs():
    """Background task to evict completed or failed jobs older than 60 minutes."""
    while True:
        await asyncio.sleep(600)  # Run every 10 minutes
        now = datetime.now()
        for j_id, j_data in list(_JOBS.items()):
            if j_data.get("status") in ("completed", "failed"):
                created_at = j_data.get("created_at")
                if created_at and (now - created_at) > timedelta(minutes=60):
                    _JOBS.pop(j_id, None)

@app.on_event("startup")
def startup_event():
    """Ensure database schema is initialized on startup."""
    init_db()
    asyncio.create_task(cleanup_old_jobs())

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "meeting-assistant"}


def run_pipeline_background(job_id: str, temp_input_path: Path, filename: str) -> None:
    """Runs the processing pipeline in a background thread and updates job progress."""
    try:
        # Step 1: Normalize audio using ffmpeg
        _JOBS[job_id].update({"status": "Normalizing audio (FFmpeg)...", "progress": 10})
        normalized_path = normalize_audio(str(temp_input_path))
        
        # Step 2: Read duration
        duration = _probe_duration_seconds(normalized_path)

        # Step 3: Transcription with callback
        def progress_cb(chunk_idx: int, total_chunks: int) -> None:
            # Map chunk transcribing to 15% - 75% range of total progress
            pct = 15 + int(60 * (chunk_idx + 1) / total_chunks)
            _JOBS[job_id].update({
                "status": f"Transcribing audio (chunk {chunk_idx + 1}/{total_chunks})...",
                "progress": pct
            })

        transcription_result = transcribe_audio(
            normalized_path,
            progress_callback=progress_cb
        )
        transcript = transcription_result["text"]

        # Step 4: Summarization
        _JOBS[job_id].update({"status": "Generating summary (BART)...", "progress": 80})
        summary = summarize_text(transcript)

        # Step 5: Entity and Task parsing
        _JOBS[job_id].update({"status": "Extracting key details and tasks...", "progress": 90})
        from app.services.parser import parse_transcript
        entities, action_items = parse_transcript(transcript)

        # Step 6: Save result to SQLite DB
        _JOBS[job_id].update({"status": "Saving record to database...", "progress": 95})
        db_id = save_meeting(
            filename=filename,
            duration=round(duration, 2),
            transcript=transcript,
            summary=summary,
            action_items=action_items,
            entities=entities
        )

        # Retrieve fully serialized database row
        detail = get_meeting_by_id(db_id)
        if detail is None:
            raise RuntimeError("Failed to retrieve saved meeting from database.")
        
        # Mark job as completed
        _JOBS[job_id].update({
            "status": "completed",
            "progress": 100,
            "result": detail
        })

    except Exception as exc:
        print(f"[ERROR] Background processing failed for job {job_id}: {exc}", flush=True)
        _JOBS[job_id].update({
            "status": "failed",
            "progress": 0,
            "error": str(exc)
        })
    finally:
        # Clean up the temp input directory
        safe_rmtree(temp_input_path.parent)


@app.post("/api/process-meeting", response_model=ProcessMeetingResponse)
async def process_meeting_endpoint(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Upload and queue a meeting audio file for asynchronous background processing.
    Instantly returns a job_id for real-time status polling.
    """
    # 1. File size validation
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large. Max size is {MAX_FILE_SIZE_MB}MB.")

    # 2. File extension validation & filename sanitization
    filename = sanitize_filename(file.filename or "unknown.wav")
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_INPUT_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{suffix}'. Supported: {', '.join(sorted(SUPPORTED_INPUT_EXTENSIONS))}"
        )

    # Create safe isolated temp directory and save file
    temp_dir = create_temp_dir(prefix="api_upload_")
    temp_input_path = build_temp_file_path(temp_dir=temp_dir, suffix=suffix, prefix="input")

    try:
        # Save uploaded stream to file
        with temp_input_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Generate a unique job ID and initialize progress tracker
        job_id = str(uuid.uuid4())
        _JOBS[job_id] = {
            "status": "Enqueuing meeting processing...",
            "progress": 5,
            "result": None,
            "error": None,
            "created_at": datetime.now()
        }

        # Schedule the heavy pipeline processing in the background
        background_tasks.add_task(run_pipeline_background, job_id, temp_input_path, filename)

        return {
            "job_id": job_id,
            "status": "started",
            "progress": 5
        }

    except Exception as exc:
        safe_rmtree(temp_dir)
        raise HTTPException(status_code=500, detail=f"Failed to queue file: {str(exc)}")


@app.get("/api/jobs/{job_id}")
async def get_job_status_endpoint(job_id: str):
    """Retrieve the real-time status and progress percentage of a queued job."""
    job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found.")
    return job


@app.get("/api/meetings", response_model=list[MeetingListItem])
async def get_meetings_endpoint():
    """Retrieve lists of all parsed meetings."""
    try:
        return get_all_meetings()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/meetings/{meeting_id}", response_model=MeetingDetailResponse)
async def get_meeting_detail_endpoint(meeting_id: int):
    """Retrieve full meeting transcript, summary, and action items by database ID."""
    meeting = get_meeting_by_id(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail=f"Meeting with ID {meeting_id} not found.")
    return meeting


@app.delete("/api/meetings/{meeting_id}")
async def delete_meeting_endpoint(meeting_id: int):
    """Delete a meeting entry by database ID."""
    meeting = get_meeting_by_id(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail=f"Meeting with ID {meeting_id} not found.")
    delete_meeting(meeting_id)
    return {"message": f"Successfully deleted meeting {meeting_id}."}


@app.post("/api/meetings/{meeting_id}/chat")
async def chat_with_meeting_endpoint(meeting_id: int, payload: ChatQuestionRequest):
    """
    Query the meeting context using the local Qwen LLM.
    Answers are constrained strictly to the meeting transcript text.
    Streams back the response using Server-Sent Events (SSE).
    """
    meeting = get_meeting_by_id(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail=f"Meeting with ID {meeting_id} not found.")
        
    transcript = meeting.get("transcript", "")
    if not transcript:
        raise HTTPException(status_code=400, detail="The selected meeting has an empty transcript.")
        
    history_dicts = [{"role": h.role, "content": h.content} for h in payload.history]
    
    def event_generator():
        try:
            for chunk in ask_meeting(transcript, payload.question, history_dicts):
                if chunk:
                    import json
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        except Exception as e:
            import json
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/models")
async def get_models_endpoint():
    """Retrieve system specs and list of models with caching/recommendation status."""
    try:
        return get_all_models_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/models/active")
async def set_active_models_endpoint(payload: ActiveModelConfigRequest):
    """
    Set active configurations.
    Requires requested models to be cached locally.
    """
    # Verify ASR model cache
    asr_cached = (payload.asr_model in ("tiny", "base", "small") and 
                  (is_whisper_model_cached(payload.asr_model) or 
                   is_hf_model_cached(f"Systran/faster-whisper-{payload.asr_model}")))
    if not asr_cached:
        raise HTTPException(
            status_code=400, 
            detail=f"ASR Model '{payload.asr_model}' is not cached offline. Please download it first."
        )
        
    # Verify Summarizer model cache
    if not is_hf_model_cached(payload.summarizer_model):
        raise HTTPException(
            status_code=400, 
            detail=f"Summarizer Model '{payload.summarizer_model}' is not cached offline. Please download it first."
        )
        
    # Verify LLM model cache
    if not is_hf_model_cached(payload.llm_model):
        raise HTTPException(
            status_code=400, 
            detail=f"Chat LLM Model '{payload.llm_model}' is not cached offline. Please download it first."
        )
        
    try:
        save_model_config({
            "asr_provider": payload.asr_provider,
            "asr_model": payload.asr_model,
            "summarizer_model": payload.summarizer_model,
            "llm_model": payload.llm_model
        })
        return {"message": "Model configuration updated successfully."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/models/download")
async def queue_model_download_endpoint(payload: ModelDownloadRequest, background_tasks: BackgroundTasks):
    """Queue a model download and cache task in the background."""
    try:
        background_tasks.add_task(download_model_background, payload.model_type, payload.model_id)
        return {"message": f"Download task queued for model '{payload.model_id}'."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/models/download/{model_id:path}")
async def get_model_download_status_endpoint(model_id: str):
    """Retrieve the real-time download progress and status of a model."""
    try:
        return get_download_status(model_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

