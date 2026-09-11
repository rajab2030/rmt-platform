"""RMT-CAP-06 (C2/D-1) -- second domain end-to-end (run-safe).

Proves the frozen Core generalises past homelab/Docker: a real git-tag
mutation, in a disposable ``tmp_path`` repository, driven through the exact
same governed lifecycle CAP-05 already uses for Docker --
Understand/propose -> authority -> Govern -> Authorize -> Execute -> Verify
-> Learn -- with the durable evidence stores isolated (same isolation
pattern as ``test_remediation.py``) so nothing real is written, but the
execution adapter and observer are the REAL ``GitTagAdapter`` / git-tag
observer -- a genuine end-to-end proof, not a mocked one.

Also covers the D-1 DoD directly: two distinct agents -- one granted and
benign, one attempting to exceed its grant -- against the git domain.
"""
import subprocess

import pytest

import app.core.intelligence.actions.service as actions_service_module
import app.core.intelligence.execution.engine as execution_engine_module
import app.core.intelligence.actions.approval_service as approval_service_module
import app.core.intelligence.verification.service as verification_service_module
import app.core.intelligence.execution.adapters.registry as registry_module
import app.agent.adapter as adapter_mod

from app.core.intelligence.execution.adapters.registry import AdapterRegistry
from app.core.intelligence.actions.authorization_storage import AuthorizationStorage
from app.core.intelligence.actions.approval_storage import (
    ApprovalHoldStorage,
    ApprovalRecordStorage,
)
from app.core.intelligence.execution.storage import ExecutionAuditStorage
from app.core.intelligence.execution.trace_storage import ExecutionTraceStorage
from app.core.intelligence.verification.storage import VerificationStorage
from app.core.intelligence.actions.models import ActionType

from app.agent import loop_config
from app.agent.authority import authority_store
from app.agent.adapter import propose_and_govern, _resolve_adapter_name
from app.agent.contract import AgentIdentity, AgentIntent, AgentProposal
from app.agent.git_adapter import GitTagAdapter
from app.ops import separation as separation_mod


@pytest.fixture(autouse=True)
def _reset():
    authority_store.reset()
    separation_mod.reset()
    yield
    authority_store.reset()
    separation_mod.reset()


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(loop_config, "AGENT_ENABLED", True)


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "t@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "test"], check=True
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-q", "-m", "init"],
        cwd=tmp_path,
        check=True,
    )
    return tmp_path


def _tag_exists(repo_path, name) -> bool:
    proc = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{name}"],
        cwd=repo_path,
        capture_output=True,
    )
    return proc.returncode == 0


@pytest.fixture
def git_isolation(monkeypatch, repo):
    """Isolate the six durable evidence stores (same shape as
    test_remediation.py::_setup_isolation), but register a REAL GitTagAdapter
    into an isolated registry pointed at the disposable ``repo`` -- and point
    the git observer at the same repo via the real env var it reads. The
    governed pipeline, verifier, and adapter are all real; only storage and
    the target repo are swapped out."""
    auth_storage = AuthorizationStorage()
    trace_storage = ExecutionTraceStorage()
    audit_storage = ExecutionAuditStorage()
    hold_storage = ApprovalHoldStorage()
    approval_record_storage = ApprovalRecordStorage()
    verification_storage = VerificationStorage()

    isolated_registry = AdapterRegistry()
    isolated_registry.register("git", GitTagAdapter(repo))

    monkeypatch.setenv("RMT_AGENT_GIT_REPO_PATH", str(repo))

    monkeypatch.setattr(
        actions_service_module, "execution_authorization_storage", auth_storage
    )
    monkeypatch.setattr(
        execution_engine_module, "execution_authorization_storage", auth_storage
    )
    monkeypatch.setattr(execution_engine_module, "execution_trace_storage", trace_storage)
    monkeypatch.setattr(execution_engine_module, "execution_audit_storage", audit_storage)
    monkeypatch.setattr(approval_service_module, "approval_hold_storage", hold_storage)
    monkeypatch.setattr(
        approval_service_module, "approval_record_storage", approval_record_storage
    )
    monkeypatch.setattr(
        approval_service_module, "execution_authorization_storage", auth_storage
    )
    monkeypatch.setattr(
        verification_service_module, "verification_storage", verification_storage
    )
    monkeypatch.setattr(execution_engine_module, "adapter_registry", isolated_registry)
    # _resolve_adapter_name does a fresh `from ...registry import adapter_registry`
    # on every call -- point that same lookup at the isolated registry too.
    monkeypatch.setattr(registry_module, "adapter_registry", isolated_registry)
    monkeypatch.setattr(adapter_mod, "record_learning", lambda *a, **k: None)

    return {
        "repo": repo,
        "trace": trace_storage,
        "audit": audit_storage,
        "hold": hold_storage,
        "verification": verification_storage,
    }


def _proposal(target, grant_id, mechanism=ActionType.CREATE, expected_state=None):
    if expected_state is None:
        expected_state = "present" if mechanism == ActionType.CREATE else "absent"
    return AgentProposal(
        identity=AgentIdentity(
            agent_id="git-proof-agent", operational_context="git"
        ),
        intent=AgentIntent(
            goal=f"tag {target}", target=target, mechanism=mechanism,
            reason="release proof", confidence=90,
        ),
        expected_state=expected_state,
        grant_id=grant_id,
    )


# ---------------------------------------------------------------------------
# _resolve_adapter_name -- the one behavior change, isolated
# ---------------------------------------------------------------------------

def test_resolve_adapter_name_homelab_default_unchanged(monkeypatch):
    monkeypatch.setattr(adapter_mod, "resolve_adapter_name", lambda: "simulation")
    assert _resolve_adapter_name("homelab") == "simulation"


def test_resolve_adapter_name_git_registered(tmp_path):
    registry = AdapterRegistry()
    registry.register("git", GitTagAdapter(tmp_path))
    import app.core.intelligence.execution.adapters.registry as rm
    real = rm.adapter_registry
    rm.adapter_registry = registry
    try:
        assert _resolve_adapter_name("git") == "git"
    finally:
        rm.adapter_registry = real


def test_resolve_adapter_name_git_not_registered_falls_back_to_simulation():
    registry = AdapterRegistry()
    import app.core.intelligence.execution.adapters.registry as rm
    real = rm.adapter_registry
    rm.adapter_registry = registry
    try:
        assert _resolve_adapter_name("git") == "simulation"
    finally:
        rm.adapter_registry = real


# ---------------------------------------------------------------------------
# Grant-scope refusal -- never reaches the governed boundary
# ---------------------------------------------------------------------------

def test_ungranted_git_proposal_is_refused_before_governance(enabled, git_isolation):
    outcome = propose_and_govern(_proposal("v1.0.0-proof", grant_id=None))
    assert outcome.decision == "no_authority"
    assert git_isolation["trace"].get_all() == []
    assert git_isolation["audit"].get_all() == []
    assert not _tag_exists(git_isolation["repo"], "v1.0.0-proof")


def test_over_reaching_grant_scope_mismatch_is_refused(enabled, git_isolation):
    """Granted create on a DIFFERENT tag than the one proposed -- refused,
    same as no grant at all."""
    grant = authority_store.grant(
        operation="create", target="v1.0.0-allowed", granted_by="operator"
    )
    outcome = propose_and_govern(
        _proposal("v1.0.0-NOT-allowed", grant_id=grant.grant_id)
    )
    assert outcome.decision == "no_authority"
    assert not _tag_exists(git_isolation["repo"], "v1.0.0-NOT-allowed")


# ---------------------------------------------------------------------------
# D-1 DoD: benign agent, end-to-end, real git mutation + real verification
# ---------------------------------------------------------------------------

def test_benign_git_proposal_reaches_governed_boundary_and_verifies(
    enabled, git_isolation
):
    grant = authority_store.grant(
        operation="create", target="v1.0.0-proof", granted_by="operator"
    )
    outcome = propose_and_govern(
        _proposal("v1.0.0-proof", grant_id=grant.grant_id)
    )

    # requires_approval defaults True -> governed hold, not an auto-bypass.
    assert outcome.decision == "hold"
    assert outcome.approval_id
    assert not _tag_exists(git_isolation["repo"], "v1.0.0-proof")  # not yet

    from app.core.intelligence.actions.approval_service import approve_held_action

    cont = approve_held_action(outcome.approval_id, approved_by="operator")
    assert cont["status"] == "executed"
    assert cont["success"] is True

    # Real mutation happened through the real GitTagAdapter.
    assert _tag_exists(git_isolation["repo"], "v1.0.0-proof")

    # Real above-Core verification against the real git observer.
    from app.ops.verification import verify_executed_action

    verification = verify_executed_action(
        cont["execution_id"],
        adapter_name="git",
        operation="create",
        target="v1.0.0-proof",
        expected=None,
        action_id=None,
    )
    assert verification.status == "verified_success"

    assert len(git_isolation["trace"].get_all()) >= 1
    assert len(git_isolation["audit"].get_all()) >= 1
