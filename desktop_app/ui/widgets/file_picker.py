from __future__ import annotations

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)


class FilePicker(QWidget):
    def __init__(
        self,
        mode: str = "file",
        file_filter: str = "",
        placeholder: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._mode = mode
        self._file_filter = file_filter

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(placeholder)
        layout.addWidget(self.line_edit, stretch=1)

        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setProperty("cssClass", "secondary")
        self.browse_btn.setFixedWidth(80)
        self.browse_btn.clicked.connect(self._browse)
        layout.addWidget(self.browse_btn)

    def _browse(self) -> None:
        if self._mode == "directory":
            path = QFileDialog.getExistingDirectory(self, "Select Folder")
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "Select File", "", self._file_filter
            )
        if path:
            self.line_edit.setText(path)

    def text(self) -> str:
        return self.line_edit.text().strip()

    def set_text(self, text: str) -> None:
        self.line_edit.setText(text)

    def setEnabled(self, enabled: bool) -> None:
        self.line_edit.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)
