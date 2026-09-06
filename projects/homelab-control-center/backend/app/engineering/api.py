"""RMT-CAP-02 read-only HTTP surface (above-Core).

GET only. No mutation, no execution, no authorization. Returns the
evidence-backed EngineeringChangeAssessment.
"""
from fastapi import APIRouter, HTTPException

from app.engineering.models import ProposedChange
from app.engineering.service import assess_engineering_change


router = APIRouter(
    prefix="/engineering",
    tags=["Engineering"],
)


@router.get("/change-impact")
def change_impact(target: str, change: str):
    """Read-only engineering change-impact & risk assessment for a target."""
    valid = {c.value for c in ProposedChange}
    if change not in valid:
        raise HTTPException(
            status_code=422,
            detail=f"proposed_change must be one of: {sorted(valid)}",
        )
    return assess_engineering_change(target, change)
