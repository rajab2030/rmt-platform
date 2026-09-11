"""RMT-CAP-06 (C2/D-1) -- register the above-Core git-tag observer.

Mirrors ``docker_observers.py`` exactly: a read-only observer, adapted to the
registry's factory signature. It only reads whether a tag exists in the one
configured scratch repository (``app/agent/git_adapter.py``) -- it never
mutates, authorizes, or becomes an execution path.
"""
import subprocess

from app.agent.git_adapter import _resolve_repo_path
from app.core.intelligence.verification.models import ObservedState
from app.ops.verification.registry import register_observer

_GIT_OPERATIONS = ("create", "remove")


def _tag_exists(repo_path, tag_name: str) -> bool:
    proc = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag_name}"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.returncode == 0


def _git_observer_factory(target: str):
    def observe():
        repo_path = _resolve_repo_path()
        if repo_path is None:
            return None
        state = "present" if _tag_exists(repo_path, target) else "absent"
        return ObservedState(target=target, state=state, source="git")

    return observe


def register() -> None:
    for operation in _GIT_OPERATIONS:
        register_observer("git", operation, _git_observer_factory)


register()
