"""RMT production-readiness P0 config -- env-overridable, read dynamically.

Above-Core / operational. No ``app/core/**`` dependency. Defaults are the
production-safe setting.

  * ``RMT_AUTH_ENABLED``      -- master switch for operator authentication
                                (default True; ``False`` is a local-dev only
                                escape hatch).
  * ``RMT_OPERATOR_TOKENS``   -- ``name:token`` pairs, comma-separated. When
                                auth is enabled this must be non-empty or the
                                app refuses to start. Under systemd, prefer a
                                ``LoadCredential=RMT_OPERATOR_TOKENS:<path>``
                                unit directive over ``Environment=`` --
                                ``systemctl show -p Environment`` exposes a
                                unit's plain environment (including secrets
                                set via ``Environment=`` in a drop-in) to any
                                local user, not just root, while
                                ``LoadCredential=`` only exposes the source
                                *path* the same way -- the token file itself
                                stays root-only. When ``$CREDENTIALS_DIRECTORY``
                                is set (systemd sets it automatically for a
                                unit using ``LoadCredential=``), the token
                                list is read from
                                ``$CREDENTIALS_DIRECTORY/RMT_OPERATOR_TOKENS``
                                instead of the environment variable.
  * ``RMT_NOTIFY_WEBHOOK_URL``-- optional held-action notification sink. Unset
                                => notifications are logged only.
  * ``RMT_AUTH_SEPARATION``   -- S3: enforce approver != grantor for
                                agent-originated approval holds (default False;
                                opt-in).
  * ``RMT_EVIDENCE_RETENTION_DAYS`` -- E4: on startup, archive evidence records
                                older than this out of the live JSON stores
                                into ``<name>.archive.jsonl`` (default 90;
                                ``<= 0`` disables).
  * ``RMT_HOMELAB_DEPENDENCIES`` -- T1-2: operator-declared inter-component
                                dependency edges (``"web:db;api:db,cache"``),
                                unioned into the static all-independent homelab
                                map; a declared edge activates T13 escalation.
                                Unset => no edges.
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


def _operator_tokens_raw() -> str:
    """The raw ``name:token,...`` string, preferring a systemd
    ``LoadCredential=RMT_OPERATOR_TOKENS:<path>`` file (via
    ``$CREDENTIALS_DIRECTORY``) over the ``RMT_OPERATOR_TOKENS`` environment
    variable, so the token list never sits in a unit's plain environment
    (``systemctl show -p Environment`` is readable by any local user, not
    just root). Falls back to the env var when no credentials directory is
    set (local dev, tests, non-systemd deployments)."""
    creds_dir = os.environ.get("CREDENTIALS_DIRECTORY", "").strip()
    if creds_dir:
        try:
            with open(os.path.join(creds_dir, "RMT_OPERATOR_TOKENS")) as f:
                return f.read()
        except OSError:
            pass
    return os.environ.get("RMT_OPERATOR_TOKENS", "") or ""


def operator_tokens() -> dict[str, str]:
    """Parse ``RMT_OPERATOR_TOKENS`` -> ``{token: operator_name}``.

    Format: ``alice:2f9c...,bob:7d1a...``. Whitespace around entries is
    tolerated; malformed entries (no ``:``, empty name or token) are skipped.
    Read dynamically so rotating a token is just a drop-in edit + restart.
    """
    raw = _operator_tokens_raw()
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


# --- T1-2: operator-declarable homelab dependency edges --------------------


def homelab_dependency_edges() -> dict[str, list[str]]:
    """Parse ``RMT_HOMELAB_DEPENDENCIES`` -> ``{component: [dep, ...]}``.

    Format: ``"web:db,cache;api:db"`` -- ``;``-separated groups, each
    ``component:dep1,dep2``. Whitespace tolerated; a group with no ``:``, an
    empty component, or no non-empty deps is skipped; duplicate deps collapse.
    Unset / empty -> ``{}``.

    Read dynamically so declaring a real edge is a drop-in edit + restart, like
    every other knob. ``app/homelab/dependencies.py`` unions this into the
    static all-independent map; a declared edge activates the T13
    dependency-cascade escalation guard (``app/agent/dependency_guard.py``).
    """
    raw = os.environ.get("RMT_HOMELAB_DEPENDENCIES", "").strip()
    if not raw:
        return {}
    out: dict[str, list[str]] = {}
    for group in raw.split(";"):
        group = group.strip()
        if not group or ":" not in group:
            continue
        comp, _, deps_raw = group.partition(":")
        comp = comp.strip()
        deps = [d.strip() for d in deps_raw.split(",") if d.strip()]
        if not comp or not deps:
            continue
        bucket = out.setdefault(comp, [])
        for d in deps:
            if d not in bucket:
                bucket.append(d)
    return out


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


def notify_format() -> str:
    """T1-4: payload shaping for the notification webhook.

      * ``generic`` (default) -- today's JSON object, unchanged.
      * ``slack``             -- ``{"text": "<one-line summary>"}`` (Slack /
                                Mattermost incoming-webhook compatible).
      * ``ntfy``              -- plain-text body + ``Title`` / ``Priority`` /
                                ``Tags`` headers (ntfy topic URL).

    Unknown value falls back to ``generic``. Read dynamically."""
    v = os.environ.get("RMT_NOTIFY_FORMAT", "generic").strip().lower()
    return v if v in ("generic", "slack", "ntfy") else "generic"


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
