"""RMT-CAP-13 -- /ops/reasoning routes (operator-auth, opt-in, rate-limited).

Disabled by default: ``RMT_REASONING_ENABLED`` unset => 503 before anything
else runs and no model is ever called. Mounted in ``app/main.py`` behind
``require_operator``, like the agent and coding-agent surfaces.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.ops import ops_config
from app.ops.auth import OperatorIdentity, require_operator
from app.ops.ratelimit import _check, _principal
from app.reasoning import config, explain as explain_mod, store

router = APIRouter(prefix="/ops/reasoning", tags=["reasoning"])


class ExplainRequest(BaseModel):
    action_id: str | None = None
    approval_id: str | None = None
    execution_id: str | None = None


def _require_enabled() -> None:
    if not config.reasoning_enabled():
        raise HTTPException(status_code=503, detail="reasoning disabled")


def _rate_limit(request: Request) -> None:
    if ops_config.ratelimit_enabled():
        _check((_principal(request), "reasoning"), ops_config.ratelimit_agent_per_min())


@router.post("/explain")
def explain_incident(
    body: ExplainRequest,
    request: Request,
    operator: OperatorIdentity = Depends(require_operator),
):
    _require_enabled()
    ids = {k: v for k, v in body.model_dump().items() if v}
    if len(ids) != 1:
        raise HTTPException(
            status_code=422,
            detail="exactly one of action_id / approval_id / execution_id required",
        )
    _rate_limit(request)
    kind, value = next(iter(ids.items()))
    return explain_mod.explain(
        incident_ref=f"{kind}:{value}",
        requested_by=operator.name,
        **ids,
    )


@router.get("/explanations")
def list_explanations(
    incident_ref: str | None = None,
    limit: int = 50,
    operator: OperatorIdentity = Depends(require_operator),
):
    _require_enabled()
    return {"explanations": store.list_for(incident_ref, limit)}
