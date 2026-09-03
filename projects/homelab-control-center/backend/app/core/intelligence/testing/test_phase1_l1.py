"""C04-L1 - read-only learning / governed-evidence integration tests.

Behavioral boundary tests: feed governed evidence, invoke the read-only
analysis path, and prove evidence is returned while no execution/authorization
function is invoked and no governance record changes.
"""
from datetime import datetime, timedelta, timezone

import app.core.intelligence.analysis.governed_history as gh

from app.core.intelligence.durable_store import DurableStore
from app.core.intelligence.execution.audit import ExecutionAuditRecord
from app.core.intelligence.execution.trace import ExecutionTrace
from app.core.intelligence.verification.models import (
    VerificationResult,
    VerificationStatus,
    ExpectedOutcome,
    ObservedState,
)
from app.core.intelligence.actions.approval import ApprovalRecord
from app.core.intelligence.actions.authorization import (
    ExecutionAuthorization,
    AuthorizationStatus,
)

from app.core.intelligence.analysis.governed_history import (
    GovernedOutcomeView,
    get_governed_outcomes,
)
from app.core.intelligence.analysis.history import analyze_governed_outcomes


def _t(seconds=0):
    return datetime.now(timezone.utc) - timedelta(seconds=seconds)


def _store(model, records):
    s = DurableStore(file_path=None, model=model)
    for r in records:
        s.save(r)
    return s


def _install_evidence(monkeypatch, **kwargs):
    monkeypatch.setattr(gh, "execution_history", kwargs.get("audits", _store(ExecutionAuditRecord, [])))
    monkeypatch.setattr(gh, "execution_trace_history", kwargs.get("traces", _store(ExecutionTrace, [])))
    monkeypatch.setattr(gh, "verification_storage", kwargs.get("verifications", _store(VerificationResult, [])))
    monkeypatch.setattr(gh, "approval_record_storage", kwargs.get("approvals", _store(ApprovalRecord, [])))
    monkeypatch.setattr(gh, "execution_authorization_storage", kwargs.get("authzs", _store(ExecutionAuthorization, [])))


# ---------------------------------------------------------------- 1. visibility
def test_governed_evidence_visible_through_read_only_boundary(monkeypatch):
    _install_evidence(
        monkeypatch,
        audits=_store(ExecutionAuditRecord, [
            ExecutionAuditRecord(execution_id="e1", action_id="a1",
                                 authorization_id="z1", adapter="simulation",
                                 status="completed", message="ok",
                                 risk_level="low", created_at=_t(30)),
        ]),
        authzs=_store(ExecutionAuthorization, [
            ExecutionAuthorization(action_id="a1", status=AuthorizationStatus.APPROVED,
                                   target="svc", operation="restart",
                                   decision_id="decision-svc", approval_id="ap1",
                                   created_at=_t(50)),
        ]),
    )
    views = get_governed_outcomes()
    assert len(views) == 1
    v = views[0]
    assert isinstance(v, GovernedOutcomeView)
    assert v.action_id == "a1"
    assert v.component == "svc"
    assert v.operation == "restart"
    assert v.execution_status == "completed"
    assert "audit" in v.sources and "authorization" in v.sources


# ------------------------------------------------------- 2. correlation by execution_id
def test_audit_trace_verification_correlate_by_execution_id(monkeypatch):
    _install_evidence(
        monkeypatch,
        audits=_store(ExecutionAuditRecord, [
            ExecutionAuditRecord(execution_id="e9", action_id="a9",
                                 authorization_id="z9", adapter="simulation",
                                 status="completed", message="ok",
                                 risk_level="medium", created_at=_t(10)),
        ]),
        traces=_store(ExecutionTrace, [
            ExecutionTrace(execution_id="e9", action_id="a9", authorization_id="z9",
                           policy_decision="allowed", risk_level="medium",
                           outcome="completed", reason="ok", created_at=_t(10)),
        ]),
        verifications=_store(VerificationResult, [
            VerificationResult(execution_id="e9",
                               status=VerificationStatus.STATE_MISMATCH,
                               created_at=_t(5)),
        ]),
    )
    views = get_governed_outcomes()
    assert len(views) == 1
    v = views[0]
    assert v.execution_id == "e9"
    assert v.verification_status == VerificationStatus.STATE_MISMATCH
    assert v.policy_decision == "allowed"
    assert {"audit", "trace", "verification"} <= set(v.sources)


# ---------------------------------------------------------------- 3. correlation by action_id
def test_action_lifecycle_correlates_by_action_id(monkeypatch):
    approval = ApprovalRecord(action_id="a3", decision="approved",
                              approved_by="approval_policy", created_at=_t(20))
    audit = ExecutionAuditRecord(execution_id="e3", action_id="a3",
                                 authorization_id="z3", adapter="simulation",
                                 status="completed", message="ok",
                                 risk_level="low", created_at=_t(9))
    authz = ExecutionAuthorization(action_id="a3", status=AuthorizationStatus.APPROVED,
                                   target="svc", operation="restart",
                                   decision_id="decision-svc", approval_id="ap3",
                                   created_at=_t(15))
    _install_evidence(
        monkeypatch,
        approvals=_store(ApprovalRecord, [approval]),
        audits=_store(ExecutionAuditRecord, [audit]),
        authzs=_store(ExecutionAuthorization, [authz]),
    )
    views = get_governed_outcomes()
    assert len(views) == 1
    v = views[0]
    assert v.approval_decision == "approved"
    assert v.decision_provenance == "decision-svc"
    assert set(v.sources) == {"approval", "audit", "authorization"}


# -------------------------------------------------- 4. approval/authz provenance distinguishable
def test_approval_authorization_provenance_distinguishable(monkeypatch):
    approval = ApprovalRecord(action_id="a4", decision="rejected",
                              approved_by="approval_policy", created_at=_t(5))
    _install_evidence(monkeypatch, approvals=_store(ApprovalRecord, [approval]))
    views = get_governed_outcomes()
    assert len(views) == 1
    v = views[0]
    assert v.approval_decision == "rejected"
    assert v.authorization_status == ""  # provenance-only; no authz minted


# ------------------------------------------- 5. blocked represented without audit
def test_blocked_denied_represented_without_audit_record(monkeypatch):
    trace = ExecutionTrace(execution_id="e7", action_id="a7", authorization_id="z7",
                           policy_decision="deny", risk_level="high",
                           outcome="blocked", reason="policy denied", created_at=_t(8))
    _install_evidence(monkeypatch, traces=_store(ExecutionTrace, [trace]))
    views = get_governed_outcomes()
    assert len(views) == 1
    v = views[0]
    assert v.outcome == "blocked"
    assert v.execution_status == "blocked"
    assert "audit" not in v.sources
    assert "trace" in v.sources
    assert v.verification_status == ""


# ------------------------------------ 6. all four verification statuses distinguishable
def test_all_four_verification_statuses_distinguishable(monkeypatch):
    statuses = [
        VerificationStatus.VERIFIED_SUCCESS,
        VerificationStatus.STATE_MISMATCH,
        VerificationStatus.OBSERVATION_UNAVAILABLE,
        VerificationStatus.VERIFICATION_FAILURE,
    ]
    audits = []
    verifs = []
    for i, st in enumerate(statuses):
        eid = f"e-{i}"
        audits.append(ExecutionAuditRecord(execution_id=eid, action_id=f"a-{i}",
                                           authorization_id="z", adapter="simulation",
                                           status="completed", message="ok",
                                           risk_level="low", created_at=_t(i + 1)))
        verifs.append(VerificationResult(execution_id=eid, status=st, created_at=_t(i)))
    _install_evidence(monkeypatch, audits=_store(ExecutionAuditRecord, audits),
                      verifications=_store(VerificationResult, verifs))
    views = get_governed_outcomes()
    got = sorted(v.verification_status for v in views)
    assert got == sorted(statuses)


# ----------------------------------- 7. observation/eval vs governed history distinguishable
def test_governed_history_distinct_from_observation_history(monkeypatch):
    # governed evidence present
    _install_evidence(
        monkeypatch,
        audits=_store(ExecutionAuditRecord, [
            ExecutionAuditRecord(execution_id="e1", action_id="a1",
                                 authorization_id="z1", adapter="simulation",
                                 status="completed", message="ok",
                                 risk_level="low", created_at=_t(10)),
        ]),
    )
    summary = analyze_governed_outcomes()
    assert summary["total_governed_outcomes"] == 1
    assert summary["completed"] == 1
    # every view carries an explicit source classification
    for o in summary["outcomes"]:
        assert o["sources"]
    # distinct function name/semantics preserved: analyze_component_history
    # still operates on observation/evaluation memory only.
    import app.core.intelligence.analysis.history as hist
    assert hasattr(hist, "analyze_component_history")
    assert hasattr(hist, "analyze_governed_outcomes")


# ------------------------------------------- 8. historical authz cannot become current
def test_historical_authorization_cannot_become_current(monkeypatch):
    authz = ExecutionAuthorization(action_id="a8", status=AuthorizationStatus.APPROVED,
                                   target="svc", operation="restart",
                                   decision_id="decision-svc", approval_id="ap8",
                                   created_at=_t(100))
    _install_evidence(monkeypatch, authzs=_store(ExecutionAuthorization, [authz]))
    views = get_governed_outcomes()
    # authorization surfaced as provenance only, not as an active new grant
    assert views[0].authorization_status == AuthorizationStatus.APPROVED
    # learning produced NO new authorization: store is unchanged (still 1)
    assert len(gh.execution_authorization_storage.get_all()) == 1
    assert all(not isinstance(v, ExecutionAuthorization)
               for v in get_governed_outcomes())


# --------------------------------------------- 9. learning cannot invoke execution
def test_learning_cannot_invoke_execution(monkeypatch):
    from app.core.intelligence.execution.engine import execution_engine
    from app.core.intelligence.actions.service import execute_governed_action

    def boom(*a, **k):
        raise AssertionError("execution/action path must never be reached by Learning")
    monkeypatch.setattr(execution_engine, "execute", boom)
    monkeypatch.setattr("app.core.intelligence.actions.service.execute_governed_action", boom)

    _install_evidence(
        monkeypatch,
        audits=_store(ExecutionAuditRecord, [
            ExecutionAuditRecord(execution_id="e1", action_id="a1",
                                 authorization_id="z1", adapter="simulation",
                                 status="completed", message="ok",
                                 risk_level="low", created_at=_t(1)),
        ]),
    )
    views = get_governed_outcomes()
    assert len(views) == 1
    summary = analyze_governed_outcomes()
    assert summary["total_governed_outcomes"] == 1


# --------------------------------------------- 10. learning cannot mint authorization
def test_learning_cannot_mint_authorization(monkeypatch):
    _install_evidence(
        monkeypatch,
        authzs=_store(ExecutionAuthorization, [
            ExecutionAuthorization(action_id="a1", status=AuthorizationStatus.APPROVED,
                                   target="svc", operation="restart", created_at=_t(2)),
        ]),
    )
    get_governed_outcomes()
    # aggregation issues no authorization: store unchanged, output holds views only
    assert len(gh.execution_authorization_storage.get_all()) == 1
    for v in get_governed_outcomes():
        assert not isinstance(v, ExecutionAuthorization)


# --------------------------------------------- 11. learning cannot mutate governance state
def test_learning_cannot_mutate_governance_state(monkeypatch):
    _install_evidence(
        monkeypatch,
        audits=_store(ExecutionAuditRecord, [
            ExecutionAuditRecord(execution_id="e1", action_id="a1",
                                 authorization_id="z1", adapter="simulation",
                                 status="completed", message="ok",
                                 risk_level="low", created_at=_t(1)),
        ]),
    )
    get_governed_outcomes()
    # After aggregation, no governance store received a write: each is still
    # its own test store with exactly the seeded records.
    assert len(gh.execution_history.get_all()) == 1
    assert len(gh.execution_trace_history.get_all()) == 0
    assert len(gh.verification_storage.get_all()) == 0
    assert len(gh.approval_record_storage.get_all()) == 0
    assert len(gh.execution_authorization_storage.get_all()) == 0


# --------------------------------------------- 12. no path reaches an adapter
def test_learning_path_never_reaches_adapter(monkeypatch):
    from app.core.intelligence.execution.adapters.registry import adapter_registry

    def boom(*a, **k):
        raise AssertionError("adapter must not be invoked by Learning")
    monkeypatch.setattr(adapter_registry, "get", boom)

    _install_evidence(monkeypatch, audits=_store(ExecutionAuditRecord, []))
    # both paths must complete without any adapter request
    get_governed_outcomes()
    analyze_governed_outcomes()


# --------------------------------------------- 13. existing memory/history intact
def test_existing_observation_history_behavior_intact():
    from app.core.intelligence.memory.query import get_health_history, get_recent_events
    from app.core.intelligence.analysis.history import analyze_component_history
    from app.core.intelligence.memory.factory import health_evaluation_to_memory
    from app.core.intelligence.memory import remember
    from app.core.intelligence.schemas import HealthEvaluation, HealthStatus, HealthReason, HealthImpact

    ev = HealthEvaluation(component="svc", status=HealthStatus.CRITICAL,
                          reason=HealthReason.COLLECTOR_FAILURE, evidence=["down"],
                          confidence=95, impact=HealthImpact.MEDIUM, message="down")
    remember(health_evaluation_to_memory(ev))
    assert get_health_history("svc")
    h = analyze_component_history("svc")
    assert "events" in h
    assert get_recent_events("svc")


# --------------------------------------------- 15. no second mutation boundary
def test_no_second_mutation_boundary(monkeypatch):
    # Learning exposes only read/analysis callables; nothing returns an ActionRequest.
    from app.core.intelligence.actions.models import ActionRequest
    _install_evidence(monkeypatch, audits=_store(ExecutionAuditRecord, []))
    out = analyze_governed_outcomes()
    assert all(not isinstance(item, ActionRequest) for item in out["outcomes"])


def test_verification_cross_episode_negative_isolation(monkeypatch):
    """Negative correlation isolation: verification for one episode must not
    leak into another, and an orphan (execution_id in neither episode) must
    attach to no view."""
    # Episode A
    audA = ExecutionAuditRecord(execution_id="eA", action_id="aA",
                                authorization_id="zA", adapter="simulation",
                                status="completed", message="ok", risk_level="low",
                                created_at=_t(20))
    trA = ExecutionTrace(execution_id="eA", action_id="aA", authorization_id="zA",
                         policy_decision="allowed", risk_level="low", outcome="completed",
                         reason="ok", created_at=_t(20))
    verA = VerificationResult(execution_id="eA",
                              status=VerificationStatus.STATE_MISMATCH, created_at=_t(10))

    # Episode B
    audB = ExecutionAuditRecord(execution_id="eB", action_id="aB",
                                authorization_id="zB", adapter="simulation",
                                status="completed", message="ok", risk_level="low",
                                created_at=_t(20))
    trB = ExecutionTrace(execution_id="eB", action_id="aB", authorization_id="zB",
                         policy_decision="allowed", risk_level="low", outcome="completed",
                         reason="ok", created_at=_t(20))
    verB = VerificationResult(execution_id="eB",
                              status=VerificationStatus.VERIFIED_SUCCESS, created_at=_t(10))

    # Orphan/decoy: execution_id belongs to neither episode.
    orphan = VerificationResult(execution_id="e-orphan",
                                status=VerificationStatus.VERIFICATION_FAILURE,
                                created_at=_t(5))

    _install_evidence(
        monkeypatch,
        audits=_store(ExecutionAuditRecord, [audA, audB]),
        traces=_store(ExecutionTrace, [trA, trB]),
        verifications=_store(VerificationResult, [verA, verB, orphan]),
        approvals=_store(ApprovalRecord, []),
        authzs=_store(ExecutionAuthorization, []),
    )

    views = {v.action_id: v for v in get_governed_outcomes()}
    assert set(views) == {"aA", "aB"}

    vA = views["aA"]
    vB = views["aB"]

    # A receives only verification A (STATE_MISMATCH).
    assert vA.verification_status == VerificationStatus.STATE_MISMATCH
    # B receives only verification B (VERIFIED_SUCCESS).
    assert vB.verification_status == VerificationStatus.VERIFIED_SUCCESS
    # The orphan verification attaches to neither view.
    assert vA.verification_status != VerificationStatus.VERIFICATION_FAILURE
    assert vB.verification_status != VerificationStatus.VERIFICATION_FAILURE
    # Cross influence is absent both ways.
    assert vA.verification_status != vB.verification_status
    assert vA.execution_id == "eA"
    assert vB.execution_id == "eB"
