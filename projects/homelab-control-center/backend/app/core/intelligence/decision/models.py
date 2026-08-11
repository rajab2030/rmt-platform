from pydantic import BaseModel


class IntelligenceDecision(BaseModel):
    component: str
    priority: str
    action: str
    reason: str
    confidence: int
