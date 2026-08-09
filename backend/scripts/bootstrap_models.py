from __future__ import annotations

import os
import sys
from pathlib import Path

# Insert project root into sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import ASR_SETTINGS, SUMMARIZER_SETTINGS, LLM_SETTINGS


def bootstrap_spacy() -> None:
    print("[INFO] Checking spaCy 'en_core_web_sm' model...")
    try:
        import spacy
        spacy.load("en_core_web_sm")
        print("[OK] spaCy model is already installed.")
    except OSError:
        print("[INFO] Downloading spaCy model 'en_core_web_sm'...")
        import subprocess
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
        print("[OK] spaCy model downloaded successfully.")


def bootstrap_whisper() -> None:
    model_name = ASR_SETTINGS.model_name
    print(f"[INFO] Checking Whisper model '{model_name}'...")
    import whisper
    # Whisper automatically checks cache and downloads if missing
    whisper.load_model(model_name)
    print(f"[OK] Whisper model '{model_name}' cached successfully.")


def bootstrap_summarizer() -> None:
    model_name = SUMMARIZER_SETTINGS.model_name
    print(f"[INFO] Checking Summarizer model '{model_name}'...")
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    
    # Pre-download tokenizer and weights
    AutoTokenizer.from_pretrained(model_name)
    AutoModelForSeq2SeqLM.from_pretrained(model_name)
    print(f"[OK] Summarizer model '{model_name}' cached successfully.")


def bootstrap_llm() -> None:
    model_name = LLM_SETTINGS.model_name
    print(f"[INFO] Checking Q&A LLM model '{model_name}' (Qwen)...")
    from transformers import AutoTokenizer, AutoModelForCausalLM
    
    AutoTokenizer.from_pretrained(model_name)
    # Using float16/bfloat16 or auto mapping is best
    AutoModelForCausalLM.from_pretrained(model_name)
    print(f"[OK] Q&A LLM model '{model_name}' cached successfully.")


def main() -> int:
    print("=== AI-Powered Meeting Assistant Model Bootstrap ===")
    print("Pre-downloading all models to ensure complete offline reliability...")
    
    try:
        bootstrap_spacy()
        bootstrap_whisper()
        bootstrap_summarizer()
        bootstrap_llm()
        print("\n[SUCCESS] All models cached successfully. You can now run completely offline!")
        return 0
    except Exception as exc:
        print(f"\n[ERROR] Bootstrap failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
