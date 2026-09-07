"""RMT-CAP-05 (5A) config -- env-overridable constants, read dynamically.

No ``app/core/configuration/**`` change. Everything defaults to the safe /
disabled setting; the agent surface does nothing until ``RMT_AGENT_ENABLED``.
"""
import os


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


# Master switch. `propose_and_govern` is a no-op ("disabled") until this is set.
AGENT_ENABLED = _env_bool("RMT_AGENT_ENABLED", False)

# TTL for an authority grant (seconds). Grants are also single-use.
AGENT_GRANT_TTL_SECONDS = _env_int("RMT_AGENT_GRANT_TTL_SECONDS", 300)

# CAP-04 safe-enablement envelope: every state-changing agent action is
# human-approval-gated. Kept as a flag so a deliberately widened future
# envelope can lower it -- at which point the T13 escalation below becomes
# load-bearing.
AGENT_DEFAULT_REQUIRES_APPROVAL = _env_bool(
    "RMT_AGENT_DEFAULT_REQUIRES_APPROVAL", True
)

# T13 closure: force human approval when an allowed-class operation would
# achieve a restricted effect on another component via known dependencies.
AGENT_DEPENDENCY_ESCALATION = _env_bool(
    "RMT_AGENT_DEPENDENCY_ESCALATION", True
)

# --- 5B: LLM-backed agent adapter (opt-in; separate from AGENT_ENABLED) ---
# The LLM only *proposes*; every proposal still passes 5A authority + T13 +
# governance + human approval. Disabled by default.
AGENT_LLM_ENABLED = _env_bool("RMT_AGENT_LLM_ENABLED", False)
AGENT_LLM_MODEL = os.environ.get(
    "RMT_AGENT_LLM_MODEL", "deepseek-v4-flash:cloud"
)
AGENT_LLM_HOST = os.environ.get(
    "RMT_AGENT_LLM_HOST", "http://127.0.0.1:11434"
)
AGENT_LLM_TIMEOUT_SECONDS = _env_int("RMT_AGENT_LLM_TIMEOUT_SECONDS", 60)
AGENT_LLM_MAX_TOKENS = _env_int("RMT_AGENT_LLM_MAX_TOKENS", 400)
AGENT_LLM_TEMPERATURE = _env_float("RMT_AGENT_LLM_TEMPERATURE", 0.1)
