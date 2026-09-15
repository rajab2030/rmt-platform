from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from app.core.intelligence.actions.binding import bind_action
from app.core.intelligence.actions.models import ActionRequest
from app.core.intelligence.actions.policy import (
    ActionPolicyResult,
    evaluate_action_policy,
)
from app.core.intelligence.actions.simulation import (
    ActionSimulationResult,
    simulate_action,
)


DEFAULT_GOVERNANCE_DOMAIN = "rmt.default"
DEFAULT_EVALUATOR_VERSION = "1"


class AssessmentError(RuntimeError):
    pass


class PolicyEvaluator(Protocol):
    evaluator_id: str
    version: str

    def evaluate(self, action: ActionRequest) -> ActionPolicyResult: ...


class RiskEvaluator(Protocol):
    evaluator_id: str
    version: str

    def evaluate(self, action: ActionRequest) -> ActionSimulationResult: ...


class DefaultPolicyEvaluator:
    evaluator_id = "rmt.default.action-policy"
    version = DEFAULT_EVALUATOR_VERSION

    def evaluate(self, action: ActionRequest) -> ActionPolicyResult:
        return evaluate_action_policy(action)


class DefaultRiskEvaluator:
    evaluator_id = "rmt.default.action-simulation"
    version = DEFAULT_EVALUATOR_VERSION

    def evaluate(self, action: ActionRequest) -> ActionSimulationResult:
        return simulate_action(action)


@dataclass(frozen=True)
class AssessmentRegistration:
    domain: str
    policy: PolicyEvaluator
    risk: RiskEvaluator
    operations: frozenset[str]
    adapters: frozenset[str]


@dataclass(frozen=True)
class GovernanceAssessment:
    assessment_id: str
    governance_domain: str
    policy_result: ActionPolicyResult
    risk_result: ActionSimulationResult
    policy_evaluator_id: str
    policy_evaluator_version: str
    risk_evaluator_id: str
    risk_evaluator_version: str
    instruction_digest: str
    canonicalization_version: str
    adapter_name: str
    assessed_at: datetime
    policy_evidence_references: tuple[str, ...]
    risk_evidence_references: tuple[str, ...]
    uncertainty: str
    recovery_semantics: str


class AssessmentRegistry:
    def __init__(self):
        self._registrations: dict[str, AssessmentRegistration] = {}

    def register(
        self,
        *,
        domain: str,
        policy: PolicyEvaluator,
        risk: RiskEvaluator,
        operations: set[str] | frozenset[str],
        adapters: set[str] | frozenset[str],
    ) -> None:
        if not domain or domain in self._registrations:
            raise AssessmentError(f"Governance domain already registered: {domain!r}")
        if not operations or not adapters:
            raise AssessmentError("Assessment registration requires operations and adapters")
        for evaluator in (policy, risk):
            if not getattr(evaluator, "evaluator_id", "") or not getattr(evaluator, "version", ""):
                raise AssessmentError("Evaluator identity and version are required")
            if not callable(getattr(evaluator, "evaluate", None)):
                raise AssessmentError("Evaluator must provide evaluate()")
        self._registrations[domain] = AssessmentRegistration(
            domain=domain,
            policy=policy,
            risk=risk,
            operations=frozenset(operations),
            adapters=frozenset(adapters),
        )

    def get(self, domain: str) -> AssessmentRegistration | None:
        return self._registrations.get(domain)


assessment_registry = AssessmentRegistry()
assessment_registry.register(
    domain=DEFAULT_GOVERNANCE_DOMAIN,
    policy=DefaultPolicyEvaluator(),
    risk=DefaultRiskEvaluator(),
    operations={
        "restart_component", "create_checkpoint", "scale_down",
        "isolate_component", "start", "stop", "restart", "create", "remove",
    },
    adapters={"simulation", "docker", "git", "module_change"},
)


def resolve_assessment(
    action: ActionRequest,
    adapter_name: str,
    *,
    registry: AssessmentRegistry = assessment_registry,
) -> GovernanceAssessment:
    registration = registry.get(action.governance_domain)
    if registration is None:
        raise AssessmentError(f"Unknown governance domain: {action.governance_domain!r}")
    operation = action.action_type.value
    if operation not in registration.operations:
        raise AssessmentError(f"Operation {operation!r} is not registered for the domain")
    if adapter_name not in registration.adapters:
        raise AssessmentError(f"Adapter {adapter_name!r} is not registered for the domain")

    try:
        instruction_digest, payload = bind_action(action, adapter_name)
        policy_result = registration.policy.evaluate(action)
        risk_result = registration.risk.evaluate(action)
    except Exception as exc:
        raise AssessmentError(f"Domain assessment unavailable: {exc}") from exc

    if not isinstance(policy_result, ActionPolicyResult):
        raise AssessmentError("Malformed policy assessment")
    if (
        not isinstance(policy_result.allowed, bool)
        or not isinstance(policy_result.requires_approval, bool)
        or not isinstance(policy_result.reason, str)
    ):
        raise AssessmentError("Malformed policy assessment fields")
    if not isinstance(policy_result.evidence_references, tuple) or not all(
        isinstance(reference, str) and reference
        for reference in policy_result.evidence_references
    ):
        raise AssessmentError("Malformed policy evidence references")
    if not isinstance(risk_result, ActionSimulationResult):
        raise AssessmentError("Malformed risk assessment")
    if risk_result.risk_level not in {"low", "medium", "high", "critical", "unknown"}:
        raise AssessmentError("Malformed risk level")
    if risk_result.action_id != action.action_id:
        raise AssessmentError("Risk assessment action mismatch")
    if (
        risk_result.component != action.component
        or risk_result.action_type != action.action_type.value
        or not isinstance(risk_result.expected_impact, str)
        or not isinstance(risk_result.rollback_available, bool)
        or not isinstance(risk_result.uncertainty, str)
        or not isinstance(risk_result.recovery_semantics, str)
    ):
        raise AssessmentError("Malformed risk assessment fields")
    if not isinstance(risk_result.evidence_references, tuple) or not all(
        isinstance(reference, str) and reference
        for reference in risk_result.evidence_references
    ):
        raise AssessmentError("Malformed risk evidence references")
    if action.governance_domain != DEFAULT_GOVERNANCE_DOMAIN and (
        not policy_result.evidence_references
        or not risk_result.evidence_references
        or not risk_result.uncertainty
        or not risk_result.recovery_semantics
    ):
        raise AssessmentError("Domain assessment evidence and recovery semantics required")

    return GovernanceAssessment(
        assessment_id=str(uuid4()),
        governance_domain=action.governance_domain,
        policy_result=policy_result,
        risk_result=risk_result,
        policy_evaluator_id=registration.policy.evaluator_id,
        policy_evaluator_version=registration.policy.version,
        risk_evaluator_id=registration.risk.evaluator_id,
        risk_evaluator_version=registration.risk.version,
        instruction_digest=instruction_digest,
        canonicalization_version=payload["canonicalization_version"],
        adapter_name=adapter_name,
        assessed_at=datetime.now(timezone.utc),
        policy_evidence_references=policy_result.evidence_references,
        risk_evidence_references=risk_result.evidence_references,
        uncertainty=risk_result.uncertainty,
        recovery_semantics=risk_result.recovery_semantics,
    )
