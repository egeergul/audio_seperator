#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.pipeline import download_youtube_audio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download YouTube audio into a run folder as "
            "<run_name>_original.mp3."
        )
    )
    parser.add_argument("youtube_url", help="YouTube URL")
    parser.add_argument("output_folder_path", help="Existing run folder path")
    return parser.parse_args()


def run() -> int:
    try:
        args = parse_args()
        output_folder = Path(args.output_folder_path).expanduser()
        audio_file = download_youtube_audio(args.youtube_url, output_folder)
        print(str(audio_file))
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
