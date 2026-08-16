from typing import List

from app.core.intelligence.execution.trace import (
    ExecutionTrace,
)


class ExecutionTraceStorage:
    """
    Stores execution decision traces.

    Initial implementation is memory-based.
    Persistence backend can be replaced later.
    """

    def __init__(self):
        self._traces: List[ExecutionTrace] = []

    def save(
        self,
        trace: ExecutionTrace,
    ) -> None:
        self._traces.append(trace)

    def get_all(
        self,
    ) -> List[ExecutionTrace]:
        return self._traces


execution_trace_storage = ExecutionTraceStorage()
