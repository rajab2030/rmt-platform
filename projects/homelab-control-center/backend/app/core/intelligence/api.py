from fastapi import APIRouter

from app.core.intelligence.service import (
    calculate_platform_health,
)


router = APIRouter(
    prefix="/intelligence",
    tags=["Intelligence"],
)


@router.get("/health")
def platform_health():

    report = calculate_platform_health()

    return report
