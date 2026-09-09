from app.core.intelligence.execution.trace import ExecutionTrace
from app.core.intelligence.durable_store import DurableStore, EVIDENCE_DB_PATH


class ExecutionTraceStorage(DurableStore):
    """
    Stores execution decision traces, durably backed by the shared SQLite
    evidence database (T0-1; was JSON).
    """

    _table = "traces"

    def __init__(self, file_path=None):
        super().__init__(
            file_path=file_path,
            model=ExecutionTrace,
        )


execution_trace_storage = ExecutionTraceStorage(file_path=EVIDENCE_DB_PATH)
