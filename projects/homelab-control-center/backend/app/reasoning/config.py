"""RMT-CAP-13 config -- env-overridable, read dynamically, safe defaults.

No ``app/core/configuration/**`` change and no ``ops_config`` edit. Everything
defaults to disabled. The LLM backend settings (model / host / timeout / token
budget) are shared with CAP-05 5B via ``app.agent.loop_config`` so there is one
place to point RMT at a model.
"""
import os
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        return default


def reasoning_enabled() -> bool:
    """Master switch for ``/ops/reasoning/*``. Default off (opt-in)."""
    return _env_bool("RMT_REASONING_ENABLED", False)


def max_prior_failures() -> int:
    """How many prior failures of the same component go into one prompt
    (proposal section 9.5; default 5)."""
    return _env_int("RMT_REASONING_MAX_FAILURES", 5)


def field_max_chars() -> int:
    """Every string field in an evidence record is truncated to this length
    before it reaches the model (bounds cost and the injection surface)."""
    return _env_int("RMT_REASONING_FIELD_MAX_CHARS", 300, minimum=20)


def db_path() -> Path:
    configured = os.environ.get("RMT_REASONING_DB")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "data" / "reasoning.db"
