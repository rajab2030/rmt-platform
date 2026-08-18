from app.core.intelligence.execution.adapters.registry import (
    adapter_registry,
)

from app.core.intelligence.execution.audit import (
    ExecutionAuditRecord,
)

from app.core.intelligence.execution.storage import (
    execution_audit_storage,
)

from app.core.intelligence.execution.trace import (
    ExecutionTrace,
)

from app.core.intelligence.execution.trace_storage import (
    execution_trace_storage,
)

from app.core.intelligence.execution.policy import (
    execution_policy,
    PolicyDecision,
)

from app.core.intelligence.execution.risk import (
    execution_risk_analyzer,
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

        risk_result = execution_risk_analyzer.evaluate(
            request,
        )

        policy_result = execution_policy.evaluate(
            request,
        )

        if policy_result != PolicyDecision.ALLOW:

            trace_record = ExecutionTrace(
                execution_id=request.execution_id,
                action_id=request.action_id,
                authorization_id=request.authorization_id,
                policy_decision=policy_result.value,
                risk_level=risk_result.value,
                outcome="blocked",
                reason=(
                    f"Execution blocked by policy: "
                    f"{policy_result.value}"
                ),
            )

            execution_trace_storage.save(
                trace_record,
            )

            return ExecutionResult(
                execution_id=request.execution_id,
                status="failed",
                success=False,
                message=(
                    f"Execution blocked by policy: "
                    f"{policy_result.value}"
                ),
            )

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
            risk_level=risk_result.value,
        )

        execution_audit_storage.save(
            audit_record,
        )

        trace_record = ExecutionTrace(
            execution_id=result.execution_id,
            action_id=request.action_id,
            authorization_id=request.authorization_id,
            policy_decision=policy_result.value,
            risk_level=risk_result.value,
            outcome=result.status,
            reason=result.message,
        )

        execution_trace_storage.save(
            trace_record,
        )

        return result


execution_engine = ExecutionEngine()
