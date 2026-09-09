from app.core.intelligence.actions.approval import (
    ApprovalHold,
    ApprovalRecord,
)
from app.core.intelligence.durable_store import DurableStore, EVIDENCE_DB_PATH


class ApprovalHoldStorage(DurableStore):
    """
    Stores governed actions held for manual approval, durably backed by the
    shared SQLite evidence database (T0-1; was JSON).
    """

    _table = "approval_holds"
    _key_field = "approval_id"

    def __init__(self, file_path=None):
        super().__init__(
            file_path=file_path,
            model=ApprovalHold,
        )

    def get_by_id(
        self,
        approval_id: str,
    ) -> ApprovalHold | None:
        for hold in self._records:
            if hold.approval_id == approval_id:
                return hold
        return None

    def update(
        self,
        approval_id: str,
        **fields,
    ) -> ApprovalHold | None:
        for i, hold in enumerate(self._records):
            if hold.approval_id == approval_id:
                self._commit_update(i, hold.model_copy(update=fields))
                return self._records[i]
        return None


class ApprovalRecordStorage(DurableStore):
    """
    Stores approval decision records, durably backed by the shared SQLite
    evidence database (T0-1; was JSON).
    """

    _table = "approval_records"
    _key_field = "approval_id"

    def __init__(self, file_path=None):
        super().__init__(
            file_path=file_path,
            model=ApprovalRecord,
        )

    def get_by_id(
        self,
        approval_id: str,
    ) -> ApprovalRecord | None:
        for rec in self._records:
            if rec.approval_id == approval_id:
                return rec
        return None

    def update(
        self,
        approval_id: str,
        **fields,
    ) -> ApprovalRecord | None:
        for i, rec in enumerate(self._records):
            if rec.approval_id == approval_id:
                self._commit_update(i, rec.model_copy(update=fields))
                return self._records[i]
        return None


approval_hold_storage = ApprovalHoldStorage(file_path=EVIDENCE_DB_PATH)

approval_record_storage = ApprovalRecordStorage(file_path=EVIDENCE_DB_PATH)
