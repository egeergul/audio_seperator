from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import CaptionItem, load_transcription_chunks


@dataclass(frozen=True)
class VideoSpec:
    transcription_path: Path
    vocals_audio_path: Path
    kareoke_audio_path: Path
    video_width: int
    video_height: int
    output_video_path: Path
    content: list[CaptionItem]


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_readable_file(path: Path, field_name: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{field_name} not found: {resolved}")
    if not os.access(resolved, os.R_OK):
        raise PermissionError(f"{field_name} is not readable: {resolved}")
    return resolved


def _derive_run_name(folder_path: Path) -> str:
    run_name = folder_path.resolve().name.strip()
    if not run_name:
        raise ValueError(f"Could not derive run name from folder: {folder_path}")
    return run_name


def build_video_spec(
    transcription_path: Path,
    vocals_audio_path: Path,
    kareoke_audio_path: Path,
    video_width: int,
    video_height: int,
    output_video_path: Path | None = None,
) -> VideoSpec:
    if not _is_int(video_width) or video_width <= 0:
        raise ValueError("video width must be an integer greater than 0.")
    if not _is_int(video_height) or video_height <= 0:
        raise ValueError("video height must be an integer greater than 0.")

    resolved_transcription_path = _require_readable_file(
        transcription_path, "Transcription file"
    )
    resolved_vocals_audio_path = _require_readable_file(vocals_audio_path, "Vocals audio")
    resolved_kareoke_audio_path = _require_readable_file(
        kareoke_audio_path, "Kareoke audio"
    )

    content = load_transcription_chunks(resolved_transcription_path)
    run_dir = resolved_transcription_path.parent
    run_name = _derive_run_name(run_dir)

    resolved_output_video_path = (
        output_video_path.expanduser().resolve()
        if output_video_path is not None
        else (run_dir / f"{run_name}.mp4").resolve()
    )

    return VideoSpec(
        transcription_path=resolved_transcription_path,
        vocals_audio_path=resolved_vocals_audio_path,
        kareoke_audio_path=resolved_kareoke_audio_path,
        video_width=video_width,
        video_height=video_height,
        output_video_path=resolved_output_video_path,
        content=content,
    )

