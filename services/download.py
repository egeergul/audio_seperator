from __future__ import annotations

import sys
from pathlib import Path

from .common import derive_run_name, run_command, validate_output_folder


def download_youtube_audio(youtube_url: str, output_folder: Path) -> Path:
    if not youtube_url.strip():
        raise ValueError("YouTube URL cannot be empty.")

    run_dir = validate_output_folder(output_folder)
    run_name = derive_run_name(run_dir)
    output_template = run_dir / f"{run_name}_original.%(ext)s"
    run_command(
        [
            sys.executable,
            "-m",
            "yt_dlp",
            "--no-playlist",
            "-x",
            "--audio-format",
            "mp3",
            "-o",
            str(output_template),
            youtube_url,
        ]
    )

    audio_file = run_dir / f"{run_name}_original.mp3"
    if not audio_file.is_file():
        raise RuntimeError(
            f"Expected downloaded file was not created: {audio_file}. "
            "Check yt-dlp/ffmpeg output above."
        )
    return audio_file.resolve()

