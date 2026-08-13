from app.core.intelligence.execution.adapters.base import (
    ExecutionAdapter,
)

from app.core.intelligence.execution.models import (
    ExecutionRequest,
    ExecutionResult,
)


class SimulationAdapter(ExecutionAdapter):
    """
    Safe execution adapter.

    Simulates execution without changing the platform.
    """

    def supports(
        self,
        request: ExecutionRequest,
    ) -> bool:
        return True

    def execute(
        self,
        request: ExecutionRequest,
    ) -> ExecutionResult:

        return ExecutionResult(
            execution_id=request.execution_id,
            status="completed",
            success=True,
            message="Execution simulated successfully",
            output={
                "simulation": True,
                "operation": request.operation,
                "target": request.target,
            },
        )
