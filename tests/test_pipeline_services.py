from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import pipeline
from app.config import (
    INSTRUMENTAL_MODEL_HASH,
    VENDOR_AUDIO_SEPARATION_DIR,
    VENDOR_DEMIX_SCRIPT,
    VOCALS_MODEL_HASH,
)


class PipelineServicesTests(unittest.TestCase):
    def test_sanitize_creation_name(self) -> None:
        self.assertEqual(pipeline.sanitize_creation_name("my song!"), "my_song")
        self.assertEqual(pipeline.sanitize_creation_name("..abc--"), "abc")
        with self.assertRaises(ValueError):
            pipeline.sanitize_creation_name("!!!")

    def test_create_normalized_run_folder_creates_under_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_outputs = Path(tmp_dir) / ".outputs"
            with patch.object(pipeline, "OUTPUTS_DIR", tmp_outputs):
                run_dir = pipeline.create_normalized_run_folder("my song")
                self.assertEqual(run_dir.name, "my_song")
                self.assertTrue(run_dir.is_dir())
                self.assertEqual(run_dir.parent, tmp_outputs.resolve())

    def test_download_youtube_audio_uses_run_name_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = Path(tmp_dir) / "wild_flower"
            run_dir.mkdir(parents=True, exist_ok=True)
            expected_audio = run_dir / "wild_flower_original.mp3"

            captured: list[list[str]] = []

            def fake_run_command(cmd: list[str], cwd: Path | None = None) -> None:
                del cwd
                captured.append(cmd)
                expected_audio.write_bytes(b"fake")

            with patch.object(pipeline, "run_command", side_effect=fake_run_command):
                output = pipeline.download_youtube_audio(
                    "https://youtube.com/watch?v=abc",
                    run_dir,
                )

            self.assertEqual(output, expected_audio.resolve())
            self.assertEqual(len(captured), 1)
            cmd = captured[0]
            self.assertEqual(cmd[0], sys.executable)
            self.assertEqual(cmd[1:3], ["-m", "yt_dlp"])
            self.assertIn("--audio-format", cmd)
            self.assertIn("mp3", cmd)
            self.assertIn(
                str((run_dir / "wild_flower_original.%(ext)s").resolve()),
                cmd,
            )

    def test_run_demix_builds_expected_command(self) -> None:
        input_audio = Path("/tmp/input.mp3")
        out_base = Path("/tmp/song")
        models_dir = Path("/tmp/models")
        model_hash = "hash123"

        with patch.object(subprocess, "run") as mocked_run:
            pipeline.run_demix(input_audio, out_base, model_hash, models_dir)

        mocked_run.assert_called_once()
        args, kwargs = mocked_run.call_args
        cmd = args[0]
        self.assertEqual(
            cmd,
            [
                sys.executable,
                str(VENDOR_DEMIX_SCRIPT),
                "-m",
                model_hash,
                "--out_base",
                str(out_base),
                "--format",
                "mp3",
                "--models_dir",
                str(models_dir),
                str(input_audio),
            ],
        )
        self.assertEqual(kwargs["cwd"], VENDOR_AUDIO_SEPARATION_DIR)
        self.assertTrue(kwargs["check"])

    def test_seperate_audio_runs_two_model_hashes_and_renames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = Path(tmp_dir) / "song_name"
            run_dir.mkdir(parents=True, exist_ok=True)
            original = run_dir / "song_name_original.mp3"
            original.write_bytes(b"audio")

            def fake_run_demix(
                input_audio: Path, output_base: Path, model_hash: str, models_dir: Path
            ) -> None:
                del input_audio, output_base, models_dir
                if model_hash == VOCALS_MODEL_HASH:
                    (run_dir / "song_name_Vocals.mp3").write_bytes(b"vocals")
                elif model_hash == INSTRUMENTAL_MODEL_HASH:
                    (run_dir / "song_name_Instrumental.mp3").write_bytes(b"inst")

            with (
                patch.object(pipeline, "check_separation_prerequisites"),
                patch.object(pipeline, "validate_vendor_runtime"),
                patch.object(pipeline, "resolve_models_dir", return_value=Path("/tmp/models")),
                patch.object(pipeline, "run_demix", side_effect=fake_run_demix) as mocked_demix,
            ):
                vocals, kareoke = pipeline.seperate_audio(original)

            self.assertEqual(vocals.name, "song_name_vocals.mp3")
            self.assertEqual(kareoke.name, "song_name_kareoke.mp3")
            self.assertTrue(vocals.is_file())
            self.assertTrue(kareoke.is_file())
            self.assertEqual(mocked_demix.call_count, 2)
            hashes = [call.args[2] for call in mocked_demix.call_args_list]
            self.assertEqual(hashes, [VOCALS_MODEL_HASH, INSTRUMENTAL_MODEL_HASH])


if __name__ == "__main__":
    unittest.main()
