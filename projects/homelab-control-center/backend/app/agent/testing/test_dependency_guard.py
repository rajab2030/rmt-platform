"""RMT-CAP-05 -- T13 dependency-cascade guard, against the real data sources.

`escalate_for_dependency_cascade` unions the above-Core homelab map
(`app/homelab/dependencies.py`) with the frozen Core
`ComponentContext.dependencies`. The current homelab records all three services
as independent, so the guard is a no-op today; it fires the moment an edge is
added to either source.
"""
import app.homelab.dependencies as deps_mod
import app.agent.dependency_guard as guard_mod
from app.agent import loop_config
from app.agent.dependency_guard import (
    escalate_for_dependency_cascade,
    dependency_view,
)
from app.core.intelligence.context.models import ComponentContext


# --- current homelab: independent -> no escalation ----------------------

def test_real_homelab_map_is_all_independent():
    view = dependency_view()
    assert set(view["homelab_map"]) == {"portainer", "dozzle", "uptime-kuma"}
    assert all(v == [] for v in view["homelab_map"].values())


def test_allowed_op_not_escalated_with_real_empty_map():
    esc, reason = escalate_for_dependency_cascade("uptime-kuma", "start")
    assert esc is False and reason == ""


# --- an above-Core edge -> escalation ----------------------------------

def test_escalates_on_homelab_map_edge(monkeypatch):
    monkeypatch.setitem(deps_mod.HOMELAB_DEPENDENCIES, "web", ["db"])
    esc, reason = escalate_for_dependency_cascade("db", "start")
    assert esc is True
    assert "T13" in reason and "web" in reason


# --- an operator-declared env edge -> escalation (T1-2) ---------------

def test_escalates_on_operator_declared_env_edge(monkeypatch):
    """RMT_HOMELAB_DEPENDENCIES activates T13 with no code change; unsetting
    it de-activates it."""
    monkeypatch.delenv("RMT_HOMELAB_DEPENDENCIES", raising=False)
    assert escalate_for_dependency_cascade("portainer", "start") == (False, "")

    monkeypatch.setenv("RMT_HOMELAB_DEPENDENCIES", "uptime-kuma:portainer")
    esc, reason = escalate_for_dependency_cascade("portainer", "start")
    assert esc is True
    assert "T13" in reason and "uptime-kuma" in reason
    assert dependency_view()["sources"]["env"] == {"uptime-kuma": ["portainer"]}

    monkeypatch.delenv("RMT_HOMELAB_DEPENDENCIES", raising=False)
    assert escalate_for_dependency_cascade("portainer", "start") == (False, "")


# --- a frozen-Core edge -> escalation (union path) --------------------

def test_escalates_on_core_context_edge(monkeypatch):
    monkeypatch.setitem(
        guard_mod.COMPONENT_CONTEXTS,
        "web",
        ComponentContext(
            name="web", role="app", criticality="high", dependencies=["db"]
        ),
    )
    esc, reason = escalate_for_dependency_cascade("db", "start")
    assert esc is True
    assert "web" in reason


# --- restricted-class op: governed directly, never escalated here -----

def test_restricted_op_not_escalated_even_with_edge(monkeypatch):
    monkeypatch.setitem(deps_mod.HOMELAB_DEPENDENCIES, "web", ["db"])
    for op in ("restart", "stop", "remove"):
        esc, _ = escalate_for_dependency_cascade("db", op)
        assert esc is False


# --- global disable -------------------------------------------------

def test_escalation_can_be_disabled(monkeypatch):
    monkeypatch.setitem(deps_mod.HOMELAB_DEPENDENCIES, "web", ["db"])
    monkeypatch.setattr(loop_config, "AGENT_DEPENDENCY_ESCALATION", False)
    esc, _ = escalate_for_dependency_cascade("db", "start")
    assert esc is False


# --- end to end through the agent adapter ---------------------------

def test_adapter_forces_approval_on_real_map_edge(monkeypatch):
    import app.agent.adapter as adapter_mod
    from app.agent.authority import authority_store
    from app.agent.contract import AgentIdentity, AgentIntent, AgentProposal
    from app.agent.adapter import propose_and_govern
    from app.core.intelligence.actions.models import ActionType

    monkeypatch.setattr(loop_config, "AGENT_ENABLED", True)
    monkeypatch.setattr(loop_config, "AGENT_DEFAULT_REQUIRES_APPROVAL", False)
    monkeypatch.setitem(deps_mod.HOMELAB_DEPENDENCIES, "web", ["db"])

    captured = {}

    def fake_execute(action, adapter_name=None):
        captured["action"] = action
        return {"status": "manual_approval_required", "approval_id": "a-esc"}

    monkeypatch.setattr(adapter_mod, "execute_governed_action", fake_execute)
    monkeypatch.setattr(adapter_mod, "resolve_adapter_name", lambda: "simulation")
    monkeypatch.setattr(adapter_mod, "record_learning", lambda *a, **k: None)

    authority_store.reset()
    g = authority_store.grant("start", "db", "operator")
    out = propose_and_govern(
        AgentProposal(
            identity=AgentIdentity(agent_id="reference-agent"),
            intent=AgentIntent(
                goal="start db", target="db", mechanism=ActionType.START,
                reason="x", confidence=80,
            ),
            grant_id=g.grant_id,
        )
    )
    authority_store.reset()

    assert captured["action"].requires_approval is True
    assert out.escalated is True
    assert out.decision == "escalated_hold"
