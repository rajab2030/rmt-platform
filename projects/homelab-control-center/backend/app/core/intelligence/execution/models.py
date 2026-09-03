from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.intelligence.verification.models import ExpectedOutcome


class ExecutionStatus(str):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionRequest(BaseModel):
    execution_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    authorization_id: str

    action_id: str

    target: str

    operation: str
    parameters: dict = Field(default_factory=dict)

    risk_level: str | None = None

    expected_outcome: ExpectedOutcome | None = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ExecutionResult(BaseModel):
    execution_id: str

    status: str

    success: bool

    message: str = ""

    output: dict = {}
