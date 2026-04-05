from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.pipeline import (
    SUPPORTED_DEVICES,
    SUPPORTED_METADATA_LANGUAGES,
    SUPPORTED_MODELS,
    SUPPORTED_PRIVACY_STATUSES,
)
from ui.widgets.file_picker import FilePicker


class _OperationCard(QGroupBox):
    run_clicked = Signal(str, dict)  # operation_name, params

    def __init__(self, title: str, op_name: str, parent: QWidget | None = None):
        super().__init__(title, parent)
        self._op_name = op_name
        self._layout = QFormLayout(self)
        self._layout.setSpacing(8)
        self._fields: dict[str, QWidget] = {}

    def add_text_field(self, label: str, key: str, placeholder: str = "") -> QLineEdit:
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        self._fields[key] = field
        self._layout.addRow(label, field)
        return field

    def add_file_picker(
        self, label: str, key: str, mode: str = "file",
        file_filter: str = "", placeholder: str = ""
    ) -> FilePicker:
        picker = FilePicker(mode=mode, file_filter=file_filter, placeholder=placeholder)
        self._fields[key] = picker
        self._layout.addRow(label, picker)
        return picker

    def add_combo(self, label: str, key: str, items: list[str], default: str = "") -> QComboBox:
        combo = QComboBox()
        combo.addItems(items)
        if default:
            combo.setCurrentText(default)
        self._fields[key] = combo
        self._layout.addRow(label, combo)
        return combo

    def add_spin(self, label: str, key: str, min_val: int, max_val: int, default: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        self._fields[key] = spin
        self._layout.addRow(label, spin)
        return spin

    def add_dimensions(self, label: str, w_key: str, h_key: str, w_default: int, h_default: int):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        w_spin = QSpinBox()
        w_spin.setRange(320, 7680)
        w_spin.setValue(w_default)
        h_spin = QSpinBox()
        h_spin.setRange(240, 4320)
        h_spin.setValue(h_default)
        layout.addWidget(QLabel("W:"))
        layout.addWidget(w_spin)
        layout.addWidget(QLabel("H:"))
        layout.addWidget(h_spin)
        layout.addStretch()
        self._fields[w_key] = w_spin
        self._fields[h_key] = h_spin
        self._layout.addRow(label, widget)
        return w_spin, h_spin

    def add_run_button(self) -> QPushButton:
        btn = QPushButton("Run")
        btn.setFixedWidth(120)
        btn.clicked.connect(self._emit_run)
        self._layout.addRow("", btn)
        self._run_btn = btn
        return btn

    def _emit_run(self) -> None:
        params = {}
        for key, widget in self._fields.items():
            if isinstance(widget, QLineEdit):
                params[key] = widget.text().strip()
            elif isinstance(widget, FilePicker):
                params[key] = widget.text()
            elif isinstance(widget, QComboBox):
                params[key] = widget.currentText()
            elif isinstance(widget, QSpinBox):
                params[key] = widget.value()
        self.run_clicked.emit(self._op_name, params)

    def set_enabled_all(self, enabled: bool) -> None:
        for widget in self._fields.values():
            widget.setEnabled(enabled)
        if hasattr(self, "_run_btn"):
            self._run_btn.setEnabled(enabled)


class OperationsTab(QWidget):
    operation_requested = Signal(str, dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(12)

        self._cards: list[_OperationCard] = []

        # 1. Create Folder
        card = _OperationCard("Create Folder", "create_folder")
        card.add_text_field("Folder Name:", "folder_name", "e.g. my_song_project")
        card.add_run_button()
        card.run_clicked.connect(self.operation_requested.emit)
        self._cards.append(card)
        main_layout.addWidget(card)

        # 2. Download Audio
        card = _OperationCard("Download Audio", "download")
        card.add_text_field("YouTube URL:", "youtube_url", "https://www.youtube.com/watch?v=...")
        card.add_file_picker("Output Folder:", "output_folder", mode="directory", placeholder="Select output folder")
        card.add_run_button()
        card.run_clicked.connect(self.operation_requested.emit)
        self._cards.append(card)
        main_layout.addWidget(card)

        # 3. Separate Audio
        card = _OperationCard("Separate Audio", "separate")
        card.add_file_picker("Audio File:", "audio_path", file_filter="Audio (*.mp3 *.wav)", placeholder="Select original audio file")
        card.add_run_button()
        card.run_clicked.connect(self.operation_requested.emit)
        self._cards.append(card)
        main_layout.addWidget(card)

        # 4. Transcribe Audio
        card = _OperationCard("Transcribe Audio", "transcribe")
        card.add_file_picker("Audio File:", "audio_path", file_filter="Audio (*.mp3 *.wav)", placeholder="Select vocals audio file")
        card.add_combo("Model:", "model", SUPPORTED_MODELS, "small")
        card.add_text_field("Language:", "language", "auto-detect (or e.g. en, tr)")
        card.add_combo("Device:", "device", SUPPORTED_DEVICES, "auto")
        card.add_run_button()
        card.run_clicked.connect(self.operation_requested.emit)
        self._cards.append(card)
        main_layout.addWidget(card)

        # 5. Create Lyric Video
        card = _OperationCard("Create Lyric Video", "create_video")
        card.add_file_picker("Transcription JSON:", "transcription_path", file_filter="JSON (*.json)", placeholder="Select transcription JSON")
        card.add_file_picker("Audio File:", "audio_path", file_filter="Audio (*.mp3 *.wav)", placeholder="Select audio to mux")
        card.add_dimensions("Video Size:", "width", "height", 1920, 1080)
        card.add_run_button()
        card.run_clicked.connect(self.operation_requested.emit)
        self._cards.append(card)
        main_layout.addWidget(card)

        # 6. Create Video Metadata
        card = _OperationCard("Create Video Metadata", "create_metadata")
        card.add_file_picker("Vocals Audio:", "vocals_audio_path", file_filter="Audio (*.mp3 *.wav)", placeholder="Select vocals audio file")
        card.add_text_field("Song Name:", "song_name", "e.g. Bohemian Rhapsody")
        card.add_text_field("Artist Name:", "artist_name", "e.g. Queen")
        card.add_combo("Language:", "language", SUPPORTED_METADATA_LANGUAGES, "en")
        card.add_run_button()
        card.run_clicked.connect(self.operation_requested.emit)
        self._cards.append(card)
        main_layout.addWidget(card)

        # 7. Extract Pitches
        card = _OperationCard("Extract Pitches", "extract_pitches")
        card.add_file_picker("Audio File:", "audio_path", file_filter="Audio (*.mp3 *.wav)", placeholder="Select audio file")
        card.add_run_button()
        card.run_clicked.connect(self.operation_requested.emit)
        self._cards.append(card)
        main_layout.addWidget(card)

        # 8. Convert Pitches to MIDI
        card = _OperationCard("Convert Pitches to MIDI", "convert_midi")
        card.add_file_picker("Pitch JSON:", "pitch_json_path", file_filter="JSON (*.json)", placeholder="Select pitch JSON file")
        card.add_run_button()
        card.run_clicked.connect(self.operation_requested.emit)
        self._cards.append(card)
        main_layout.addWidget(card)

        # 9. Visualize Waveform
        card = _OperationCard("Visualize Waveform", "visualize_waveform")
        card.add_file_picker("Audio File:", "audio_path", file_filter="Audio (*.mp3 *.wav)", placeholder="Select audio file")
        card.add_dimensions("Image Size:", "width", "height", 1920, 400)
        card.add_run_button()
        card.run_clicked.connect(self.operation_requested.emit)
        self._cards.append(card)
        main_layout.addWidget(card)

        # 10. Upload to YouTube
        card = _OperationCard("Upload to YouTube", "upload_youtube")
        card.add_file_picker("Video File:", "video_path", file_filter="Video (*.mp4)", placeholder="Select video file")
        card.add_file_picker("Metadata File:", "metadata_path", file_filter="Text (*.txt)", placeholder="Select metadata text file")
        card.add_combo("Privacy:", "privacy_status", SUPPORTED_PRIVACY_STATUSES, "public")
        card.add_run_button()
        card.run_clicked.connect(self.operation_requested.emit)
        self._cards.append(card)
        main_layout.addWidget(card)

        main_layout.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def set_running(self, running: bool) -> None:
        for card in self._cards:
            card.set_enabled_all(not running)
