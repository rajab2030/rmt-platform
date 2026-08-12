from abc import ABC, abstractmethod

from app.core.intelligence.execution.models import (
    ExecutionRequest,
    ExecutionResult,
)


class ExecutionAdapter(ABC):
    """
    Stable contract for infrastructure execution adapters.

    Adapters implement how execution happens.
    They do not decide whether execution is allowed.
    """

    @abstractmethod
    def supports(
        self,
        request: ExecutionRequest,
    ) -> bool:
        """
        Return True if this adapter can handle the request.
        """
        raise NotImplementedError

    @abstractmethod
    def execute(
        self,
        request: ExecutionRequest,
    ) -> ExecutionResult:
        """
        Execute an already-authorized request.
        """
        raise NotImplementedError
