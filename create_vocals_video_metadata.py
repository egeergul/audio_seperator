#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from services.video_metadata import create_video_metadata_for_vocals, find_vocals_audio_in_folder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a video metadata text file from the vocals track in the provided "
            "folder. Expects a '<run_name>_vocals.mp3' file (or a single '*_vocals.mp3')."
        )
    )
    parser.add_argument("song_name", help="Song name (e.g. Golden)")
    parser.add_argument("artist_name", help="Artist name (e.g. Harry Styles)")
    parser.add_argument(
        "folder_path",
        help="Folder containing the vocals file (expects <run_name>_vocals.mp3)",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Language key for the template (default: en)",
    )
    return parser.parse_args()


def run() -> int:
    try:
        args = parse_args()
        vocals_path = find_vocals_audio_in_folder(Path(args.folder_path))
        output_path = create_video_metadata_for_vocals(
            vocals_audio_path=vocals_path,
            song_name=args.song_name,
            artist_name=args.artist_name,
            language=args.language,
        )
        print(f"Video metadata created: {output_path}")
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
