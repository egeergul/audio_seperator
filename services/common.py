from __future__ import annotations

import os
import subprocess
from pathlib import Path


def run_command(cmd: list[str], cwd: Path | None = None) -> None:
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
    except subprocess.CalledProcessError as exc:
        joined = " ".join(cmd)
        raise RuntimeError(f"Command failed: {joined}") from exc


def derive_run_name(folder_path: Path) -> str:
    resolved = folder_path.resolve()
    run_name = resolved.name.strip()
    if not run_name:
        raise ValueError(f"Could not derive run name from folder: {folder_path}")
    return run_name


def validate_output_folder(output_folder: Path) -> Path:
    resolved = output_folder.expanduser().resolve()
    if not resolved.is_dir():
        raise FileNotFoundError(
            f"Output folder does not exist or is not a directory: {resolved}"
        )
    return resolved


def validate_readable_file(file_path: Path) -> Path:
    resolved = file_path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"File not found: {resolved}")
    if not os.access(resolved, os.R_OK):
        raise PermissionError(f"File is not readable: {resolved}")
    return resolved

