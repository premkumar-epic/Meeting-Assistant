from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from app.services.summarizer import summarize_text


def test_summarize_text_empty():
    assert summarize_text("") == ""
    assert summarize_text("   ") == ""


@patch("app.services.summarizer._get_summarizer_pipeline")
def test_summarize_text_single_chunk(mock_get_pipeline):
    mock_pipeline = MagicMock()
    mock_tokenizer = MagicMock()
    
    # Mock tokenizer output for short text (50 tokens)
    mock_tokenizer.return_value = {"input_ids": [1] * 50}
    mock_pipeline.return_value = [{"summary_text": "This is a summary."}]
    
    mock_get_pipeline.return_value = {
        "pipeline": mock_pipeline,
        "tokenizer": mock_tokenizer
    }
    
    result = summarize_text("short text input", max_chunk_tokens=100)
    assert result == "This is a summary."
    mock_pipeline.assert_called_once()
    
    args, kwargs = mock_pipeline.call_args
    assert kwargs["min_length"] > 0
    assert kwargs["max_length"] > kwargs["min_length"]


@patch("app.services.summarizer._get_summarizer_pipeline")
def test_summarize_text_hierarchical(mock_get_pipeline):
    mock_pipeline = MagicMock()
    mock_tokenizer = MagicMock()
    
    # Call sequence sequence:
    # 1. Total tokens check for input: 150 tokens.
    # 2. Since 150 > max_chunk_tokens (50), it decodes 3 chunks.
    # 3. For each of the 3 chunks, it measures chunk token length.
    # 4. Recursion: Total tokens check for combined text: 40 tokens.
    # 5. Since 40 <= 50, it summarizes directly.
    mock_tokenizer.side_effect = [
        {"input_ids": [1] * 150},  # Initial input count
        {"input_ids": [1] * 40},   # Chunk 1 count
        {"input_ids": [1] * 40},   # Chunk 2 count
        {"input_ids": [1] * 40},   # Chunk 3 count
        {"input_ids": [1] * 40},   # Recursive call input count
    ]
    
    # Mock decoding of chunks
    mock_tokenizer.decode.side_effect = [
        "chunk 1 text",
        "chunk 2 text",
        "chunk 3 text",
    ]
    
    # Pipeline returns for the 3 chunks and then the final summary
    mock_pipeline.side_effect = [
        [{"summary_text": "sum 1"}],
        [{"summary_text": "sum 2"}],
        [{"summary_text": "sum 3"}],
        [{"summary_text": "final combined summary"}]
    ]
    
    mock_get_pipeline.return_value = {
        "pipeline": mock_pipeline,
        "tokenizer": mock_tokenizer
    }
    
    result = summarize_text("long text input here...", max_chunk_tokens=50)
    assert result == "final combined summary"
    assert mock_pipeline.call_count == 4


@patch("app.services.summarizer._get_summarizer_pipeline")
def test_summarize_text_extremely_short_guardrail(mock_get_pipeline):
    mock_pipeline = MagicMock()
    mock_tokenizer = MagicMock()
    
    # Very short input (3 tokens)
    mock_tokenizer.return_value = {"input_ids": [1] * 3}
    
    mock_get_pipeline.return_value = {
        "pipeline": mock_pipeline,
        "tokenizer": mock_tokenizer
    }
    
    # Should bypass model call and return input directly
    result = summarize_text("Hi", max_chunk_tokens=50, min_length=30, max_length=150)
    assert result == "Hi"
    mock_pipeline.assert_not_called()


@patch("app.services.summarizer._get_summarizer_pipeline")
def test_summarize_text_chunk_failure_fallback(mock_get_pipeline):
    mock_pipeline = MagicMock()
    mock_tokenizer = MagicMock()
    
    # Input has 70 tokens, max_chunk_tokens = 50
    mock_tokenizer.side_effect = [
        {"input_ids": [1] * 70},  # Initial input count
        {"input_ids": [1] * 40},  # Chunk 1 count
        {"input_ids": [1] * 30},  # Chunk 2 count
        {"input_ids": [1] * 40},  # Recursive call input count
    ]
    
    mock_tokenizer.decode.side_effect = [
        "chunk 1 original text content",
        "chunk 2 original text content",
    ]
    
    # Chunk 1 summarization succeeds; chunk 2 fails (raises exception)
    mock_pipeline.side_effect = [
        [{"summary_text": "sum 1"}],
        Exception("Summarizer failed internally"),
        [{"summary_text": "final fallback summary"}]
    ]
    
    mock_get_pipeline.return_value = {
        "pipeline": mock_pipeline,
        "tokenizer": mock_tokenizer
    }
    
    result = summarize_text("long text with failing chunk", max_chunk_tokens=50)
    assert result == "final fallback summary"
    assert mock_pipeline.call_count == 3
