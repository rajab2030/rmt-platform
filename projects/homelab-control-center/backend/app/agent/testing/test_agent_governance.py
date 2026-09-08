"""RMT-CAP-05 (5A) -- governed agent surface (run-safe).

``execute_governed_action`` and the above-Core helpers are mocked, so no
governed pipeline runs and no durable evidence is written. The agent-layer
logic under test is: the disabled gate, authority (capability != authority,
scope, single-use, TTL), T13 dependency-cascade escalation, outcome mapping,
fault containment, and the deterministic reference agent.
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import app.agent.adapter as adapter_mod
import app.agent.dependency_guard as guard_mod
from app.agent import loop_config
from app.agent.authority import authority_store
from app.agent.contract import AgentIdentity, AgentIntent, AgentProposal
from app.agent.adapter import propose_and_govern
from app.core.intelligence.actions.models import ActionType


@pytest.fixture(autouse=True)
def _reset():
    authority_store.reset()
    yield
    authority_store.reset()


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(loop_config, "AGENT_ENABLED", True)


@pytest.fixture
def captured_governed(monkeypatch):
    """Mock execute_governed_action + the above-Core helpers; capture the
    ActionRequest and return a scripted governed result."""
    box = {"action": None, "result": {"status": "executed",
                                      "execution_id": "exec-1", "success": True}}

    def fake_execute(action, adapter_name=None):
        box["action"] = action
        r = box["result"]
        if isinstance(r, BaseException):
            raise r
        return r

    learn_calls = []
    verify_calls = []
    failed_evidence_calls = []

    class _V:
        status = "verified_success"
        reason = "ok"

    class _FailedRec:
        status = "adapter_execution_failed"

    monkeypatch.setattr(adapter_mod, "execute_governed_action", fake_execute)
    monkeypatch.setattr(adapter_mod, "resolve_adapter_name", lambda: "simulation")
    monkeypatch.setattr(
        adapter_mod, "record_learning",
        lambda *a, **k: learn_calls.append((a, k)),
    )
    monkeypatch.setattr(
        adapter_mod, "verify_docker_execution",
        lambda *a, **k: verify_calls.append((a, k)) or _V(),
    )
    monkeypatch.setattr(
        adapter_mod, "record_failed_execution_evidence",
        lambda *a, **k: failed_evidence_calls.append((a, k)) or _FailedRec(),
    )
    box["learn"] = learn_calls
    box["verify"] = verify_calls
    box["failed_evidence"] = failed_evidence_calls
    return box


def _proposal(mechanism=ActionType.RESTART, target="uptime-kuma", grant_id=None):
    return AgentProposal(
        identity=AgentIdentity(agent_id="reference-agent"),
        intent=AgentIntent(
            goal=f"restore {target}", target=target, mechanism=mechanism,
            reason="critical", confidence=80,
        ),
        expected_state="running",
        grant_id=grant_id,
    )


# 1 -----------------------------------------------------------------------

def test_disabled_by_default(captured_governed):
    assert loop_config.AGENT_ENABLED is False
    out = propose_and_govern(_proposal())
    assert out.decision == "disabled"
    assert captured_governed["action"] is None  # boundary never reached


# 2 -----------------------------------------------------------------------

def test_allowed_proposal_executes_verifies_learns(enabled, captured_governed):
    g = authority_store.grant("restart", "uptime-kuma", "operator")
    out = propose_and_govern(_proposal(grant_id=g.grant_id))
    assert out.decision == "allow"
    assert out.execution_id == "exec-1"
    assert out.verification_status == "verified_success"
    assert out.learn_recorded and len(captured_governed["learn"]) == 1
    assert authority_store.get(g.grant_id).consumed is True


def test_failed_execution_records_e3_evidence(enabled, captured_governed):
    """E3: adapter invoked and failed -> a distinguishable evidence record,
    no Docker verify, grant still consumed, still learned."""
    captured_governed["result"] = {
        "status": "executed", "execution_id": "exec-9",
        "success": False, "message": "adapter boom",
    }
    g = authority_store.grant("restart", "uptime-kuma", "operator")
    out = propose_and_govern(_proposal(grant_id=g.grant_id))

    assert out.decision == "allow"
    assert out.execution_id == "exec-9"
    assert out.verification_status == "adapter_execution_failed"
    assert captured_governed["verify"] == []          # no success -> no Docker verify
    assert len(captured_governed["failed_evidence"]) == 1
    assert captured_governed["failed_evidence"][0][1]["source"] == "agent_adapter"
    assert out.learn_recorded
    assert authority_store.get(g.grant_id).consumed is True


# 3 -----------------------------------------------------------------------

def test_held_proposal_recorded_not_continued(enabled, captured_governed):
    captured_governed["result"] = {
        "status": "manual_approval_required", "approval_id": "appr-1",
    }
    g = authority_store.grant("restart", "uptime-kuma", "operator")
    out = propose_and_govern(_proposal(grant_id=g.grant_id))
    assert out.decision == "hold"
    assert out.approval_id == "appr-1"
    assert out.learn_recorded
    # no continuation path is imported by the agent adapter
    assert not hasattr(adapter_mod, "continue_remediation")
    assert authority_store.get(g.grant_id).consumed is True


# 4 -----------------------------------------------------------------------

def test_policy_denied_leaves_grant_intact(enabled, captured_governed):
    captured_governed["result"] = {"status": "policy_denied", "reason": "low conf"}
    g = authority_store.grant("restart", "uptime-kuma", "operator")
    out = propose_and_govern(_proposal(grant_id=g.grant_id))
    assert out.decision == "deny"
    assert out.verification_status is None
    assert captured_governed["verify"] == []
    assert authority_store.get(g.grant_id).consumed is False


# 5 -----------------------------------------------------------------------

def test_no_grant_is_denied_before_boundary(enabled, captured_governed):
    out = propose_and_govern(_proposal(grant_id=None))
    assert out.decision == "no_authority"
    assert out.detail == "no_grant"
    assert captured_governed["action"] is None


# 6 -----------------------------------------------------------------------

def test_grant_is_single_use(enabled, captured_governed):
    g = authority_store.grant("restart", "uptime-kuma", "operator")
    first = propose_and_govern(_proposal(grant_id=g.grant_id))
    assert first.decision == "allow"
    second = propose_and_govern(_proposal(grant_id=g.grant_id))
    assert second.decision == "no_authority"
    assert second.detail == "grant_consumed"


# 7 -----------------------------------------------------------------------

def test_expired_grant_is_denied(enabled, captured_governed):
    g = authority_store.grant("restart", "uptime-kuma", "operator", ttl_seconds=1)
    g.expires_at = datetime.now(timezone.utc)  # force-expire
    out = propose_and_govern(_proposal(grant_id=g.grant_id))
    assert out.decision == "no_authority"
    assert out.detail == "grant_expired"


# 8 -----------------------------------------------------------------------

def test_grant_scope_is_enforced(enabled, captured_governed):
    g = authority_store.grant("restart", "uptime-kuma", "operator")
    out = propose_and_govern(
        _proposal(mechanism=ActionType.STOP, grant_id=g.grant_id)
    )
    assert out.decision == "no_authority"
    assert out.detail == "grant_scope_mismatch"
    assert captured_governed["action"] is None


# 9 -----------------------------------------------------------------------

def test_t13_dependency_cascade_forces_approval(
    enabled, captured_governed, monkeypatch
):
    """Widened envelope (default auto) + a seeded dependency edge: an allowed
    'start' whose target has a dependent must be escalated to approval."""
    monkeypatch.setattr(loop_config, "AGENT_DEFAULT_REQUIRES_APPROVAL", False)
    monkeypatch.setattr(guard_mod, "_dependents_of", lambda t: {"web"})
    captured_governed["result"] = {
        "status": "manual_approval_required", "approval_id": "appr-esc",
    }

    g = authority_store.grant("start", "db", "operator")
    out = propose_and_govern(
        _proposal(mechanism=ActionType.START, target="db", grant_id=g.grant_id)
    )

    assert out.escalated is True
    assert out.decision == "escalated_hold"
    assert captured_governed["action"].requires_approval is True
    assert "T13" in out.detail


# 10 ----------------------------------------------------------------------

def test_t13_noop_when_no_dependencies(enabled, captured_governed, monkeypatch):
    """Same widened envelope, real (empty) dependency graph: an allowed op is
    NOT escalated -- no false positives."""
    monkeypatch.setattr(loop_config, "AGENT_DEFAULT_REQUIRES_APPROVAL", False)
    g = authority_store.grant("start", "uptime-kuma", "operator")
    out = propose_and_govern(
        _proposal(
            mechanism=ActionType.START, target="uptime-kuma", grant_id=g.grant_id
        )
    )
    assert out.escalated is False
    assert captured_governed["action"].requires_approval is False


# 11 ----------------------------------------------------------------------

def test_status_and_authority_endpoints_readonly(monkeypatch):
    import app.main as main_app

    authority_store.reset()
    with TestClient(main_app.app) as client:
        s1 = client.get("/agent/status")
        a1 = client.get("/agent/authority")
        s2 = client.get("/agent/status")

    assert s1.status_code == 200 and a1.status_code == 200
    body = s1.json()
    for k in ("enabled", "default_requires_approval", "dependency_escalation",
              "active_grants", "last_outcome"):
        assert k in body
    assert body["enabled"] is False
    assert s1.json()["active_grants"] == s2.json()["active_grants"] == 0
    assert a1.json()["active_grants"] == []


# 12 ----------------------------------------------------------------------

def test_governed_boundary_exception_is_contained(enabled, captured_governed):
    captured_governed["result"] = RuntimeError("boundary blew up")
    g = authority_store.grant("restart", "uptime-kuma", "operator")
    out = propose_and_govern(_proposal(grant_id=g.grant_id))
    assert out.decision == "error"
    assert "boundary blew up" in out.detail
    assert authority_store.get(g.grant_id).consumed is False


# 13 ----------------------------------------------------------------------

def test_reference_agent_proposes_only_on_critical():
    from types import SimpleNamespace
    from app.agent.reference_agent import propose_from_evaluation
    from app.core.intelligence.schemas import HealthStatus

    crit = SimpleNamespace(
        component="uptime-kuma", status=HealthStatus.CRITICAL,
        message="unavailable", confidence=80,
    )
    healthy = SimpleNamespace(
        component="uptime-kuma", status=HealthStatus.HEALTHY,
        message="ok", confidence=100,
    )
    p = propose_from_evaluation(crit, grant_id="g1")
    assert p is not None
    assert p.intent.mechanism == ActionType.RESTART
    assert p.intent.target == "uptime-kuma"
    assert p.grant_id == "g1"
    assert propose_from_evaluation(healthy) is None
