"""RMT-CAP-04 -- continuous Homelab operational loop (run-safe).

All externals are mocked: ``remediate_component`` (the governed entrypoint),
``observe_container_state`` (recovery signal), ``remember`` (Learn store), and
the approval hold store (isolated to an empty in-memory instance). No real
container is mutated, no governed pipeline runs, no durable evidence file is
touched. Cycles are driven synchronously via ``run_cycle_once`` -- the asyncio
task is never started.
"""
import pytest
from fastapi.testclient import TestClient

from datetime import datetime, timedelta, timezone

import app.core.intelligence.actions.approval_service as approval_service
from app.core.intelligence.actions.approval import (
    ApprovalHold,
    ApprovalRecord,
    ApprovalStatus,
)
from app.core.intelligence.actions.approval_storage import (
    ApprovalHoldStorage,
    ApprovalRecordStorage,
)
from app.core.intelligence.actions.models import ActionRequest, ActionType

import app.homelab.operational_loop as loop_mod
from app.homelab.operational_loop import HomelabOperationalLoop


@pytest.fixture(autouse=True)
def isolate_hold_store(monkeypatch):
    """CAP-04's duplicate-hold guard reads the approval hold + record stores.
    Isolate both to empty in-memory instances so tests never see real data; the
    tests that exercise the guard add rows to the returned hold store (and to
    ``approval_service.approval_record_storage`` for resolution checks)."""
    holds = ApprovalHoldStorage()
    records = ApprovalRecordStorage()
    monkeypatch.setattr(approval_service, "approval_hold_storage", holds)
    monkeypatch.setattr(approval_service, "approval_record_storage", records)
    return holds


def _pending_hold(
    component="uptime-kuma", approval_id="hold-1", expires_at=None
):
    return ApprovalHold(
        approval_id=approval_id,
        action_id="act-1",
        action=ActionRequest(
            decision_id="d-1",
            component=component,
            action_type=ActionType.RESTART,
            reason="test hold",
            confidence=80,
        ),
        adapter_name="simulation",
        status=ApprovalStatus.PENDING,
        expires_at=(
            expires_at
            if expires_at is not None
            else datetime.now(timezone.utc) + timedelta(seconds=300)
        ),
    )


@pytest.fixture
def loop():
    return HomelabOperationalLoop()


@pytest.fixture
def learn(monkeypatch):
    records = []
    monkeypatch.setattr(loop_mod, "remember", lambda r: records.append(r) or r)
    return records


@pytest.fixture
def single_component(monkeypatch):
    """Constrain the policy view the loop iterates to one component."""
    monkeypatch.setattr(loop_mod, "REMEDIATION_POLICY", {"uptime-kuma": {}})
    return "uptime-kuma"


def _mock_remediate(monkeypatch, mapping):
    """mapping: component -> outcome dict OR callable(component)->dict OR Exception."""
    calls = []

    def fake(component):
        calls.append(component)
        spec = mapping[component]
        if isinstance(spec, BaseException):
            raise spec
        if callable(spec):
            return spec(component)
        return spec

    monkeypatch.setattr(loop_mod, "remediate_component", fake)
    return calls


# ---------------------------------------------------------------------------
# 1. Disabled by default
# ---------------------------------------------------------------------------

def test_loop_disabled_by_default(loop):
    import app.homelab.loop_config as lc

    assert lc.LOOP_ENABLED is False
    status = loop.get_status()
    assert status["enabled"] is False
    assert status["running"] is False
    assert status["cycle_count"] == 0


# ---------------------------------------------------------------------------
# 2. Healthy cycle -> no state change
# ---------------------------------------------------------------------------

def test_healthy_cycle_no_state_change(loop, learn, single_component, monkeypatch):
    calls = _mock_remediate(
        monkeypatch,
        {"uptime-kuma": {"status": "no_remediation", "component": "uptime-kuma"}},
    )

    loop.run_cycle_once()

    assert calls == ["uptime-kuma"]
    state = loop.get_status()["components"]["uptime-kuma"]
    assert state["quarantined"] is False
    assert state["cooldown_until"] is None
    assert state["attempts_in_window"] == 0
    assert state["healthy_streak"] == 1
    assert learn == []  # no transition recorded


# ---------------------------------------------------------------------------
# 3. Held outcome: recorded, NOT continued, cooldown set
# ---------------------------------------------------------------------------

def test_held_outcome_recorded_not_continued(loop, learn, single_component, monkeypatch):
    calls = _mock_remediate(
        monkeypatch,
        {
            "uptime-kuma": {
                "status": "manual_approval_required",
                "approval_id": "appr-1",
                "component": "uptime-kuma",
            }
        },
    )

    loop.run_cycle_once()

    assert calls == ["uptime-kuma"]
    # The loop must not import or use the approval-continuation path.
    assert not hasattr(loop_mod, "continue_remediation")

    state = loop.get_status()["components"]["uptime-kuma"]
    assert state["last_outcome"] == "manual_approval_required"
    assert state["cooldown_until"] is not None
    assert state["attempts_in_window"] == 1
    assert state["quarantined"] is False

    hist = loop.get_status()["history"][-1]
    assert hist["results"][0]["detail"] == "appr-1"


# ---------------------------------------------------------------------------
# 4. Repeated held attempts -> quarantine; then no more remediation attempts
# ---------------------------------------------------------------------------

def test_repeated_held_triggers_quarantine(loop, learn, single_component, monkeypatch):
    monkeypatch.setattr(loop_mod.loop_config, "LOOP_COOLDOWN_SECONDS", 0)
    monkeypatch.setattr(loop_mod.loop_config, "LOOP_MAX_ATTEMPTS_PER_WINDOW", 3)
    ops_alerts = []
    monkeypatch.setattr(loop_mod, "notify_ops", lambda **k: ops_alerts.append(k))
    calls = _mock_remediate(
        monkeypatch,
        {
            "uptime-kuma": {
                "status": "manual_approval_required",
                "approval_id": "appr-x",
            }
        },
    )

    for _ in range(3):
        loop.run_cycle_once()

    state = loop.get_status()["components"]["uptime-kuma"]
    assert state["quarantined"] is True
    assert any(r.event_type == "homelab_loop_quarantine" for r in learn)
    assert len(calls) == 3
    # O3: a quarantine raised exactly one ops alert, keyed on the component
    assert [a["kind"] for a in ops_alerts] == ["loop_quarantine"]
    assert ops_alerts[0]["key"] == "uptime-kuma"

    # 4th cycle: quarantined -> observe only, no remediation attempt.
    monkeypatch.setattr(
        loop_mod, "observe_container_state", lambda c: type("O", (), {"state": "stopped"})()
    )
    loop.run_cycle_once()
    assert len(calls) == 3  # unchanged


# ---------------------------------------------------------------------------
# 5. Cooldown skips the component
# ---------------------------------------------------------------------------

def test_cooldown_skips_component(loop, learn, single_component, monkeypatch):
    calls = _mock_remediate(
        monkeypatch,
        {"uptime-kuma": {"status": "manual_approval_required", "approval_id": "a"}},
    )

    loop.run_cycle_once()
    loop.run_cycle_once()

    assert len(calls) == 1
    hist = loop.get_status()["history"][-1]
    assert hist["results"][0]["outcome"] == "skipped_cooldown"


# ---------------------------------------------------------------------------
# 6. A per-component exception is contained; other components still processed
# ---------------------------------------------------------------------------

def test_cycle_exception_is_contained(loop, learn, monkeypatch):
    monkeypatch.setattr(loop_mod, "REMEDIATION_POLICY", {"a": {}, "b": {}})
    calls = _mock_remediate(
        monkeypatch,
        {
            "a": RuntimeError("boom"),
            "b": {"status": "no_remediation"},
        },
    )

    result = loop.run_cycle_once()  # must not raise

    assert set(calls) == {"a", "b"}
    assert result["status"] == "ok"
    state_a = loop.get_status()["components"]["a"]
    assert state_a["last_outcome"] == "error"
    assert state_a["consecutive_failures"] == 1
    state_b = loop.get_status()["components"]["b"]
    assert state_b["last_outcome"] == "no_remediation"


def test_loop_cycle_error_triggers_ops_alert(loop, monkeypatch):
    """O3: if run_cycle_once itself raises, run()'s guard records it AND fires
    a de-duped loop_cycle_error ops alert."""
    import asyncio

    alerts = []
    monkeypatch.setattr(loop_mod, "notify_ops", lambda **k: alerts.append(k))

    def boom():
        raise RuntimeError("cycle boom")

    monkeypatch.setattr(loop, "run_cycle_once", boom)

    async def _stop(_seconds):
        raise asyncio.CancelledError

    monkeypatch.setattr(loop_mod.asyncio, "sleep", _stop)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(loop.run())

    assert loop._last_cycle_error == "RuntimeError('cycle boom')"
    assert [a["kind"] for a in alerts] == ["loop_cycle_error"]
    assert alerts[0]["source"] == "cap04_loop"


# ---------------------------------------------------------------------------
# 7. Quarantine auto-clears after a healthy streak
# ---------------------------------------------------------------------------

def test_quarantine_auto_clears_on_healthy_streak(loop, learn, single_component, monkeypatch):
    monkeypatch.setattr(loop_mod.loop_config, "LOOP_RECOVERY_HEALTHY_STREAK", 2)
    calls = _mock_remediate(monkeypatch, {"uptime-kuma": {"status": "no_remediation"}})
    monkeypatch.setattr(
        loop_mod, "observe_container_state", lambda c: type("O", (), {"state": "running"})()
    )

    state = loop._get_state("uptime-kuma")
    state.quarantined = True
    state.quarantined_at = loop_mod._now()
    state.quarantine_reason = "test"

    loop.run_cycle_once()
    assert loop.get_status()["components"]["uptime-kuma"]["quarantined"] is True

    loop.run_cycle_once()
    assert loop.get_status()["components"]["uptime-kuma"]["quarantined"] is False
    assert any(r.event_type == "homelab_loop_recovery" for r in learn)
    assert calls == []  # remediate_component never called while quarantined


# ---------------------------------------------------------------------------
# 8. Status endpoint is read-only
# ---------------------------------------------------------------------------

def test_status_endpoint_readonly():
    from app.homelab.operational_loop import operational_loop

    operational_loop.reset()
    import app.main as main_app

    with TestClient(main_app.app) as client:
        r1 = client.get("/homelab/loop/status")
        r2 = client.get("/homelab/loop/status")

    assert r1.status_code == 200
    body = r1.json()
    for key in ("enabled", "running", "cycle_count", "components", "history"):
        assert key in body
    assert body["enabled"] is False
    assert r1.json()["cycle_count"] == r2.json()["cycle_count"] == 0


# ---------------------------------------------------------------------------
# 9. Single-flight guard
# ---------------------------------------------------------------------------

def test_single_flight_guard(loop, single_component, monkeypatch):
    calls = _mock_remediate(monkeypatch, {"uptime-kuma": {"status": "no_remediation"}})

    loop._cycle_in_progress = True
    result = loop.run_cycle_once()

    assert result == {"status": "cycle_already_in_progress"}
    assert calls == []


# ---------------------------------------------------------------------------
# 10. An executed outcome resets flap state and sets a cooldown
# ---------------------------------------------------------------------------

def test_executed_outcome_resets_flap_state(loop, learn, single_component, monkeypatch):
    monkeypatch.setattr(loop_mod.loop_config, "LOOP_COOLDOWN_SECONDS", 0)
    seq = [
        {"status": "manual_approval_required", "approval_id": "a1"},
        {"status": "manual_approval_required", "approval_id": "a2"},
        {"status": "executed", "execution_id": "e1"},
    ]
    monkeypatch.setattr(
        loop_mod, "remediate_component", lambda c: seq.pop(0)
    )

    for _ in range(3):
        loop.run_cycle_once()

    state = loop.get_status()["components"]["uptime-kuma"]
    assert state["last_outcome"] == "executed"
    assert state["attempts_in_window"] == 0
    assert state["consecutive_failures"] == 0
    assert state["quarantined"] is False


# ---------------------------------------------------------------------------
# 11. Manual quarantine clear endpoint
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 12-14. Duplicate-hold guard (store query)
# ---------------------------------------------------------------------------

def test_pending_hold_suppresses_new_remediation(
    loop, isolate_hold_store, single_component, monkeypatch
):
    isolate_hold_store.save(_pending_hold("uptime-kuma", "appr-pending"))
    calls = _mock_remediate(
        monkeypatch, {"uptime-kuma": {"status": "manual_approval_required"}}
    )

    loop.run_cycle_once()

    assert calls == []  # no second remediation routed
    state = loop.get_status()["components"]["uptime-kuma"]
    assert state["last_outcome"] == "awaiting_approval"
    assert state["attempts_in_window"] == 0
    assert state["cooldown_until"] is None
    assert state["quarantined"] is False
    hist = loop.get_status()["history"][-1]["results"][0]
    assert hist["outcome"] == "awaiting_approval"
    assert "appr-pending" in hist["detail"]


def test_awaiting_approval_never_quarantines(
    loop, isolate_hold_store, single_component, monkeypatch
):
    monkeypatch.setattr(loop_mod.loop_config, "LOOP_COOLDOWN_SECONDS", 0)
    monkeypatch.setattr(loop_mod.loop_config, "LOOP_MAX_ATTEMPTS_PER_WINDOW", 3)
    isolate_hold_store.save(_pending_hold("uptime-kuma", "appr-pending"))
    calls = _mock_remediate(
        monkeypatch, {"uptime-kuma": {"status": "manual_approval_required"}}
    )

    for _ in range(6):
        loop.run_cycle_once()

    assert calls == []
    state = loop.get_status()["components"]["uptime-kuma"]
    assert state["quarantined"] is False
    assert state["attempts_in_window"] == 0


def test_cycling_resumes_after_hold_resolved(
    loop, isolate_hold_store, single_component, monkeypatch
):
    hold = _pending_hold("uptime-kuma", "appr-pending")
    isolate_hold_store.save(hold)
    calls = _mock_remediate(
        monkeypatch, {"uptime-kuma": {"status": "no_remediation"}}
    )

    loop.run_cycle_once()
    assert calls == []
    assert loop.get_status()["components"]["uptime-kuma"]["last_outcome"] == (
        "awaiting_approval"
    )

    hold.status = ApprovalStatus.APPROVED  # hold resolved

    loop.run_cycle_once()
    assert calls == ["uptime-kuma"]
    assert loop.get_status()["components"]["uptime-kuma"]["last_outcome"] == (
        "no_remediation"
    )


def test_resolved_hold_still_pending_on_disk_does_not_block(
    loop, isolate_hold_store, single_component, monkeypatch
):
    """Core `approve_held_action` flips hold.status in memory but does not
    always persist the hold store -- a resolved hold can still read PENDING on
    disk after a restart. The guard must consult the approval RECORD store and
    ignore such a hold."""
    isolate_hold_store.save(_pending_hold("uptime-kuma", "appr-stale"))
    approval_service.approval_record_storage.save(
        ApprovalRecord(
            approval_id="appr-stale",
            action_id="act-1",
            decision="approved",
            approved_by="operator",
        )
    )
    calls = _mock_remediate(
        monkeypatch, {"uptime-kuma": {"status": "no_remediation"}}
    )

    loop.run_cycle_once()

    assert calls == ["uptime-kuma"]  # not blocked
    assert loop.get_status()["components"]["uptime-kuma"]["last_outcome"] == (
        "no_remediation"
    )


def test_expired_hold_does_not_block(
    loop, isolate_hold_store, single_component, monkeypatch
):
    """A PENDING hold past its resolution TTL cannot be continued by the Core,
    so it must not block a new remediation either."""
    stale = _pending_hold(
        "uptime-kuma",
        "appr-expired",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=60),
    )
    isolate_hold_store.save(stale)
    calls = _mock_remediate(
        monkeypatch, {"uptime-kuma": {"status": "no_remediation"}}
    )

    loop.run_cycle_once()

    assert calls == ["uptime-kuma"]  # not blocked


def test_loop_processes_second_live_policy_component(loop, learn, monkeypatch):
    """T1-1: the loop's cycle iterates the REAL REMEDIATION_POLICY (not a
    single-component test fixture) and drives both `uptime-kuma` and
    `portainer` -- holds one, remediates the other -- in the same cycle."""
    calls = _mock_remediate(
        monkeypatch,
        {
            "uptime-kuma": {
                "status": "manual_approval_required",
                "component": "uptime-kuma",
                "approval_id": "hold-uk",
            },
            "portainer": {
                "status": "no_remediation",
                "component": "portainer",
            },
        },
    )

    loop.run_cycle_once()

    assert set(calls) == {"uptime-kuma", "portainer"}
    components = loop.get_status()["components"]
    assert components["uptime-kuma"]["last_outcome"] == "manual_approval_required"
    assert components["portainer"]["last_outcome"] == "no_remediation"


def test_remediation_policy_within_cap04_safe_envelope():
    """T13 disposition (docs/RMT_T13_DISPOSITION.md §3b): the CAP-04 loop may be
    enabled only while every remediation-policy entry is (1) independent -- no
    declared dependency on another governed component -- and (2) approval-gated
    for any state-changing action. Inside this envelope the MCR-EXP-3 T13
    pattern (a restricted effect reached via an allowed dependency operation) is
    unreachable. This guard fails loudly if a future edit breaks the envelope
    before the dependency-cascade escalation fix (assigned to CAP-05) lands.
    """
    from app.homelab.remediation import REMEDIATION_POLICY as LIVE_POLICY

    assert LIVE_POLICY, "expected at least one remediation-policy component"
    for name, policy in LIVE_POLICY.items():
        # (1) independent: no dependency edge to another governed component.
        deps = policy.get("depends_on") or policy.get("dependencies") or []
        assert not deps, (
            f"{name}: remediation policy declares dependencies {deps!r}; "
            "outside the CAP-04 T13 safe envelope (see RMT_T13_DISPOSITION.md)"
        )
        # (2) every state-changing remediation action is human-approval-gated.
        assert policy.get("requires_approval", True) is True, (
            f"{name}: requires_approval is not True; outside the CAP-04 T13 "
            "safe envelope (see RMT_T13_DISPOSITION.md)"
        )


def test_manual_clear_quarantine_endpoint(learn):
    from app.homelab.operational_loop import operational_loop

    operational_loop.reset()

    state = operational_loop._get_state("uptime-kuma")
    state.quarantined = True
    state.quarantined_at = loop_mod._now()
    state.quarantine_reason = "test"

    import app.main as main_app

    with TestClient(main_app.app) as client:
        resp = client.post("/homelab/loop/clear", params={"component": "uptime-kuma"})

    assert resp.status_code == 200
    assert resp.json()["status"] == "quarantine_cleared"
    assert operational_loop.get_status()["components"]["uptime-kuma"]["quarantined"] is False
    assert any(rec.event_type == "homelab_loop_quarantine_cleared" for rec in learn)
