#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from services.pitch import (
    derive_pitch_midi_output_path,
    read_pitch_json,
    write_pitch_midi,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a pitch JSON file to a MIDI file. "
            "Default output is the same path with .mid extension."
        )
    )
    parser.add_argument(
        "pitch_json_path",
        help="Path to input pitch JSON file (for example: xxx_pitches.json)",
    )
    parser.add_argument(
        "--output-midi-path",
        default=None,
        help="Optional output MIDI path (default: same path with .mid extension)",
    )
    return parser.parse_args()


def run() -> int:
    try:
        args = parse_args()
        pitch_json_path = Path(args.pitch_json_path).expanduser()
        output_midi_path = (
            Path(args.output_midi_path).expanduser()
            if args.output_midi_path is not None
            else derive_pitch_midi_output_path(pitch_json_path)
        )

        payload = read_pitch_json(pitch_json_path)
        written_midi_path = write_pitch_midi(
            payload=payload,
            output_midi_path=output_midi_path,
        )

        print("MIDI conversion completed successfully.")
        print(f"Input JSON: {pitch_json_path.resolve()}")
        print(f"Output MIDI: {written_midi_path}")
        print(f"Notes: {payload.get('note_count', len(payload.get('notes', [])))}")
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
