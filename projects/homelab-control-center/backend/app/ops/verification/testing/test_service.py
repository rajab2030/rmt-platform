"""B1a -- above-Core post-execution verification layer.

Covers the registry, the expected-state table, the ``absent`` observer
extension, and ``verify_executed_action`` (settling poll, reason token,
supersedes clause, and the no-observer branch that writes nothing).
"""
import pytest

import app.homelab.observer as observer_module
import app.core.intelligence.verification.storage as verification_storage_module
from app.core.intelligence.verification.models import (
    ExpectedOutcome,
    ObservedState,
    VerificationResult,
    VerificationStatus,
)
from app.core.intelligence.verification.storage import VerificationStorage

from app.ops.verification import verify_executed_action
from app.ops.verification.expected import expected_state_for
from app.ops.verification import registry as registry_module
from app.ops.verification.registry import (
    register_observer,
    resolve_observer,
    registered_pairs,
)


@pytest.fixture
def store(monkeypatch):
    s = VerificationStorage(file_path=None)
    monkeypatch.setattr(
        verification_storage_module, "verification_storage", s
    )
    return s


def _mock_docker(monkeypatch, *, available=True, containers=None):
    monkeypatch.setattr(observer_module, "docker_available", lambda: available)
    monkeypatch.setattr(
        observer_module,
        "get_containers",
        lambda: containers if containers is not None else [],
    )


# --- registry ---------------------------------------------------------------

def test_registry_has_the_five_docker_operations():
    pairs = registered_pairs()
    for op in ("start", "stop", "restart", "create", "remove"):
        assert ("docker", op) in pairs


def test_resolve_observer_miss_returns_none():
    assert resolve_observer("nope", "restart", "x") is None
    assert resolve_observer("docker", "frobnicate", "x") is None


def test_register_observer_is_idempotent_and_case_insensitive(monkeypatch):
    calls = []
    monkeypatch.setitem(registry_module._REGISTRY, ("unit", "op"), None)
    register_observer("UNIT", "OP", lambda target: lambda: calls.append(target))
    obs = resolve_observer("unit", "op", "t1")
    obs()
    assert calls == ["t1"]


# --- expected-state table -------------------------------------------------

@pytest.mark.parametrize(
    "operation,expected",
    [
        ("start", "running"),
        ("restart", "running"),
        ("create", "running"),
        ("stop", "exited"),
        ("remove", "absent"),
        ("inspect", None),
    ],
)
def test_expected_state_for_docker(operation, expected):
    assert expected_state_for("docker", operation) == expected


def test_expected_state_for_unknown_adapter_is_none():
    assert expected_state_for("simulation", "restart") is None


# --- observe_container_state absent extension ----------------------------

def test_observe_absent_when_reachable_and_gone(monkeypatch):
    _mock_docker(monkeypatch, available=True, containers=[{"name": "other", "status": "running"}])
    observed = observer_module.observe_container_state("target")
    assert isinstance(observed, ObservedState)
    assert observed.state == "absent"


def test_observe_none_when_docker_down(monkeypatch):
    _mock_docker(monkeypatch, available=False)
    assert observer_module.observe_container_state("target") is None


# --- verify_executed_action: happy paths --------------------------------

def test_restart_verified_success(monkeypatch, store):
    _mock_docker(monkeypatch, containers=[{"name": "svc", "status": "running"}])
    r = verify_executed_action(
        "e1", adapter_name="docker", operation="restart", target="svc"
    )
    assert r.status == VerificationStatus.VERIFIED_SUCCESS
    assert r.reason.startswith("[layer=above_core adapter=docker")
    assert len(store.get_all()) == 1


def test_stop_verified_success_against_exited(monkeypatch, store):
    _mock_docker(monkeypatch, containers=[{"name": "svc", "status": "exited"}])
    r = verify_executed_action(
        "e2", adapter_name="docker", operation="stop", target="svc"
    )
    assert r.status == VerificationStatus.VERIFIED_SUCCESS
    assert r.observed.state == "exited"


def test_remove_verified_success_against_absent(monkeypatch, store):
    _mock_docker(monkeypatch, containers=[{"name": "kept", "status": "running"}])
    r = verify_executed_action(
        "e3", adapter_name="docker", operation="remove", target="svc"
    )
    assert r.status == VerificationStatus.VERIFIED_SUCCESS
    assert r.observed.state == "absent"


def test_state_mismatch(monkeypatch, store):
    _mock_docker(monkeypatch, containers=[{"name": "svc", "status": "exited"}])
    r = verify_executed_action(
        "e4", adapter_name="docker", operation="restart", target="svc"
    )
    assert r.status == VerificationStatus.STATE_MISMATCH


def test_caller_supplied_expected_wins(monkeypatch, store):
    _mock_docker(monkeypatch, containers=[{"name": "svc", "status": "paused"}])
    r = verify_executed_action(
        "e5",
        adapter_name="docker",
        operation="restart",
        target="svc",
        expected=ExpectedOutcome(target="svc", operation="restart", expected_state="paused"),
    )
    assert r.status == VerificationStatus.VERIFIED_SUCCESS


# --- verify_executed_action: no observer -> writes nothing --------------

def test_no_observer_returns_observation_unavailable_and_writes_nothing(store):
    r = verify_executed_action(
        "e6", adapter_name="simulation", operation="restart", target="svc"
    )
    assert r.status == VerificationStatus.OBSERVATION_UNAVAILABLE
    assert "no above-Core observer" in r.reason
    assert store.get_all() == []


# --- supersedes clause -------------------------------------------------

def test_supersedes_clause_when_core_record_exists(monkeypatch, store):
    store.save(
        VerificationResult(
            execution_id="e7",
            status=VerificationStatus.OBSERVATION_UNAVAILABLE,
            reason="Observation unavailable",
        )
    )
    _mock_docker(monkeypatch, containers=[{"name": "svc", "status": "running"}])
    r = verify_executed_action(
        "e7", adapter_name="docker", operation="restart", target="svc"
    )
    assert "supersedes=observation_unavailable" in r.reason


def test_no_supersedes_clause_when_no_core_record(monkeypatch, store):
    _mock_docker(monkeypatch, containers=[{"name": "svc", "status": "running"}])
    r = verify_executed_action(
        "e8", adapter_name="docker", operation="restart", target="svc"
    )
    assert "supersedes=" not in r.reason


# --- settling poll ---------------------------------------------------

def test_settling_poll_returns_early_and_tolerates_a_transient_reading(monkeypatch, store):
    monkeypatch.setenv("RMT_VERIFY_OBSERVE_TIMEOUT_S", "3")
    sleeps = []
    monkeypatch.setattr(
        "app.ops.verification.service.time.sleep", lambda s: sleeps.append(s)
    )
    seq = iter(
        [
            ObservedState(target="svc", state="restarting", source="docker"),
            ObservedState(target="svc", state="running", source="docker"),
        ]
    )
    register_observer("unit-poll", "op", lambda target: lambda: next(seq))
    try:
        r = verify_executed_action(
            "e9",
            adapter_name="unit-poll",
            operation="op",
            target="svc",
            expected=ExpectedOutcome(target="svc", operation="op", expected_state="running"),
        )
    finally:
        registry_module._REGISTRY.pop(("unit-poll", "op"), None)
    assert r.status == VerificationStatus.VERIFIED_SUCCESS
    # one transient reading -> exactly one sleep, then the match
    assert len(sleeps) == 1


def test_single_shot_when_timeout_zero(monkeypatch, store):
    monkeypatch.setenv("RMT_VERIFY_OBSERVE_TIMEOUT_S", "0")
    calls = {"n": 0}

    def _obs():
        calls["n"] += 1
        return ObservedState(target="svc", state="restarting", source="docker")

    register_observer("unit-once", "op", lambda target: _obs)
    try:
        r = verify_executed_action(
            "e10",
            adapter_name="unit-once",
            operation="op",
            target="svc",
            expected=ExpectedOutcome(target="svc", operation="op", expected_state="running"),
        )
    finally:
        registry_module._REGISTRY.pop(("unit-once", "op"), None)
    assert calls["n"] == 1
    assert r.status == VerificationStatus.STATE_MISMATCH
