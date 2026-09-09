from app.core.intelligence.verification.models import VerificationResult
from app.core.intelligence.durable_store import DurableStore, EVIDENCE_DB_PATH


class VerificationStorage(DurableStore):
    """
    Durable storage for post-execution verification evidence.

    Backed by the shared SQLite evidence database (T0-1; was the C02 JSON
    DurableStore mechanism).
    """

    _table = "verifications"
    _key_field = "execution_id"

    def __init__(self, file_path=None):
        super().__init__(
            file_path=file_path,
            model=VerificationResult,
        )

    def get_by_execution_id(self, execution_id: str):
        for record in self._records:
            if record.execution_id == execution_id:
                return record
        return None


verification_storage = VerificationStorage(file_path=EVIDENCE_DB_PATH)
