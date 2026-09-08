"""RMT-PROD P2 (D6) -- runtime prerequisite / environment-parity reporting.

Above-Core / operational. No ``app/core/**`` dependency.

The platform's behaviour changes with two host capabilities that are easy to
get wrong on a new box:

  * **Docker socket reachability** -- the execution adapter resolves to the real
    ``docker`` adapter only when the daemon is reachable; otherwise it silently
    falls back to the safe ``simulation`` adapter. A production host that was
    meant to drive real containers but comes up in simulation is a
    misconfiguration, not a safe default.
  * **git presence** -- ``/platform/state`` needs a working ``git``.

``runtime_status()`` makes both observable (surfaced on ``GET /health``), and
``warn_on_capability_mismatch()`` logs a WARNING at startup when the configured
engine cannot actually be provided.
"""
import shutil

from app.core.configuration.settings import load_settings
from app.core.intelligence.execution.adapters.registry import adapter_registry
from app.docker_api import docker_available


def resolved_adapter() -> str:
    """The adapter that would actually run a governed action right now -- the
    configured engine if its adapter is registered, else ``simulation``.
    Mirrors ``app.main._resolve_adapter_name`` without importing it."""
    engine = load_settings().runtime.engine
    if adapter_registry.get(engine) is not None:
        return engine
    return "simulation"


def runtime_status() -> dict:
    """A snapshot of the capability-sensitive runtime state."""
    configured = load_settings().runtime.engine
    resolved = resolved_adapter()
    docker_ok = docker_available()
    git_ok = shutil.which("git") is not None

    degraded: list[str] = []
    if configured != resolved:
        degraded.append(
            f"configured engine '{configured}' unavailable -- running '{resolved}'"
        )
    if not git_ok:
        degraded.append("git not on PATH -- /platform/state will fail")

    return {
        "configured_engine": configured,
        "resolved_adapter": resolved,
        "docker_available": docker_ok,
        "git_available": git_ok,
        "adapter_degraded": bool(degraded),
        "notes": degraded,
    }


def warn_on_capability_mismatch(logger) -> dict:
    """Log one WARNING per missing capability at startup. Returns the status
    dict so the caller can log/inspect it. Never raises."""
    try:
        status = runtime_status()
    except Exception:  # pragma: no cover -- diagnostics must never block startup
        return {}
    for note in status["notes"]:
        logger.warning("runtime capability mismatch: %s", note)
    return status
