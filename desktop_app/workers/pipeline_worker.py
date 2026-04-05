from __future__ import annotations

from core.pipeline import PipelineConfig, PipelineRunner
from workers.base_worker import BaseWorker


class PipelineWorker(BaseWorker):
    def __init__(self, config: PipelineConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def execute(self) -> object:
        runner = PipelineRunner(
            config=self.config,
            on_step=lambda step, total, desc: self.step_changed.emit(step, total, desc),
            on_log=lambda msg: self.log_message.emit(msg),
            is_cancelled=lambda: self._cancelled,
        )
        return runner.run()
