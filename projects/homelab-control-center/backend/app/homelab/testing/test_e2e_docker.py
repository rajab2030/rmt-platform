"""RMT-PROD P1 (V1) -- automated end-to-end test on the REAL Docker adapter.

Every other suite mocks the execution adapter. This one drives the actual
governed lifecycle against a **disposable** Alpine container:

    fault (stop) -> observe -> governed remediation held for approval
    -> approve -> real `docker restart` -> above-Core Docker verify
    -> correlated durable evidence

It **auto-skips** when the Docker daemon is unreachable or `alpine:latest`
cannot be obtained, so it stays in the default suite and in CI without needing
a homelab.

Isolation: the six durable evidence stores + both verification-storage
references are swapped to in-memory instances, so nothing is written to the
real JSON stores. The execution adapter registry is **left real** -- that is
the point of this test. The throwaway container has a unique
``rmt-e2e-<hex>`` name (never a homelab component) and is force-removed on
teardown.
"""
import time
import uuid

import pytest

from app.core.intelligence.actions.models import ActionRequest, ActionType
from app.core.intelligence.actions.service import execute_governed_action
from app.core.intelligence.actions.approval_service import approve_held_action
from app.core.intelligence.verification.models import ExpectedOutcome
from app.core.intelligence.execution.adapters.bootstrap import (
    register_default_adapters,
)
from app.homelab.observer import observe_container_state
from app.homelab.verification import verify_docker_execution
from app.ops.execution_evidence import record_failed_execution_evidence

# storage classes
from app.core.intelligence.actions.approval_storage import (
    ApprovalHoldStorage,
    ApprovalRecordStorage,
)
from app.core.intelligence.actions.authorization_storage import AuthorizationStorage
from app.core.intelligence.execution.storage import ExecutionAuditStorage
from app.core.intelligence.execution.trace_storage import ExecutionTraceStorage
from app.core.intelligence.verification.storage import VerificationStorage

# modules holding the singleton refs the governed path reads
import app.core.intelligence.actions.service as actions_service_module
import app.core.intelligence.execution.engine as engine_module
import app.core.intelligence.actions.approval_service as approval_service_module
import app.core.intelligence.verification.service as verification_service_module
import app.core.intelligence.verification.storage as verification_storage_module
import app.homelab.verification as homelab_verification_module
import app.ops.execution_evidence as execution_evidence_module

pytestmark = pytest.mark.e2e

E2E_IMAGE = "alpine:latest"


@pytest.fixture(scope="module")
def docker_client():
    docker = pytest.importorskip("docker", reason="docker SDK not installed")
    try:
        client = docker.from_env()
        client.ping()
    except Exception as exc:  # daemon down / socket denied
        pytest.skip(f"Docker daemon not reachable: {exc!r}")
    try:
        client.images.get(E2E_IMAGE)
    except Exception:
        try:
            client.images.pull(E2E_IMAGE)
        except Exception as exc:
            pytest.skip(f"{E2E_IMAGE} unavailable and cannot pull: {exc!r}")
    return client


@pytest.fixture
def isolated_stores(monkeypatch):
    """Swap every durable evidence store to in-memory. Adapter registry stays real."""
    auth = AuthorizationStorage()
    trace = ExecutionTraceStorage()
    audit = ExecutionAuditStorage()
    hold = ApprovalHoldStorage()
    record = ApprovalRecordStorage()
    verification = VerificationStorage()

    monkeypatch.setattr(actions_service_module, "execution_authorization_storage", auth)
    monkeypatch.setattr(engine_module, "execution_authorization_storage", auth)
    monkeypatch.setattr(engine_module, "execution_trace_storage", trace)
    monkeypatch.setattr(engine_module, "execution_audit_storage", audit)
    monkeypatch.setattr(approval_service_module, "approval_hold_storage", hold)
    monkeypatch.setattr(approval_service_module, "approval_record_storage", record)
    monkeypatch.setattr(approval_service_module, "execution_authorization_storage", auth)
    # verification_storage is imported by name in several modules -- patch all
    # of them (missing one writes an e2e record to the real verifications.json).
    for mod in (
        verification_service_module,
        verification_storage_module,
        homelab_verification_module,
        execution_evidence_module,
    ):
        monkeypatch.setattr(mod, "verification_storage", verification)

    return {
        "auth": auth,
        "trace": trace,
        "audit": audit,
        "hold": hold,
        "record": record,
        "verification": verification,
    }


@pytest.fixture
def probe(docker_client):
    """A running, disposable container. Force-removed on teardown."""
    register_default_adapters()  # ensure the "docker" adapter is registered
    name = f"rmt-e2e-{uuid.uuid4().hex[:10]}"
    container = docker_client.containers.run(
        E2E_IMAGE, ["sleep", "3600"], name=name, detach=True,
        labels={"rmt-e2e": "1"},
    )
    try:
        yield name
    finally:
        try:
            container.remove(force=True)
        except Exception:
            pass


def _wait_status(docker_client, name, want, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            c = docker_client.containers.get(name)
            c.reload()
            if c.status == want:
                return c.status
        except Exception:
            pass
        time.sleep(0.3)
    return docker_client.containers.get(name).status


def _restart_action(target):
    return ActionRequest(
        decision_id=f"v1-e2e-{target}",
        component=target,
        action_type=ActionType.RESTART,
        reason="V1 end-to-end: held -> approve -> real docker restart -> verify",
        confidence=100,
        requires_approval=True,
        expected_outcome=ExpectedOutcome(
            target=target, operation="restart", expected_state="running",
        ),
    )


def test_fault_held_approved_executed_verified(docker_client, probe, isolated_stores):
    target = probe
    assert _wait_status(docker_client, target, "running") == "running"

    # --- fault injection (out of band -- not the thing under test) ---
    docker_client.containers.get(target).stop(timeout=2)
    assert _wait_status(docker_client, target, "exited") == "exited"
    observed = observe_container_state(target)
    assert observed is not None and observed.state == "exited"

    # --- governed remediation: must be HELD for human approval ---
    action = _restart_action(target)
    held = execute_governed_action(action, adapter_name="docker")
    assert held["status"] == "manual_approval_required", held
    approval_id = held["approval_id"]
    # nothing executed yet: the container is still down
    assert docker_client.containers.get(target).status == "exited"
    assert isolated_stores["audit"].get_all() == []

    # --- approve -> real docker restart ---
    result = approve_held_action(approval_id, approved_by="v1-e2e-operator", approved=True)
    assert result["status"] == "executed", result
    assert result["success"] is True
    execution_id = result["execution_id"]

    # the REAL container actually came back
    assert _wait_status(docker_client, target, "running") == "running"

    # --- above-Core Docker verification ---
    verification = verify_docker_execution(
        execution_id, action.expected_outcome, target
    )
    assert verification.status == "verified_success", verification

    # --- correlated durable evidence (in the isolated stores) ---
    authz = [
        a for a in isolated_stores["auth"].get_all() if a.approval_id == approval_id
    ]
    assert authz, "no authorization linked to the approval"
    assert authz[0].action_id == action.action_id

    audit = [
        r for r in isolated_stores["audit"].get_all() if r.execution_id == execution_id
    ]
    assert audit and audit[0].adapter == "docker"
    assert audit[0].status in ("completed", "executed", "success")

    trace = [
        t for t in isolated_stores["trace"].get_all() if t.execution_id == execution_id
    ]
    assert trace, "no execution trace recorded"

    # Two verification records for this execution, both legitimate: the Core
    # verifier's fail-safe `observation_unavailable` (it is not the Docker
    # observer) and the above-Core Docker observer's `verified_success`.
    vstatuses = {
        r.status
        for r in isolated_stores["verification"].get_all()
        if r.execution_id == execution_id
    }
    assert "verified_success" in vstatuses, vstatuses

    # real JSON stores untouched
    from app.core.intelligence.execution.trace_storage import execution_trace_storage
    assert all(
        t.execution_id != execution_id for t in execution_trace_storage.get_all()
    )


def test_real_adapter_failure_records_e3_evidence(docker_client, isolated_stores):
    register_default_adapters()
    absent = f"rmt-e2e-absent-{uuid.uuid4().hex[:8]}"
    action = ActionRequest(
        decision_id=f"v1-e2e-{absent}",
        component=absent,
        action_type=ActionType.RESTART,
        reason="V1 end-to-end: adapter invoked against a missing container",
        confidence=100,
        requires_approval=False,
        expected_outcome=ExpectedOutcome(
            target=absent, operation="restart", expected_state="running",
        ),
    )

    outcome = execute_governed_action(action, adapter_name="docker")
    # risk may still gate it -- continue through the hold if so
    if outcome.get("status") == "manual_approval_required":
        outcome = approve_held_action(
            outcome["approval_id"], approved_by="v1-e2e-operator", approved=True
        )

    assert outcome["status"] == "executed", outcome
    assert outcome["success"] is False  # the adapter was invoked and failed

    rec = record_failed_execution_evidence(
        outcome, expected=action.expected_outcome, source="v1_e2e"
    )
    assert rec is not None
    assert rec.status == "adapter_execution_failed"
    assert rec.execution_id == outcome["execution_id"]
