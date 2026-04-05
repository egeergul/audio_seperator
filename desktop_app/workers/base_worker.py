from __future__ import annotations

import sys
import traceback

from PySide6.QtCore import QThread, Signal


class _SignalWriter:
    """Replacement for sys.stdout that emits text via a Qt signal
    while also forwarding to the original stream."""

    def __init__(self, signal: Signal, original_stream):
        self._signal = signal
        self._original = original_stream

    def write(self, text: str) -> None:
        if self._original:
            self._original.write(text)
            self._original.flush()
        if text and text.strip():
            self._signal.emit(text.rstrip("\n"))

    def flush(self) -> None:
        if self._original:
            self._original.flush()


class BaseWorker(QThread):
    log_message = Signal(str)
    step_changed = Signal(int, int, str)  # step_num, total_steps, description
    finished_ok = Signal(object)
    finished_err = Signal(str)

    def run(self) -> None:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = _SignalWriter(self.log_message, old_stdout)
        sys.stderr = _SignalWriter(self.log_message, old_stderr)
        try:
            result = self.execute()
            self.finished_ok.emit(result)
        except InterruptedError:
            self.finished_err.emit("Cancelled by user.")
        except Exception as exc:
            tb = traceback.format_exc()
            self.log_message.emit(tb)
            self.finished_err.emit(str(exc))
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def execute(self) -> object:
        raise NotImplementedError
