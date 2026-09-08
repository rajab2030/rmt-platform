"""RMT-PROD P2 (S7) -- per-principal rate limiting on the expensive routes.

Above-Core / operational. No ``app/core/**`` dependency.

``POST /execute`` (a real governed mutation) and the agent ``act`` / ``grant``
routes (a model call and an authority grant) have no throttle beyond the agent
single-use grant. This adds a simple in-process **fixed-window** limiter keyed
by ``(principal, bucket)``: N requests per rolling 60s, then HTTP 429 with
``Retry-After`` until the window rolls.

Deliberately in-process and approximate -- the deployment is a single uvicorn
process (R4 accepted). It is a guard against a stuck client or a runaway agent
loop, not a distributed quota system. ``RMT_RATELIMIT_ENABLED=false`` turns it
off.
"""
import threading
import time

from fastapi import Depends, HTTPException, Request

from app.ops import ops_config
from app.ops.auth import require_operator

_WINDOW_SECONDS = 60
_lock = threading.Lock()
# key -> (window_start_epoch, count)
_hits: dict[tuple[str, str], tuple[float, int]] = {}


def _principal(request: Request) -> str:
    """The authenticated operator name (set by ``require_operator`` on
    ``request.state.principal``); falls back to the peer address."""
    p = getattr(request.state, "principal", None)
    if p:
        return str(p)
    client = request.client
    return client.host if client else "unknown"


def _check(key: tuple[str, str], limit: int) -> None:
    """Raise 429 if ``key`` is over ``limit`` in the current window."""
    now = time.monotonic()
    with _lock:
        start, count = _hits.get(key, (now, 0))
        if now - start >= _WINDOW_SECONDS:
            start, count = now, 0
        count += 1
        _hits[key] = (start, count)
        over = count > limit
        retry_after = max(1, int(_WINDOW_SECONDS - (now - start)))
    if over:
        raise HTTPException(
            status_code=429,
            detail=(
                f"rate limit exceeded: >{limit} requests / {_WINDOW_SECONDS}s "
                f"for this principal on '{key[1]}'"
            ),
            headers={"Retry-After": str(retry_after)},
        )


def rate_limit_execute(request: Request, _op=Depends(require_operator)) -> None:
    """FastAPI dependency for ``POST /execute``. Depends on ``require_operator``
    so ``request.state.principal`` is set before the key is built."""
    if not ops_config.ratelimit_enabled():
        return
    _check((_principal(request), "execute"), ops_config.ratelimit_execute_per_min())


def rate_limit_agent(request: Request, _op=Depends(require_operator)) -> None:
    """FastAPI dependency for the agent state-changing routes."""
    if not ops_config.ratelimit_enabled():
        return
    _check((_principal(request), "agent"), ops_config.ratelimit_agent_per_min())


def reset() -> None:
    """Clear all counters -- for tests and a manual operator reset."""
    with _lock:
        _hits.clear()
