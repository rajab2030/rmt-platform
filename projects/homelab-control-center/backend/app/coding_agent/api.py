"""RMT-CAP-10 HTTP surface (above-Core).

  POST /coding-agent/propose         -- the hook's call: a proposed command
  GET  /coding-agent/holds           -- list holds (``?status=`` filter)
  GET  /coding-agent/holds/{hold_id} -- single-hold poll
  POST /coding-agent/decide          -- operator decision on a held command

No LLM anywhere in the review path; evidence is real or absent, never
fabricated. Gated by ``RMT_CODING_AGENT_ENABLED`` (default off). No
``app/core/**`` change; no new mutation path -- this only decides whether a
shell command proposed by *this repository's own Claude Code session* is
allowed to run, via the project-scoped ``PreToolUse`` hook.

A new hold fires the same fail-open ``notify_held`` sink every other domain's
holds already use (``app/ops/notifications.py``) -- the hook only polls for
``RMT_CODING_AGENT_POLL_TIMEOUT_S`` before failing open, so a real alert
matters here more than most: a human who never sees the hold otherwise finds
out only after the command already went through unreviewed.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.coding_agent import config as coding_agent_config
from app.coding_agent import risk_rules
from app.coding_agent.models import CommandHold
from app.coding_agent.review import assess
from app.coding_agent.store import command_hold_store
from app.ops.auth import OperatorIdentity, require_operator
from app.ops.notifications import notify_held

router = APIRouter(prefix="/coding-agent", tags=["Coding Agent"])


def _disabled() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail="coding-agent governance disabled (RMT_CODING_AGENT_ENABLED)",
    )


class ProposeBody(BaseModel):
    command: str
    cwd: str
    reason: str | None = None
    session_id: str | None = None


class DecideBody(BaseModel):
    hold_id: str
    approved: bool


@router.post("/propose")
def propose(body: ProposeBody):
    """The hook's call. No rule match => auto-allow, no hold created, no
    evidence computed (zero cost on the common path). A match => a hold is
    created and its evidence + verdict returned for a human to review."""
    if not coding_agent_config.enabled():
        raise _disabled()

    match = risk_rules.classify(body.command)
    if match is None:
        return {"decision": "auto_allow"}

    evidence, verdict = assess(match.rule, body.cwd)
    hold = CommandHold(
        command=body.command,
        cwd=body.cwd,
        reason=body.reason,
        session_id=body.session_id,
        risk_rule=match.rule.name,
        risk_level=match.rule.risk_level,
        evidence=evidence,
        verdict=verdict,
    )
    command_hold_store.create(hold)
    # O2-equivalent: a human is needed and the hook only polls for so long
    # (RMT_CODING_AGENT_POLL_TIMEOUT_S) before failing open -- a real alert
    # gives them a chance to act before that window closes, same fail-open
    # notification sink every other domain's holds already use.
    notify_held(
        kind="coding_agent_command",
        component=match.rule.name,
        approval_id=hold.hold_id,
        detail=f"{body.command!r} in {body.cwd} (verdict: {verdict})",
        source="coding_agent",
    )
    return {
        "decision": "hold",
        "hold_id": hold.hold_id,
        "review": {
            "risk_rule": hold.risk_rule,
            "risk_level": hold.risk_level,
            "evidence": [e.model_dump() for e in evidence],
            "verdict": verdict,
        },
    }


@router.get("/holds")
def list_holds(status: str | None = None):
    if not coding_agent_config.enabled():
        raise _disabled()
    holds = command_hold_store.all()
    if status is not None:
        holds = [h for h in holds if h.status == status]
    return {"holds": [h.model_dump() for h in holds]}


@router.get("/holds/{hold_id}")
def get_hold(hold_id: str):
    if not coding_agent_config.enabled():
        raise _disabled()
    hold = command_hold_store.get(hold_id)
    if hold is None:
        raise HTTPException(status_code=404, detail="hold not found")
    return hold.model_dump()


@router.post("/decide")
def decide(
    body: DecideBody,
    operator: OperatorIdentity = Depends(require_operator),
):
    """The human decision. ``decided_by`` comes from the authenticated
    operator, not the request body -- same pattern ``/approve`` already
    established."""
    if not coding_agent_config.enabled():
        raise _disabled()
    hold = command_hold_store.get(body.hold_id)
    if hold is None:
        raise HTTPException(status_code=404, detail="hold not found")
    if hold.status != "pending":
        raise HTTPException(
            status_code=409, detail=f"hold already {hold.status}"
        )
    decided = command_hold_store.decide(
        body.hold_id, approved=body.approved, decided_by=operator.name
    )
    return decided.model_dump()
