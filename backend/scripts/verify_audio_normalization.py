from __future__ import annotations

import argparse
from pathlib import Path
import sys
import wave

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.audio_processor import normalize_audio
from app.utils.temp_files import safe_unlink


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify audio normalization to 16kHz mono WAV for a sample audio file."
    )
    parser.add_argument("input", help="Path to the input audio file (mp3/wav/m4a/...)")
    parser.add_argument(
        "--output",
        help="Optional output WAV path. If omitted, a temp output is generated and cleaned up.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}")
        return 1

    generated_temp = args.output is None
    output_path = normalize_audio(str(input_path), args.output)

    with wave.open(output_path, "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_rate = wav_file.getframerate()
        sample_width_bits = wav_file.getsampwidth() * 8
        duration = wav_file.getnframes() / float(sample_rate)

    print("[OK] Normalization complete")
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Channels: {channels}")
    print(f"Sample rate: {sample_rate} Hz")
    print(f"Sample width: {sample_width_bits} bit")
    print(f"Duration: {duration:.2f} sec")

    if generated_temp:
        safe_unlink(output_path)
        print("[OK] Cleaned up generated temp output file")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
