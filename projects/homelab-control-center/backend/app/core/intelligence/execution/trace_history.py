from typing import List

from app.core.intelligence.execution.trace import (
    ExecutionTrace,
)

from app.core.intelligence.execution.trace_storage import (
    execution_trace_storage,
)


class ExecutionTraceHistory:
    """
    Provides read access to execution decision traces.

    This layer does not execute actions.
    It only queries execution reasoning records.
    """

    def get_all(
        self,
    ) -> List[ExecutionTrace]:
        return execution_trace_storage.get_all()


execution_trace_history = ExecutionTraceHistory()
