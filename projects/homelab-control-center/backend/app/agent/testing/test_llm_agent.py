"""RMT-CAP-05 (5B) -- LLM-backed agent adapter (run-safe; model always mocked).

No real Ollama call. The LLM only produces text; every proposal still runs the
5A governed path. Fail-closed behaviour (disabled / no proposal / invalid /
parse error / transport error) is the focus.
"""
import json

import pytest
from fastapi.testclient import TestClient

import app.agent.adapter as adapter_mod
import app.agent.api as api_mod
from app.agent import loop_config
from app.agent.authority import authority_store
from app.agent.llm_agent import LlmAgent, LlmProposalError, parse_proposal
from app.core.intelligence.actions.models import ActionType


class _FakeClient:
    def __init__(self, text=None, exc=None):
        self._text = text
        self._exc = exc

    def generate(self, prompt):
        if self._exc is not None:
            raise self._exc
        return self._text


def _ok_json(target="uptime-kuma", mechanism="restart", confidence=80):
    return json.dumps(
        {
            "propose": True,
            "target": target,
            "mechanism": mechanism,
            "reason": "component down",
            "confidence": confidence,
        }
    )


@pytest.fixture(autouse=True)
def _reset():
    authority_store.reset()
    yield
    authority_store.reset()


# --- unit: parse / propose --------------------------------------------

def test_parse_valid_proposal():
    p = parse_proposal(_ok_json(), goal="restore uptime-kuma", grant_id="g1")
    assert p.intent.target == "uptime-kuma"
    assert p.intent.mechanism == ActionType.RESTART
    assert p.intent.confidence == 80
    assert p.identity.agent_id == "llm-agent"
    assert p.grant_id == "g1"


def test_parse_propose_false_is_no_proposal():
    with pytest.raises(LlmProposalError) as e:
        parse_proposal('{"propose": false}', goal="x")
    assert e.value.reason == "no_proposal"


@pytest.mark.parametrize(
    "text,reason",
    [
        (json.dumps({"propose": True, "target": "not-a-service",
                     "mechanism": "restart", "confidence": 50}), "invalid_proposal"),
        (json.dumps({"propose": True, "target": "uptime-kuma",
                     "mechanism": "obliterate", "confidence": 50}), "invalid_proposal"),
        (json.dumps({"propose": True, "target": "uptime-kuma",
                     "mechanism": "restart", "confidence": 250}), "invalid_proposal"),
        (json.dumps({"propose": True, "target": "uptime-kuma",
                     "mechanism": "restart", "confidence": "high"}), "invalid_proposal"),
        ("not json at all", "llm_parse_error"),
        ("{broken json", "llm_parse_error"),
    ],
)
def test_parse_rejects_bad_output(text, reason):
    with pytest.raises(LlmProposalError) as e:
        parse_proposal(text, goal="x")
    assert e.value.reason == reason


def test_propose_wraps_transport_error_as_llm_error():
    agent = LlmAgent(client=_FakeClient(exc=TimeoutError("boom")))
    with pytest.raises(LlmProposalError) as e:
        agent.propose("restore uptime-kuma", [])
    assert e.value.reason == "llm_error"


def test_propose_tolerates_prose_around_json():
    agent = LlmAgent(
        client=_FakeClient(text="Sure! " + _ok_json() + "\nHope that helps.")
    )
    p = agent.propose("restore uptime-kuma", [])
    assert p.intent.target == "uptime-kuma"


# --- endpoint: disabled gate ----------------------------------------

def test_llm_endpoint_disabled_by_default(monkeypatch):
    import app.main as main_app

    assert loop_config.AGENT_LLM_ENABLED is False
    with TestClient(main_app.app) as c:
        r = c.post("/agent/act/llm", json={"goal": "restore uptime-kuma"})
    assert r.status_code == 200
    assert r.json()["decision"] == "llm_disabled"


# --- endpoint: enabled, model + governed path mocked ---------------

@pytest.fixture
def llm_client(monkeypatch):
    monkeypatch.setattr(loop_config, "AGENT_LLM_ENABLED", True)
    monkeypatch.setattr(loop_config, "AGENT_ENABLED", True)

    box = {"model_text": _ok_json(), "governed": {
        "status": "manual_approval_required", "approval_id": "a-llm"}}

    def _fake_agent_factory():
        return LlmAgent(client=_FakeClient(text=box["model_text"]))

    def _fake_execute(action, adapter_name=None):
        box["action"] = action
        return box["governed"]

    monkeypatch.setattr(api_mod, "LlmAgent", _fake_agent_factory)
    monkeypatch.setattr(adapter_mod, "execute_governed_action", _fake_execute)
    monkeypatch.setattr(adapter_mod, "resolve_adapter_name", lambda: "simulation")
    monkeypatch.setattr(adapter_mod, "record_learning", lambda *a, **k: None)

    import app.main as main_app
    with TestClient(main_app.app) as c:
        yield c, box


def test_llm_valid_proposal_runs_governed_path_and_holds(llm_client):
    c, box = llm_client
    g = c.post("/agent/authority/grant", json={
        "operation": "restart", "target": "uptime-kuma",
        "granted_by": "operator"}).json()
    r = c.post("/agent/act/llm", json={
        "goal": "restore uptime-kuma", "grant_id": g["grant_id"]}).json()
    assert r["decision"] == "hold"
    assert r["approval_id"] == "a-llm"
    assert box["action"].requires_approval is True


def test_llm_proposal_without_grant_is_denied(llm_client):
    c, box = llm_client
    r = c.post("/agent/act/llm", json={"goal": "restore uptime-kuma"}).json()
    assert r["decision"] == "no_authority"
    assert "action" not in box  # governed boundary never reached


def test_llm_invalid_target_never_reaches_governance(llm_client):
    c, box = llm_client
    box["model_text"] = _ok_json(target="../etc/passwd")
    r = c.post("/agent/act/llm", json={"goal": "do a bad thing"}).json()
    assert r["decision"] == "invalid_proposal"
    assert "action" not in box


def test_llm_transport_error_is_contained(llm_client):
    c, box = llm_client
    # replace the factory with one whose client raises
    import app.agent.api as _api

    _api.LlmAgent = lambda: LlmAgent(client=_FakeClient(exc=OSError("no ollama")))
    r = c.post("/agent/act/llm", json={"goal": "restore uptime-kuma"}).json()
    assert r["decision"] == "llm_error"


def test_llm_semantic_injection_still_needs_approval(llm_client):
    """A structurally valid but goal-mismatched proposal (the shape a prompt
    injection would take) is NOT rejected by validation -- it is caught by
    human approval. Documents the layered defence."""
    c, box = llm_client
    box["model_text"] = _ok_json(target="portainer", mechanism="restart")
    g = c.post("/agent/authority/grant", json={
        "operation": "restart", "target": "portainer",
        "granted_by": "operator"}).json()
    r = c.post("/agent/act/llm", json={
        "goal": "restore uptime-kuma", "grant_id": g["grant_id"]}).json()
    assert r["decision"] == "hold"
    assert box["action"].requires_approval is True
    assert box["action"].component == "portainer"


def test_status_exposes_llm_block():
    import app.main as main_app

    with TestClient(main_app.app) as c:
        body = c.get("/agent/status").json()
    assert "llm" in body
    assert body["llm"]["enabled"] is False
    assert body["llm"]["model"]
