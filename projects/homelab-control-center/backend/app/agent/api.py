"""RMT-CAP-05 (5A) HTTP surface (above-Core).

  POST /agent/authority/grant  -- operator grants the agent a scoped,
                                  single-use, time-limited authority
  POST /agent/act              -- agent submits a proposal -> governed lifecycle
  GET  /agent/status           -- read-only: flags, active grants, last outcome
  GET  /agent/authority        -- read-only: current active grants

Granting authority is an operator action (capability != authority). Every
``/agent/act`` proposal still passes full policy / risk / approval; a held
proposal is never auto-continued here.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.intelligence.actions.models import ActionType

from app.ops.auth import OperatorIdentity, require_operator
from app.ops.separation import separation_enabled
from app.agent import loop_config
from app.agent.authority import authority_store
from app.agent.contract import AgentIdentity, AgentIntent, AgentProposal
from app.agent.adapter import propose_and_govern
from app.agent.dependency_guard import dependency_view
from app.agent.llm_agent import LlmAgent, LlmProposalError


router = APIRouter(prefix="/agent", tags=["Agent"])

_last_outcome: dict = {"value": None}


class GrantBody(BaseModel):
    operation: str
    target: str
    granted_by: str | None = None  # deprecated: identity comes from auth
    ttl_seconds: int | None = None


class ProposeBody(BaseModel):
    agent_id: str
    goal: str
    target: str
    mechanism: str
    reason: str = ""
    confidence: int = 0
    expected_state: str = "running"
    grant_id: str | None = None


class LlmActBody(BaseModel):
    goal: str
    grant_id: str | None = None


@router.post("/authority/grant")
def grant_authority(
    body: GrantBody,
    operator: OperatorIdentity = Depends(require_operator),
):
    """Operator action: issue a scoped, single-use, time-limited grant.

    The granting identity is the authenticated operator; any ``granted_by`` in
    the body is ignored (kept only for transitional compatibility).
    """
    try:
        ActionType(body.operation)
    except ValueError:
        return {
            "error": "invalid_operation",
            "detail": f"unknown operation '{body.operation}'",
        }
    g = authority_store.grant(
        operation=body.operation,
        target=body.target,
        granted_by=operator.name,
        ttl_seconds=body.ttl_seconds,
    )
    return g.as_dict()


@router.post("/act")
def act(body: ProposeBody):
    """Agent proposes a consequential action -> governed lifecycle."""
    try:
        mechanism = ActionType(body.mechanism)
    except ValueError:
        return {
            "decision": "invalid",
            "detail": f"unknown mechanism '{body.mechanism}'",
        }

    proposal = AgentProposal(
        identity=AgentIdentity(agent_id=body.agent_id),
        intent=AgentIntent(
            goal=body.goal,
            target=body.target,
            mechanism=mechanism,
            reason=body.reason,
            confidence=body.confidence,
        ),
        expected_state=body.expected_state,
        grant_id=body.grant_id,
    )
    payload = propose_and_govern(proposal).as_dict()
    _last_outcome["value"] = payload
    return payload


@router.post("/act/llm")
def act_llm(body: LlmActBody):
    """5B: an LLM turns a natural-language goal into a proposal, then the
    proposal runs the identical 5A governed path (authority -> T13 ->
    governance -> human approval). The LLM never executes anything."""
    if not loop_config.AGENT_LLM_ENABLED:
        return {
            "decision": "llm_disabled",
            "detail": "LLM agent disabled (RMT_AGENT_LLM_ENABLED)",
        }

    try:
        from app.core.observability.service import (
            get_current_container_metrics,
        )

        observations = get_current_container_metrics()
    except Exception:
        observations = []

    try:
        proposal = LlmAgent().propose(
            body.goal, observations, grant_id=body.grant_id
        )
    except LlmProposalError as exc:
        payload = {
            "decision": exc.reason,
            "detail": exc.detail,
            "goal": body.goal,
        }
        _last_outcome["value"] = payload
        return payload

    payload = propose_and_govern(proposal).as_dict()
    _last_outcome["value"] = payload
    return payload


@router.get("/status")
def status():
    return {
        "enabled": loop_config.AGENT_ENABLED,
        "default_requires_approval": loop_config.AGENT_DEFAULT_REQUIRES_APPROVAL,
        "dependency_escalation": loop_config.AGENT_DEPENDENCY_ESCALATION,
        "dependency_map": dependency_view(),
        "separation_of_duties": separation_enabled(),
        "llm": {
            "enabled": loop_config.AGENT_LLM_ENABLED,
            "model": loop_config.AGENT_LLM_MODEL,
            "host": loop_config.AGENT_LLM_HOST,
        },
        "active_grants": len(authority_store.list_active()),
        "last_outcome": _last_outcome["value"],
    }


@router.get("/authority")
def authority():
    return {
        "active_grants": [g.as_dict() for g in authority_store.list_active()]
    }
