from pathlib import Path

from app.core.intelligence.verification.models import VerificationResult
from app.core.intelligence.durable_store import DurableStore


class VerificationStorage(DurableStore):
    """
    Durable storage for post-execution verification evidence.

    Backed by the C02 DurableStore JSON mechanism.
    """

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


verification_storage = VerificationStorage(
    file_path=Path(__file__).parent / "verifications.json"
)
