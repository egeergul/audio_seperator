from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .config import (
    INSTRUMENTAL_MODEL_HASH,
    LOCAL_MODELS_MDX_DIR,
    OUTPUT_FORMAT,
    OUTPUTS_DIR,
    VENDOR_AUDIO_SEPARATION_DIR,
    VENDOR_DEMIX_SCRIPT,
    VENDOR_MODELS_DB_JSON,
    VOCALS_MODEL_HASH,
)


def run_command(cmd: list[str], cwd: Path | None = None) -> None:
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
    except subprocess.CalledProcessError as exc:
        joined = " ".join(cmd)
        raise RuntimeError(f"Command failed: {joined}") from exc


def check_prerequisites() -> None:
    if shutil.which("git") is None:
        raise EnvironmentError("Missing required command: git")
    if shutil.which("ffmpeg") is None:
        raise EnvironmentError(
            "Missing required command: ffmpeg. Install ffmpeg and ensure it is on PATH."
        )
    try:
        import torchcodec  # noqa: F401
    except Exception as exc:
        raise EnvironmentError(
            "Missing required Python package: torchcodec. "
            "Run: python -m pip install -r requirements.txt"
        ) from exc
    try:
        import packaging  # noqa: F401
    except Exception as exc:
        raise EnvironmentError(
            "Missing required Python package: packaging. "
            "Run: python -m pip install -r requirements.txt"
        ) from exc


def validate_vendor_runtime() -> None:
    missing = [
        path
        for path in [VENDOR_DEMIX_SCRIPT, VENDOR_MODELS_DB_JSON]
        if not path.is_file()
    ]
    if missing:
        msg = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(
            "Missing vendored AudioSeparation runtime files. Not found: " + msg
        )


def prompt_user_inputs() -> tuple[str, str]:
    youtube_url = input("Enter YouTube URL: ").strip()
    if not youtube_url:
        raise ValueError("YouTube URL cannot be empty.")

    creation_name = input("Enter creation name: ").strip()
    if not creation_name:
        raise ValueError("Creation name cannot be empty.")

    return youtube_url, creation_name


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
    return run_dir


def resolve_models_dir() -> Path:
    env_override = os.environ.get("AUDIO_SEP_MODELS_DIR")
    if env_override:
        override_path = Path(env_override).expanduser()
        if not override_path.is_dir():
            raise FileNotFoundError(
                f"AUDIO_SEP_MODELS_DIR does not exist: {override_path}"
            )
        return override_path

    LOCAL_MODELS_MDX_DIR.mkdir(parents=True, exist_ok=True)
    return LOCAL_MODELS_MDX_DIR


def download_youtube_audio(youtube_url: str, run_dir: Path) -> Path:
    output_template = run_dir / "source_audio.%(ext)s"
    print("Downloading audio from YouTube...")
    run_command(
        [
            sys.executable,
            "-m",
            "yt_dlp",
            "--no-playlist",
            "-x",
            "--audio-format",
            "wav",
            "-o",
            str(output_template),
            youtube_url,
        ]
    )

    audio_file = run_dir / "source_audio.wav"
    if not audio_file.is_file():
        raise RuntimeError(
            f"Expected downloaded file was not created: {audio_file}. "
            "Check yt-dlp/ffmpeg output above."
        )
    return audio_file


def run_demix(
    input_audio: Path, output_base: Path, model_hash: str, models_dir: Path
) -> None:
    print(f"Running separation with model {model_hash}...")
    run_command(
        [
            sys.executable,
            str(VENDOR_DEMIX_SCRIPT),
            "-m",
            model_hash,
            "--out_base",
            str(output_base),
            "--format",
            OUTPUT_FORMAT,
            "--models_dir",
            str(models_dir),
            str(input_audio),
        ],
        cwd=VENDOR_AUDIO_SEPARATION_DIR,
    )


def rename_outputs_to_required_names(
    run_dir: Path, output_base_name: str
) -> tuple[Path, Path]:
    source_vocals = run_dir / f"{output_base_name}_Vocals.{OUTPUT_FORMAT}"
    source_instrumental = run_dir / f"{output_base_name}_Instrumental.{OUTPUT_FORMAT}"

    target_vocals = run_dir / f"{output_base_name}_vocals.{OUTPUT_FORMAT}"
    target_kareoke = run_dir / f"{output_base_name}_kareoke.{OUTPUT_FORMAT}"

    if not source_vocals.is_file():
        raise FileNotFoundError(f"Expected vocals output not found: {source_vocals}")
    if not source_instrumental.is_file():
        raise FileNotFoundError(
            f"Expected instrumental output not found: {source_instrumental}"
        )

    source_vocals.replace(target_vocals)
    source_instrumental.replace(target_kareoke)
    return target_vocals, target_kareoke


def run_cli() -> int:
    try:
        check_prerequisites()
        validate_vendor_runtime()

        youtube_url, creation_name_raw = prompt_user_inputs()
        creation_name = sanitize_creation_name(creation_name_raw)
        if creation_name != creation_name_raw:
            print(f"Using sanitized creation name: {creation_name}")

        run_dir = create_run_folder(creation_name)
        print(f"Created folder: {run_dir}")

        audio_file = download_youtube_audio(youtube_url, run_dir)
        models_dir = resolve_models_dir()
        print(f"Using model directory: {models_dir}")

        output_base = run_dir / creation_name
        run_demix(audio_file, output_base, VOCALS_MODEL_HASH, models_dir)
        run_demix(audio_file, output_base, INSTRUMENTAL_MODEL_HASH, models_dir)

        vocals_path, kareoke_path = rename_outputs_to_required_names(
            run_dir, creation_name
        )

        print("\nPipeline completed successfully.")
        print(f"Source audio: {audio_file}")
        print(f"Vocals: {vocals_path}")
        print(f"Kareoke: {kareoke_path}")
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
