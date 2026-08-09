from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.transcriber import transcribe_audio


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify local ASR transcription with sliding-window chunking."
    )
    parser.add_argument("input", help="Path to normalized or raw audio file")
    parser.add_argument(
        "--provider",
        default="openai-whisper",
        choices=["openai-whisper", "faster-whisper"],
        help="ASR backend provider (default: openai-whisper)",
    )
    parser.add_argument("--model", default="base", help="Whisper model name (default: base)")
    parser.add_argument("--window", type=int, default=30, help="Chunk window in seconds")
    parser.add_argument("--overlap", type=int, default=2, help="Chunk overlap in seconds")
    parser.add_argument(
        "--segments-json",
        help="Optional path to save segment output as JSON",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}")
        return 1

    result = transcribe_audio(
        str(input_path),
        provider=args.provider,
        model_name=args.model,
        window_seconds=args.window,
        overlap_seconds=args.overlap,
    )

    print("[OK] Transcription complete")
    print(f"Provider: {result['provider']}")
    print(f"Model: {result['model_name']}")
    print(f"Transcript length: {len(result['text'])} characters")
    print(f"Segment count: {len(result['segments'])}")
    print("Transcript preview:")
    print(result["text"][:600] or "(empty)")

    if args.segments_json:
        output_path = Path(args.segments_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result["segments"], indent=2), encoding="utf-8")
        print(f"[OK] Saved segments JSON: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
