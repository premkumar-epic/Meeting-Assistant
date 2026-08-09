from __future__ import annotations

import pytest
from unittest.mock import patch
from app.database import init_db, save_meeting, get_all_meetings, get_meeting_by_id, delete_meeting


@pytest.fixture(autouse=True)
def mock_db_connection(tmp_path):
    # Redirect DB path to a temporary database file in testing
    test_db_path = tmp_path / "test_meeting_assistant.db"
    with patch("app.database.DB_PATH", test_db_path):
        init_db()
        yield


def test_db_save_and_retrieve():
    action_items = [{"id": 0, "text": "Task 1", "assignee": "Alice"}]
    entities = [{"text": "Alice", "label": "PERSON"}]
    
    # Save a meeting
    meeting_id = save_meeting(
        filename="meeting_1.mp3",
        duration=120.5,
        transcript="Hello John.",
        summary="Short meeting summary.",
        action_items=action_items,
        entities=entities
    )
    
    assert meeting_id > 0
    
    # Retrieve all meetings
    meetings = get_all_meetings()
    assert len(meetings) == 1
    assert meetings[0]["id"] == meeting_id
    assert meetings[0]["filename"] == "meeting_1.mp3"
    assert meetings[0]["duration"] == 120.5
    
    # Retrieve single meeting by ID
    detail = get_meeting_by_id(meeting_id)
    assert detail is not None
    assert detail["transcript"] == "Hello John."
    assert detail["summary"] == "Short meeting summary."
    assert detail["action_items"] == action_items
    assert detail["entities"] == entities


def test_db_get_non_existent():
    assert get_meeting_by_id(999) is None


def test_db_delete():
    meeting_id = save_meeting(
        filename="temp.mp3",
        duration=10.0,
        transcript="Temp.",
        summary="Temp.",
        action_items=[],
        entities=[]
    )
    
    assert len(get_all_meetings()) == 1
    delete_meeting(meeting_id)
    assert len(get_all_meetings()) == 0
