from app.core.intelligence.actions.models import (
    ActionRequest,
)

from app.core.intelligence.execution.models import (
    ExecutionRequest,
)


def translate_action_to_execution(
    action: ActionRequest,
    authorization_id: str,
    risk_level: str | None = None,
    adapter_name: str | None = None,
    assessment=None,
    hold=None,
) -> ExecutionRequest:
    """
    Translate an approved action into an execution request.

    This layer does not authorize actions.
    It only converts intent into execution format.
    """

    return ExecutionRequest(
        authorization_id=authorization_id,
        action_id=action.action_id,
        decision_id=action.decision_id,
        governance_domain=action.governance_domain,
        target=action.component,
        operation=action.action_type.value,
        parameters=action.model_copy(deep=True).parameters,
        risk_level=risk_level,
        expected_outcome=action.expected_outcome,
        adapter_name=adapter_name,
        assessment_id=(
            getattr(assessment, "assessment_id", None)
            or getattr(hold, "assessment_id", None)
        ),
        policy_evaluator_id=(
            getattr(assessment, "policy_evaluator_id", None)
            or getattr(hold, "policy_evaluator_id", None)
        ),
        policy_evaluator_version=(
            getattr(assessment, "policy_evaluator_version", None)
            or getattr(hold, "policy_evaluator_version", None)
        ),
        risk_evaluator_id=(
            getattr(assessment, "risk_evaluator_id", None)
            or getattr(hold, "risk_evaluator_id", None)
        ),
        risk_evaluator_version=(
            getattr(assessment, "risk_evaluator_version", None)
            or getattr(hold, "risk_evaluator_version", None)
        ),
        canonicalization_version=(
            getattr(assessment, "canonicalization_version", None)
            or getattr(hold, "canonicalization_version", None)
        ),
        instruction_digest=(
            getattr(assessment, "instruction_digest", None)
            or getattr(hold, "instruction_digest", None)
        ),
        policy_evidence_references=list(
            getattr(assessment, "policy_evidence_references", ())
            or getattr(hold, "policy_evidence_references", ())
        ),
        risk_evidence_references=list(
            getattr(assessment, "risk_evidence_references", ())
            or getattr(hold, "risk_evidence_references", ())
        ),
        uncertainty=(
            getattr(assessment, "uncertainty", "")
            or getattr(hold, "uncertainty", "")
        ),
        recovery_semantics=(
            getattr(assessment, "recovery_semantics", "")
            or getattr(hold, "recovery_semantics", "")
        ),
    )
