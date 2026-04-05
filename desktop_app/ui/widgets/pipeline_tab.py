from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.pipeline import (
    SUPPORTED_DEVICES,
    SUPPORTED_METADATA_LANGUAGES,
    SUPPORTED_MODELS,
    SUPPORTED_PRIVACY_STATUSES,
    PipelineConfig,
)


class PipelineTab(QWidget):
    run_requested = Signal(object)
    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Configuration Form ---
        form_group = QGroupBox("Pipeline Configuration")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)

        self.folder_name = QLineEdit()
        self.folder_name.setPlaceholderText("e.g. my_song_project")
        form_layout.addRow("Folder Name:", self.folder_name)

        self.youtube_url = QLineEdit()
        self.youtube_url.setPlaceholderText("https://www.youtube.com/watch?v=...")
        form_layout.addRow("YouTube URL:", self.youtube_url)

        self.song_name = QLineEdit()
        self.song_name.setPlaceholderText("e.g. Bohemian Rhapsody")
        form_layout.addRow("Song Name:", self.song_name)

        self.artist_name = QLineEdit()
        self.artist_name.setPlaceholderText("e.g. Queen")
        form_layout.addRow("Artist Name:", self.artist_name)

        self.model_combo = QComboBox()
        self.model_combo.addItems(SUPPORTED_MODELS)
        self.model_combo.setCurrentText("small")
        form_layout.addRow("Whisper Model:", self.model_combo)

        self.language = QLineEdit()
        self.language.setPlaceholderText("auto-detect (or e.g. en, tr, es)")
        form_layout.addRow("Language:", self.language)

        self.device_combo = QComboBox()
        self.device_combo.addItems(SUPPORTED_DEVICES)
        self.device_combo.setCurrentText("auto")
        form_layout.addRow("Device:", self.device_combo)

        dims_widget = QWidget()
        dims_layout = QHBoxLayout(dims_widget)
        dims_layout.setContentsMargins(0, 0, 0, 0)
        self.video_width = QSpinBox()
        self.video_width.setRange(320, 7680)
        self.video_width.setValue(1920)
        self.video_height = QSpinBox()
        self.video_height.setRange(240, 4320)
        self.video_height.setValue(1080)
        dims_layout.addWidget(QLabel("W:"))
        dims_layout.addWidget(self.video_width)
        dims_layout.addWidget(QLabel("H:"))
        dims_layout.addWidget(self.video_height)
        dims_layout.addStretch()
        form_layout.addRow("Video Size:", dims_widget)

        self.metadata_lang_combo = QComboBox()
        self.metadata_lang_combo.addItems(SUPPORTED_METADATA_LANGUAGES)
        self.metadata_lang_combo.setCurrentText("en")
        form_layout.addRow("Metadata Language:", self.metadata_lang_combo)

        yt_widget = QWidget()
        yt_layout = QHBoxLayout(yt_widget)
        yt_layout.setContentsMargins(0, 0, 0, 0)
        self.youtube_upload_check = QCheckBox("Upload to YouTube")
        yt_layout.addWidget(self.youtube_upload_check)
        yt_layout.addWidget(QLabel("Privacy:"))
        self.privacy_combo = QComboBox()
        self.privacy_combo.addItems(SUPPORTED_PRIVACY_STATUSES)
        self.privacy_combo.setCurrentText("public")
        yt_layout.addWidget(self.privacy_combo)
        yt_layout.addStretch()
        form_layout.addRow("", yt_widget)

        layout.addWidget(form_group)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.run_btn = QPushButton("Run Full Pipeline")
        self.run_btn.setFixedHeight(44)
        self.run_btn.setMinimumWidth(200)
        self.run_btn.clicked.connect(self._on_run)
        btn_layout.addWidget(self.run_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("cssClass", "danger")
        self.cancel_btn.setFixedHeight(44)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # --- Progress Panel ---
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 7)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%v / %m steps")
        progress_layout.addWidget(self.progress_bar)

        self.step_labels: list[QLabel] = []
        step_names = [
            "1. Create run folder",
            "2. Download audio",
            "3. Separate vocals and kareoke",
            "4. Transcribe vocals",
            "5. Create lyric video",
            "6. Create video metadata",
            "7. Upload to YouTube",
        ]
        for name in step_names:
            lbl = QLabel(f"  {name}")
            lbl.setStyleSheet("color: #666680; padding: 2px 0;")
            progress_layout.addWidget(lbl)
            self.step_labels.append(lbl)

        layout.addWidget(progress_group)
        layout.addStretch()

        # Collect form widgets for enabling/disabling
        self._form_widgets = [
            self.folder_name, self.youtube_url, self.song_name,
            self.artist_name, self.model_combo, self.language,
            self.device_combo, self.video_width, self.video_height,
            self.metadata_lang_combo, self.youtube_upload_check,
            self.privacy_combo,
        ]

    def _on_run(self) -> None:
        folder = self.folder_name.text().strip()
        url = self.youtube_url.text().strip()
        song = self.song_name.text().strip()
        artist = self.artist_name.text().strip()

        if not folder or not url or not song or not artist:
            return

        config = PipelineConfig(
            folder_name=folder,
            youtube_url=url,
            song_name=song,
            artist_name=artist,
            model=self.model_combo.currentText(),
            language=self.language.text().strip() or None,
            device=self.device_combo.currentText(),
            video_width=self.video_width.value(),
            video_height=self.video_height.value(),
            metadata_language=self.metadata_lang_combo.currentText(),
            youtube_upload=self.youtube_upload_check.isChecked(),
            privacy_status=self.privacy_combo.currentText(),
        )
        self.run_requested.emit(config)

    def set_running(self, running: bool) -> None:
        self.run_btn.setEnabled(not running)
        self.cancel_btn.setEnabled(running)
        for w in self._form_widgets:
            w.setEnabled(not running)
        if running:
            self.progress_bar.setValue(0)
            for lbl in self.step_labels:
                lbl.setStyleSheet("color: #666680; padding: 2px 0;")

    def update_step(self, step: int, total: int, description: str) -> None:
        self.progress_bar.setValue(step - 1)
        for i, lbl in enumerate(self.step_labels):
            if i < step - 1:
                lbl.setStyleSheet("color: #22c55e; padding: 2px 0;")
            elif i == step - 1:
                lbl.setStyleSheet("color: #7c3aed; font-weight: bold; padding: 2px 0;")
            else:
                lbl.setStyleSheet("color: #666680; padding: 2px 0;")

    def mark_complete(self) -> None:
        self.progress_bar.setValue(7)
        for lbl in self.step_labels:
            lbl.setStyleSheet("color: #22c55e; padding: 2px 0;")

    def mark_error(self, step: int) -> None:
        if 0 < step <= len(self.step_labels):
            self.step_labels[step - 1].setStyleSheet(
                "color: #ef4444; font-weight: bold; padding: 2px 0;"
            )
