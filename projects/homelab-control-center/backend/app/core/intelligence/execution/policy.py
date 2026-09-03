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

    This is a final deny-only safety gate. It can only block execution; it
    cannot grant permission or require approval. Approval is handled in the
    governance layer (action policy + approval policy) before execution.

    This layer does not execute actions.
    It only evaluates policy rules.
    """

    def evaluate(
        self,
        request: ExecutionRequest,
    ) -> PolicyDecision:

        operation = request.operation.lower()

        if operation in {
            "format",
            "wipe",
        }:
            return PolicyDecision.DENY

        return PolicyDecision.ALLOW


execution_policy = ExecutionPolicy()
