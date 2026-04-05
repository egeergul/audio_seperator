#!/usr/bin/env python3

import os
import sys

# Ensure the desktop_app directory is on sys.path so that
# "from services..." and "from core..." imports work correctly.
_app_dir = os.path.dirname(os.path.abspath(__file__))
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

# Auto-activate the project venv if not already in a virtual environment.
_project_root = os.path.dirname(_app_dir)
_venv_python = os.path.join(_project_root, ".venv", "bin", "python")
_in_venv = sys.prefix != sys.base_prefix
if not _in_venv and os.path.isfile(_venv_python):
    print("Re-launching with project venv...")
    os.execv(_venv_python, [_venv_python] + sys.argv)

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.theme import get_dark_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Audio Scraper")
    app.setStyleSheet(get_dark_theme())

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
