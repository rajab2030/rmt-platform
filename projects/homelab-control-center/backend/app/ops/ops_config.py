"""RMT production-readiness P0 config -- env-overridable, read dynamically.

Above-Core / operational. No ``app/core/**`` dependency. Defaults are the
production-safe setting.

  * ``RMT_AUTH_ENABLED``      -- master switch for operator authentication
                                (default True; ``False`` is a local-dev only
                                escape hatch).
  * ``RMT_OPERATOR_TOKENS``   -- ``name:token`` pairs, comma-separated. When
                                auth is enabled this must be non-empty or the
                                app refuses to start.
  * ``RMT_NOTIFY_WEBHOOK_URL``-- optional held-action notification sink. Unset
                                => notifications are logged only.
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


# --- S1 / S2-lite: operator authentication -----------------------------------

AUTH_ENABLED = _env_bool("RMT_AUTH_ENABLED", True)


def auth_enabled() -> bool:
    """Read dynamically so tests / a drop-in edit take effect without reimport."""
    return _env_bool("RMT_AUTH_ENABLED", True)


def operator_tokens() -> dict[str, str]:
    """Parse ``RMT_OPERATOR_TOKENS`` -> ``{token: operator_name}``.

    Format: ``alice:2f9c...,bob:7d1a...``. Whitespace around entries is
    tolerated; malformed entries (no ``:``, empty name or token) are skipped.
    Read dynamically so rotating a token is just a drop-in edit + restart.
    """
    raw = os.environ.get("RMT_OPERATOR_TOKENS", "") or ""
    out: dict[str, str] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry or ":" not in entry:
            continue
        name, _, token = entry.partition(":")
        name, token = name.strip(), token.strip()
        if name and token:
            out[token] = name
    return out


# --- O2: held-action notifications -----------------------------------------


def notify_webhook_url() -> str | None:
    return os.environ.get("RMT_NOTIFY_WEBHOOK_URL", "").strip() or None


def notify_timeout_seconds() -> int:
    return _env_int("RMT_NOTIFY_TIMEOUT_SECONDS", 5)


def notify_min_interval_seconds() -> int:
    return _env_int("RMT_NOTIFY_MIN_INTERVAL_SECONDS", 60)
