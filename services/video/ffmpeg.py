from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .spec import VideoSpec

FPS = 30


def _format_seconds(seconds: float) -> str:
    formatted = f"{seconds:.3f}".rstrip("0").rstrip(".")
    return formatted or "0"


def check_video_prerequisites() -> None:
    if shutil.which("ffmpeg") is None:
        raise EnvironmentError(
            "Missing required command: ffmpeg. Install ffmpeg and ensure it is on PATH."
        )
    if shutil.which("ffprobe") is None:
        raise EnvironmentError(
            "Missing required command: ffprobe. Install ffprobe and ensure it is on PATH."
        )


def probe_audio_duration_seconds(audio_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
    )
    duration_raw = result.stdout.strip()
    if not duration_raw:
        raise RuntimeError(f"ffprobe did not return duration for: {audio_path}")
    try:
        duration = float(duration_raw)
    except ValueError as exc:
        raise RuntimeError(
            f"Failed to parse audio duration '{duration_raw}' for: {audio_path}"
        ) from exc
    if duration <= 0:
        raise RuntimeError(f"Audio duration must be positive, got {duration}.")
    return duration


def build_ffmpeg_command(
    spec: VideoSpec, duration_seconds: float, overlays: list[Path]
) -> list[str]:
    color_input = (
        f"color=black:s={spec.video_width}x{spec.video_height}:"
        f"r={FPS}:d={_format_seconds(duration_seconds)}"
    )

    cmd: list[str] = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        color_input,
        "-i",
        str(spec.mux_audio_path),
    ]

    for overlay_path in overlays:
        cmd.extend(["-loop", "1", "-i", str(overlay_path)])

    if overlays:
        filter_parts: list[str] = []
        previous = "[0:v]"
        for idx, item in enumerate(spec.content):
            overlay_stream = f"[{idx + 2}:v]"
            output_stream = f"[v{idx + 1}]"
            start_s = _format_seconds(item.start_time_ms / 1000.0)
            end_s = _format_seconds(item.end_time_ms / 1000.0)
            filter_parts.append(
                f"{previous}{overlay_stream}overlay=x=0:y=0:"
                f"enable=between(t\\,{start_s}\\,{end_s}){output_stream}"
            )
            previous = output_stream

        cmd.extend(
            [
                "-filter_complex",
                ";".join(filter_parts),
                "-map",
                previous,
                "-map",
                "1:a",
            ]
        )
    else:
        cmd.extend(["-map", "0:v", "-map", "1:a"])

    cmd.extend(
        [
            "-t",
            _format_seconds(duration_seconds),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            "-shortest",
            str(spec.output_video_path),
        ]
    )

    return cmd


def run_ffmpeg_command(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("ffmpeg command failed. See logs above for details.") from exc
