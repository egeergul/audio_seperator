from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPlainTextEdit, QWidget


class LogViewer(QPlainTextEdit):
    MAX_LINES = 10_000

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(self.MAX_LINES)

    def _print_to_console(self, text: str) -> None:
        sys.__stdout__.write(text + "\n")
        sys.__stdout__.flush()

    def append_log(self, text: str) -> None:
        self._print_to_console(text)
        self.appendPlainText(text)
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_error(self, text: str) -> None:
        msg = f"ERROR: {text}"
        self._print_to_console(msg)
        self.appendPlainText(msg)
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_success(self, text: str) -> None:
        msg = f"OK: {text}"
        self._print_to_console(msg)
        self.appendPlainText(msg)
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
