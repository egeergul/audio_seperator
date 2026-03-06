#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from services.waveform import create_audio_waveform_image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a waveform PNG image from an audio file. "
            "Defaults to <audio_stem>_waveform.png beside the input."
        )
    )
    parser.add_argument("audio_path", help="Path to input audio file")
    parser.add_argument(
        "--output-image-path",
        default=None,
        help="Optional output PNG path (default: beside input audio)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1920,
        help="Waveform image width in pixels (default: 1920)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=400,
        help="Waveform image height in pixels (default: 400)",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=22050,
        help="Decode sample rate used for visualization (default: 22050)",
    )
    parser.add_argument(
        "--background-color",
        default="#0B1020",
        help="Background color (default: #0B1020)",
    )
    parser.add_argument(
        "--waveform-color",
        default="#38BDF8",
        help="Wave color (default: #38BDF8)",
    )
    parser.add_argument(
        "--center-line-color",
        default="#1E293B",
        help="Center line color (default: #1E293B)",
    )
    return parser.parse_args()


def run() -> int:
    try:
        args = parse_args()
        output_path = (
            Path(args.output_image_path).expanduser()
            if args.output_image_path is not None
            else None
        )
        image_path = create_audio_waveform_image(
            audio_path=Path(args.audio_path).expanduser(),
            output_image_path=output_path,
            width=args.width,
            height=args.height,
            sample_rate=args.sample_rate,
            background_color=args.background_color,
            waveform_color=args.waveform_color,
            center_line_color=args.center_line_color,
        )
        print(f"Waveform image created: {image_path}")
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
