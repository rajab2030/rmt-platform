from pydantic import BaseModel

from app.core.intelligence.verification.models import ExpectedOutcome


class IntelligenceDecision(BaseModel):
    component: str
    priority: str
    action: str
    reason: str
    confidence: int

    # D4: declared intended outcome as a PROPOSAL only. It conveys no authority;
    # it is carried forward as data toward the C03 expected_outcome field.
    intended_outcome: ExpectedOutcome | None = None

    # D4: preserve the evidence basis used by the intelligence/evaluation layer
    # so decisions are inspectable and evidence-backed.
    evidence: list[str] = []
