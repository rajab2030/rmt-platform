from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class AuthorizationStatus(str):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExecutionAuthorization(BaseModel):
    authorization_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    action_id: str

    status: str = AuthorizationStatus.PENDING

    authorized_by: str | None = None

    authorization_type: str = "manual"

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    expires_at: datetime | None = None

    reason: str = ""
