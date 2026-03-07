#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from services.pitch import extract_note_pitches, write_pitch_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract sung melody note events from an audio file using Basic Pitch "
            "and write <run_name>_pitches.json beside the input."
        )
    )
    parser.add_argument("audio_path", help="Path to input audio file (for example: xxx_vocals.mp3)")
    parser.add_argument(
        "--output-json-path",
        default=None,
        help="Optional output JSON path (default: beside input audio)",
    )
    return parser.parse_args()


def run() -> int:
    try:
        args = parse_args()
        audio_path = Path(args.audio_path).expanduser()
        output_json_path = (
            Path(args.output_json_path).expanduser()
            if args.output_json_path is not None
            else None
        )

        payload = extract_note_pitches(audio_path)
        output_path = write_pitch_json(
            audio_path=audio_path,
            payload=payload,
            output_path=output_json_path,
        )

        print("Pitch extraction completed successfully.")
        print(f"Audio: {audio_path.resolve()}")
        print(f"Output: {output_path}")
        print(f"Notes: {payload.get('note_count', 0)}")
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
