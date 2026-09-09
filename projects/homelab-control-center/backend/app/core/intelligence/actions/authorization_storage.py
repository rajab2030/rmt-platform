from app.core.intelligence.actions.authorization import ExecutionAuthorization
from app.core.intelligence.durable_store import DurableStore, EVIDENCE_DB_PATH


class AuthorizationStorage(DurableStore):
    """
    Stores execution authorization records, durably backed by the shared SQLite
    evidence database (T0-1; was JSON).
    """

    _table = "authorizations"
    _key_field = "authorization_id"

    def __init__(self, file_path=None):
        super().__init__(
            file_path=file_path,
            model=ExecutionAuthorization,
        )

    def get_by_id(
        self,
        authorization_id: str,
    ) -> ExecutionAuthorization | None:
        for auth in self._records:
            if auth.authorization_id == authorization_id:
                return auth
        return None


execution_authorization_storage = AuthorizationStorage(
    file_path=EVIDENCE_DB_PATH
)
