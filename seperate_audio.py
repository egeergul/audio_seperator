#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from services.separation import seperate_audio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Separate an original audio file into vocals and kareoke tracks in "
            "the same folder."
        )
    )
    parser.add_argument(
        "original_file_path",
        help="Path to <run_name>_original.mp3 (or another readable source audio)",
    )
    return parser.parse_args()


def run() -> int:
    try:
        args = parse_args()
        original_file_path = Path(args.original_file_path).expanduser()
        vocals_path, kareoke_path = seperate_audio(original_file_path)
        print(f"Vocals: {vocals_path}")
        print(f"Kareoke: {kareoke_path}")
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
