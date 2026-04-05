#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from services.config import OUTPUTS_DIR
from services.youtube_upload import upload_video_to_youtube

RELEASED_DIR = OUTPUTS_DIR.parent / ".released"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload a video to YouTube with metadata from a text file."
    )
    parser.add_argument("video_path", help="Path to the video file (.mp4).")
    parser.add_argument("metadata_path", help="Path to the metadata text file (_video_texts.txt).")
    parser.add_argument(
        "--privacy",
        choices=["private", "unlisted", "public"],
        default="public",
        help="Privacy status for the uploaded video (default: public).",
    )
    return parser.parse_args()


def _move_to_released(run_dir: Path) -> Path:
    RELEASED_DIR.mkdir(parents=True, exist_ok=True)
    dest = RELEASED_DIR / run_dir.name
    if dest.exists():
        raise FileExistsError(f"Already exists in .released: {dest}")
    shutil.move(str(run_dir), str(dest))
    return dest


def main() -> int:
    try:
        args = parse_args()
        video_path = Path(args.video_path).expanduser().resolve()
        metadata_path = Path(args.metadata_path).expanduser().resolve()

        print("YouTube Video Uploader")
        print("======================")
        print(f"Video:    {video_path}")
        print(f"Metadata: {metadata_path}")
        print(f"Privacy:  {args.privacy}")

        video_id = upload_video_to_youtube(
            video_file_path=video_path,
            metadata_text_path=metadata_path,
            privacy_status=args.privacy,
        )

        print(f"\nUpload complete!")
        print(f"Video ID: {video_id}")
        print(f"URL:      https://www.youtube.com/watch?v={video_id}")

        run_dir = video_path.parent
        if run_dir.parent == OUTPUTS_DIR:
            released_path = _move_to_released(run_dir)
            print(f"Moved:    {run_dir} -> {released_path}")
        else:
            print(f"Skipped move: video is not inside .outputs/")
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
