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

    governance_domain: str = "rmt.default"

    assessment_id: str | None = None

    instruction_digest: str | None = None

    adapter_name: str | None = None

    policy_evidence_references: list[str] = Field(default_factory=list)

    risk_evidence_references: list[str] = Field(default_factory=list)

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

    governance_domain: str = "rmt.default"

    assessment_id: str | None = None

    policy_evaluator_id: str | None = None

    policy_evaluator_version: str | None = None

    risk_evaluator_id: str | None = None

    risk_evaluator_version: str | None = None

    canonicalization_version: str | None = None

    instruction_digest: str | None = None

    policy_evidence_references: list[str] = Field(default_factory=list)

    risk_evidence_references: list[str] = Field(default_factory=list)

    uncertainty: str = ""

    recovery_semantics: str = ""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
