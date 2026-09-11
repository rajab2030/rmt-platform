"""RMT-CAP-06 (C2/D-1) -- a second, structurally different execution domain:
governed git-tag mutations, proving the frozen Core generalises beyond
Docker/homelab with zero ``app/core/**`` change.

``GitTagAdapter`` implements the same ``ExecutionAdapter`` contract the Core
defines and the Docker adapter already uses -- Core owns the interface and the
registry; domains register their own adapter into it. This is the intended
extension point, not a Core edit.

Scope, deliberately narrow: ``create`` / ``remove`` a tag in one
pre-configured, dedicated scratch repository (``RMT_AGENT_GIT_REPO_PATH``).
The adapter never takes a repo path from the request -- only the path fixed at
registration time -- and shells out to ``git`` with a fixed argument list
(never a shell string), so there is no path or command injection surface.

Registration is conditional and inert by default: unless
``RMT_AGENT_GIT_REPO_PATH`` is set and resolves to a directory containing a
``.git``, the adapter is never registered and ``"git"`` remains an unknown
adapter name -- the same graceful-degradation shape Docker's own conditional
registration (``bootstrap.py::register_default_adapters``) already uses.
"""
import os
import subprocess
from pathlib import Path

from app.core.intelligence.execution.adapters.base import ExecutionAdapter
from app.core.intelligence.execution.adapters.registry import adapter_registry
from app.core.intelligence.execution.models import ExecutionRequest, ExecutionResult


class GitTagAdapter(ExecutionAdapter):
    """Real execution adapter for one pre-configured git repository.

    Dispatches ``create`` / ``remove`` to ``git tag`` in ``repo_path``. Does
    not decide whether execution is allowed -- that stays with the policy /
    risk / approval chain, exactly like every other adapter.
    """

    SUPPORTED_OPERATIONS = {"create", "remove"}

    def __init__(self, repo_path: Path) -> None:
        self._repo_path = repo_path

    def supports(self, request: ExecutionRequest) -> bool:
        return request.operation.lower() in self.SUPPORTED_OPERATIONS

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        operation = request.operation.lower()
        tag_name = request.target

        if operation == "create":
            argv = ["git", "tag", tag_name]
        elif operation == "remove":
            argv = ["git", "tag", "-d", tag_name]
        else:
            return ExecutionResult(
                execution_id=request.execution_id,
                status="failed",
                success=False,
                message=f"Operation {operation} not supported by git adapter",
            )

        try:
            proc = subprocess.run(
                argv,
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception as e:
            return ExecutionResult(
                execution_id=request.execution_id,
                status="failed",
                success=False,
                message=f"Execution failed: {str(e)}",
            )

        if proc.returncode != 0:
            return ExecutionResult(
                execution_id=request.execution_id,
                status="failed",
                success=False,
                message=f"git tag failed: {proc.stderr.strip() or proc.stdout.strip()}",
            )

        return ExecutionResult(
            execution_id=request.execution_id,
            status="completed",
            success=True,
            message=f"Execution completed: {operation} on {tag_name}",
            output={"action": operation, "name": tag_name},
        )


def _resolve_repo_path() -> Path | None:
    raw = os.environ.get("RMT_AGENT_GIT_REPO_PATH", "").strip()
    if not raw:
        return None
    path = Path(raw)
    if not (path / ".git").is_dir():
        return None
    return path


def register_git_adapter() -> bool:
    """Register the ``"git"`` adapter iff a valid repo path is configured.

    Idempotent (re-registering just overwrites the same entry). Returns
    whether it registered, for the caller to log / expose in status.
    """
    repo_path = _resolve_repo_path()
    if repo_path is None:
        return False
    adapter_registry.register("git", GitTagAdapter(repo_path))
    return True
