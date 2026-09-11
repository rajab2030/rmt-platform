"""RMT-CAP-05 (5A) -- authority grants (MCR sect 9: capability != authority).

An agent may technically be able to name any operation; it may only act on one
for which it holds a valid grant. Grants are:
  * operation- and target-scoped,
  * time-limited (``AGENT_GRANT_TTL_SECONDS``),
  * single-use (consumed when a proposal is accepted into the governed
    pipeline -- executed or held; not consumed on a pre-boundary denial).

RMT-CAP-08: durably backed (a grant survives a process restart) via the same
``DurableStore`` extension point six frozen-Core evidence stores already use
(``app/core/intelligence/durable_store.py``) -- a new table
(``agent_authority_grants``) in the same shared evidence database. No
``app/core/**`` change: the Core only owns the storage *interface*; this is
the same extension point ``app/ops/verification/index.py`` already uses for
its own above-Core persistence.

This is not a governed mutation path -- a grant just lets the agent submit a
proposal that still passes full policy / risk / approval.
"""
import uuid
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from app.agent import loop_config
from app.core.intelligence.durable_store import DurableStore, EVIDENCE_DB_PATH


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AuthorityGrant(BaseModel):
    grant_id: str
    operation: str
    target: str
    granted_by: str
    expires_at: datetime
    consumed: bool = False
    consumed_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now)

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


class AuthorityGrantStorage(DurableStore):
    """Durable backing for agent authority grants. Same shared evidence DB
    (``data/governance_evidence.db``) six Core stores already write to; a
    new table, no existing table touched."""

    _table = "agent_authority_grants"
    _key_field = "grant_id"

    def __init__(self, file_path=None):
        super().__init__(file_path=file_path, model=AuthorityGrant)

    def get_by_id(self, grant_id) -> AuthorityGrant | None:
        for g in self._records:
            if g.grant_id == grant_id:
                return g
        return None

    def update(self, grant_id, **fields) -> AuthorityGrant | None:
        for i, g in enumerate(self._records):
            if g.grant_id == grant_id:
                self._commit_update(i, g.model_copy(update=fields))
                return self._records[i]
        return None

    def clear(self) -> None:
        """Wipe every grant in this storage. On the real (file-backed)
        singleton this deletes real, durable grants -- tests must construct
        an isolated ``AuthorityGrantStorage(file_path=None)`` instead of
        calling this on the shared one."""
        self._replace_records([])


class AuthorityStore:
    def __init__(self, storage: AuthorityGrantStorage | None = None) -> None:
        self._storage = (
            storage
            if storage is not None
            else AuthorityGrantStorage(file_path=EVIDENCE_DB_PATH)
        )

    def reset(self) -> None:
        self._storage.clear()

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
        self._storage.save(g)
        return g

    def check(self, grant_id, operation: str, target: str):
        """Return ``(ok: bool, reason: str)``. Does not consume."""
        g = self._storage.get_by_id(grant_id) if grant_id else None
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
        g = self._storage.get_by_id(grant_id)
        if g is None or g.consumed:
            return False
        self._storage.update(grant_id, consumed=True, consumed_at=_now())
        return True

    def get(self, grant_id):
        return self._storage.get_by_id(grant_id)

    def list_active(self):
        now = _now()
        return [
            g
            for g in self._storage.get_all()
            if not g.consumed and g.expires_at > now
        ]


authority_store = AuthorityStore()
