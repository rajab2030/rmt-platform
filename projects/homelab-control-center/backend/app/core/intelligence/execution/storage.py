from typing import List

from app.core.intelligence.execution.audit import (
    ExecutionAuditRecord,
)


class ExecutionAuditStorage:
    """
    Stores execution audit records.

    Initial implementation is memory-based.
    Persistence backend can be replaced later.
    """

    def __init__(self):
        self._records: List[ExecutionAuditRecord] = []

    def save(
        self,
        record: ExecutionAuditRecord,
    ) -> None:
        self._records.append(record)

    def get_all(
        self,
    ) -> List[ExecutionAuditRecord]:
        return self._records


execution_audit_storage = ExecutionAuditStorage()
