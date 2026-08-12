from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class ApprovalDecision(str):
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalRecord(BaseModel):

    approval_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    action_id: str

    decision: str

    approved_by: str

    reason: str = ""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
