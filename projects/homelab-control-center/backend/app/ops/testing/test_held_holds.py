"""RMT T1-4 -- read-only open-holds view + the GET /ops/holds route.

``open_holds_view()`` classifies every PENDING approval hold for the external
escalation script. Unit tests drive it against isolated in-memory stores; two
route tests cover auth + shape.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import app.core.intelligence.actions.approval_service as approval_service_module
from app.core.intelligence.actions.approval import ApprovalHold, ApprovalStatus
from app.core.intelligence.actions.approval_storage import (
    ApprovalHoldStorage,
    ApprovalRecordStorage,
)
from app.core.intelligence.actions.models import ActionRequest, ActionType
from app.core.intelligence.verification.models import ExpectedOutcome

from app.ops import separation
from app.ops.held_holds import open_holds_view


def _hold(approval_age_s=10, ttl_s=300, component="uptime-kuma"):
    now = datetime.now(timezone.utc)
    action = ActionRequest(
        decision_id="d-1",
        component=component,
        action_type=ActionType.RESTART,
        reason="x",
        confidence=80,
        requires_approval=True,
        expected_outcome=ExpectedOutcome(
            target=component, operation="restart", expected_state="running"
        ),
    )
    created = now - timedelta(seconds=approval_age_s)
    h = ApprovalHold(
        action_id=action.action_id,
        action=action,
        adapter_name="simulation",
        reason="held",
        status=ApprovalStatus.PENDING,
        expires_at=created + timedelta(seconds=ttl_s),
        risk_level="medium",
    )
    h.created_at = created
    return h


@pytest.fixture
def stores(monkeypatch):
    holds = ApprovalHoldStorage()
    records = ApprovalRecordStorage()
    monkeypatch.setattr(approval_service_module, "approval_hold_storage", holds)
    monkeypatch.setattr(
        approval_service_module, "approval_record_storage", records
    )
    separation.reset()
    yield holds, records
    separation.reset()


# --- classification ----------------------------------------------------

def test_actionable_pending_hold(stores):
    holds, _ = stores
    holds.save(_hold(approval_age_s=200, ttl_s=300))

    view = open_holds_view()
    assert len(view) == 1
    h = view[0]
    assert h["actionable"] is True
    assert h["expired"] is False
    assert h["record_terminal"] is False
    assert 190 <= h["age_seconds"] <= 210
    assert h["component"] == "uptime-kuma"
    assert h["action_type"] == "restart"
    assert h["kind"] == "held_action"


def test_expired_unapproved_hold(stores):
    holds, _ = stores
    holds.save(_hold(approval_age_s=400, ttl_s=300))

    h = open_holds_view()[0]
    assert h["expired"] is True
    assert h["actionable"] is False
    assert h["record_terminal"] is False


def test_hold_with_terminal_record_is_not_actionable(stores):
    from app.core.intelligence.actions.approval import ApprovalRecord

    holds, records = stores
    hold = _hold(approval_age_s=100, ttl_s=300)
    holds.save(hold)
    records.save(
        ApprovalRecord(
            approval_id=hold.approval_id,
            action_id=hold.action_id,
            decision="approved",
            approved_by="alice",
        )
    )

    h = open_holds_view()[0]
    assert h["record_decision"] == "approved"
    assert h["record_terminal"] is True
    assert h["actionable"] is False


def test_non_pending_holds_are_skipped(stores):
    holds, _ = stores
    h = _hold()
    h.status = ApprovalStatus.APPROVED
    holds.save(h)
    assert open_holds_view() == []


def test_s3_provenance_surfaces(stores):
    holds, _ = stores
    hold = _hold(approval_age_s=50)
    holds.save(hold)
    separation.record_hold_provenance(
        hold.approval_id, grant_id="g1", granted_by="alice", agent_id="llm-agent"
    )

    h = open_holds_view()[0]
    assert h["kind"] == "agent_proposal"
    assert h["granted_by"] == "alice"
    assert h["agent_id"] == "llm-agent"


def test_fail_open_on_store_error(monkeypatch):
    class Boom:
        def get_all(self):
            raise RuntimeError("store down")

    monkeypatch.setattr(
        approval_service_module, "approval_hold_storage", Boom()
    )
    assert open_holds_view() == []


# --- the route -------------------------------------------------------

def test_ops_holds_route_open_when_auth_off():
    # conftest defaults RMT_AUTH_ENABLED=false for this suite.
    import app.main as main_app

    with TestClient(main_app.app) as c:
        r = c.get("/ops/holds")
    assert r.status_code == 200
    assert isinstance(r.json()["holds"], list)


def test_ops_holds_route_requires_token_when_auth_on(monkeypatch):
    monkeypatch.setenv("RMT_AUTH_ENABLED", "true")
    monkeypatch.setenv("RMT_OPERATOR_TOKENS", "alice:sekret")
    import app.main as main_app

    with TestClient(main_app.app) as c:
        assert c.get("/ops/holds").status_code == 401
        ok = c.get("/ops/holds", headers={"Authorization": "Bearer sekret"})
    assert ok.status_code == 200
    assert isinstance(ok.json()["holds"], list)
