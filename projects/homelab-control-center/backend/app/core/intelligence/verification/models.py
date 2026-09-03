from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class VerificationStatus(str):
    VERIFIED_SUCCESS = "verified_success"
    STATE_MISMATCH = "state_mismatch"
    OBSERVATION_UNAVAILABLE = "observation_unavailable"
    VERIFICATION_FAILURE = "verification_failure"


class ExpectedOutcome(BaseModel):
    """
    Explicit expected outcome of a governed execution.

    This is part of the governed execution intent. It is never derived or
    manufactured by the verifier; it is carried from the ActionRequest
    through authorization and execution.
    """

    target: str = ""

    operation: str = ""

    expected_state: str = ""


class ObservedState(BaseModel):
    """
    Infrastructure-agnostic observed state after execution.

    The observer abstraction produces this; it is not Docker-specific.
    """

    target: str = ""

    state: str = ""

    source: str = "unknown"

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class VerificationResult(BaseModel):
    """
    Post-execution verification evidence.

    Correlated to the actual execution via execution_id. Distinct from the
    execution result: it records whether the observed state matched the
    authorized expected outcome.
    """

    verification_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    execution_id: str

    status: str = VerificationStatus.VERIFICATION_FAILURE

    expected: ExpectedOutcome | None = None

    observed: ObservedState | None = None

    reason: str = ""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
