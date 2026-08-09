from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.database import init_db


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    test_db = tmp_path / "test_api.db"
    with patch("app.database.DB_PATH", test_db):
        init_db()
        yield


def test_get_meetings_empty():
    client = TestClient(app)
    response = client.get("/api/meetings")
    assert response.status_code == 200
    assert response.json() == []


def test_delete_meeting_404():
    client = TestClient(app)
    response = client.delete("/api/meetings/999")
    assert response.status_code == 404


def test_get_meeting_404():
    client = TestClient(app)
    response = client.get("/api/meetings/999")
    assert response.status_code == 404


def test_get_job_404():
    client = TestClient(app)
    response = client.get("/api/jobs/non-existent-job")
    assert response.status_code == 404


@patch("app.main.extract_action_items")
@patch("app.main.extract_entities")
@patch("app.main.summarize_text")
@patch("app.main.transcribe_audio")
@patch("app.main._probe_duration_seconds")
@patch("app.main.normalize_audio")
def test_process_meeting_success(
    mock_normalize,
    mock_probe,
    mock_transcribe,
    mock_summarize,
    mock_entities,
    mock_actions
):
    # Setup mock return values
    mock_normalize.return_value = "normalized.wav"
    mock_probe.return_value = 10.0
    mock_transcribe.return_value = {"text": "Hello world", "segments": []}
    mock_summarize.return_value = "Hello summary"
    mock_entities.return_value = [{"text": "Hello", "label": "ORG"}]
    mock_actions.return_value = [{"id": 0, "text": "Task", "assignee": "Speaker"}]
    
    client = TestClient(app)
    
    file_content = b"fake audio content"
    files = {"file": ("test.mp3", file_content, "audio/mpeg")}
    
    # POST to process meeting (queues background task)
    response = client.post("/api/process-meeting", files=files)
    assert response.status_code == 200
    
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "started"
    assert data["progress"] == 5
    
    job_id = data["job_id"]
    
    # In TestClient, background tasks run synchronously during the request.
    # Therefore, the job should already be completed when we poll it.
    job_response = client.get(f"/api/jobs/{job_id}")
    assert job_response.status_code == 200
    
    job_data = job_response.json()
    assert job_data["status"] == "completed"
    assert job_data["progress"] == 100
    assert job_data["result"]["filename"] == "test.mp3"
    assert job_data["result"]["duration"] == 10.0
    assert job_data["result"]["transcript"] == "Hello world"
    assert job_data["result"]["summary"] == "Hello summary"


def test_process_meeting_invalid_format():
    client = TestClient(app)
    files = {"file": ("test.txt", b"invalid text", "text/plain")}
    response = client.post("/api/process-meeting", files=files)
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


@patch("app.main.ask_meeting")
def test_chat_with_meeting_success(mock_ask):
    mock_ask.return_value = "The project is due next Monday."
    
    # Save a meeting first to query
    from app.database import save_meeting
    meeting_id = save_meeting(
        filename="meeting.mp3",
        duration=10.0,
        transcript="We must submit the project next Monday.",
        summary="Summary",
        action_items=[],
        entities=[]
    )
    
    client = TestClient(app)
    response = client.post(
        f"/api/meetings/{meeting_id}/chat",
        json={"question": "When is the project due?"}
    )
    
    assert response.status_code == 200
    assert response.json()["answer"] == "The project is due next Monday."
    mock_ask.assert_called_once_with("We must submit the project next Monday.", "When is the project due?")


def test_chat_with_meeting_404():
    client = TestClient(app)
    response = client.post(
        "/api/meetings/999/chat",
        json={"question": "When is the project due?"}
    )
    assert response.status_code == 404


@patch("app.main.get_all_models_status")
def test_get_models_endpoint(mock_status):
    mock_status.return_value = {"asr": [], "specs": {"ram_gb": 8.0}}
    client = TestClient(app)
    response = client.get("/api/models")
    assert response.status_code == 200
    assert response.json()["specs"]["ram_gb"] == 8.0


@patch("app.main.is_whisper_model_cached")
@patch("app.main.is_hf_model_cached")
@patch("app.main.save_model_config")
def test_set_active_models_endpoint_success(mock_save, mock_hf, mock_whisper):
    mock_whisper.return_value = True
    mock_hf.return_value = True
    
    client = TestClient(app)
    payload = {
        "asr_provider": "faster-whisper",
        "asr_model": "base",
        "summarizer_model": "sshleifer/distilbart-cnn-12-6",
        "llm_model": "Qwen/Qwen2.5-0.5B-Instruct"
    }
    response = client.post("/api/models/active", json=payload)
    assert response.status_code == 200
    assert "updated successfully" in response.json()["message"]
    mock_save.assert_called_once_with(payload)


@patch("app.main.is_whisper_model_cached")
@patch("app.main.is_hf_model_cached")
def test_set_active_models_endpoint_uncached_error(mock_hf, mock_whisper):
    mock_whisper.return_value = False
    mock_hf.return_value = False
    
    client = TestClient(app)
    payload = {
        "asr_provider": "faster-whisper",
        "asr_model": "base",
        "summarizer_model": "sshleifer/distilbart-cnn-12-6",
        "llm_model": "Qwen/Qwen2.5-0.5B-Instruct"
    }
    response = client.post("/api/models/active", json=payload)
    assert response.status_code == 400
    assert "is not cached offline" in response.json()["detail"]


@patch("app.main.download_model_background")
def test_queue_model_download_endpoint(mock_download):
    client = TestClient(app)
    response = client.post(
        "/api/models/download",
        json={"model_type": "asr", "model_id": "tiny"}
    )
    assert response.status_code == 200
    assert "queued" in response.json()["message"]


@patch("app.main.get_download_status")
def test_get_model_download_status_endpoint(mock_status):
    mock_status.return_value = {"status": "completed", "progress": 100}
    client = TestClient(app)
    response = client.get("/api/models/download/Qwen/Qwen2.5-0.5B-Instruct")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


