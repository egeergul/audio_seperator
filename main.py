#!/usr/bin/env python3
"""Terminal pipeline for YouTube audio download + vocal/instrumental separation."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import os
from pathlib import Path


AUDIO_SEPARATION_REPO_URL = "https://github.com/set-soft/AudioSeparation"
SCRIPT_DIR = Path(__file__).resolve().parent
THIRD_PARTY_DIR = SCRIPT_DIR / "third_party"
AUDIO_SEPARATION_DIR = THIRD_PARTY_DIR / "AudioSeparation"

VOCALS_MODEL_HASH = "499a6a6bf9da6d330235a1576007ddc0"
INSTRUMENTAL_MODEL_HASH = "a78fcc2e0ff8d575edd2c55add1eaa64"
OUTPUT_FORMAT = "mp3"
DEFAULT_COMFYUI_MODELS_ROOT = Path.home() / "Documents" / "ComfyUI" / "models"


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
    run_dir = SCRIPT_DIR / creation_name
    if run_dir.exists():
        raise FileExistsError(
            f"Folder already exists: {run_dir}. Use a different creation name."
        )
    run_dir.mkdir(parents=False, exist_ok=False)
    return run_dir


def run_command(cmd: list[str], cwd: Path | None = None) -> None:
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
    except subprocess.CalledProcessError as exc:
        joined = " ".join(cmd)
        raise RuntimeError(f"Command failed: {joined}") from exc


def ensure_audioseparation_repo() -> Path:
    demix_script = AUDIO_SEPARATION_DIR / "tool" / "demix.py"
    if demix_script.is_file():
        return AUDIO_SEPARATION_DIR

    THIRD_PARTY_DIR.mkdir(parents=True, exist_ok=True)
    print("AudioSeparation repository not found. Cloning...")
    run_command(
        [
            "git",
            "clone",
            "--depth",
            "1",
            AUDIO_SEPARATION_REPO_URL,
            str(AUDIO_SEPARATION_DIR),
        ],
        cwd=SCRIPT_DIR,
    )

    if not demix_script.is_file():
        raise RuntimeError("AudioSeparation clone completed but demix.py is missing.")
    return AUDIO_SEPARATION_DIR


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
        ],
        cwd=SCRIPT_DIR,
    )

    audio_file = run_dir / "source_audio.wav"
    if not audio_file.is_file():
        raise RuntimeError(
            f"Expected downloaded file was not created: {audio_file}. "
            "Check yt-dlp/ffmpeg output above."
        )
    return audio_file


def run_demix(
    repo_dir: Path,
    input_audio: Path,
    output_base: Path,
    model_hash: str,
    models_dir: Path | None = None,
) -> None:
    demix_script = repo_dir / "tool" / "demix.py"
    print(f"Running separation with model {model_hash}...")
    cmd = [
        sys.executable,
        str(demix_script),
        "-m",
        model_hash,
        "--out_base",
        str(output_base),
        "--format",
        OUTPUT_FORMAT,
    ]
    if models_dir is not None:
        cmd.extend(["--models_dir", str(models_dir)])
    cmd.append(str(input_audio))
    run_command(cmd, cwd=repo_dir)


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
            "Run: python -m pip install torchcodec (or reinstall with requirements.txt)."
        ) from exc
    try:
        import packaging  # noqa: F401
    except Exception as exc:
        raise EnvironmentError(
            "Missing required Python package: packaging. "
            "Run: python -m pip install packaging (or reinstall with requirements.txt)."
        ) from exc


def resolve_models_dir() -> Path | None:
    """Prefer existing ComfyUI MDX models to avoid re-downloads."""
    env_override = os.environ.get("AUDIO_SEP_MODELS_DIR")
    if env_override:
        override_path = Path(env_override).expanduser()
        if override_path.is_dir():
            return override_path

    comfy_mdx = DEFAULT_COMFYUI_MODELS_ROOT / "audio" / "MDX"
    if comfy_mdx.is_dir():
        return comfy_mdx

    if DEFAULT_COMFYUI_MODELS_ROOT.is_dir():
        return DEFAULT_COMFYUI_MODELS_ROOT

    return None


def main() -> int:
    try:
        check_prerequisites()

        youtube_url, creation_name_raw = prompt_user_inputs()
        creation_name = sanitize_creation_name(creation_name_raw)
        if creation_name != creation_name_raw:
            print(f"Using sanitized creation name: {creation_name}")

        run_dir = create_run_folder(creation_name)
        print(f"Created folder: {run_dir}")

        repo_dir = ensure_audioseparation_repo()
        audio_file = download_youtube_audio(youtube_url, run_dir)
        models_dir = resolve_models_dir()
        if models_dir is not None:
            print(f"Using existing model directory: {models_dir}")
        else:
            print("No external model directory detected, models will be downloaded as needed.")

        output_base = run_dir / creation_name
        run_demix(repo_dir, audio_file, output_base, VOCALS_MODEL_HASH, models_dir)
        run_demix(repo_dir, audio_file, output_base, INSTRUMENTAL_MODEL_HASH, models_dir)

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


if __name__ == "__main__":
    raise SystemExit(main())
