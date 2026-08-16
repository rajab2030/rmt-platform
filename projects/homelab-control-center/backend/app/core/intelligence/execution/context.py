from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class ExecutionContext(BaseModel):
    """
    Carries decision context into the execution boundary.

    This object does not execute actions.
    It preserves the intelligence decisions
    that allowed execution to proceed.
    """

    context_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    action_id: str

    authorization_id: str

    risk_level: str

    approval_type: str

    reason: str = ""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
