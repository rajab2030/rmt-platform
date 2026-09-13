"""RMT-CAP-09 (P-B) -- read-only evidence-chain correlation route.

Tests that ``evidence_chain()`` assembles the Govern -> Verify chain from the
durable stores, resolves by any of the three identifiers, is fail-open, and
**never writes**. All stores are isolated in-memory instances wired into the
module (same discipline as the other ops tests); no test touches the real
``data/governance_evidence.db``.
"""
import pytest

import app.ops.evidence_chain as evidence_chain
from app.core.intelligence.actions.approval import (
    ApprovalHold,
    ApprovalRecord,
    ApprovalStatus,
)
from app.core.intelligence.actions.approval_storage import (
    ApprovalHoldStorage,
    ApprovalRecordStorage,
)
from app.core.intelligence.actions.authorization import ExecutionAuthorization
from app.core.intelligence.actions.authorization_storage import (
    AuthorizationStorage,
)
from app.core.intelligence.actions.models import ActionRequest, ActionType
from app.core.intelligence.execution.audit import ExecutionAuditRecord
from app.core.intelligence.execution.storage import ExecutionAuditStorage
from app.core.intelligence.execution.trace import ExecutionTrace
from app.core.intelligence.execution.trace_storage import ExecutionTraceStorage
from app.core.intelligence.verification.models import VerificationResult
from app.core.intelligence.verification.storage import VerificationStorage


@pytest.fixture
def stores(monkeypatch):
    """In-memory stores wired into evidence_chain, pre-seeded with one action."""
    authz = AuthorizationStorage()
    records = ApprovalRecordStorage()
    holds = ApprovalHoldStorage()
    audit = ExecutionAuditStorage()
    traces = ExecutionTraceStorage()
    verif = VerificationStorage()

    # Correlated action a-1 / approval ap-1 / execution e-1
    authz.save(
        ExecutionAuthorization(
            action_id="a-1",
            approval_id="ap-1",
            authorized_by="grantor",
            status="authorized",
        )
    )
    records.save(
        ApprovalRecord(
            approval_id="ap-1", action_id="a-1",
            decision="approved", approved_by="ops",
        )
    )
    holds.save(
        ApprovalHold(
            approval_id="ap-1",
            action_id="a-1",
            action=ActionRequest(
                decision_id="d-1",
                component="svc",
                action_type=ActionType.START,
                reason="test",
            ),
            adapter_name="docker",
            status=ApprovalStatus.PENDING,
        )
    )
    audit.save(
        ExecutionAuditRecord(
            execution_id="e-1", action_id="a-1", authorization_id="auth-1",
            adapter="docker", status="executed", message="ok",
        )
    )
    traces.save(
        ExecutionTrace(
            execution_id="e-1", action_id="a-1", authorization_id="auth-1",
            policy_decision="allow", risk_level="low", outcome="executed",
        )
    )
    verif.save(
        VerificationResult(execution_id="e-1", status="verified_success")
    )

    for name, _store in {
        "execution_authorization_storage": authz,
        "approval_record_storage": records,
        "approval_hold_storage": holds,
        "execution_audit_storage": audit,
        "execution_trace_storage": traces,
        "verification_storage": verif,
    }.items():
        monkeypatch.setattr(evidence_chain, name, _store)

    return {name: _store for name, _store in {
        "authz": authz, "records": records, "holds": holds,
        "audit": audit, "traces": traces, "verif": verif,
    }.items()}


def _counts(stores):
    return {k: len(s.get_all()) for k, s in stores.items()}


def test_full_chain_by_action_id(stores):
    out = evidence_chain.evidence_chain(action_id="a-1")
    assert out["resolved"]["action_id"] == "a-1"
    assert len(out["authorizations"]) == 1
    assert len(out["approvals"]) == 1
    assert len(out["holds"]) == 1
    assert len(out["audit"]) == 1
    assert len(out["traces"]) == 1
    assert len(out["verifications"]) == 1
    assert out["verifications"][0]["execution_id"] == "e-1"
    assert out["approvals"][0]["decision"] == "approved"


def test_resolution_by_approval_id(stores):
    out = evidence_chain.evidence_chain(approval_id="ap-1")
    assert out["resolved"]["action_id"] == "a-1"
    assert out["resolved"]["approval_id"] == "ap-1"
    assert len(out["approvals"]) == 1
    assert len(out["holds"]) == 1  # pulled via resolved action_id


def test_resolution_by_execution_id(stores):
    out = evidence_chain.evidence_chain(execution_id="e-1")
    assert out["resolved"]["action_id"] == "a-1"
    assert len(out["audit"]) >= 1
    assert len(out["verifications"]) >= 1


def test_unknown_identifier_returns_empty_fail_open(stores):
    out = evidence_chain.evidence_chain(action_id="does-not-exist")
    assert out["resolved"]["action_id"] == "does-not-exist"
    for section in ("authorizations", "approvals", "holds",
                    "audit", "traces", "verifications"):
        assert out[section] == []


def test_store_read_failure_is_fail_open(stores, monkeypatch):
    def boom():
        raise RuntimeError("store unavailable")

    monkeypatch.setattr(evidence_chain, "execution_audit_storage", type(
        "BadStore", (), {"get_all": boom}
    )())
    out = evidence_chain.evidence_chain(action_id="a-1")
    assert out["audit"] == []        # degraded section -> [] not 500
    assert len(out["authorizations"]) == 1  # other sections unaffected


def test_no_identifier_returns_empty_shape(stores):
    out = evidence_chain.evidence_chain()
    assert out["resolved"]["action_id"] is None
    assert out["authorizations"] == []


def test_read_only_no_writes(stores):
    before = _counts(stores)
    evidence_chain.evidence_chain(action_id="a-1")
    evidence_chain.evidence_chain(approval_id="ap-1")
    evidence_chain.evidence_chain(execution_id="e-1")
    assert _counts(stores) == before
