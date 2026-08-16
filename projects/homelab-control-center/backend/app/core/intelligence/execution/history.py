from typing import List

from app.core.intelligence.execution.audit import (
    ExecutionAuditRecord,
)

from app.core.intelligence.execution.storage import (
    execution_audit_storage,
)


class ExecutionHistory:
    """
    Provides read access to execution audit history.

    This layer does not execute actions.
    It only queries execution evidence.
    """

    def get_all(
        self,
    ) -> List[ExecutionAuditRecord]:
        return execution_audit_storage.get_all()


execution_history = ExecutionHistory()
