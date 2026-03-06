from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.transcription import (
    derive_transcription_output_path,
    segments_to_sentence_chunks_ms,
    write_transcription_json,
)


class TranscriptionServicesTests(unittest.TestCase):
    def test_segments_to_sentence_chunks_ms_uses_millisecond_fields(self) -> None:
        segments = [
            {
                "start": 0.0,
                "end": 4.0,
                "text": "Hello world. How are you?",
            }
        ]
        chunks = segments_to_sentence_chunks_ms(segments)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["index"], 0)
        self.assertEqual(chunks[1]["index"], 1)
        self.assertEqual(chunks[0]["start_time_ms"], 0)
        self.assertEqual(chunks[-1]["end_time_ms"], 4000)
        self.assertIn("text", chunks[0])
        self.assertTrue(all("start_time_ms" in chunk for chunk in chunks))
        self.assertTrue(all("end_time_ms" in chunk for chunk in chunks))

    def test_derive_output_path_uses_parent_folder_name(self) -> None:
        audio_path = Path("/tmp/wild_flower/wild_flower_vocals.mp3")
        output_path = derive_transcription_output_path(audio_path)
        self.assertEqual(output_path.name, "wild_flower_transcription.json")
        self.assertEqual(output_path.parent.resolve(), audio_path.parent.resolve())

    def test_write_transcription_json_name_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = Path(tmp_dir) / "run_a"
            run_dir.mkdir(parents=True, exist_ok=True)
            audio_path = run_dir / "run_a_vocals.mp3"
            audio_path.write_bytes(b"v")

            payload = {
                "source_audio": str(audio_path),
                "model": "small",
                "language": "en",
                "duration_ms": 1000,
                "created_at": "2026-01-01T00:00:00+00:00",
                "chunks": [
                    {
                        "index": 0,
                        "start_time_ms": 0,
                        "end_time_ms": 1000,
                        "text": "Hello.",
                    }
                ],
            }

            output_path = write_transcription_json(audio_path, payload)
            self.assertEqual(output_path.name, "run_a_transcription.json")
            loaded = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["chunks"][0]["start_time_ms"], 0)
            self.assertEqual(loaded["chunks"][0]["end_time_ms"], 1000)


if __name__ == "__main__":
    unittest.main()
