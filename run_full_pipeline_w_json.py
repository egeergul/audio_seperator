#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from services.download import download_youtube_audio
from services.folder import create_normalized_run_folder
from services.separation import seperate_audio
from services.transcription import transcribe_audio, write_transcription_json
from services.video import build_video_spec, create_video_from_transcription
from services.video_metadata import create_video_metadata_for_vocals

SUPPORTED_MODELS = [
    "tiny",
    "tiny.en",
    "base",
    "base.en",
    "small",
    "small.en",
    "medium",
    "medium.en",
    "large",
    "large-v1",
    "large-v2",
    "large-v3",
    "turbo",
]

SUPPORTED_DEVICES = {"auto", "cpu", "cuda"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the full audio pipeline using a JSON config file."
    )
    parser.add_argument("json_path", help="Path to JSON config file.")
    return parser.parse_args()


def _load_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    if not path.is_file():
        raise ValueError(f"JSON path must be a file: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        return [data]
    if not isinstance(data, list):
        raise ValueError("Top-level JSON must be a list of objects.")
    if not data:
        raise ValueError("Top-level JSON list cannot be empty.")
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Entry {index} must be an object.")
    return data


def _get_required_str(data: dict[str, Any], key: str) -> str:
    if key not in data:
        raise ValueError(f"Missing required field: {key}")
    value = data[key]
    if not isinstance(value, str):
        raise ValueError(f"Field '{key}' must be a string.")
    value = value.strip()
    if not value:
        raise ValueError(f"Field '{key}' cannot be empty.")
    return value


def _get_optional_str(
    data: dict[str, Any], key: str, default: str | None
) -> str | None:
    if key not in data:
        return default
    value = data[key]
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Field '{key}' must be a string or null.")
    value = value.strip()
    if value == "":
        return default
    return value


def _get_optional_positive_int(
    data: dict[str, Any],
    key: str,
    default: int,
    aliases: Iterable[str] = (),
) -> int:
    value = None
    if key in data:
        value = data[key]
    else:
        for alias in aliases:
            if alias in data:
                value = data[alias]
                break
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"Field '{key}' must be an integer greater than 0.")
    if isinstance(value, str):
        if value.strip() == "":
            return default
        try:
            value = int(value)
        except ValueError as exc:
            raise ValueError(f"Field '{key}' must be an integer.") from exc
    elif isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"Field '{key}' must be an integer.")
        value = int(value)
    elif not isinstance(value, int):
        raise ValueError(f"Field '{key}' must be an integer.")
    if value <= 0:
        raise ValueError(f"Field '{key}' must be greater than 0.")
    return int(value)


def _run_single(config: dict[str, Any], index: int, total: int) -> None:
    raw_folder_name = _get_required_str(config, "folder_name")
    youtube_url = _get_required_str(config, "youtube_url")
    model_name = _get_optional_str(config, "model", default="small")
    language = _get_optional_str(config, "language", default=None)
    device = _get_optional_str(config, "device", default="auto")
    width = _get_optional_positive_int(
        config, "video_width", default=1920, aliases=("width",)
    )
    height = _get_optional_positive_int(
        config, "video_height", default=1080, aliases=("height",)
    )
    song_name = _get_required_str(config, "song_name")
    artist_name = _get_required_str(config, "artist_name")
    metadata_language = _get_optional_str(config, "metadata_language", default="en")

    if model_name is None:
        model_name = "small"
    if device is None:
        device = "auto"
    if metadata_language is None:
        metadata_language = "en"

    if model_name not in SUPPORTED_MODELS:
        raise ValueError(
            "Unsupported model. Choose one of: " + ", ".join(SUPPORTED_MODELS)
        )
    if device not in SUPPORTED_DEVICES:
        raise ValueError("Unsupported device. Use: auto, cpu, or cuda.")
    if metadata_language is None or not metadata_language.strip():
        raise ValueError("Field 'metadata_language' cannot be empty.")

    youtube_upload = config.get("youtube_upload", False)
    if not isinstance(youtube_upload, bool):
        raise ValueError("Field 'youtube_upload' must be a boolean.")
    privacy_status = _get_optional_str(config, "privacy_status", default="private")
    if privacy_status is None:
        privacy_status = "private"

    if total > 1:
        print(f"\n=== Run {index}/{total} ===")

    print("\nStep 1/7: Create run folder")
    run_dir = create_normalized_run_folder(raw_folder_name)
    run_name = run_dir.name
    print(f"Created: {run_dir}")

    print("\nStep 2/7: Download audio")
    original_audio_path = download_youtube_audio(youtube_url, run_dir)
    print(f"Downloaded: {original_audio_path}")

    print("\nStep 3/7: Separate vocals and kareoke")
    vocals_path, kareoke_path = seperate_audio(original_audio_path)
    print(f"Vocals:  {vocals_path}")
    print(f"Kareoke: {kareoke_path}")

    print("\nStep 4/7: Transcribe vocals")
    transcription_payload = transcribe_audio(
        audio_path=vocals_path,
        model_name=model_name,
        language=language,
        device=device,
    )
    transcription_path = write_transcription_json(vocals_path, transcription_payload)
    print(f"Transcription: {transcription_path}")

    print("\nStep 5/7: Create lyric videos (kareoke + vocals)")
    kareoke_video_spec = build_video_spec(
        transcription_path=transcription_path,
        mux_audio_path=kareoke_path,
        video_width=width,
        video_height=height,
        output_video_path=None,
    )
    vocals_video_spec = build_video_spec(
        transcription_path=transcription_path,
        mux_audio_path=vocals_path,
        video_width=width,
        video_height=height,
        output_video_path=None,
    )
    vocals_video_path = create_video_from_transcription(vocals_video_spec)
    # kareoke_video_path = create_video_from_transcription(kareoke_video_spec)
    # print(f"Kareoke video: {kareoke_video_path}")
    print(f"Vocals video:  {vocals_video_path}")

    print("\nStep 6/7: Create vocals video metadata")
    metadata_path = create_video_metadata_for_vocals(
        vocals_audio_path=vocals_path,
        song_name=song_name,
        artist_name=artist_name,
        language=metadata_language,
    )
    print(f"Video metadata: {metadata_path}")

    if youtube_upload:
        print("\nStep 7/7: Upload vocals video to YouTube")
        from services.youtube_upload import upload_video_to_youtube

        video_id = upload_video_to_youtube(
            video_file_path=vocals_video_path,
            metadata_text_path=metadata_path,
            privacy_status=privacy_status,
        )
        print(f"YouTube video ID: {video_id}")
        print(f"YouTube URL: https://www.youtube.com/watch?v={video_id}")
    else:
        print("\nStep 7/7: YouTube upload skipped (youtube_upload not set)")

    print("\nPipeline completed successfully.")
    print(f"Run name: {run_name}")
    print(f"Run dir:  {run_dir}")


def run() -> int:
    print("Audio Scraper Full Pipeline (JSON)")
    print("==================================")

    try:
        args = parse_args()
        config_path = Path(args.json_path).expanduser()
        configs = _load_json(config_path)

        print(f"\nConfig: {config_path.resolve()}")

        for index, config in enumerate(configs, start=1):
            _run_single(config, index=index, total=len(configs))
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
