from enum import Enum

from app.core.intelligence.execution.models import (
    ExecutionRequest,
)


class ExecutionRisk(str, Enum):
    """
    Execution risk classification.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ExecutionRiskAnalyzer:
    """
    Evaluates execution risk.

    This layer does not block execution.
    It only provides risk information.
    """

    def evaluate(
        self,
        request: ExecutionRequest,
    ) -> ExecutionRisk:

        operation = request.operation.lower()

        if operation in {
            "delete",
            "destroy",
            "remove",
            "wipe",
            "format",
        }:
            return ExecutionRisk.HIGH

        if operation in {
            "restart",
            "rebuild",
            "update",
        }:
            return ExecutionRisk.MEDIUM

        return ExecutionRisk.LOW


execution_risk_analyzer = ExecutionRiskAnalyzer()
