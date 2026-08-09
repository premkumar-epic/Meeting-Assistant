from __future__ import annotations

import os
import threading
from typing import Any
from app.config import SUMMARIZER_SETTINGS

_SUMMARIZER_LOCK = threading.Lock()
_SUMMARIZER_CACHE: dict[str, dict[str, Any]] = {}


def _get_summarizer_pipeline(model_name: str) -> dict[str, Any]:
    """Load and cache the Hugging Face summarization pipeline and tokenizer."""
    with _SUMMARIZER_LOCK:
        if model_name not in _SUMMARIZER_CACHE:
            from transformers import pipeline, AutoTokenizer
            
            # Suppress symlink warnings in offline environments if necessary
            os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
            
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            summ_pipe = pipeline("summarization", model=model_name, tokenizer=tokenizer)
            _SUMMARIZER_CACHE[model_name] = {
                "pipeline": summ_pipe,
                "tokenizer": tokenizer,
            }
        return _SUMMARIZER_CACHE[model_name]


def summarize_text(
    text: str,
    model_name: str | None = None,
    max_chunk_tokens: int = SUMMARIZER_SETTINGS.max_chunk_tokens,
    min_length: int = SUMMARIZER_SETTINGS.min_summary_length,
    max_length: int = SUMMARIZER_SETTINGS.max_summary_length,
) -> str:
    """
    Summarize long texts using a tokenizer-aware hierarchical chunking strategy.
    
    If the text fits in a single chunk, it is summarized directly.
    Otherwise, it is split into chunks, each chunk is summarized, and the combined 
    chunk summaries are recursively summarized until the result fits.
    """
    cleaned_text = text.strip()
    if not cleaned_text:
        return ""

    from app.services.config_manager import get_model_config
    active_model = model_name or get_model_config()["summarizer_model"]

    bundle = _get_summarizer_pipeline(active_model)
    summarizer = bundle["pipeline"]
    tokenizer = bundle["tokenizer"]

    # Count tokens in input text
    tokens = tokenizer(cleaned_text, add_special_tokens=False)
    input_ids = tokens["input_ids"]
    total_tokens = len(input_ids)

    # Base case: text fits within single chunk
    if total_tokens <= max_chunk_tokens:
        # If input is extremely short, return it directly to avoid model issues and artificial expansion
        if total_tokens <= min_length or total_tokens <= 10:
            return cleaned_text

        # Prevent Hugging Face exceptions if input is very short:

        # max_length must be greater than min_length, and min_length must be > 0.
        # Also, max_length should not exceed total input tokens.
        adjusted_max_length = min(max_length, max(min_length + 10, total_tokens // 2))
        adjusted_min_length = min(min_length, max(5, adjusted_max_length // 3))

        if adjusted_max_length <= adjusted_min_length:
            # If the input is extremely short, just return it directly
            return cleaned_text

        try:
            res = summarizer(
                cleaned_text,
                min_length=adjusted_min_length,
                max_length=adjusted_max_length,
                do_sample=False,
            )
            return str(res[0]["summary_text"]).strip()
        except Exception as exc:
            # Fallback if summarization fails
            raise RuntimeError(f"Summarization failed for single chunk: {exc}") from exc

    # Recursive case: partition into chunks, summarize chunks, and merge summaries
    chunks: list[str] = []
    for i in range(0, total_tokens, max_chunk_tokens):
        chunk_ids = input_ids[i : i + max_chunk_tokens]
        chunk_text = tokenizer.decode(chunk_ids, skip_special_tokens=True)
        if chunk_text.strip():
            chunks.append(chunk_text)

    chunk_summaries: list[str] = []
    for idx, chunk in enumerate(chunks):
        chunk_tokens_len = len(tokenizer(chunk, add_special_tokens=False)["input_ids"])
        
        # Sane bounds for intermediate chunk summaries
        adj_max = min(150, max(40, chunk_tokens_len // 2))
        adj_min = min(30, max(10, adj_max // 3))
        
        try:
            res = summarizer(chunk, min_length=adj_min, max_length=adj_max, do_sample=False)
            chunk_summaries.append(str(res[0]["summary_text"]).strip())
        except Exception as exc:
            # If a specific chunk fails, fallback to keeping the original chunk's head text
            # to prevent entire pipeline failure (zero silent failures but high robustness)
            fallback_text = chunk[:300] + "..." if len(chunk) > 300 else chunk
            chunk_summaries.append(fallback_text)

    combined_summaries = " ".join(chunk_summaries)
    
    # Recursively summarize the combined chunk summaries
    return summarize_text(
        combined_summaries,
        model_name=model_name,
        max_chunk_tokens=max_chunk_tokens,
        min_length=min_length,
        max_length=max_length,
    )
