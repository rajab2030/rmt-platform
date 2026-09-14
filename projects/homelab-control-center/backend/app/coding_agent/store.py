"""RMT-CAP-10: durable backing for command holds.

Same ``DurableStore`` extension point six frozen-Core evidence stores and
``app/agent/authority.py``'s grants table already use -- a new table in the
same shared evidence database. No ``app/core/**`` change.
"""
from app.coding_agent.models import CommandHold, _now
from app.core.intelligence.durable_store import DurableStore, EVIDENCE_DB_PATH


class CommandHoldStorage(DurableStore):
    _table = "coding_agent_holds"
    _key_field = "hold_id"

    def __init__(self, file_path=None):
        super().__init__(file_path=file_path, model=CommandHold)

    def get_by_id(self, hold_id: str) -> CommandHold | None:
        for h in self._records:
            if h.hold_id == hold_id:
                return h
        return None

    def by_rule(self, risk_rule: str) -> list[CommandHold]:
        return [h for h in self._records if h.risk_rule == risk_rule]

    def pending(self) -> list[CommandHold]:
        return [h for h in self._records if h.status == "pending"]

    def update(self, hold_id: str, **fields) -> CommandHold | None:
        for i, h in enumerate(self._records):
            if h.hold_id == hold_id:
                self._commit_update(i, h.model_copy(update=fields))
                return self._records[i]
        return None


class CommandHoldStore:
    """Thin wrapper around :class:`CommandHoldStorage` so tests can swap
    ``_storage`` for an isolated in-memory instance -- same pattern as
    ``app.agent.authority.AuthorityStore``."""

    def __init__(self, storage: CommandHoldStorage | None = None) -> None:
        self._storage = (
            storage
            if storage is not None
            else CommandHoldStorage(file_path=EVIDENCE_DB_PATH)
        )

    def create(self, hold: CommandHold) -> CommandHold:
        self._storage.save(hold)
        return hold

    def get(self, hold_id: str) -> CommandHold | None:
        return self._storage.get_by_id(hold_id)

    def by_rule(self, risk_rule: str) -> list[CommandHold]:
        return self._storage.by_rule(risk_rule)

    def pending(self) -> list[CommandHold]:
        return self._storage.pending()

    def all(self) -> list[CommandHold]:
        return self._storage.get_all()

    def decide(self, hold_id: str, approved: bool, decided_by: str) -> CommandHold | None:
        return self._storage.update(
            hold_id,
            status="approved" if approved else "rejected",
            decided_at=_now(),
            decided_by=decided_by,
        )


command_hold_store = CommandHoldStore()
