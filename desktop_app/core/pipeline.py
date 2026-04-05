from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from services.download import download_youtube_audio
from services.folder import create_normalized_run_folder
from services.separation import seperate_audio
from services.transcription import transcribe_audio, write_transcription_json
from services.video import build_video_spec, create_video_from_transcription
from services.video_metadata import create_video_metadata_for_vocals

SUPPORTED_MODELS = [
    "tiny", "tiny.en", "base", "base.en", "small", "small.en",
    "medium", "medium.en", "large", "large-v1", "large-v2", "large-v3", "turbo",
]

SUPPORTED_DEVICES = ["auto", "cpu", "cuda"]
SUPPORTED_METADATA_LANGUAGES = ["en", "tr"]
SUPPORTED_PRIVACY_STATUSES = ["private", "unlisted", "public"]


@dataclass
class PipelineConfig:
    folder_name: str
    youtube_url: str
    song_name: str
    artist_name: str
    model: str = "small"
    language: str | None = None
    device: str = "auto"
    video_width: int = 1920
    video_height: int = 1080
    metadata_language: str = "en"
    youtube_upload: bool = False
    privacy_status: str = "public"


class PipelineRunner:
    def __init__(
        self,
        config: PipelineConfig,
        on_step: Callable[[int, int, str], None],
        on_log: Callable[[str], None],
        is_cancelled: Callable[[], bool],
    ):
        self.config = config
        self.on_step = on_step
        self.on_log = on_log
        self.is_cancelled = is_cancelled

    def _check_cancel(self) -> None:
        if self.is_cancelled():
            raise InterruptedError("Pipeline cancelled by user.")

    def run(self) -> Path:
        cfg = self.config
        total = 7

        self._check_cancel()
        self.on_step(1, total, "Create run folder")
        run_dir = create_normalized_run_folder(cfg.folder_name)
        self.on_log(f"Created: {run_dir}")

        self._check_cancel()
        self.on_step(2, total, "Download audio")
        original_audio_path = download_youtube_audio(cfg.youtube_url, run_dir)
        self.on_log(f"Downloaded: {original_audio_path}")

        self._check_cancel()
        self.on_step(3, total, "Separate vocals and kareoke")
        vocals_path, kareoke_path = seperate_audio(original_audio_path)
        self.on_log(f"Vocals: {vocals_path}")
        self.on_log(f"Kareoke: {kareoke_path}")

        self._check_cancel()
        self.on_step(4, total, "Transcribe vocals")
        transcription_payload = transcribe_audio(
            audio_path=vocals_path,
            model_name=cfg.model,
            language=cfg.language,
            device=cfg.device,
        )
        transcription_path = write_transcription_json(vocals_path, transcription_payload)
        self.on_log(f"Transcription: {transcription_path}")

        self._check_cancel()
        self.on_step(5, total, "Create lyric video")
        vocals_video_spec = build_video_spec(
            transcription_path=transcription_path,
            mux_audio_path=vocals_path,
            video_width=cfg.video_width,
            video_height=cfg.video_height,
            output_video_path=None,
        )
        vocals_video_path = create_video_from_transcription(vocals_video_spec)
        self.on_log(f"Vocals video: {vocals_video_path}")

        self._check_cancel()
        self.on_step(6, total, "Create video metadata")
        metadata_path = create_video_metadata_for_vocals(
            vocals_audio_path=vocals_path,
            song_name=cfg.song_name,
            artist_name=cfg.artist_name,
            language=cfg.metadata_language,
        )
        self.on_log(f"Video metadata: {metadata_path}")

        self._check_cancel()
        if cfg.youtube_upload:
            self.on_step(7, total, "Upload to YouTube")
            from services.youtube_upload import upload_video_to_youtube

            video_id = upload_video_to_youtube(
                video_file_path=vocals_video_path,
                metadata_text_path=metadata_path,
                privacy_status=cfg.privacy_status,
            )
            self.on_log(f"YouTube video ID: {video_id}")
            self.on_log(f"YouTube URL: https://www.youtube.com/watch?v={video_id}")

            released_dir = run_dir.parent.parent / ".released"
            released_dir.mkdir(parents=True, exist_ok=True)
            dest = released_dir / run_dir.name
            if dest.exists():
                self.on_log(f"Warning: {dest} already exists in .released, skipping move.")
            else:
                shutil.move(str(run_dir), str(dest))
                self.on_log(f"Moved: {run_dir} -> {dest}")
                run_dir = dest
        else:
            self.on_step(7, total, "YouTube upload skipped")
            self.on_log("YouTube upload skipped (not enabled)")

        self.on_log("Pipeline completed successfully.")
        return run_dir
