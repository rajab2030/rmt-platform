from app.core.intelligence.execution.adapters.base import (
    ExecutionAdapter,
)

from app.core.intelligence.execution.models import (
    ExecutionRequest,
    ExecutionResult,
)

from app.docker_api import (
    start_container,
    stop_container,
    restart_container,
    create_container,
    remove_container,
)


class DockerExecutionAdapter(ExecutionAdapter):
    """
    Real execution adapter for Docker runtime.

    Dispatches supported operations to the existing docker_api layer.
    Does not decide whether execution is allowed - that stays with
    the policy/risk chain.
    """

    SUPPORTED_OPERATIONS = {
        "restart",
        "start",
        "stop",
        "create",
        "remove",
    }

    def supports(self, request: ExecutionRequest) -> bool:
        return request.operation.lower() in self.SUPPORTED_OPERATIONS

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        operation = request.operation.lower()
        target = request.target

        try:
            if operation == "restart":
                result = restart_container(target)
            elif operation == "start":
                result = start_container(target)
            elif operation == "stop":
                result = stop_container(target)
            elif operation == "create":
                image = request.parameters.get("image", "unknown")
                result = create_container(target, image)
            elif operation == "remove":
                result = remove_container(target)
            else:
                return ExecutionResult(
                    execution_id=request.execution_id,
                    status="failed",
                    success=False,
                    message=f"Operation {operation} not supported by Docker adapter",
                )

            return ExecutionResult(
                execution_id=request.execution_id,
                status="completed",
                success=True,
                message=f"Execution completed: {result['action']} on {result['name']}",
                output=result,
            )

        except Exception as e:
            return ExecutionResult(
                execution_id=request.execution_id,
                status="failed",
                success=False,
                message=f"Execution failed: {str(e)}",
            )
