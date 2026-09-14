"""RMT-CAP-10 config -- env-overridable, read dynamically.

No ``app/core/**`` dependency. Defaults to disabled; the coding-agent
surface does nothing until ``RMT_CODING_AGENT_ENABLED`` is set.
"""
import os


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def enabled() -> bool:
    """Master switch for the ``/coding-agent/*`` routes. Default off
    (opt-in), same shape as ``RMT_HOMELAB_LOOP_ENABLED`` /
    ``RMT_AGENT_ENABLED`` / ``RMT_OPS_EVIDENCE_ENABLED``. Read dynamically so
    a drop-in edit + restart is enough to turn the surface on."""
    return _env_bool("RMT_CODING_AGENT_ENABLED", False)
