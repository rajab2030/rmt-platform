from app.core.intelligence.execution.audit import ExecutionAuditRecord
from app.core.intelligence.durable_store import DurableStore, EVIDENCE_DB_PATH


class ExecutionAuditStorage(DurableStore):
    """
    Stores execution audit records, durably backed by the shared SQLite
    evidence database (T0-1; was JSON).
    """

    _table = "audit"

    def __init__(self, file_path=None):
        super().__init__(
            file_path=file_path,
            model=ExecutionAuditRecord,
        )


execution_audit_storage = ExecutionAuditStorage(file_path=EVIDENCE_DB_PATH)
