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


def check_separation_prerequisites() -> None:
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


def derive_run_name(folder_path: Path) -> str:
    resolved = folder_path.resolve()
    run_name = resolved.name.strip()
    if not run_name:
        raise ValueError(f"Could not derive run name from folder: {folder_path}")
    return run_name


def validate_output_folder(output_folder: Path) -> Path:
    resolved = output_folder.expanduser().resolve()
    if not resolved.is_dir():
        raise FileNotFoundError(
            f"Output folder does not exist or is not a directory: {resolved}"
        )
    return resolved


def validate_readable_file(file_path: Path) -> Path:
    resolved = file_path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"File not found: {resolved}")
    if not os.access(resolved, os.R_OK):
        raise PermissionError(f"File is not readable: {resolved}")
    return resolved


def resolve_models_dir() -> Path:
    env_override = os.environ.get("AUDIO_SEP_MODELS_DIR")
    if env_override:
        override_path = Path(env_override).expanduser()
        if not override_path.is_dir():
            raise FileNotFoundError(
                f"AUDIO_SEP_MODELS_DIR does not exist: {override_path}"
            )
        return override_path.resolve()

    LOCAL_MODELS_MDX_DIR.mkdir(parents=True, exist_ok=True)
    return LOCAL_MODELS_MDX_DIR.resolve()


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


def run_demix(
    input_audio: Path, output_base: Path, model_hash: str, models_dir: Path
) -> None:
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

    if target_vocals.exists() and not target_vocals.samefile(source_vocals):
        raise FileExistsError(f"Target vocals file already exists: {target_vocals}")
    if target_kareoke.exists() and not target_kareoke.samefile(source_instrumental):
        raise FileExistsError(f"Target kareoke file already exists: {target_kareoke}")

    _replace_with_case_only_support(source_vocals, target_vocals)
    _replace_with_case_only_support(source_instrumental, target_kareoke)
    return target_vocals.resolve(), target_kareoke.resolve()


def _replace_with_case_only_support(source: Path, target: Path) -> None:
    if source == target:
        return
    if source.parent == target.parent and source.name.lower() == target.name.lower():
        temp_target = source.parent / f".tmp_case_rename_{os.getpid()}_{source.name}"
        if temp_target.exists():
            raise FileExistsError(f"Temporary rename path already exists: {temp_target}")
        source.replace(temp_target)
        temp_target.replace(target)
        return
    source.replace(target)


def seperate_audio(original_file_path: Path) -> tuple[Path, Path]:
    original_file = validate_readable_file(original_file_path)
    check_separation_prerequisites()
    validate_vendor_runtime()

    run_dir = original_file.parent
    run_name = derive_run_name(run_dir)

    output_base = run_dir / run_name
    models_dir = resolve_models_dir()

    run_demix(original_file, output_base, VOCALS_MODEL_HASH, models_dir)
    run_demix(original_file, output_base, INSTRUMENTAL_MODEL_HASH, models_dir)

    return rename_outputs_to_required_names(run_dir, run_name)
