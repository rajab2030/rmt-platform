from enum import Enum

from app.core.intelligence.execution.models import (
    ExecutionRequest,
)


class PolicyDecision(str, Enum):
    """
    Result of execution policy evaluation.
    """

    ALLOW = "allow"
    DENY = "deny"
    REQUIRES_APPROVAL = "requires_approval"


class ExecutionPolicy:
    """
    Evaluates whether an execution request is allowed.

    This layer does not execute actions.
    It only evaluates policy rules.
    """

    def evaluate(
        self,
        request: ExecutionRequest,
    ) -> PolicyDecision:

        return PolicyDecision.ALLOW


execution_policy = ExecutionPolicy()
