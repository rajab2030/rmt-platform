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

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
