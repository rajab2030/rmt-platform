from pathlib import Path

from app.core.intelligence.execution.trace import ExecutionTrace
from app.core.intelligence.durable_store import DurableStore


class ExecutionTraceStorage(DurableStore):
    """
    Stores execution decision traces, durably backed by JSON.
    """

    def __init__(self, file_path=None):
        super().__init__(
            file_path=file_path,
            model=ExecutionTrace,
        )


execution_trace_storage = ExecutionTraceStorage(
    file_path=Path(__file__).parent / "traces.json"
)
