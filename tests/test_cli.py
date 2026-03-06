from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_script(script_name: str, *args: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(PROJECT_ROOT / script_name), *args]
    return subprocess.run(cmd, capture_output=True, text=True)


class CliTests(unittest.TestCase):
    def test_help_for_all_scripts(self) -> None:
        scripts = [
            "create_folder.py",
            "scrape_audio.py",
            "seperate_audio.py",
            "transcribe_audio.py",
            "create_video_from_transcription.py",
        ]
        for script in scripts:
            with self.subTest(script=script):
                result = run_script(script, "--help")
                self.assertEqual(result.returncode, 0)
                self.assertIn("usage:", result.stdout.lower())

    def test_missing_required_args(self) -> None:
        scripts = [
            "create_folder.py",
            "scrape_audio.py",
            "seperate_audio.py",
            "transcribe_audio.py",
            "create_video_from_transcription.py",
        ]
        for script in scripts:
            with self.subTest(script=script):
                result = run_script(script)
                self.assertEqual(result.returncode, 2)
                self.assertIn("usage:", result.stderr.lower())

    def test_scrape_audio_invalid_folder_path(self) -> None:
        result = run_script(
            "scrape_audio.py",
            "https://youtube.com/watch?v=abc",
            "/path/that/does/not/exist",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Output folder does not exist", result.stderr)

    def test_seperate_audio_invalid_original_file_path(self) -> None:
        result = run_script("seperate_audio.py", "/path/that/does/not/exist.mp3")
        self.assertEqual(result.returncode, 1)
        self.assertIn("File not found", result.stderr)

    def test_transcribe_audio_invalid_path(self) -> None:
        result = run_script("transcribe_audio.py", "/path/that/does/not/exist.mp3")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Audio file not found", result.stderr)

    def test_create_video_from_transcription_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            transcription = tmp_path / "bad_transcription.json"
            vocals = tmp_path / "run_vocals.mp3"
            kareoke = tmp_path / "run_kareoke.mp3"

            transcription.write_text("{ this is invalid json", encoding="utf-8")
            vocals.write_bytes(b"v")
            kareoke.write_bytes(b"k")

            result = run_script(
                "create_video_from_transcription.py",
                str(transcription),
                str(vocals),
                str(kareoke),
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("not valid JSON", result.stderr)


if __name__ == "__main__":
    unittest.main()
