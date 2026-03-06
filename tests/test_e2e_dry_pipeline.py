from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import pipeline
from app.config import INSTRUMENTAL_MODEL_HASH, VOCALS_MODEL_HASH
from app.transcription import write_transcription_json
from app.video import build_video_spec, create_video_from_transcription


class EndToEndDryPipelineTests(unittest.TestCase):
    def test_dry_pipeline_handoff_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            outputs_root = root / ".outputs"

            with patch.object(pipeline, "OUTPUTS_DIR", outputs_root):
                run_dir = pipeline.create_normalized_run_folder("Wild Flower")

            run_name = run_dir.name
            expected_original = run_dir / f"{run_name}_original.mp3"
            expected_vocals = run_dir / f"{run_name}_vocals.mp3"
            expected_kareoke = run_dir / f"{run_name}_kareoke.mp3"

            def fake_run_command(cmd: list[str], cwd: Path | None = None) -> None:
                del cwd
                cmd_joined = " ".join(cmd)
                if "yt_dlp" in cmd_joined:
                    expected_original.write_bytes(b"orig")
                    return

                if "--out_base" in cmd and "-m" in cmd:
                    model_hash = cmd[cmd.index("-m") + 1]
                    out_base = Path(cmd[cmd.index("--out_base") + 1])
                    if model_hash == VOCALS_MODEL_HASH:
                        (out_base.parent / f"{out_base.name}_Vocals.mp3").write_bytes(b"v")
                    elif model_hash == INSTRUMENTAL_MODEL_HASH:
                        (out_base.parent / f"{out_base.name}_Instrumental.mp3").write_bytes(
                            b"k"
                        )

            with (
                patch.object(pipeline, "run_command", side_effect=fake_run_command),
                patch.object(pipeline, "check_separation_prerequisites"),
                patch.object(pipeline, "validate_vendor_runtime"),
                patch.object(pipeline, "resolve_models_dir", return_value=root / "models"),
            ):
                original = pipeline.download_youtube_audio(
                    "https://youtube.com/watch?v=abc",
                    run_dir,
                )
                vocals, kareoke = pipeline.seperate_audio(original)

            self.assertEqual(original, expected_original.resolve())
            self.assertEqual(vocals, expected_vocals.resolve())
            self.assertEqual(kareoke, expected_kareoke.resolve())

            transcription_payload = {
                "source_audio": str(vocals),
                "model": "small",
                "language": "en",
                "duration_ms": 2500,
                "created_at": "2026-03-07T00:00:00+00:00",
                "chunks": [
                    {
                        "index": 0,
                        "start_time_ms": 0,
                        "end_time_ms": 2500,
                        "text": "Hello world",
                    }
                ],
            }
            transcription_path = write_transcription_json(vocals, transcription_payload)
            self.assertEqual(transcription_path.name, f"{run_name}_transcription.json")

            spec = build_video_spec(
                transcription_path=transcription_path,
                vocals_audio_path=vocals,
                kareoke_audio_path=kareoke,
                video_width=1280,
                video_height=720,
            )
            self.assertEqual(spec.output_video_path, (run_dir / f"{run_name}.mp4").resolve())

            captured_cmd: list[str] = []

            def fake_render_overlay(
                output_path: Path, text: str, width: int, height: int, index: int
            ) -> Path:
                del text, width, height
                overlay = output_path / f"caption_{index:04d}.png"
                overlay.write_bytes(b"png")
                return overlay

            def fake_run_video_command(cmd: list[str]) -> None:
                captured_cmd.extend(cmd)

            with (
                patch("app.video.check_video_prerequisites"),
                patch("app.video._probe_audio_duration_seconds", return_value=3.0),
                patch("app.video._render_caption_image", side_effect=fake_render_overlay),
                patch("app.video._run_command", side_effect=fake_run_video_command),
            ):
                output_video = create_video_from_transcription(spec)

            self.assertEqual(output_video, (run_dir / f"{run_name}.mp4").resolve())
            self.assertIn(str(kareoke), captured_cmd)
            self.assertIn(str(output_video), captured_cmd)

            loaded = json.loads(transcription_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["chunks"][0]["start_time_ms"], 0)
            self.assertEqual(loaded["chunks"][0]["end_time_ms"], 2500)


if __name__ == "__main__":
    unittest.main()
