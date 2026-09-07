"""RMT-PROD P0 (S1 + S2-lite) -- operator authentication.

Above-Core / operational. No ``app/core/**`` change.

Every mutating HTTP route depends on :func:`require_operator`. A request must
carry a bearer token (``Authorization: Bearer <t>``) or ``X-API-Key: <t>`` that
maps to a named operator in ``RMT_OPERATOR_TOKENS``. That name -- not a
free-text request field -- is what the handlers pass into the governed
lifecycle, so ``authorized_by`` / ``approved_by`` in the durable evidence is
trustworthy.

Threat model (b): trusted LAN, few operators -- a shared-secret-per-operator
boundary, not full IAM.
"""
import hmac
from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from app.ops import ops_config


@dataclass(frozen=True)
class OperatorIdentity:
    """The authenticated caller. ``local-dev`` when auth is disabled."""

    name: str


def auth_misconfigured() -> bool:
    """True when auth is enabled but no operator tokens are configured."""
    return ops_config.auth_enabled() and not ops_config.operator_tokens()


def _match(presented: str, tokens: dict[str, str]) -> str | None:
    """Constant-time compare against every configured token; return the name."""
    matched: str | None = None
    for configured, name in tokens.items():
        if hmac.compare_digest(presented, configured):
            matched = name
    return matched


def _extract(authorization: str | None, x_api_key: str | None) -> str | None:
    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer" and value.strip():
            return value.strip()
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    return None


def resolve_operator(
    authorization: str | None = None,
    x_api_key: str | None = None,
) -> OperatorIdentity:
    """Core auth check, framework-independent (unit-testable)."""
    if not ops_config.auth_enabled():
        return OperatorIdentity(name="local-dev")

    tokens = ops_config.operator_tokens()
    if not tokens:
        # Enabled but unconfigured: refuse rather than serve an open surface.
        # (The lifespan startup guard normally prevents ever reaching here.)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="operator authentication is misconfigured",
        )

    presented = _extract(authorization, x_api_key)
    if presented is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="operator authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    name = _match(presented, tokens)
    if name is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid operator token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return OperatorIdentity(name=name)


def require_operator(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> OperatorIdentity:
    """FastAPI dependency: the authenticated :class:`OperatorIdentity` or 401."""
    return resolve_operator(authorization=authorization, x_api_key=x_api_key)
