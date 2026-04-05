from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QToolBar,
    QWidget,
)

from core.operations import (
    op_convert_to_midi,
    op_create_folder,
    op_create_metadata,
    op_create_video,
    op_download,
    op_extract_pitches,
    op_separate,
    op_transcribe,
    op_upload_youtube,
    op_visualize_waveform,
)
from core.pipeline import PipelineConfig
from services.config import OUTPUTS_DIR
from ui.widgets.log_viewer import LogViewer
from ui.widgets.operations_tab import OperationsTab
from ui.widgets.pipeline_tab import PipelineTab
from workers.operation_worker import OperationWorker
from workers.pipeline_worker import PipelineWorker

OPERATION_MAP = {
    "create_folder": lambda p: op_create_folder(p["folder_name"]),
    "download": lambda p: op_download(p["youtube_url"], p["output_folder"]),
    "separate": lambda p: op_separate(p["audio_path"]),
    "transcribe": lambda p: op_transcribe(p["audio_path"], p["model"], p["language"], p["device"]),
    "create_video": lambda p: op_create_video(p["transcription_path"], p["audio_path"], p["width"], p["height"]),
    "create_metadata": lambda p: op_create_metadata(p["vocals_audio_path"], p["song_name"], p["artist_name"], p["language"]),
    "extract_pitches": lambda p: op_extract_pitches(p["audio_path"]),
    "convert_midi": lambda p: op_convert_to_midi(p["pitch_json_path"]),
    "visualize_waveform": lambda p: op_visualize_waveform(p["audio_path"], p["width"], p["height"]),
    "upload_youtube": lambda p: op_upload_youtube(p["video_path"], p["metadata_path"], p["privacy_status"]),
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Scraper")
        self.setMinimumSize(800, 700)
        self.resize(960, 800)

        self._current_worker = None
        self._current_pipeline_step = 0

        # --- Central Tabs ---
        self.tabs = QTabWidget()
        self.pipeline_tab = PipelineTab()
        self.operations_tab = OperationsTab()
        self.tabs.addTab(self.pipeline_tab, "Full Pipeline")
        self.tabs.addTab(self.operations_tab, "Individual Operations")
        self.setCentralWidget(self.tabs)

        # --- Log Dock ---
        self.log_viewer = LogViewer()
        dock = QDockWidget("Log Output")
        dock.setWidget(self.log_viewer)
        dock.setFeatures(QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)

        # --- Toolbar ---
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        clear_btn = QPushButton("Clear Log")
        clear_btn.setProperty("cssClass", "secondary")
        clear_btn.clicked.connect(self.log_viewer.clear)
        toolbar.addWidget(clear_btn)

        open_btn = QPushButton("Open Outputs Folder")
        open_btn.setProperty("cssClass", "secondary")
        open_btn.clicked.connect(self._open_outputs_folder)
        toolbar.addWidget(open_btn)

        # --- Connect Signals ---
        self.pipeline_tab.run_requested.connect(self._start_pipeline)
        self.pipeline_tab.cancel_requested.connect(self._cancel_pipeline)
        self.operations_tab.operation_requested.connect(self._start_operation)

    def _set_busy(self, busy: bool) -> None:
        self.pipeline_tab.set_running(busy)
        self.operations_tab.set_running(busy)

    def _start_pipeline(self, config: PipelineConfig) -> None:
        if self._current_worker is not None:
            return

        self.log_viewer.append_log("--- Starting Full Pipeline ---")
        self._current_pipeline_step = 0
        self._set_busy(True)

        worker = PipelineWorker(config)
        worker.log_message.connect(self.log_viewer.append_log)
        worker.step_changed.connect(self._on_pipeline_step)
        worker.finished_ok.connect(self._on_pipeline_ok)
        worker.finished_err.connect(self._on_pipeline_err)
        self._current_worker = worker
        worker.start()

    def _cancel_pipeline(self) -> None:
        if isinstance(self._current_worker, PipelineWorker):
            self._current_worker.cancel()
            self.log_viewer.append_log("Cancelling pipeline...")

    def _on_pipeline_step(self, step: int, total: int, description: str) -> None:
        self._current_pipeline_step = step
        self.pipeline_tab.update_step(step, total, description)
        self.log_viewer.append_log(f"Step {step}/{total}: {description}")

    def _on_pipeline_ok(self, result: object) -> None:
        self.pipeline_tab.mark_complete()
        self.log_viewer.append_success("Pipeline completed successfully!")
        self._current_worker = None
        self._set_busy(False)

    def _on_pipeline_err(self, error: str) -> None:
        self.pipeline_tab.mark_error(self._current_pipeline_step)
        self.log_viewer.append_error(f"Pipeline failed: {error}")
        self._current_worker = None
        self._set_busy(False)

    def _start_operation(self, op_name: str, params: dict) -> None:
        if self._current_worker is not None:
            return

        handler = OPERATION_MAP.get(op_name)
        if handler is None:
            self.log_viewer.append_error(f"Unknown operation: {op_name}")
            return

        self.log_viewer.append_log(f"--- Running: {op_name} ---")
        self._set_busy(True)

        worker = OperationWorker(handler, args=(params,))
        worker.log_message.connect(self.log_viewer.append_log)
        worker.finished_ok.connect(self._on_operation_ok)
        worker.finished_err.connect(self._on_operation_err)
        self._current_worker = worker
        worker.start()

    def _on_operation_ok(self, result: object) -> None:
        self.log_viewer.append_success("Operation completed successfully!")
        self._current_worker = None
        self._set_busy(False)

    def _on_operation_err(self, error: str) -> None:
        self.log_viewer.append_error(f"Operation failed: {error}")
        self._current_worker = None
        self._set_busy(False)

    def _open_outputs_folder(self) -> None:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(OUTPUTS_DIR)])
        elif sys.platform == "win32":
            subprocess.Popen(["explorer", str(OUTPUTS_DIR)])
        else:
            subprocess.Popen(["xdg-open", str(OUTPUTS_DIR)])
