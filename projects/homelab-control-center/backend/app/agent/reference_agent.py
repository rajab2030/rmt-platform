"""RMT-CAP-05 (5A) -- deterministic reference agent.

The first "child" for the governed agent surface: no model, no network. Given a
Core ``HealthEvaluation`` it emits an ``AgentProposal`` (RESTART when CRITICAL,
otherwise none). This is what 5A validates the surface against; an LLM-backed
agent (5B) is a separate, opt-in adapter that produces the same
``AgentProposal`` type.
"""
from app.core.intelligence.actions.models import ActionType
from app.core.intelligence.schemas import HealthStatus

from app.agent.contract import AgentIdentity, AgentIntent, AgentProposal


REFERENCE_AGENT = AgentIdentity(
    agent_id="reference-agent",
    role="operator",
    operational_context="homelab",
)


def propose_from_evaluation(
    evaluation, grant_id: str | None = None, identity: AgentIdentity | None = None
) -> AgentProposal | None:
    """CRITICAL -> a RESTART proposal; anything else -> None."""
    if evaluation.status != HealthStatus.CRITICAL:
        return None
    return AgentProposal(
        identity=identity or REFERENCE_AGENT,
        intent=AgentIntent(
            goal=f"restore {evaluation.component} availability",
            target=evaluation.component,
            mechanism=ActionType.RESTART,
            reason=getattr(evaluation, "message", "") or "component critical",
            confidence=getattr(evaluation, "confidence", 0),
        ),
        expected_state="running",
        grant_id=grant_id,
    )
