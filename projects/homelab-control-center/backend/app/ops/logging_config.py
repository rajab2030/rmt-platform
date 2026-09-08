"""RMT-PROD P1 (O1) -- structured application logging.

Above-Core / operational. stdlib ``logging`` only -- **no new dependency**.

What this gives the platform:

  * ``configure_logging()`` owns the ``rmt`` logger tree: one line per record
    on **stdout** (systemd -> journald), JSON by default, ``propagate=False``
    so uvicorn's root handler does not also print it. Idempotent -- safe to
    call from the lifespan and from tests.
  * A ``request_id`` :class:`~contextvars.ContextVar` plus
    :class:`RequestContextMiddleware`: every request gets an id (an inbound
    ``X-Request-ID`` is honoured, otherwise a fresh 16-hex id), it is echoed
    on the response, and **one** ``http_request`` line is logged when the
    request finishes (method, path, status, duration_ms, principal). Every
    ``rmt.*`` line emitted while handling that request carries the same
    ``request_id``.
  * :func:`log_event` -- emit one structured line at a governed-lifecycle
    boundary; keyword fields become top-level JSON keys, ``None`` values are
    dropped.

This layer instruments the **above-Core** boundary only. It does not import or
modify ``app/core/**``; Core-internal steps are not logged here, exactly as
O2 / O3 / E3 are scoped.

Config (env, read when ``configure_logging()`` runs -- see
``app/ops/ops_config.py``):

  * ``RMT_LOG_LEVEL`` -- default ``INFO``.
  * ``RMT_LOG_JSON``  -- default ``true``; ``false`` => plain text (local dev).
"""
import contextvars
import json
import logging
import sys
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware

from app.ops import ops_config

# Bound per request by RequestContextMiddleware; "-" outside any request
# (startup reconcile, the CAP-04 loop task, tests calling helpers directly).
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "rmt_request_id", default="-"
)

# LogRecord attributes we must not treat as caller-supplied "extra" fields.
_RESERVED = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}

_LOGGER_ROOT = "rmt"
_configured = False

http_logger = logging.getLogger("rmt.http")


def _extra_fields(record: logging.LogRecord) -> dict:
    return {
        k: v
        for k, v in record.__dict__.items()
        if k not in _RESERVED and not k.startswith("_")
    }


class JsonFormatter(logging.Formatter):
    """One compact JSON object per record; caller ``extra`` fields inline."""

    def format(self, record: logging.LogRecord) -> str:
        out = {
            "ts": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)
            )
            + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        out.update(_extra_fields(record))
        if record.exc_info:
            out["exc"] = self.formatException(record.exc_info)
        return json.dumps(out, default=str, separators=(",", ":"))


class TextFormatter(logging.Formatter):
    """Human-readable fallback for local dev (``RMT_LOG_JSON=false``)."""

    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)-7s %(name)s %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        base = f"[{request_id_var.get()}] {super().format(record)}"
        extra = _extra_fields(record)
        return f"{base} {extra}" if extra else base


def configure_logging() -> None:
    """Idempotently attach one stdout handler to the ``rmt`` logger tree.

    Re-callable: the level is refreshed from the environment each time (so a
    test toggling ``RMT_LOG_LEVEL`` takes effect), but the handler is added
    only once.
    """
    global _configured

    root = logging.getLogger(_LOGGER_ROOT)
    level_name = ops_config.log_level().upper()
    level = getattr(logging, level_name, logging.INFO)
    root.setLevel(level)

    if _configured:
        for handler in root.handlers:
            handler.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(
        JsonFormatter() if ops_config.log_json() else TextFormatter()
    )
    root.addHandler(handler)
    root.propagate = False
    _configured = True


def log_event(
    logger: logging.Logger,
    event: str,
    /,
    level: int = logging.INFO,
    **fields,
) -> None:
    """Emit one structured line for a governed-lifecycle boundary.

    ``event`` is both the message and an ``event`` key. Keyword ``fields``
    become top-level keys; ``None`` values and any key that would collide
    with a ``LogRecord`` attribute are dropped.
    """
    clean = {
        k: v
        for k, v in fields.items()
        if v is not None and k not in _RESERVED and k != "event"
    }
    logger.log(level, event, extra={"event": event, **clean})


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Bind a ``request_id`` for the request and log one ``http_request`` line.

    Outermost middleware (added last), so it also covers CORS pre-flight and
    any error surfaced by an inner layer.
    """

    async def dispatch(self, request, call_next):
        rid = (
            request.headers.get("x-request-id", "").strip()
            or uuid.uuid4().hex[:16]
        )
        token = request_id_var.set(rid)
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.monotonic() - started) * 1000, 1)
            log_event(
                http_logger,
                "http_request",
                level=logging.ERROR,
                method=request.method,
                path=request.url.path,
                status=500,
                duration_ms=duration_ms,
                principal=getattr(request.state, "principal", None),
            )
            request_id_var.reset(token)
            raise

        duration_ms = round((time.monotonic() - started) * 1000, 1)
        response.headers["X-Request-ID"] = rid
        log_event(
            http_logger,
            "http_request",
            level=logging.ERROR if response.status_code >= 500 else logging.INFO,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            principal=getattr(request.state, "principal", None),
        )
        request_id_var.reset(token)
        return response


def _reset_for_tests() -> None:
    """Detach the handler and clear the one-time guard (test hygiene)."""
    global _configured
    root = logging.getLogger(_LOGGER_ROOT)
    for handler in list(root.handlers):
        root.removeHandler(handler)
    root.propagate = True
    _configured = False
