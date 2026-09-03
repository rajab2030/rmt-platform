from app.core.intelligence.execution.adapters.base import (
    ExecutionAdapter,
)
from app.core.intelligence.execution.models import (
    ExecutionRequest,
    ExecutionResult,
)
from app.core.module_factory.factory import create_module
from app.core.module_registry.registry import register_module


class ModuleChangeAdapter(ExecutionAdapter):
    """
    Applies a bounded module-registration change to the module registry.

    This adapter is an executor only. It does not decide whether the change
    is allowed; governance stays in the policy/risk/approval/authorization
    chain. It modifies ONLY the module registry, never governance state.
    """

    SUPPORTED_OPERATIONS = {"create"}

    def supports(self, request: ExecutionRequest) -> bool:
        return request.operation.lower() in self.SUPPORTED_OPERATIONS

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        module_name = request.parameters.get("module_name")
        version = request.parameters.get("version", "0.1.0")
        module_type = request.parameters.get("module_type", "platform-service")

        if not module_name:
            return ExecutionResult(
                execution_id=request.execution_id,
                status="failed",
                success=False,
                message="Module name is required",
            )

        try:
            module = create_module(
                name=module_name,
                version=version,
                module_type=module_type,
                runtime_engine="docker",
                container=module_name,
            )
            register_module(module)
        except ValueError as e:
            return ExecutionResult(
                execution_id=request.execution_id,
                status="failed",
                success=False,
                message=f"Module registration failed: {str(e)}",
            )

        return ExecutionResult(
            execution_id=request.execution_id,
            status="completed",
            success=True,
            message=f"Module {module_name} registered",
            output={
                "module_id": module.module_id,
                "name": module_name,
                "version": version,
            },
        )
