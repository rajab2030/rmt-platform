from __future__ import annotations

from app.budget.models import ADAPTER_NAME, BudgetError
from app.budget.repository import budget_repository
from app.core.intelligence.actions.binding import bind_action
from app.core.intelligence.actions.policy import ActionPolicyResult
from app.core.intelligence.actions.simulation import ActionSimulationResult


class BudgetPolicyEvaluator:
    evaluator_id = "rmt.budget.v1.policy"
    version = "1"

    def evaluate(self, action):
        try:
            instruction_digest, _ = bind_action(action, ADAPTER_NAME)
            evidence = budget_repository.validate_mutation(
                action.parameters,
                instruction_digest,
            )
        except BudgetError as exc:
            return ActionPolicyResult(
                allowed=False,
                reason=f"Budget policy denied [{exc.code}]: {exc.message}",
                requires_approval=False,
                evidence_references=(f"budget:denial:{exc.code}",),
            )
        return ActionPolicyResult(
            allowed=True,
            reason="Budget domain policy and permission checks passed",
            requires_approval=False,
            evidence_references=tuple(evidence["evidence"]),
        )


class BudgetRiskEvaluator:
    evaluator_id = "rmt.budget.v1.risk"
    version = "1"

    def evaluate(self, action):
        try:
            instruction_digest, _ = bind_action(action, ADAPTER_NAME)
            evidence = budget_repository.validate_mutation(
                action.parameters,
                instruction_digest,
            )
            mutation = evidence["mutation_type"]
            impact = (
                f"Apply {mutation} for {evidence['amount_minor']} "
                f"{evidence['currency']} minor units; available changes from "
                f"{evidence['available_before']} to {evidence['available_after']}"
            )
            return ActionSimulationResult(
                action_id=action.action_id,
                component=action.component,
                action_type=action.action_type.value,
                expected_impact=impact,
                risk_level="medium",
                rollback_available=True,
                uncertainty="low: serialized transaction revalidates all evidence",
                recovery_semantics=(
                    "query durable receipt by immutable instruction digest; "
                    "never replay an unresolved outcome"
                ),
                evidence_references=tuple(evidence["evidence"]),
            )
        except BudgetError as exc:
            return ActionSimulationResult(
                action_id=action.action_id,
                component=action.component,
                action_type=action.action_type.value,
                expected_impact=f"Budget mutation cannot be safely assessed: {exc.message}",
                risk_level="unknown",
                rollback_available=False,
                uncertainty=f"denied:{exc.code}",
                recovery_semantics="stop without adapter invocation",
                evidence_references=(f"budget:denial:{exc.code}",),
            )
