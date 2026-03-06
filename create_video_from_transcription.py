#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.video import build_video_spec, create_video_from_transcription


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a lyric video from <run_name>_transcription.json and audio paths."
        )
    )
    parser.add_argument(
        "transcription_json_path",
        help="Path to <run_name>_transcription.json",
    )
    parser.add_argument("vocals_audio_path", help="Path to <run_name>_vocals.mp3")
    parser.add_argument("kareoke_audio_path", help="Path to <run_name>_kareoke.mp3")
    parser.add_argument(
        "--width",
        type=int,
        default=1920,
        help="Output video width (default: 1920)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=1080,
        help="Output video height (default: 1080)",
    )
    parser.add_argument(
        "--output-video-path",
        default=None,
        help="Optional output video path (default: <run_name>.mp4 next to transcription)",
    )
    return parser.parse_args()


def run() -> int:
    try:
        args = parse_args()
        output_video_path = (
            Path(args.output_video_path).expanduser()
            if args.output_video_path is not None
            else None
        )
        spec = build_video_spec(
            transcription_path=Path(args.transcription_json_path).expanduser(),
            vocals_audio_path=Path(args.vocals_audio_path).expanduser(),
            kareoke_audio_path=Path(args.kareoke_audio_path).expanduser(),
            video_width=args.width,
            video_height=args.height,
            output_video_path=output_video_path,
        )
        created_video_path = create_video_from_transcription(spec)
        print(f"Video created successfully: {created_video_path}")
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
