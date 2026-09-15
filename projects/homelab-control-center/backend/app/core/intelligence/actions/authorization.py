from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.intelligence.verification.models import ExpectedOutcome


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

    decision_id: str | None = None

    approval_id: str | None = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    expires_at: datetime | None = None

    reason: str = ""

    target: str = ""

    operation: str = ""

    governance_domain: str = "rmt.default"

    adapter_name: str | None = None

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

    expected_outcome: ExpectedOutcome | None = None
