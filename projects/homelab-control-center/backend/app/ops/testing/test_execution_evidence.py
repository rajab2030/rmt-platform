"""RMT-PROD P1 (E3) -- distinguishable evidence for a failed adapter execution.

``record_failed_execution_evidence`` writes one ``VerificationResult`` with
status ``adapter_execution_failed`` into the existing verification store when a
governed execution reached the adapter and failed with no verification record.
It is strictly bounded (real execution attempts only), idempotent, and
fail-open.
"""
import pytest

import app.ops.execution_evidence as execution_evidence
from app.core.intelligence.verification.models import (
    ExpectedOutcome,
    VerificationResult,
)
from app.core.intelligence.verification.storage import VerificationStorage
from app.ops.execution_evidence import (
    ADAPTER_EXECUTION_FAILED,
    record_failed_execution_evidence,
)


@pytest.fixture
def store(monkeypatch):
    """Isolated in-memory verification store wired into the module."""
    s = VerificationStorage(file_path=None)
    monkeypatch.setattr(execution_evidence, "verification_storage", s)
    return s


def _failed(execution_id="e-1", message="Adapter error: container not found"):
    return {
        "status": "executed",
        "success": False,
        "execution_id": execution_id,
        "status_detail": "failed",
        "message": message,
    }


def test_failed_execution_gets_a_distinguishable_record(store):
    rec = record_failed_execution_evidence(_failed(), source="execute_endpoint")

    assert isinstance(rec, VerificationResult)
    assert rec.status == ADAPTER_EXECUTION_FAILED
    assert rec.execution_id == "e-1"
    assert rec.reason == "Adapter error: container not found"
    assert store.get_by_execution_id("e-1") is rec


def test_expected_outcome_is_carried_through(store):
    expected = ExpectedOutcome(
        target="uptime-kuma", operation="restart", expected_state="running"
    )
    rec = record_failed_execution_evidence(
        _failed(), expected=expected, source="agent_adapter"
    )
    assert rec.expected == expected
    assert rec.observed is None


def test_idempotent_when_a_verification_record_already_exists(store):
    # an above-Core observer already recorded an outcome for this run
    store.save(
        VerificationResult(execution_id="e-1", status="state_mismatch")
    )

    rec = record_failed_execution_evidence(_failed(), source="homelab_remediate")

    assert rec is None
    # still exactly one record, and it is the original
    assert len(store.get_all()) == 1
    assert store.get_by_execution_id("e-1").status == "state_mismatch"


def test_successful_execution_is_not_recorded(store):
    outcome = {
        "status": "executed",
        "success": True,
        "execution_id": "e-1",
    }
    assert record_failed_execution_evidence(outcome, source="x") is None
    assert store.get_all() == []


@pytest.mark.parametrize(
    "outcome",
    [
        {"status": "manual_approval_required", "approval_id": "a-1"},
        {"status": "policy_denied", "reason": "blocked"},
        {"status": "no_authority", "detail": "no_grant"},
        {"status": "authorization_not_created"},
        {"status": "rejected"},
        {"status": "no_remediation", "component": "x"},
        {"status": "unsupported_operation"},
        {"status": "error", "detail": "boom"},
    ],
)
def test_blocked_before_execution_outcomes_are_left_alone(store, outcome):
    assert record_failed_execution_evidence(outcome, source="x") is None
    assert store.get_all() == []


def test_failed_but_no_execution_id_is_not_recorded(store):
    outcome = {"status": "executed", "success": False, "execution_id": ""}
    assert record_failed_execution_evidence(outcome, source="x") is None
    assert store.get_all() == []


@pytest.mark.parametrize("outcome", [None, "nope", 42, []])
def test_non_dict_outcome_is_safe(store, outcome):
    assert record_failed_execution_evidence(outcome, source="x") is None
    assert store.get_all() == []


def test_reason_falls_back_to_status_detail_then_default(store):
    r1 = record_failed_execution_evidence(
        {
            "status": "executed",
            "success": False,
            "execution_id": "e-1",
            "status_detail": "failed",
        },
        source="x",
    )
    assert r1.reason == "failed"

    r2 = record_failed_execution_evidence(
        {"status": "executed", "success": False, "execution_id": "e-2"},
        source="x",
    )
    assert r2.reason == "Adapter invoked and returned failure"


def test_fail_open_when_the_store_raises(store, monkeypatch):
    def boom(_record):
        raise RuntimeError("disk gone")

    monkeypatch.setattr(store, "save", boom)

    # must not raise
    assert record_failed_execution_evidence(_failed(), source="x") is None
