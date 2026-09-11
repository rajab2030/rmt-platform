"""RMT-CAP-06 (C2/D-1) -- GitTagAdapter + registration (run-safe).

Real ``git`` CLI against a disposable ``tmp_path`` repository -- no network,
nothing persistent, nothing touching the project's own ``.git`` or the
configured scratch repo. Fast: no daemon, no image pull, unlike the Docker
e2e test.
"""
import subprocess

import pytest

from app.agent.git_adapter import (
    GitTagAdapter,
    _resolve_repo_path,
    register_git_adapter,
)
from app.core.intelligence.execution.adapters.registry import adapter_registry
from app.core.intelligence.execution.models import ExecutionRequest


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


def test_supports_create_and_remove_only(repo):
    adapter = GitTagAdapter(repo)
    assert adapter.supports(ExecutionRequest(authorization_id="a", action_id="b", target="t", operation="create"))
    assert adapter.supports(ExecutionRequest(authorization_id="a", action_id="b", target="t", operation="remove"))
    assert not adapter.supports(ExecutionRequest(authorization_id="a", action_id="b", target="t", operation="restart"))


def test_create_tag_succeeds_and_is_observable(repo):
    adapter = GitTagAdapter(repo)
    req = ExecutionRequest(
        authorization_id="a", action_id="b", target="proof-1", operation="create"
    )
    result = adapter.execute(req)
    assert result.success is True
    assert result.status == "completed"
    assert _tag_exists(repo, "proof-1")


def test_remove_tag_succeeds(repo):
    adapter = GitTagAdapter(repo)
    adapter.execute(
        ExecutionRequest(authorization_id="a", action_id="b", target="proof-2", operation="create")
    )
    result = adapter.execute(
        ExecutionRequest(authorization_id="a", action_id="b", target="proof-2", operation="remove")
    )
    assert result.success is True
    assert not _tag_exists(repo, "proof-2")


def test_create_duplicate_tag_fails_cleanly(repo):
    adapter = GitTagAdapter(repo)
    req = ExecutionRequest(
        authorization_id="a", action_id="b", target="proof-3", operation="create"
    )
    adapter.execute(req)
    result = adapter.execute(req)
    assert result.success is False
    assert result.status == "failed"


def test_unsupported_operation_fails_cleanly(repo):
    adapter = GitTagAdapter(repo)
    result = adapter.execute(
        ExecutionRequest(authorization_id="a", action_id="b", target="t", operation="stop")
    )
    assert result.success is False


def test_resolve_repo_path_none_when_env_unset(monkeypatch):
    monkeypatch.delenv("RMT_AGENT_GIT_REPO_PATH", raising=False)
    assert _resolve_repo_path() is None


def test_resolve_repo_path_none_when_not_a_git_repo(monkeypatch, tmp_path):
    monkeypatch.setenv("RMT_AGENT_GIT_REPO_PATH", str(tmp_path))
    assert _resolve_repo_path() is None


def test_resolve_repo_path_returns_path_for_real_repo(monkeypatch, repo):
    monkeypatch.setenv("RMT_AGENT_GIT_REPO_PATH", str(repo))
    assert _resolve_repo_path() == repo


def test_register_git_adapter_inert_by_default(monkeypatch):
    monkeypatch.delenv("RMT_AGENT_GIT_REPO_PATH", raising=False)
    registered = register_git_adapter()
    assert registered is False
    assert adapter_registry.get("git") is None


def test_register_git_adapter_registers_when_configured(monkeypatch, repo):
    monkeypatch.setenv("RMT_AGENT_GIT_REPO_PATH", str(repo))
    try:
        registered = register_git_adapter()
        assert registered is True
        assert adapter_registry.get("git") is not None
    finally:
        adapter_registry._adapters.pop("git", None)
