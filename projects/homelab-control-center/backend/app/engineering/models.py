"""RMT-CAP-02 output/input contracts (above-Core).

All models are read-only data. None carries authority or triggers execution.
"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class ProposedChange(str, Enum):
    """Bounded set of engineering changes CAP-02 can assess (owner-approved)."""

    RESTART = "restart"
    UPDATE = "update"
    REMOVE = "remove"
    REGISTER = "register"
    CONFIG_CHANGE = "config_change"


class ResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    UNKNOWN_COMPONENT = "unknown_component"
    AMBIGUOUS_COMPONENT = "ambiguous_component"


class AffectedComponent(BaseModel):
    """One component identified as affected, with the evidence that supports it."""

    component: str
    relationship: str  # target | dependent | evidence_related | source_related
    evidence_source: str


class RiskFactor(BaseModel):
    """One deterministic engineering-change risk factor and its evidence source."""

    name: str
    value: str
    evidence_source: str


class EngineeringChangeRisk(BaseModel):
    """Separate above-Core engineering-change risk (NOT frozen execution risk)."""

    classification: str  # low | medium | high (derived by explicit rule)
    factors: List[RiskFactor]
    explanation: List[str]


class Recommendation(BaseModel):
    """Thin above-Core engineering-change recommendation (evidence-referenced)."""

    text: str
    evidence_source: str


class EvidenceItem(BaseModel):
    """A traceable claim: what was concluded, from which source, with what detail."""

    claim: str
    source: str
    detail: str


class EngineeringChangeAssessment(BaseModel):
    """Complete read-only result of an engineering change-impact assessment."""

    target: str
    proposed_change: str
    resolution: ResolutionStatus
    resolved_entity: Optional[str] = None
    affected_components: List[AffectedComponent] = []
    risk: Optional[EngineeringChangeRisk] = None
    recommendation: Optional[Recommendation] = None
    evidence: List[EvidenceItem] = []
