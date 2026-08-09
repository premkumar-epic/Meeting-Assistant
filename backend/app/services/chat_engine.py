from __future__ import annotations

import torch
import threading
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, TextIteratorStreamer
from typing import Any, Iterator
from app.config import LLM_SETTINGS

# Global cache to prevent reloading model on every query
_CHAT_LOCK = threading.Lock()
_CHAT_PIPELINE: Any = None


def _get_chat_pipeline(model_name: str) -> Any:
    global _CHAT_PIPELINE
    with _CHAT_LOCK:
        if _CHAT_PIPELINE is None:
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            
            # Load model on selected device with memory optimizations
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=dtype,
                low_cpu_mem_usage=True
            )
            
            _CHAT_PIPELINE = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                device=0 if torch.cuda.is_available() else -1
            )
    return _CHAT_PIPELINE


def ask_meeting(transcript: str, question: str, history: list[dict[str, str]] = None) -> Iterator[str]:
    """
    Answer a user question based strictly on the provided transcript context.
    Enforces strict rules to prevent hallucinating external information.
    Yields tokens for SSE streaming.
    """
    if not transcript.strip():
        yield "I cannot find the answer to this question because the meeting transcript is empty."
        return
    if not question.strip():
        yield "Please enter a valid question."
        return

    # Build system instructions
    system_prompt = (
        "You are a strict, helpful meeting assistant. Answer the user's question using ONLY the provided meeting transcript context.\n"
        "Rules:\n"
        "1. Do not use external knowledge or assume facts outside the transcript.\n"
        "2. If the context does not contain the answer, reply exactly with: \"I cannot find the answer to this question in the meeting transcript.\"\n"
        "3. Keep the answer concise and truthful to the context."
    )

    from app.services.config_manager import get_model_config
    active_model = get_model_config()["llm_model"]
    pipe = _get_chat_pipeline(active_model)
    
    if history is None:
        history = []

    messages = [
        {"role": "system", "content": system_prompt}
    ]
    for h in history[-5:]:
        messages.append({"role": h["role"], "content": h["content"]})
    
    # Inject transcript into the latest user message so the model doesn't lose it over long histories
    user_prompt = f"Meeting Transcript Context:\n---\n{transcript.strip()}\n---\n\nQuestion: {question.strip()}"
    messages.append({"role": "user", "content": user_prompt})
    
    # Format chat template using tokenizer
    prompt = pipe.tokenizer.apply_chat_template(
        messages, 
        tokenize=False, 
        add_generation_prompt=True
    )
    
    streamer = TextIteratorStreamer(pipe.tokenizer, skip_prompt=True, skip_special_tokens=True)
    
    kwargs = dict(
        text_inputs=prompt,
        max_new_tokens=LLM_SETTINGS.max_new_tokens,
        temperature=LLM_SETTINGS.temperature,
        do_sample=LLM_SETTINGS.temperature > 0.0,
        pad_token_id=pipe.tokenizer.eos_token_id,
        streamer=streamer
    )
    
    thread = threading.Thread(target=pipe, kwargs=kwargs)
    thread.start()
    
    for text in streamer:
        yield text
