"""RMT-CAP-13 -- append-only SQLite store for explanation attempts.

A separate file (``reasoning.db``): the frozen Core evidence stores are never
written. One row per attempt, *including rejected ones*, so refusals are visible
and every explanation is replayable from its stored bundle/prompt hashes.
"""
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

from app.reasoning import config

_lock = threading.Lock()
_MAX_RAW = 20000

_SCHEMA = """
CREATE TABLE IF NOT EXISTS explanations (
    explanation_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    incident_ref TEXT NOT NULL,
    requested_by TEXT,
    model TEXT,
    host TEXT,
    temperature REAL,
    prompt_sha256 TEXT,
    input_bundle_sha256 TEXT,
    raw_output TEXT,
    validated_output TEXT,
    status TEXT NOT NULL,
    detail TEXT,
    dropped_claims INTEGER NOT NULL DEFAULT 0
)
"""


def _connect() -> sqlite3.Connection:
    path = config.db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    return conn


def _row(r: sqlite3.Row) -> dict:
    d = dict(r)
    validated = d.pop("validated_output")
    d["explanation"] = json.loads(validated) if validated else None
    return d


def append(
    *,
    incident_ref: str,
    status: str,
    requested_by: str | None = None,
    model=None,
    host=None,
    temperature=None,
    prompt_sha256=None,
    input_bundle_sha256=None,
    raw_output=None,
    validated=None,
    detail: str = "",
    dropped_claims: int = 0,
) -> dict:
    explanation_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    with _lock:
        conn = _connect()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO explanations (explanation_id, created_at, incident_ref,"
                    " requested_by, model, host, temperature, prompt_sha256,"
                    " input_bundle_sha256, raw_output, validated_output, status, detail,"
                    " dropped_claims) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        explanation_id,
                        created_at,
                        incident_ref,
                        requested_by,
                        model,
                        host,
                        temperature,
                        prompt_sha256,
                        input_bundle_sha256,
                        (raw_output or "")[:_MAX_RAW] if raw_output is not None else None,
                        json.dumps(validated) if validated is not None else None,
                        status,
                        detail[:500],
                        dropped_claims,
                    ),
                )
            return _row(
                conn.execute(
                    "SELECT * FROM explanations WHERE explanation_id = ?", (explanation_id,)
                ).fetchone()
            )
        finally:
            conn.close()


def list_for(incident_ref: str | None = None, limit: int = 50) -> list[dict]:
    limit = max(1, min(int(limit), 200))
    conn = _connect()
    try:
        if incident_ref:
            rows = conn.execute(
                "SELECT * FROM explanations WHERE incident_ref = ?"
                " ORDER BY created_at DESC LIMIT ?",
                (incident_ref, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM explanations ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_row(r) for r in rows]
    finally:
        conn.close()
