from datetime import datetime, timezone

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

from app.core.intelligence.actions.authorization import (
    AuthorizationStatus,
)

from app.core.intelligence.actions.authorization_storage import (
    execution_authorization_storage,
)


def _create_blocked_trace(
    request: ExecutionRequest,
    policy_decision: str,
    risk_level: str,
    outcome: str,
    reason: str,
) -> ExecutionTrace:
    return ExecutionTrace(
        execution_id=request.execution_id,
        action_id=request.action_id,
        authorization_id=request.authorization_id,
        policy_decision=policy_decision,
        risk_level=risk_level,
        outcome=outcome,
        reason=reason,
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

        authorization = execution_authorization_storage.get_by_id(
            request.authorization_id,
        )

        if authorization is None:
            trace_record = _create_blocked_trace(
                request,
                policy_decision="not_evaluated",
                risk_level="not_evaluated",
                outcome="blocked",
                reason="Authorization not found",
            )
            execution_trace_storage.save(trace_record)
            return ExecutionResult(
                execution_id=request.execution_id,
                status="failed",
                success=False,
                message="Authorization not found",
            )

        if authorization.status != AuthorizationStatus.APPROVED:
            trace_record = _create_blocked_trace(
                request,
                policy_decision="not_evaluated",
                risk_level="not_evaluated",
                outcome="blocked",
                reason="Authorization not approved",
            )
            execution_trace_storage.save(trace_record)
            return ExecutionResult(
                execution_id=request.execution_id,
                status="failed",
                success=False,
                message="Authorization not approved",
            )

        if (
            authorization.expires_at is not None
            and authorization.expires_at < datetime.now(timezone.utc)
        ):
            trace_record = _create_blocked_trace(
                request,
                policy_decision="not_evaluated",
                risk_level="not_evaluated",
                outcome="blocked",
                reason="Authorization expired",
            )
            execution_trace_storage.save(trace_record)
            return ExecutionResult(
                execution_id=request.execution_id,
                status="failed",
                success=False,
                message="Authorization expired",
            )

        if authorization.action_id != request.action_id:
            trace_record = _create_blocked_trace(
                request,
                policy_decision="not_evaluated",
                risk_level="not_evaluated",
                outcome="blocked",
                reason="Authorization action_id mismatch",
            )
            execution_trace_storage.save(trace_record)
            return ExecutionResult(
                execution_id=request.execution_id,
                status="failed",
                success=False,
                message="Authorization action_id mismatch",
            )

        if authorization.target != request.target:
            trace_record = _create_blocked_trace(
                request,
                policy_decision="not_evaluated",
                risk_level="not_evaluated",
                outcome="blocked",
                reason="Authorization target mismatch",
            )
            execution_trace_storage.save(trace_record)
            return ExecutionResult(
                execution_id=request.execution_id,
                status="failed",
                success=False,
                message="Authorization target mismatch",
            )

        if authorization.operation != request.operation:
            trace_record = _create_blocked_trace(
                request,
                policy_decision="not_evaluated",
                risk_level="not_evaluated",
                outcome="blocked",
                reason="Authorization operation mismatch",
            )
            execution_trace_storage.save(trace_record)
            return ExecutionResult(
                execution_id=request.execution_id,
                status="failed",
                success=False,
                message="Authorization operation mismatch",
            )

        if request.expected_outcome != authorization.expected_outcome:
            trace_record = _create_blocked_trace(
                request,
                policy_decision="not_evaluated",
                risk_level="not_evaluated",
                outcome="blocked",
                reason="Authorization expected_outcome mismatch",
            )
            execution_trace_storage.save(trace_record)
            return ExecutionResult(
                execution_id=request.execution_id,
                status="failed",
                success=False,
                message="Authorization expected_outcome mismatch",
            )

        if request.risk_level is not None:
            risk_result = request.risk_level
        else:
            risk_result = execution_risk_analyzer.evaluate(
                request,
            ).value

        policy_result = execution_policy.evaluate(
            request,
        )

        if policy_result != PolicyDecision.ALLOW:

            trace_record = ExecutionTrace(
                execution_id=request.execution_id,
                action_id=request.action_id,
                authorization_id=request.authorization_id,
                policy_decision=policy_result.value,
                risk_level=risk_result,
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
            risk_level=risk_result,
        )

        execution_audit_storage.save(
            audit_record,
        )

        trace_record = ExecutionTrace(
            execution_id=result.execution_id,
            action_id=request.action_id,
            authorization_id=request.authorization_id,
            policy_decision=policy_result.value,
            risk_level=risk_result,
            outcome=result.status,
            reason=result.message,
        )

        execution_trace_storage.save(
            trace_record,
        )

        return result


execution_engine = ExecutionEngine()
