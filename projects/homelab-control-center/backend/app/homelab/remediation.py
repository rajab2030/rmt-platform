"""Above-Core Homelab remediation wiring (G2).

Connects the frozen Core's intelligence/decision output to the single
governed execution boundary for Homelab services. This module is Homelab-
specific and above-Core; it does not modify the frozen Core.

Path:  Understand -> Decide -> ActionRequest -> execute_governed_action
       -> Govern -> Authorize -> Execute -> Verify -> Learn

Guarantees:
  * Remediation confidence originates from the actual health evaluation; it
    is never fabricated (no hardcoded confidence=100).
  * A healthy Homelab target stays continue_monitoring and produces no
    remediation ActionRequest.
  * An unhealthy/critical Homelab target may produce a restart ActionRequest.
  * The ActionRequest enters execute_governed_action() only. There is no
    direct Docker call and no direct adapter invocation from this layer.
"""
import uuid
from datetime import datetime, timezone

from app.core.intelligence.schemas import HealthStatus
from app.core.intelligence.actions.models import ActionRequest, ActionType
from app.core.intelligence.actions.service import execute_governed_action
from app.core.intelligence.verification.models import ExpectedOutcome
from app.core.configuration.settings import load_settings
from app.core.intelligence.execution.adapters.registry import adapter_registry
from app.core.intelligence.memory.models import MemoryRecord
from app.core.intelligence.memory.service import remember
from app.homelab.verification import verify_docker_execution


# Homelab remediation policy. Confidence is intentionally NOT set here; it is
# taken from the actual evaluation at build time.
REMEDIATION_POLICY = {
    "uptime-kuma": {
        "action_type": ActionType.RESTART,
        "remediate_on": {HealthStatus.CRITICAL},
        "expected_state": "running",
        "requires_approval": True,
    },
}


def resolve_adapter_name() -> str:
    """Resolve the execution adapter from configuration (mirrors main.py).

    Returns the configured runtime engine when that adapter is registered,
    otherwise the safe simulation adapter. The decision layer never invokes
    an adapter directly; this only selects the adapter for the governed
    boundary.
    """
    settings = load_settings()
    engine = settings.runtime.engine
    if adapter_registry.get(engine) is not None:
        return engine
    return "simulation"


def build_remediation_action(evaluation, decision=None):
    """Build a governed ActionRequest for a Homelab target, or None.

    Returns None when remediation is not justified: the target is not a
    remediable Homelab service, or its evaluation is not in the remediate-on
    set (e.g. HEALTHY -> continue_monitoring, no action).

    The returned ActionRequest carries confidence from the actual evaluation
    and an explicit expected_outcome, so the governed chain can authorize and
    verify the intended result.
    """
    policy = REMEDIATION_POLICY.get(evaluation.component)
    if policy is None:
        return None
    if evaluation.status not in policy["remediate_on"]:
        return None

    return ActionRequest(
        decision_id=f"homelab-{evaluation.component}-{uuid.uuid4().hex[:8]}",
        component=evaluation.component,
        action_type=policy["action_type"],
        reason=(
            decision.reason
            if decision is not None and decision.reason
            else evaluation.message
        ),
        confidence=evaluation.confidence,
        requires_approval=policy.get("requires_approval", True),
        expected_outcome=ExpectedOutcome(
            target=evaluation.component,
            operation=policy["action_type"].value,
            expected_state=policy["expected_state"],
        ),
    )


def remediate(evaluation, decision=None, adapter_name=None):
    """Build and route a remediation ActionRequest through the governed
    boundary.

    Returns the governed outcome dict, or a no_remediation marker when
    remediation is not justified. Never bypasses policy, risk, approval,
    authorization, or execution-boundary validation.
    """
    action = build_remediation_action(evaluation, decision)
    if action is None:
        return {
            "status": "no_remediation",
            "component": evaluation.component,
        }
    return execute_governed_action(
        action,
        adapter_name=adapter_name or resolve_adapter_name(),
    )


def record_learning(component, outcome, confidence=None):
    """Record the remediation outcome via the existing Core learning/memory
    capability (append-only, read-only learning).

    Reuses the existing MemoryRecord/remember interface and ties the record
    to the actual remediation run through the governed outcome's
    execution_id/approval_id. Does not invoke execution or mint
    authorization.

    Shared with the approval-continuation wiring
    (``app/homelab/continuation.py``) so a held remediation that is later
    continued via ``POST /homelab/approve`` records its executed outcome
    through the same Learn boundary.
    """
    record = MemoryRecord(
        component=component,
        event_type="remediation",
        timestamp=datetime.now(timezone.utc),
        data={
            "status": outcome.get("status"),
            "execution_id": outcome.get("execution_id"),
            "approval_id": outcome.get("approval_id"),
            "docker_verification_status": outcome.get("docker_verification_status"),
            "docker_verification_reason": outcome.get("docker_verification_reason"),
            "confidence": confidence,
        },
    )
    return remember(record)


def remediate_and_verify(evaluation, decision=None, adapter_name=None):
    """Full Homelab remediation flow: build the ActionRequest, route it through
    the governed boundary, then verify the resulting Docker state through the
    existing verification boundary (fed by the above-Core Docker observer).

    Decision -> ActionRequest -> Govern -> Authorize -> Execute -> Verify
    -> Learn

    Returns the governed outcome dict, augmented with the Docker verification
    result when execution succeeded. Never bypasses governance.
    """
    action = build_remediation_action(evaluation, decision)
    if action is None:
        return {
            "status": "no_remediation",
            "component": evaluation.component,
        }

    result = execute_governed_action(
        action,
        adapter_name=adapter_name or resolve_adapter_name(),
    )

    if (
        result.get("status") == "executed"
        and result.get("execution_id")
        and action.expected_outcome is not None
    ):
        verification = verify_docker_execution(
            result["execution_id"],
            action.expected_outcome,
            action.component,
        )
        result["docker_verification_status"] = verification.status
        result["docker_verification_reason"] = verification.reason

    # Learn: record the remediation outcome through the existing Core
    # learning/memory capability (append-only, read-only). Tied to the actual
    # run via the governed outcome's execution_id/approval_id.
    #
    # NOTE: when this remediation is held for manual approval, the outcome
    # recorded here is the held state ("manual_approval_required"). The
    # executed outcome of the continuation is recorded by
    # app/homelab/continuation.py::continue_remediation.
    record_learning(
        action.component,
        result,
        confidence=evaluation.confidence,
    )

    return result


def remediate_component(component, adapter_name=None):
    """End-to-end Homelab remediation for a component from its current
    observation.

    Understand -> Decide -> ActionRequest -> Govern -> Authorize -> Execute
    -> Verify

    Reads the current observation for the component, evaluates health, builds
    the decision, and routes remediation through the governed boundary with
    Docker verification. Returns a governed outcome dict.
    """
    from app.core.observability.service import get_current_container_metrics
    from app.core.intelligence.observation.normalize import normalize_observation
    from app.core.intelligence.context.service import enrich_component
    from app.core.intelligence.rules import create_health_evaluation
    from app.core.intelligence.decision.engine import make_decision

    metrics = get_current_container_metrics()
    metric = next((m for m in metrics if m.name == component), None)
    if metric is None:
        return {"status": "no_observation", "component": component}

    observation = normalize_observation(metric)
    context = enrich_component(observation)["context"]
    evaluation = create_health_evaluation(observation, context)
    decision = make_decision(evaluation)

    return remediate_and_verify(
        evaluation,
        decision,
        adapter_name=adapter_name,
    )
