"""RMT-CAP-10 -- coding-agent command governance.

Covers: risk-rule matching, evidence assembly + verdict logic (review.py),
and the HTTP surface (isolated store, auth required, auto-allow vs. hold,
decide updates status/decided_by from the authenticated operator).
"""
import pytest
from fastapi.testclient import TestClient

from app.coding_agent import api as coding_agent_api
from app.coding_agent import config as coding_agent_config
from app.coding_agent import risk_rules
from app.coding_agent.models import EvidenceItem
from app.coding_agent.review import assess
from app.coding_agent.store import CommandHoldStorage, command_hold_store
import app.main as main_module


@pytest.fixture(autouse=True)
def _isolate_store(monkeypatch):
    monkeypatch.setattr(command_hold_store, "_storage", CommandHoldStorage(file_path=None))


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(coding_agent_config, "enabled", lambda: True)


@pytest.fixture
def client():
    return TestClient(main_module.app)


# --- risk_rules.py -----------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "git push origin main --force",
        "git push origin main -f",
        "git push --force-with-lease origin main",
    ],
)
def test_git_force_push_matches(command):
    match = risk_rules.classify(command)
    assert match is not None
    assert match.rule.name == "git-force-push"


def test_git_push_without_force_does_not_match():
    assert risk_rules.classify("git push origin main") is None


def test_git_hard_reset_matches():
    match = risk_rules.classify("git reset --hard HEAD~1")
    assert match is not None
    assert match.rule.name == "git-hard-reset"


def test_git_soft_reset_does_not_match():
    assert risk_rules.classify("git reset --soft HEAD~1") is None


def test_recursive_delete_matches():
    match = risk_rules.classify("rm -rf ./build")
    assert match is not None
    assert match.rule.name == "recursive-delete"


def test_recursive_delete_confined_to_tmp_does_not_match():
    assert risk_rules.classify("rm -rf /tmp/scratch/foo") is None


def test_plain_rm_does_not_match():
    assert risk_rules.classify("rm ./file.txt") is None


def test_sudo_matches():
    match = risk_rules.classify("sudo systemctl status nginx")
    assert match is not None
    assert match.rule.name == "sudo"


def test_service_restart_matches():
    match = risk_rules.classify("systemctl restart uptime-kuma")
    assert match is not None
    assert match.rule.name == "service-restart"


def test_unrelated_command_does_not_match():
    assert risk_rules.classify("ls -la") is None


# --- review.py ---------------------------------------------------------------


def _no_signal_evidence():
    # A medium-risk rule item leans "neutral"; no history, no situational
    # signal -- nothing leans approve or reject.
    return [EvidenceItem(source="policy_rule", claim="matched", leans="neutral")]


def test_verdict_no_signal_defaults_to_reject():
    from app.coding_agent.review import _verdict

    assert _verdict(_no_signal_evidence()) == "reject"


def test_verdict_reject_leaning_evidence_rejects():
    from app.coding_agent.review import _verdict

    evidence = [
        EvidenceItem(source="policy_rule", claim="matched", leans="neutral"),
        EvidenceItem(source="situational", claim="dirty tree", leans="reject"),
    ]
    assert _verdict(evidence) == "reject"


def test_verdict_approve_leaning_with_no_reject_signal_approves():
    from app.coding_agent.review import _verdict

    evidence = [
        EvidenceItem(source="policy_rule", claim="matched", leans="neutral"),
        EvidenceItem(source="history", claim="3 approved / 0 rejected", leans="approve"),
    ]
    assert _verdict(evidence) == "approve"


def test_verdict_mixed_reject_wins():
    from app.coding_agent.review import _verdict

    evidence = [
        EvidenceItem(source="policy_rule", claim="matched", leans="reject"),
        EvidenceItem(source="history", claim="3 approved / 0 rejected", leans="approve"),
    ]
    assert _verdict(evidence) == "reject"


def test_assess_high_risk_rule_with_no_repo_signal_defaults_reject(tmp_path):
    match = risk_rules.classify("git reset --hard HEAD~1")
    evidence, verdict = assess(match.rule, str(tmp_path))
    assert verdict == "reject"
    assert any(e.source == "policy_rule" and e.leans == "reject" for e in evidence)


def test_assess_history_evidence_included(tmp_path):
    from app.coding_agent.models import CommandHold

    match = risk_rules.classify("sudo reboot")
    # Seed two approved decisions for this rule.
    for _ in range(2):
        hold = CommandHold(
            command="sudo reboot",
            cwd=str(tmp_path),
            risk_rule=match.rule.name,
            risk_level=match.rule.risk_level,
            verdict="approve",
            status="approved",
        )
        command_hold_store.create(hold)

    evidence, verdict = assess(match.rule, str(tmp_path))
    history_items = [e for e in evidence if e.source == "history"]
    assert len(history_items) == 1
    assert history_items[0].leans == "approve"
    assert verdict == "approve"


# --- api.py --------------------------------------------------------------


def test_routes_disabled_by_default(client):
    resp = client.post(
        "/coding-agent/propose",
        json={"command": "git reset --hard", "cwd": "/tmp"},
    )
    assert resp.status_code == 503


def test_propose_auto_allows_non_matching_command(client, enabled):
    resp = client.post(
        "/coding-agent/propose",
        json={"command": "ls -la", "cwd": "/tmp"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"decision": "auto_allow"}
    assert command_hold_store.all() == []


def test_propose_matching_command_creates_hold(client, enabled, tmp_path):
    resp = client.post(
        "/coding-agent/propose",
        json={"command": "git reset --hard", "cwd": str(tmp_path)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "hold"
    assert body["review"]["risk_rule"] == "git-hard-reset"
    assert len(body["review"]["evidence"]) >= 1

    holds = command_hold_store.all()
    assert len(holds) == 1
    assert holds[0].status == "pending"


def test_decide_approve_updates_status_and_decided_by(client, enabled, tmp_path):
    propose_resp = client.post(
        "/coding-agent/propose",
        json={"command": "git reset --hard", "cwd": str(tmp_path)},
    )
    hold_id = propose_resp.json()["hold_id"]

    decide_resp = client.post(
        "/coding-agent/decide", json={"hold_id": hold_id, "approved": True}
    )
    assert decide_resp.status_code == 200
    decided = decide_resp.json()
    assert decided["status"] == "approved"
    assert decided["decided_by"] == "local-dev"  # auth disabled in the suite


def test_decide_rejects_unknown_hold(client, enabled):
    resp = client.post(
        "/coding-agent/decide", json={"hold_id": "does-not-exist", "approved": True}
    )
    assert resp.status_code == 404


def test_propose_matching_command_notifies(client, enabled, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        coding_agent_api, "notify_held", lambda **kwargs: calls.append(kwargs)
    )

    resp = client.post(
        "/coding-agent/propose",
        json={"command": "git reset --hard", "cwd": str(tmp_path)},
    )
    hold_id = resp.json()["hold_id"]

    assert len(calls) == 1
    assert calls[0]["kind"] == "coding_agent_command"
    assert calls[0]["component"] == "git-hard-reset"
    assert calls[0]["approval_id"] == hold_id


def test_propose_auto_allow_does_not_notify(client, enabled, monkeypatch):
    calls = []
    monkeypatch.setattr(
        coding_agent_api, "notify_held", lambda **kwargs: calls.append(kwargs)
    )

    client.post("/coding-agent/propose", json={"command": "ls -la", "cwd": "/tmp"})

    assert calls == []


def test_decide_twice_conflicts(client, enabled, tmp_path):
    propose_resp = client.post(
        "/coding-agent/propose",
        json={"command": "git reset --hard", "cwd": str(tmp_path)},
    )
    hold_id = propose_resp.json()["hold_id"]
    client.post("/coding-agent/decide", json={"hold_id": hold_id, "approved": True})

    resp = client.post(
        "/coding-agent/decide", json={"hold_id": hold_id, "approved": False}
    )
    assert resp.status_code == 409


def test_list_holds_filters_by_status(client, enabled, tmp_path):
    propose_resp = client.post(
        "/coding-agent/propose",
        json={"command": "git reset --hard", "cwd": str(tmp_path)},
    )
    hold_id = propose_resp.json()["hold_id"]
    client.post("/coding-agent/decide", json={"hold_id": hold_id, "approved": True})

    pending = client.get("/coding-agent/holds", params={"status": "pending"}).json()
    approved = client.get("/coding-agent/holds", params={"status": "approved"}).json()
    assert pending["holds"] == []
    assert len(approved["holds"]) == 1


def test_decide_requires_auth(client, enabled, monkeypatch):
    monkeypatch.setenv("RMT_AUTH_ENABLED", "true")
    monkeypatch.setenv("RMT_OPERATOR_TOKENS", "alice:secret")

    resp = client.post(
        "/coding-agent/decide", json={"hold_id": "whatever", "approved": True}
    )
    assert resp.status_code == 401
