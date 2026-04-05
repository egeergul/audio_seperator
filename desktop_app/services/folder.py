from __future__ import annotations

import re
from pathlib import Path

from .config import OUTPUTS_DIR


def sanitize_creation_name(raw_name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_name).strip("._-")
    if not sanitized:
        raise ValueError("Creation name is invalid after sanitization.")
    return sanitized


def create_run_folder(creation_name: str) -> Path:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    run_dir = OUTPUTS_DIR / creation_name
    if run_dir.exists():
        raise FileExistsError(
            f"Folder already exists: {run_dir}. Use a different creation name."
        )
    run_dir.mkdir(parents=False, exist_ok=False)
    return run_dir.resolve()


def create_normalized_run_folder(raw_name: str) -> Path:
    creation_name = sanitize_creation_name(raw_name)
    return create_run_folder(creation_name)
