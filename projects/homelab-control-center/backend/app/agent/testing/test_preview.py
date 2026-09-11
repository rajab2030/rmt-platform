"""RMT-CAP-07 (C3) -- preview_proposal (run-safe).

The central guarantee under test: preview resolves a proposal using the REAL
frozen policy/risk/approval functions, with zero durable writes -- no grant
consumed, no hold created, execute_governed_action never called -- and its
predicted outcome must never drift from what propose_and_govern would
actually do for the same input.
"""
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

import app.agent.adapter as adapter_mod
from app.agent import loop_config
from app.agent.authority import authority_store, AuthorityGrantStorage
from app.agent.contract import AgentIdentity, AgentIntent, AgentProposal
from app.agent.preview import preview_proposal
from app.core.intelligence.actions.models import ActionType
from app.core.intelligence.actions.approval_storage import ApprovalHoldStorage
from app.ops import separation as separation_mod


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    # RMT-CAP-08: authority_store is durably backed -- isolate per test.
    monkeypatch.setattr(authority_store, "_storage", AuthorityGrantStorage(file_path=None))
    separation_mod.reset()
    yield
    separation_mod.reset()


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(loop_config, "AGENT_ENABLED", True)


def _proposal(target="proof-target", grant_id=None, mechanism=ActionType.CREATE, confidence=90):
    return AgentProposal(
        identity=AgentIdentity(agent_id="preview-agent"),
        intent=AgentIntent(
            goal=f"do something to {target}", target=target, mechanism=mechanism,
            reason="because", confidence=confidence,
        ),
        grant_id=grant_id,
    )


def test_preview_disabled_by_default():
    assert loop_config.AGENT_ENABLED is False
    result = preview_proposal(_proposal())
    assert result["decision"] == "disabled"


def test_preview_no_proposal_for_empty_goal(enabled):
    proposal = AgentProposal(
        identity=AgentIdentity(agent_id="a"),
        intent=AgentIntent(goal="", target="t", mechanism=ActionType.CREATE),
    )
    assert preview_proposal(proposal)["decision"] == "no_proposal"


def test_preview_no_proposal_for_empty_target(enabled):
    proposal = AgentProposal(
        identity=AgentIdentity(agent_id="a"),
        intent=AgentIntent(goal="g", target="", mechanism=ActionType.CREATE),
    )
    assert preview_proposal(proposal)["decision"] == "no_proposal"


def test_preview_resolves_action_and_predicts_manual_hold(enabled):
    grant = authority_store.grant(operation="create", target="proof-target", granted_by="op")
    result = preview_proposal(_proposal(grant_id=grant.grant_id))

    assert result["decision"] == "preview"
    assert result["action"]["component"] == "proof-target"
    assert result["action"]["action_type"] == "create"
    assert result["action"]["requires_approval"] is True
    assert result["authority"]["ok"] is True
    assert result["predicted"]["policy_allowed"] is True
    assert result["predicted"]["approval_mode"] == "manual"
    assert result["predicted"]["approval_reason"] == "Action explicitly requires approval"


def test_preview_reports_missing_authority_without_blocking(enabled):
    """Preview does not gate on authority -- it reports it, so an operator
    deciding whether to grant can see what WOULD happen if they did."""
    result = preview_proposal(_proposal(grant_id=None))
    assert result["decision"] == "preview"
    assert result["authority"]["ok"] is False
    assert result["authority"]["detail"] == "no_grant"
    # Still resolves the concrete action + predicted outcome.
    assert result["action"]["component"] == "proof-target"
    assert result["predicted"]["approval_mode"] == "manual"


def test_preview_high_risk_remove_predicts_manual_for_high_risk_reason(enabled):
    grant = authority_store.grant(operation="remove", target="proof-target", granted_by="op")
    result = preview_proposal(
        _proposal(grant_id=grant.grant_id, mechanism=ActionType.REMOVE)
    )
    assert result["predicted"]["risk_level"] == "high"
    assert result["predicted"]["approval_mode"] == "manual"
    assert result["predicted"]["approval_reason"] == "High-risk action requires human approval"


# ---------------------------------------------------------------------------
# The core guarantee: zero side effects
# ---------------------------------------------------------------------------

def test_preview_never_calls_execute_governed_action(enabled, monkeypatch):
    spy = Mock(side_effect=AssertionError("preview must never execute"))
    monkeypatch.setattr(adapter_mod, "execute_governed_action", spy)
    grant = authority_store.grant(operation="create", target="proof-target", granted_by="op")

    result = preview_proposal(_proposal(grant_id=grant.grant_id))

    assert result["decision"] == "preview"
    spy.assert_not_called()


def test_preview_does_not_consume_the_grant(enabled):
    grant = authority_store.grant(operation="create", target="proof-target", granted_by="op")
    preview_proposal(_proposal(grant_id=grant.grant_id))

    reloaded = authority_store.get(grant.grant_id)
    assert reloaded.consumed is False


def test_preview_creates_no_hold(enabled, monkeypatch):
    import app.core.intelligence.actions.approval_service as approval_service_module

    hold_storage = ApprovalHoldStorage()
    monkeypatch.setattr(approval_service_module, "approval_hold_storage", hold_storage)

    grant = authority_store.grant(operation="create", target="proof-target", granted_by="op")
    preview_proposal(_proposal(grant_id=grant.grant_id))

    assert hold_storage.get_all() == []


# ---------------------------------------------------------------------------
# Regression guard: preview must never drift from the real outcome
# ---------------------------------------------------------------------------

def test_preview_matches_the_real_governed_outcome_for_the_same_input(enabled, monkeypatch):
    from app.homelab.testing.test_remediation import _setup_isolation  # reuse the same isolation shape

    stores = _setup_isolation(monkeypatch)
    monkeypatch.setattr(adapter_mod, "record_learning", lambda *a, **k: None)

    grant_a = authority_store.grant(operation="create", target="proof-target", granted_by="op")
    grant_b = authority_store.grant(operation="create", target="proof-target", granted_by="op")

    preview = preview_proposal(_proposal(grant_id=grant_a.grant_id))
    assert preview["predicted"]["approval_mode"] == "manual"

    from app.agent.adapter import propose_and_govern

    outcome = propose_and_govern(_proposal(grant_id=grant_b.grant_id))
    assert outcome.decision == "hold"  # manual -> a governed hold, consistent with the prediction
    assert len(stores["hold"].get_all()) == 1


# ---------------------------------------------------------------------------
# HTTP route
# ---------------------------------------------------------------------------

def test_act_preview_route_invalid_mechanism():
    import app.main as main_app

    with TestClient(main_app.app) as c:
        r = c.post(
            "/agent/act/preview",
            json={
                "agent_id": "a", "goal": "g", "target": "t",
                "mechanism": "not-a-real-mechanism",
            },
        )
    assert r.status_code == 200
    assert r.json()["decision"] == "invalid_proposal"


def test_act_preview_route_resolves_without_side_effects(monkeypatch):
    monkeypatch.setattr(loop_config, "AGENT_ENABLED", True)
    grant = authority_store.grant(operation="create", target="route-proof", granted_by="op")

    import app.main as main_app

    with TestClient(main_app.app) as c:
        r = c.post(
            "/agent/act/preview",
            json={
                "agent_id": "a", "goal": "tag it", "target": "route-proof",
                "mechanism": "create", "grant_id": grant.grant_id,
            },
        )
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "preview"
    assert body["action"]["component"] == "route-proof"
    # Grant untouched by a preview call through the real route.
    assert authority_store.get(grant.grant_id).consumed is False
