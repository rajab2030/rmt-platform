from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.intelligence.actions.models import (
    ActionRequest,
)


class ApprovalDecision(str):
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
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


class ApprovalHold(BaseModel):
    """
    A governed action held for manual approval.

    Preserves the previously governed action and the adapter it was
    destined for, so a legitimate continuation can resume the lifecycle
    without re-fabricating policy, risk, or authorization.
    """

    approval_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    action_id: str

    action: ActionRequest

    adapter_name: str

    reason: str = ""

    status: ApprovalStatus = ApprovalStatus.PENDING

    approved_by: str | None = None

    expires_at: datetime | None = None

    risk_level: str | None = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
