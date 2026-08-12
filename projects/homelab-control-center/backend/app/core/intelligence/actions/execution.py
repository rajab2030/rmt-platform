from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class ExecutionRequest(BaseModel):

    execution_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    authorization_id: str

    action_id: str

    component: str

    action_type: str

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ExecutionResult(BaseModel):

    execution_id: str

    success: bool

    status: str

    output: str = ""

    error: str = ""

    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
