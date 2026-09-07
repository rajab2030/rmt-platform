"""RMT-CAP-05 (5A) -- authority grants (MCR sect 9: capability != authority).

An agent may technically be able to name any operation; it may only act on one
for which it holds a valid grant. Grants are:
  * operation- and target-scoped,
  * time-limited (``AGENT_GRANT_TTL_SECONDS``),
  * single-use (consumed when a proposal is accepted into the governed
    pipeline -- executed or held; not consumed on a pre-boundary denial).

In-memory only. This is not a governed mutation path -- a grant just lets the
agent submit a proposal that still passes full policy / risk / approval.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.agent import loop_config


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AuthorityGrant:
    grant_id: str
    operation: str
    target: str
    granted_by: str
    expires_at: datetime
    consumed: bool = False
    consumed_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)

    def as_dict(self) -> dict:
        return {
            "grant_id": self.grant_id,
            "operation": self.operation,
            "target": self.target,
            "granted_by": self.granted_by,
            "expires_at": self.expires_at.isoformat(),
            "consumed": self.consumed,
            "consumed_at": (
                self.consumed_at.isoformat() if self.consumed_at else None
            ),
        }


class AuthorityStore:
    def __init__(self) -> None:
        self._grants: dict[str, AuthorityGrant] = {}

    def reset(self) -> None:
        self._grants = {}

    def grant(
        self,
        operation: str,
        target: str,
        granted_by: str,
        ttl_seconds: int | None = None,
    ) -> AuthorityGrant:
        ttl = (
            loop_config.AGENT_GRANT_TTL_SECONDS
            if ttl_seconds is None
            else ttl_seconds
        )
        g = AuthorityGrant(
            grant_id=uuid.uuid4().hex[:12],
            operation=operation,
            target=target,
            granted_by=granted_by,
            expires_at=_now() + timedelta(seconds=ttl),
        )
        self._grants[g.grant_id] = g
        return g

    def check(self, grant_id, operation: str, target: str):
        """Return ``(ok: bool, reason: str)``. Does not consume."""
        g = self._grants.get(grant_id) if grant_id else None
        if g is None:
            return False, "no_grant"
        if g.consumed:
            return False, "grant_consumed"
        if g.expires_at <= _now():
            return False, "grant_expired"
        if g.operation != operation or g.target != target:
            return False, "grant_scope_mismatch"
        return True, "ok"

    def consume(self, grant_id) -> bool:
        g = self._grants.get(grant_id)
        if g is None or g.consumed:
            return False
        g.consumed = True
        g.consumed_at = _now()
        return True

    def get(self, grant_id):
        return self._grants.get(grant_id)

    def list_active(self):
        now = _now()
        return [
            g
            for g in self._grants.values()
            if not g.consumed and g.expires_at > now
        ]


authority_store = AuthorityStore()
