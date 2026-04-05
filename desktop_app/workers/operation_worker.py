from __future__ import annotations

from typing import Any, Callable

from workers.base_worker import BaseWorker


class OperationWorker(BaseWorker):
    def __init__(self, operation: Callable, args: tuple = (), kwargs: dict[str, Any] | None = None, parent=None):
        super().__init__(parent)
        self.operation = operation
        self.args = args
        self.kwargs = kwargs or {}

    def execute(self) -> object:
        return self.operation(*self.args, **self.kwargs)
