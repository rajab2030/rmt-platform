"""RMT-CAP-06 (C2/D-1) -- git-tag observer registration (run-safe).

Real ``git`` CLI against a disposable ``tmp_path`` repository.
"""
import subprocess

import pytest

from app.ops.verification.registry import registered_pairs, resolve_observer
from app.ops.verification.expected import expected_state_for

# Importing this registers the observers (idempotent, side-effecting import).
import app.ops.verification.git_observers  # noqa: F401


@pytest.fixture
def repo(tmp_path, monkeypatch):
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
    monkeypatch.setenv("RMT_AGENT_GIT_REPO_PATH", str(tmp_path))
    return tmp_path


def test_git_pairs_registered():
    assert ("git", "create") in registered_pairs()
    assert ("git", "remove") in registered_pairs()


def test_expected_state_table_has_git_rows():
    assert expected_state_for("git", "create") == "present"
    assert expected_state_for("git", "remove") == "absent"


def test_observer_reports_absent_before_tag_exists(repo):
    observe = resolve_observer("git", "create", "proof-x")
    observed = observe()
    assert observed.state == "absent"
    assert observed.source == "git"


def test_observer_reports_present_after_tag_created(repo):
    subprocess.run(["git", "tag", "proof-y"], cwd=repo, check=True)
    observe = resolve_observer("git", "create", "proof-y")
    observed = observe()
    assert observed.state == "present"


def test_observer_returns_none_when_repo_not_configured(monkeypatch):
    monkeypatch.delenv("RMT_AGENT_GIT_REPO_PATH", raising=False)
    observe = resolve_observer("git", "create", "anything")
    assert observe() is None
