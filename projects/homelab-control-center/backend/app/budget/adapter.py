from __future__ import annotations

from app.budget.models import GOVERNANCE_DOMAIN, BudgetError, MutationType
from app.budget.repository import budget_repository
from app.core.intelligence.execution.adapters.base import ExecutionAdapter
from app.core.intelligence.execution.models import ExecutionRequest, ExecutionResult


class BudgetLedgerAdapter(ExecutionAdapter):
    """Executes an already-authorized Budget instruction atomically."""

    def supports(self, request: ExecutionRequest) -> bool:
        try:
            MutationType(request.parameters.get("mutation_type"))
        except (TypeError, ValueError):
            return False
        return (
            request.governance_domain == GOVERNANCE_DOMAIN
            and request.operation == "create"
            and bool(request.instruction_digest)
        )

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        try:
            receipt = budget_repository.apply_mutation(
                parameters=request.parameters,
                instruction_digest=str(request.instruction_digest),
                execution_id=request.execution_id,
            )
            return ExecutionResult(
                execution_id=request.execution_id,
                status="completed",
                success=True,
                message="Budget mutation committed atomically",
                output={"receipt": receipt.as_dict()},
            )
        except BudgetError as exc:
            try:
                receipt = budget_repository.receipt(str(request.instruction_digest))
            except Exception:
                receipt = None
                outcome = "outcome_unknown"
            else:
                outcome = "adapter_failed_no_effect"
            if receipt is not None:
                return ExecutionResult(
                    execution_id=request.execution_id,
                    status="completed",
                    success=True,
                    message="Recovered existing durable Budget mutation receipt",
                    output={"receipt": receipt.as_dict(), "recovered": True},
                )
            return ExecutionResult(
                execution_id=request.execution_id,
                status="failed",
                success=False,
                message=f"Budget adapter rejected [{exc.code}]: {exc.message}",
                output={"financial_outcome": outcome, "error_code": exc.code},
            )
        except Exception as exc:
            try:
                receipt = budget_repository.receipt(str(request.instruction_digest))
            except Exception:
                receipt = None
            if receipt is not None:
                return ExecutionResult(
                    execution_id=request.execution_id,
                    status="completed",
                    success=True,
                    message="Recovered committed Budget mutation after ambiguous response",
                    output={"receipt": receipt.as_dict(), "recovered": True},
                )
            return ExecutionResult(
                execution_id=request.execution_id,
                status="failed",
                success=False,
                message=f"Budget mutation outcome is unknown: {type(exc).__name__}",
                output={"financial_outcome": "outcome_unknown"},
            )
