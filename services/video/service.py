from __future__ import annotations

import tempfile
from pathlib import Path

from .captions import render_caption_image
from .ffmpeg import (
    build_ffmpeg_command,
    check_video_prerequisites,
    probe_audio_duration_seconds,
    run_ffmpeg_command,
)
from .spec import VideoSpec


def create_video_from_transcription(spec: VideoSpec) -> Path:
    check_video_prerequisites()
    spec.output_video_path.parent.mkdir(parents=True, exist_ok=True)
    duration_seconds = probe_audio_duration_seconds(spec.kareoke_audio_path)

    with tempfile.TemporaryDirectory(prefix="video_overlays_") as tmp_dir:
        overlay_dir = Path(tmp_dir)
        overlays = [
            render_caption_image(
                overlay_dir,
                item.text,
                spec.video_width,
                spec.video_height,
                idx,
            )
            for idx, item in enumerate(spec.content)
        ]
        cmd = build_ffmpeg_command(spec, duration_seconds, overlays)
        run_ffmpeg_command(cmd)

    return spec.output_video_path

