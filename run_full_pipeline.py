#!/usr/bin/env python3

from __future__ import annotations

import sys

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


def _prompt_non_empty(label: str) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        print("Value cannot be empty. Please try again.")


def _prompt_optional(label: str, default: str | None = None) -> str | None:
    suffix = f" [{default}]" if default is not None else ""
    value = input(f"{label}{suffix}: ").strip()
    if not value:
        return default
    return value


def _prompt_model() -> str:
    print("\nTranscription model options:")
    print(", ".join(SUPPORTED_MODELS))
    while True:
        model = _prompt_optional("Model", default="small")
        if model in SUPPORTED_MODELS:
            return model
        print("Unsupported model. Choose one of the listed model names.")


def _prompt_language() -> str | None:
    language = _prompt_optional(
        "Language code (optional, e.g. en, tr; leave blank for auto-detect)",
        default=None,
    )
    if language is None:
        return None
    return language.strip() or None


def _prompt_metadata_language() -> str:
    language = _prompt_optional(
        "Metadata language key (e.g. en, tr)",
        default="en",
    )
    assert language is not None
    return language.strip() or "en"


def _prompt_device() -> str:
    while True:
        device = _prompt_optional("Device (auto/cpu/cuda)", default="auto")
        if device in SUPPORTED_DEVICES:
            return device
        print("Unsupported device. Use: auto, cpu, or cuda.")


def _prompt_positive_int(label: str, default: int) -> int:
    while True:
        value = _prompt_optional(label, default=str(default))
        assert value is not None  # default always set
        try:
            parsed = int(value)
        except ValueError:
            print("Please enter a valid integer.")
            continue
        if parsed <= 0:
            print("Please enter an integer greater than 0.")
            continue
        return parsed


def run() -> int:
    print("Audio Scraper Full Pipeline")
    print("===========================")

    try:
        print("\nStep 1/6: Create run folder")
        raw_folder_name = _prompt_non_empty("Folder name")
        run_dir = create_normalized_run_folder(raw_folder_name)
        run_name = run_dir.name
        print(f"Created: {run_dir}")

        print("\nStep 2/6: Download audio")
        youtube_url = _prompt_non_empty("YouTube URL")
        original_audio_path = download_youtube_audio(youtube_url, run_dir)
        print(f"Downloaded: {original_audio_path}")

        print("\nStep 3/6: Separate vocals and kareoke")
        vocals_path, kareoke_path = seperate_audio(original_audio_path)
        print(f"Vocals:  {vocals_path}")
        print(f"Kareoke: {kareoke_path}")

        print("\nStep 4/6: Transcribe vocals")
        model_name = _prompt_model()
        language = _prompt_language()
        device = _prompt_device()
        transcription_payload = transcribe_audio(
            audio_path=vocals_path,
            model_name=model_name,
            language=language,
            device=device,
        )
        transcription_path = write_transcription_json(vocals_path, transcription_payload)
        print(f"Transcription: {transcription_path}")

        print("\nStep 5/6: Create lyric videos (kareoke + vocals)")
        width = _prompt_positive_int("Video width", default=1920)
        height = _prompt_positive_int("Video height", default=1080)
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
        #print(f"Kareoke video: {kareoke_video_path}")
        print(f"Vocals video:  {vocals_video_path}")

        print("\nStep 6/6: Create vocals video metadata")
        song_name = _prompt_non_empty("Song name")
        artist_name = _prompt_non_empty("Artist name")
        metadata_language = _prompt_metadata_language()
        metadata_path = create_video_metadata_for_vocals(
            vocals_audio_path=vocals_path,
            song_name=song_name,
            artist_name=artist_name,
            language=metadata_language,
        )
        print(f"Video metadata: {metadata_path}")

        print("\nPipeline completed successfully.")
        print(f"Run name: {run_name}")
        print(f"Run dir:  {run_dir}")
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
