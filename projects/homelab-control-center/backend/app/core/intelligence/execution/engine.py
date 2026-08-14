from app.core.intelligence.execution.adapters.registry import (
    adapter_registry,
)

from app.core.intelligence.execution.audit import (
    ExecutionAuditRecord,
)

from app.core.intelligence.execution.storage import (
    execution_audit_storage,
)

from app.core.intelligence.execution.models import (
    ExecutionRequest,
    ExecutionResult,
)


class ExecutionEngine:
    """
    Coordinates controlled execution.

    This layer selects adapters and triggers execution.
    It does not authorize actions.
    """

    def execute(
        self,
        request: ExecutionRequest,
        adapter_name: str = "simulation",
    ) -> ExecutionResult:

        adapter = adapter_registry.get(
            adapter_name,
        )

        if adapter is None:
            return ExecutionResult(
                execution_id=request.execution_id,
                status="failed",
                success=False,
                message=f"Adapter '{adapter_name}' not found",
            )

        if not adapter.supports(request):
            return ExecutionResult(
                execution_id=request.execution_id,
                status="failed",
                success=False,
                message="Adapter does not support request",
            )

        result = adapter.execute(request)

        audit_record = ExecutionAuditRecord(
            execution_id=result.execution_id,
            action_id=request.action_id,
            authorization_id=request.authorization_id,
            adapter=adapter_name,
            status=result.status,
            message=result.message,
        )

        execution_audit_storage.save(
            audit_record,
        )

        return result


execution_engine = ExecutionEngine()
