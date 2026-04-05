from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPlainTextEdit, QWidget


class LogViewer(QPlainTextEdit):
    MAX_LINES = 10_000

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(self.MAX_LINES)

    def append_log(self, text: str) -> None:
        self.appendPlainText(text)
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_error(self, text: str) -> None:
        self.appendPlainText(f"ERROR: {text}")
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_success(self, text: str) -> None:
        self.appendPlainText(f"OK: {text}")
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
