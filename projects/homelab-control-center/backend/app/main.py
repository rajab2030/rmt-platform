import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.schemas.container import Container

from app.ops import ops_config
from app.ops.auth import OperatorIdentity, require_operator
from app.ops.execution_evidence import record_failed_execution_evidence
from app.ops.logging_config import (
    RequestContextMiddleware,
    configure_logging,
    log_event,
)
from app.ops.notifications import notify_held
from app.ops.reconcile import reconcile_governance_stores
from app.ops.retention import archive_aged_evidence
from app.ops.ratelimit import rate_limit_execute
from app.ops.runtime_info import runtime_status, warn_on_capability_mismatch
from app.ops.separation import check_separation
from app.ops.verification import verify_executed_action
from app.ops.verification import index as verification_index
from app.ops.verification.index import rebuild as rebuild_verification_index

from app.monitor import get_history
from app.collector import collect_metrics

from app.core.module_registry.registry import get_modules
from app.core.configuration.settings import load_settings
from app.core.configuration.public import create_public_config
from app.core.platform_state.service import get_platform_state
from app.docker_provider import DockerPlatformStateProvider

from app.core.observability.api import router as observability_router
from app.core.observability.storage import (
    init_storage as init_observability_storage,
)
from app.core.intelligence.memory.storage import (
    init_storage as init_intelligence_memory_storage,
)
from app.core.intelligence.api import router as intelligence_router
from app.engineering.api import router as engineering_router
from app.agent.api import router as agent_router
from app.coding_agent.api import router as coding_agent_router

from app.homelab import loop_config
from app.homelab.operational_loop import operational_loop

from app.core.intelligence.execution.adapters.bootstrap import (
    register_default_adapters,
)
from app.agent.git_adapter import register_git_adapter

from app.core.intelligence.actions.models import (
    ActionRequest,
    ActionType,
)

from app.core.intelligence.actions.service import (
    execute_governed_action,
)

from app.core.intelligence.actions.approval_service import (
    approve_held_action,
)

from app.core.intelligence.execution.adapters.registry import (
    adapter_registry,
)

import asyncio


logger = logging.getLogger("rmt.http")


OPERATION_TO_ACTION_TYPE = {
    "start": ActionType.START,
    "stop": ActionType.STOP,
    "restart": ActionType.RESTART,
    "create": ActionType.CREATE,
    "remove": ActionType.REMOVE,
}


def _resolve_adapter_name() -> str:
    """
    Resolve the execution adapter from configuration.

    Uses the configured runtime engine when that adapter is registered.
    Falls back to the safe simulation adapter otherwise, so the platform
    never hard-depends on a specific provider (e.g. docker).
    """
    settings = load_settings()
    engine = settings.runtime.engine

    if adapter_registry.get(engine) is not None:
        return engine

    return "simulation"


def _log_governed(event: str, *, principal: str, result, **ctx) -> None:
    """O1: one structured line per governed HTTP mutation, correlated by the
    ids the durable evidence already uses. `result` may not be a dict."""
    r = result if isinstance(result, dict) else {}
    log_event(
        logger,
        event,
        principal=principal,
        governed_status=r.get("status"),
        action_id=r.get("action_id"),
        execution_id=r.get("execution_id"),
        **ctx,
    )


collector_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global collector_task

    # O1: own the `rmt` logger tree (JSON to stdout -> journald) before any
    # other startup step so the reconcile / retention / loop lines are captured.
    configure_logging()
    log_event(
        logger,
        "startup",
        loop_enabled=loop_config.LOOP_ENABLED,
        auth_enabled=ops_config.auth_enabled(),
    )

    # S1: refuse to start with an unauthenticated mutating surface.
    if ops_config.auth_enabled() and not ops_config.operator_tokens():
        raise RuntimeError(
            "RMT_AUTH_ENABLED is true but RMT_OPERATOR_TOKENS is empty -- "
            "refusing to start. Set operator tokens or (local dev only) "
            "RMT_AUTH_ENABLED=false."
        )

    register_default_adapters()

    # RMT-CAP-06 (C2/D-1): above-Core registration of the git-tag domain
    # adapter into the Core's adapter_registry -- the same extension point
    # register_default_adapters itself uses. Inert unless
    # RMT_AGENT_GIT_REPO_PATH is set to a real git repo (see
    # app/agent/git_adapter.py). No app/core/** change.
    register_git_adapter()

    # Ensure the SQLite substrate exists before anything reads or writes it.
    # Both tables live in data/observability.db and are created by these
    # (idempotent) init_storage() calls; nothing else invokes them, so a fresh
    # deploy with an empty data/ would otherwise 500 on the first metrics write
    # or intelligence-memory read. Mirrors the reconcile / retention steps
    # below: startup makes the durable substrate ready.
    init_observability_storage()
    init_intelligence_memory_storage()

    # D6: log a WARNING if the configured runtime engine (config.yaml
    # runtime.engine) cannot actually be provided on this host -- e.g. 'docker'
    # requested but the daemon is unreachable, so governed actions would
    # silently run on the simulation adapter.
    warn_on_capability_mismatch(logger)

    # E2 + E6: on startup, correct the approval hold store against the
    # authoritative record store (a resolved hold is not persisted by the Core),
    # then audit the execution-authorization store against holds + records for
    # inconsistent approval linkage (log-only). Fail-open; see
    # app/ops/reconcile.py.
    reconcile_governance_stores()

    # E4: archive evidence records older than RMT_EVIDENCE_RETENTION_DAYS out of
    # the live JSON stores into <name>.archive.jsonl so the live files stay
    # bounded. After the reconcile above; fail-open; see app/ops/retention.py.
    archive_aged_evidence()

    # B1b: build the above-Core effective-status verification index from the
    # durable evidence (after retention so it reflects the trimmed store).
    # Silent -- fires no notification; marks history rows already-notified.
    # Fail-open; see app/ops/verification/index.py.
    try:
        rebuild_verification_index()
    except Exception as exc:  # never block startup
        logger.warning("verification index rebuild skipped (non-fatal): %r", exc)

    collector_task = asyncio.create_task(
        collect_metrics()
    )

    # RMT-CAP-04: the continuous Homelab operational loop is opt-in and
    # disabled by default. It only starts when explicitly enabled
    # (RMT_HOMELAB_LOOP_ENABLED) or via POST /homelab/loop/start.
    if loop_config.LOOP_ENABLED:
        operational_loop.start()

    yield

    if collector_task:
        collector_task.cancel()

    operational_loop.stop()


app = FastAPI(
    title="RMT Platform Center",
    version="0.1",
    lifespan=lifespan,
)


# S5: origins from RMT_CORS_ORIGINS (default: local Vite dev origin only);
# methods/headers scoped to what the API and its browser client actually use.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ops_config.cors_origins(),
    allow_credentials=True,
    allow_methods=ops_config.CORS_ALLOW_METHODS,
    allow_headers=ops_config.CORS_ALLOW_HEADERS,
)

# O1: added last => outermost. Binds a request id (honours inbound
# X-Request-ID), echoes it on the response, logs one `http_request` line.
app.add_middleware(RequestContextMiddleware)


app.include_router(observability_router)

app.include_router(intelligence_router)

app.include_router(engineering_router)

# S1: the agent surface (grant / act / act.llm and its read-only status) is
# entirely behind operator authentication.
app.include_router(agent_router, dependencies=[Depends(require_operator)])

# RMT-CAP-10: coding-agent command governance -- entirely behind operator
# authentication, same as every other above-Core mutation-adjacent surface.
app.include_router(coding_agent_router, dependencies=[Depends(require_operator)])


@app.get("/")
def root():
    return {
        "name": "RMT Platform Control Center",
        "version": "0.1"
    }


@app.get("/health")
def health():
    """O3: a lightweight, unauthenticated liveness/readiness probe for an
    external monitor / heartbeat (``scripts/rmt-heartbeat.sh``). Always HTTP
    200 while the process answers; ``status`` is ``"degraded"`` when the CAP-04
    loop has a cycle error or a quarantined component."""
    loop = operational_loop.get_status()
    quarantined = [
        name
        for name, s in loop.get("components", {}).items()
        if s.get("quarantined")
    ]
    degraded = loop.get("last_cycle_error") is not None or bool(quarantined)
    return {
        "status": "degraded" if degraded else "ok",
        "loop": {
            "enabled": loop.get("enabled"),
            "running": loop.get("running"),
            "cycle_count": loop.get("cycle_count"),
            "last_cycle_at": loop.get("last_cycle_at"),
            "last_cycle_error": loop.get("last_cycle_error"),
            "quarantined_components": quarantined,
        },
        # D6: capability-sensitive runtime state (adapter mode, git). Advisory
        # only -- an `adapter_degraded` here does not flip `status`.
        "runtime": runtime_status(),
    }


@app.get("/metrics")
def metrics():
    """O4: platform self-metrics in Prometheus text format. Unauthenticated
    (like /health) so a scraper can reach it; read-only derivation from the
    operational-loop status and the durable evidence stores -- no new evidence,
    no write path."""
    from app.ops.metrics import CONTENT_TYPE, render_prometheus

    return PlainTextResponse(render_prometheus(), media_type=CONTENT_TYPE)


@app.get("/ops/holds")
def ops_holds(operator: OperatorIdentity = Depends(require_operator)):
    """T1-4: read-only snapshot of every PENDING approval hold, classified
    (age, expiry, whether the approval record already resolved it, whether it
    is still actionable, and S3 provenance when present) for the external
    escalation script ``scripts/rmt-escalate.sh``. Derives from the durable
    hold + record stores only; writes nothing; never 500s (``[]`` on error)."""
    from app.ops.held_holds import open_holds_view

    return {"holds": open_holds_view()}


@app.get("/ops/verifications")
def ops_verifications(
    limit: int = 50,
    effective_status: str | None = None,
    operator: OperatorIdentity = Depends(require_operator),
):
    """B1b: read-only view of the above-Core effective-status verification
    index -- per executed governed action, whether it was actually verified
    and, if not, why (``adapter_execution_failed`` / ``state_mismatch`` /
    ``unverified``). Newest first; ``?limit=`` (default 50) and
    ``?effective_status=`` filter. Derives from the durable evidence; writes
    nothing; ``[]`` on error."""
    return {
        "verifications": verification_index.view(
            limit=limit, effective_status=effective_status
        )
    }

@app.get("/ops/evidence")
def ops_evidence(
    action_id: str | None = None,
    approval_id: str | None = None,
    execution_id: str | None = None,
    operator: OperatorIdentity = Depends(require_operator),
):
    """RMT-CAP-09 (P-B): read-only Govern -> Verify evidence chain for one
    governed action, resolved by action_id / approval_id / execution_id.
    Derives from the durable evidence stores only; writes nothing; each
    section is fail-open (never 500s). At least one identifier required.
    Gated by ``RMT_OPS_EVIDENCE_ENABLED`` (default off -- opt-in)."""
    if not ops_config.ops_evidence_enabled():
        raise HTTPException(status_code=503, detail="ops evidence route disabled")
    if not any([action_id, approval_id, execution_id]):
        raise HTTPException(
            status_code=422,
            detail="exactly one of action_id / approval_id / execution_id required",
        )
    from app.ops.evidence_chain import evidence_chain

    return evidence_chain(
        action_id=action_id, approval_id=approval_id, execution_id=execution_id
    )



@app.get("/containers", response_model=list[Container])
def containers():
    from app.docker_api import get_containers
    try:
        return get_containers()
    except Exception as exc:  # V3: Docker socket unreachable -> 503, not 500
        raise HTTPException(status_code=503, detail=f"docker unavailable: {exc}")


@app.get("/modules")
def modules():
    return get_modules()


@app.get("/config")
def config():

    settings = load_settings()

    return create_public_config(
        settings
    )


@app.get("/platform/state")
def platform_state():
    try:
        return get_platform_state(
            DockerPlatformStateProvider()
        )
    except FileNotFoundError as exc:  # V3: `git` not on PATH -> 503, not 500
        raise HTTPException(status_code=503, detail=f"git unavailable: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"platform state unavailable: {exc}")


@app.get("/containers/{name}/stats")
def container_stats(name: str):
    from app.docker_api import get_container_stats
    try:
        return get_container_stats(name)
    except Exception as exc:  # V3: Docker socket unreachable -> 503, not 500
        raise HTTPException(status_code=503, detail=f"docker unavailable: {exc}")


@app.get("/monitor/history")
def history():
    return get_history()


@app.post("/execute", dependencies=[Depends(rate_limit_execute)])
def execute(
    operation: str,
    target: str,
    image: str | None = None,
    operator: OperatorIdentity = Depends(require_operator),
):
    """
    Route container mutations through the single authoritative governed
    lifecycle.

    Pipeline: Action -> Policy -> Risk(Simulation) -> Approval ->
    Authorization -> Execution Translation -> ExecutionEngine.

    Authorization is never fabricated here; it is created only from a
    legitimate approval result inside the governed lifecycle.
    """
    action_type = OPERATION_TO_ACTION_TYPE.get(operation)

    if action_type is None:
        return {
            "status": "unsupported_operation",
            "reason": f"Operation '{operation}' is not supported",
        }

    action = ActionRequest(
        decision_id=f"operator-{operator.name}-{operation}",
        component=target,
        action_type=action_type,
        reason=f"Operator {operator.name} requested {operation} on {target}",
        confidence=100,
        requires_approval=False,
        parameters={"image": image} if image else {},
    )

    result = execute_governed_action(
        action,
        adapter_name=_resolve_adapter_name(),
    )

    if isinstance(result, dict) and result.get("status") == "manual_approval_required":
        notify_held(
            kind="operator_execute",
            component=target,
            approval_id=result.get("approval_id"),
            detail=result.get("reason", "") or "",
            source="http_execute",
        )

    # E3: distinguishable evidence when the adapter was invoked and failed.
    record_failed_execution_evidence(
        result,
        expected=getattr(action, "expected_outcome", None),
        source="http_execute",
    )

    # B1a/B1b: above-Core post-condition verification for an executed operator
    # action. Resolves an observer for the resolved execution adapter +
    # operation; when none is registered (e.g. the simulation adapter) it
    # records nothing new and the Core's observation_unavailable stands. B1b
    # also updates the effective-status index and surfaces its verdict.
    if (
        isinstance(result, dict)
        and result.get("status") == "executed"
        and result.get("success")
        and result.get("execution_id")
    ):
        above_core = verify_executed_action(
            result["execution_id"],
            adapter_name=_resolve_adapter_name(),
            operation=operation,
            target=target,
            action_id=action.action_id,
        )
        result["above_core_verification_status"] = above_core.status
        _vrow = verification_index.get(result["execution_id"])
        result["effective_verification_status"] = (
            _vrow.effective_status if _vrow is not None else None
        )

    _log_governed(
        "governed_execute",
        principal=operator.name,
        result=result,
        operation=operation,
        target=target,
        approval_id=result.get("approval_id") if isinstance(result, dict) else None,
    )
    return result


@app.post("/approve")
def approve(
    approval_id: str,
    approved: bool = True,
    approved_by: str | None = None,  # deprecated: identity comes from auth
    operator: OperatorIdentity = Depends(require_operator),
):
    """
    Legitimate continuation for a manually held governed action.

    Resumes the previously governed action only after the required approval
    has been granted. It does not create a new action, skip policy/risk, or
    manufacture authorization independently.

    The approving identity is the authenticated operator; any ``approved_by``
    query field is ignored (kept only for transitional compatibility).
    """
    # S3: for an agent-originated hold, the approver must differ from the
    # operator who granted the agent's authority (opt-in: RMT_AUTH_SEPARATION).
    ok, why = check_separation(approval_id, operator.name)
    if not ok:
        raise HTTPException(status_code=403, detail=f"separation of duties: {why}")

    result = approve_held_action(
        approval_id,
        approved_by=operator.name,
        approved=approved,
    )
    # E3: distinguishable evidence when the adapter was invoked and failed.
    record_failed_execution_evidence(result, source="http_approve")
    _log_governed(
        "governed_approve",
        principal=operator.name,
        result=result,
        approval_id=approval_id,
        approved=approved,
    )
    return result


@app.post("/homelab/remediate")
def homelab_remediate(
    component: str,
    operator: OperatorIdentity = Depends(require_operator),
):
    """
    Above-Core Homelab remediation entrypoint.

    Runs the full governed capability for a Homelab component from its current
    observation: Understand -> Decide -> ActionRequest -> Govern -> Authorize
    -> Execute -> Verify. Routes through the single governed execution boundary
    (execute_governed_action) and the existing verification boundary. Never
    bypasses policy, risk, approval, authorization, or execution validation.
    """
    from app.homelab.remediation import remediate_component
    result = remediate_component(component)

    if isinstance(result, dict) and result.get("status") == "manual_approval_required":
        notify_held(
            kind="remediation",
            component=component,
            approval_id=result.get("approval_id"),
            detail=result.get("reason", "") or "",
            source="http_remediate",
        )

    # E3: covers the case remediate_and_verify skips (no expected_outcome);
    # a no-op when the above-Core Docker verify already recorded an outcome.
    record_failed_execution_evidence(result, source="http_remediate")

    _log_governed(
        "homelab_remediate",
        principal=operator.name,
        result=result,
        component=component,
        approval_id=result.get("approval_id") if isinstance(result, dict) else None,
    )
    return result


@app.post("/homelab/approve")
def homelab_approve(
    approval_id: str,
    approved: bool = True,
    approved_by: str | None = None,  # deprecated: identity comes from auth
    operator: OperatorIdentity = Depends(require_operator),
):
    """
    Above-Core Homelab remediation approval-continuation entrypoint.

    Continues a manually held Homelab remediation through the frozen Core
    approve_held_action(), then closes the Learn stage: runs the above-Core
    Docker verification and records the executed outcome as a learning
    record, correlated by approval_id / execution_id. The frozen Core
    continuation is called unchanged; this layer only records evidence after
    the Core has executed. A non-Homelab held action is continued exactly as
    the generic POST /approve would.

    The approving identity is the authenticated operator; any ``approved_by``
    query field is ignored (kept only for transitional compatibility).
    """
    # S3: for an agent-originated hold, the approver must differ from the
    # operator who granted the agent's authority (opt-in: RMT_AUTH_SEPARATION).
    ok, why = check_separation(approval_id, operator.name)
    if not ok:
        raise HTTPException(status_code=403, detail=f"separation of duties: {why}")

    from app.homelab.continuation import continue_remediation
    result = continue_remediation(
        approval_id,
        approved_by=operator.name,
        approved=approved,
    )
    # E3: covers a non-REMEDIATION_POLICY component, where continue_remediation
    # early-returns before the above-Core Docker verify; a no-op otherwise.
    record_failed_execution_evidence(result, source="http_homelab_approve")
    _log_governed(
        "homelab_approve",
        principal=operator.name,
        result=result,
        approval_id=approval_id,
        approved=approved,
    )
    return result


@app.get("/homelab/loop/status")
def homelab_loop_status():
    """
    Above-Core RMT-CAP-04 read-only status of the continuous Homelab
    operational loop: enabled/running flags, per-component loop state
    (cooldown, flap-window attempts, quarantine), and recent cycle history.
    Mutates nothing.
    """
    return operational_loop.get_status()


@app.post("/homelab/loop/start", dependencies=[Depends(require_operator)])
async def homelab_loop_start():
    """
    Above-Core RMT-CAP-04 control: enable the continuous Homelab operational
    loop and start its driving task. Idempotent. The loop only ever calls the
    existing governed entrypoint (remediate_component); it never continues a
    manual approval hold.
    """
    return operational_loop.start()


@app.post("/homelab/loop/stop", dependencies=[Depends(require_operator)])
async def homelab_loop_stop():
    """
    Above-Core RMT-CAP-04 control: disable the continuous Homelab operational
    loop and cancel its driving task. Idempotent.
    """
    return operational_loop.stop()


@app.post("/homelab/loop/clear", dependencies=[Depends(require_operator)])
def homelab_loop_clear(component: str):
    """
    Above-Core RMT-CAP-04 control: manually clear a component's loop
    quarantine so the loop resumes attempting remediation for it. Records the
    transition through the existing Core learning/memory capability.
    """
    return operational_loop.clear_quarantine(component)
