from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class ExecutionTrace(BaseModel):
    """
    Represents the reasoning chain behind an execution.

    This layer does not execute actions.
    It preserves why execution was allowed,
    what risk was accepted,
    and what outcome occurred.
    """

    trace_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    execution_id: str

    action_id: str

    authorization_id: str

    policy_decision: str

    risk_level: str

    outcome: str

    reason: str = ""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
