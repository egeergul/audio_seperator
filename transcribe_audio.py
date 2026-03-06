#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from services.transcription import (
    transcribe_audio,
    write_transcription_json,
)

SUPPORTED_MODELS = [
    "tiny",
    "tiny.en",
    "base",
    "base.en",
    "small",
    "small.en",
    "medium",
    "medium.en",
    "large",
    "large-v1",
    "large-v2",
    "large-v3",
    "turbo",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Transcribe an audio file using Whisper and write a timestamped "
            "<run_name>_transcription.json next to the input file."
        )
    )
    parser.add_argument(
        "audio_path", help="Path to input vocals audio file (e.g. xxx_vocals.mp3)"
    )
    parser.add_argument(
        "--model",
        default="small",
        choices=SUPPORTED_MODELS,
        help="Whisper model name (default: small)",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Optional language code (for example: en, tr). If omitted, auto-detect.",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="Device selection (default: auto)",
    )

    return parser.parse_args()


def run() -> int:
    try:
        args = parse_args()
        audio_path = Path(args.audio_path).expanduser()

        payload = transcribe_audio(
            audio_path=audio_path,
            model_name=args.model,
            language=args.language,
            device=args.device,
        )
        output_path = write_transcription_json(audio_path, payload)

        print("Transcription completed successfully.")
        print(f"Audio: {audio_path.resolve()}")
        print(f"Output: {output_path}")
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
