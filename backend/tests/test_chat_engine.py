from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from app.services.chat_engine import ask_meeting


def test_ask_meeting_empty_inputs():
    assert "transcript is empty" in ask_meeting("", "What was decided?")
    assert "valid question" in ask_meeting("Hello world", "")


@patch("app.services.chat_engine._get_chat_pipeline")
def test_ask_meeting_success(mock_get_pipe):
    # Setup mock pipeline
    mock_pipe = MagicMock()
    mock_pipe.tokenizer.eos_token_id = 50256
    
    # Mocking apply_chat_template to return a dummy prompt string
    mock_pipe.tokenizer.apply_chat_template.return_value = "<PROMPT>"
    
    # Mocking pipeline generation call
    mock_pipe.return_value = [{"generated_text": "<PROMPT>The action items were assigned to John."}]
    mock_get_pipe.return_value = mock_pipe
    
    transcript = "We discussed project deadlines. John is assigned to review the database schema."
    question = "Who is assigned to the database schema?"
    
    response = ask_meeting(transcript, question)
    assert response == "The action items were assigned to John."
    
    # Verify tokenizer formatting was called with correct context
    args, kwargs = mock_pipe.tokenizer.apply_chat_template.call_args
    messages = args[0]
    
    assert messages[0]["role"] == "system"
    assert "John is assigned to review the database schema." in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == question
