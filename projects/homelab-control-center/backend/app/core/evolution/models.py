from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.intelligence.verification.models import ExpectedOutcome


class ChangeProposal(BaseModel):
    """
    A bounded, explicit platform-evolution change proposal.

    Carries a stable change identity and the declared scope, target,
    operation, and expected outcome. It is a proposal only: it conveys no
    authority and does not execute anything.
    """

    change_id: str = Field(default_factory=lambda: str(uuid4()))
    scope: str
    target: str
    operation: str
    version: str = "0.1.0"
    reason: str = ""
    confidence: int = 100
    requires_approval: bool = False
    expected_outcome: ExpectedOutcome | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class CompatibilityAssessment(BaseModel):
    """
    Read-only scope/compatibility assessment of a change proposal.

    Produced before governance. It never authorizes, approves, executes, or
    mutates any state.
    """

    change_id: str | None = None
    compatible: bool
    reason: str
    scope: str


class ChangeResult(BaseModel):
    """
    Outcome of a governed evolution change, correlated to the change identity
    and the resulting governed lifecycle evidence.
    """

    change_id: str | None = None
    status: str
    action_id: str | None = None
    execution_id: str | None = None
    authorization_id: str | None = None
    verification_status: str | None = None
    verification_reason: str = ""
    message: str = ""
