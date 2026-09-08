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
  * ``RMT_AUTH_SEPARATION``   -- S3: enforce approver != grantor for
                                agent-originated approval holds (default False;
                                opt-in).
  * ``RMT_EVIDENCE_RETENTION_DAYS`` -- E4: on startup, archive evidence records
                                older than this out of the live JSON stores
                                into ``<name>.archive.jsonl`` (default 90;
                                ``<= 0`` disables).
  * ``RMT_LOG_LEVEL``        -- O1: level for the ``rmt`` logger tree
                                (default ``INFO``).
  * ``RMT_LOG_JSON``         -- O1: ``true`` (default) => one JSON line per
                                record; ``false`` => plain text (local dev).
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


# --- S3: separation of duties --------------------------------------------------


def separation_enabled() -> bool:
    """Enforce approver != grantor / proposer for agent-originated approval
    holds. Default off (opt-in); read dynamically so a drop-in edit + restart
    is enough."""
    return _env_bool("RMT_AUTH_SEPARATION", False)


# --- E4: evidence retention -------------------------------------------------


def evidence_retention_days() -> int:
    """Age (days) past which an evidence record is archived out of the live
    store on startup. Default 90; ``<= 0`` disables archival. Dynamic."""
    return _env_int("RMT_EVIDENCE_RETENTION_DAYS", 90)


# --- O2: held-action notifications -----------------------------------------


def notify_webhook_url() -> str | None:
    return os.environ.get("RMT_NOTIFY_WEBHOOK_URL", "").strip() or None


def notify_timeout_seconds() -> int:
    return _env_int("RMT_NOTIFY_TIMEOUT_SECONDS", 5)


def notify_min_interval_seconds() -> int:
    return _env_int("RMT_NOTIFY_MIN_INTERVAL_SECONDS", 60)


# --- O1: structured logging ----------------------------------------------------


def log_level() -> str:
    """Level name for the ``rmt`` logger tree. Default ``INFO``. Dynamic."""
    return os.environ.get("RMT_LOG_LEVEL", "INFO").strip() or "INFO"


def log_json() -> bool:
    """One JSON line per record (default) vs. plain text for local dev."""
    return _env_bool("RMT_LOG_JSON", True)


# --- S5: CORS ----------------------------------------------------------------

# The API exposes only GET (reads) and POST (governed mutations); no browser
# client needs anything else. Preflight OPTIONS is handled by the middleware.
CORS_ALLOW_METHODS = ["GET", "POST"]

# The only request headers a browser client sends: the two auth schemes, a JSON
# body content type, and the O1 correlation id.
CORS_ALLOW_HEADERS = ["Authorization", "X-API-Key", "Content-Type", "X-Request-ID"]


def cors_origins() -> list[str]:
    """Browser origins allowed to call the API, from ``RMT_CORS_ORIGINS``
    (comma-separated). Default: the local Vite dev origin only. Set this in a
    drop-in to the deployed frontend's origin(s). Read dynamically."""
    raw = os.environ.get("RMT_CORS_ORIGINS", "").strip()
    if not raw:
        return ["http://localhost:5173"]
    return [o.strip() for o in raw.split(",") if o.strip()]


# --- S7: abuse / rate protection on the expensive mutating routes -----------


def ratelimit_enabled() -> bool:
    """Per-principal fixed-window rate limiting on ``/execute`` and the agent
    ``act`` / ``grant`` routes. Default on; ``RMT_RATELIMIT_ENABLED=false``
    disables it entirely. Dynamic."""
    return _env_bool("RMT_RATELIMIT_ENABLED", True)


def ratelimit_execute_per_min() -> int:
    """Max ``POST /execute`` calls per operator per 60s (default 30)."""
    return _env_int("RMT_RATELIMIT_EXECUTE_PER_MINUTE", 30)


def ratelimit_agent_per_min() -> int:
    """Max agent state-changing calls (``/agent/act``, ``/agent/act/llm``,
    ``/agent/authority/grant``) per operator per 60s (default 20)."""
    return _env_int("RMT_RATELIMIT_AGENT_PER_MINUTE", 20)
