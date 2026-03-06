from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.video import (
    CaptionItem,
    VideoSpec,
    build_ffmpeg_command,
    build_video_spec,
    load_transcription_chunks,
)


class VideoServicesTests(unittest.TestCase):
    def test_load_transcription_chunks_validates_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "a.json"
            path.write_text(
                json.dumps({"chunks": [{"start_time_ms": 0, "end_time_ms": 1000, "text": "x"}]}),
                encoding="utf-8",
            )
            chunks = load_transcription_chunks(path)
            self.assertEqual(len(chunks), 1)
            self.assertEqual(chunks[0].start_time_ms, 0)

            path.write_text(json.dumps({"chunks": [{"end_time_ms": 1000, "text": "x"}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_transcription_chunks(path)

    def test_build_video_spec_default_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = Path(tmp_dir) / "wild_flower"
            run_dir.mkdir(parents=True, exist_ok=True)
            transcription = run_dir / "wild_flower_transcription.json"
            vocals = run_dir / "wild_flower_vocals.mp3"
            kareoke = run_dir / "wild_flower_kareoke.mp3"

            transcription.write_text(
                json.dumps(
                    {
                        "chunks": [
                            {
                                "start_time_ms": 0,
                                "end_time_ms": 1000,
                                "text": "Hello",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            vocals.write_bytes(b"v")
            kareoke.write_bytes(b"k")

            spec = build_video_spec(
                transcription_path=transcription,
                vocals_audio_path=vocals,
                kareoke_audio_path=kareoke,
                video_width=1920,
                video_height=1080,
            )
            self.assertEqual(spec.output_video_path, (run_dir / "wild_flower.mp4").resolve())

    def test_build_ffmpeg_command_uses_ms_timing_windows(self) -> None:
        spec = VideoSpec(
            transcription_path=Path("/tmp/transcription.json"),
            vocals_audio_path=Path("/tmp/vocals.mp3"),
            kareoke_audio_path=Path("/tmp/kareoke.mp3"),
            video_width=1920,
            video_height=1080,
            output_video_path=Path("/tmp/out.mp4"),
            content=[CaptionItem(start_time_ms=1500, end_time_ms=2600, text="Line")],
        )
        cmd = build_ffmpeg_command(spec, duration_seconds=10.0, overlays=[Path("/tmp/c0.png")])
        self.assertIn(str(spec.kareoke_audio_path), cmd)
        filter_complex = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("between(t\\,1.5\\,2.6)", filter_complex)


if __name__ == "__main__":
    unittest.main()
