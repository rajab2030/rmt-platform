from pathlib import Path

from app.core.intelligence.execution.audit import ExecutionAuditRecord
from app.core.intelligence.durable_store import DurableStore


class ExecutionAuditStorage(DurableStore):
    """
    Stores execution audit records, durably backed by JSON.
    """

    def __init__(self, file_path=None):
        super().__init__(
            file_path=file_path,
            model=ExecutionAuditRecord,
        )


execution_audit_storage = ExecutionAuditStorage(
    file_path=Path(__file__).parent / "audit.json"
)
