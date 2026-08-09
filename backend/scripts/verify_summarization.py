from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.summarizer import summarize_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify local summarizer with tokenizer-aware chunking."
    )
    parser.add_argument("input", help="Path to input text file or segments JSON file")
    parser.add_argument(
        "--model",
        default="sshleifer/distilbart-cnn-12-6",
        help="Summarizer model name (default: sshleifer/distilbart-cnn-12-6)",
    )
    parser.add_argument(
        "--max-chunk-tokens",
        type=int,
        default=800,
        help="Max chunk tokens size (default: 800)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}")
        return 1

    content = input_path.read_text(encoding="utf-8")
    
    # Try parsing as JSON to see if it's a segments file from transcription
    try:
        data = json.loads(content)
        if isinstance(data, list) and len(data) > 0 and "text" in data[0]:
            text = " ".join(seg["text"] for seg in data).strip()
        else:
            text = content
    except json.JSONDecodeError:
        text = content

    print(f"Input text character count: {len(text)}")
    print("Loading model and generating summary (this may take a moment on first download)...")
    
    summary = summarize_text(
        text,
        model_name=args.model,
        max_chunk_tokens=args.max_chunk_tokens,
    )
    
    print("\n[OK] Summarization complete")
    print(f"Summary length: {len(summary)} characters")
    print("\nSummary output:")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
