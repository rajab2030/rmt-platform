from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ExecutionAuditRecord(BaseModel):
    """
    Immutable execution evidence record.

    Captures what was executed,
    under which authorization,
    why it was allowed,
    and what result occurred.
    """

    execution_id: str

    action_id: str

    authorization_id: str

    adapter: str

    status: str

    message: str = ""

    risk_level: str = "unknown"

    approval_type: str = "unknown"

    decision_reason: str = ""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
