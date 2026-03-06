#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys

from services.folder import create_normalized_run_folder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize a run name and create a new folder under .outputs/. "
            "Prints the absolute folder path."
        )
    )
    parser.add_argument("name", help="Run name to normalize and create")
    return parser.parse_args()


def run() -> int:
    try:
        args = parse_args()
        run_dir = create_normalized_run_folder(args.name)
        print(str(run_dir))
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
