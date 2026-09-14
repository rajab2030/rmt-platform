"""RMT-CAP-10: record shapes for a held command."""
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


Lean = Literal["approve", "reject", "neutral"]


class EvidenceItem(BaseModel):
    source: str  # "policy_rule" | "history" | "situational"
    claim: str
    leans: Lean


class CommandHold(BaseModel):
    hold_id: str = Field(default_factory=lambda: str(uuid4()))
    command: str
    cwd: str
    reason: str | None = None
    session_id: str | None = None
    risk_rule: str
    risk_level: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    verdict: Lean
    status: Literal["pending", "approved", "rejected"] = "pending"
    created_at: datetime = Field(default_factory=_now)
    decided_at: datetime | None = None
    decided_by: str | None = None
