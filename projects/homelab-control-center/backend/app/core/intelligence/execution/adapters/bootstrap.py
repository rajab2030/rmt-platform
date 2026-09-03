from app.core.intelligence.execution.adapters.registry import (
    adapter_registry,
)

from app.core.intelligence.execution.adapters.simulation import (
    SimulationAdapter,
)

from app.docker_api import (
    docker_available,
)


def register_default_adapters():
    """
    Register built-in execution adapters.

    Simulation is always registered as the safe/no-op binding.
    ModuleChange is the bounded evolution adapter and is always registered.
    Docker is an optional runtime adapter and is registered only when the
    docker daemon is reachable. The Core must not rely on docker.
    """
    adapter_registry.register(
        "simulation",
        SimulationAdapter(),
    )

    from app.core.evolution.adapters.module_change import (
        ModuleChangeAdapter,
    )

    adapter_registry.register(
        "module_change",
        ModuleChangeAdapter(),
    )

    if docker_available():
        from app.core.intelligence.execution.adapters.docker import (
            DockerExecutionAdapter,
        )

        adapter_registry.register(
            "docker",
            DockerExecutionAdapter(),
        )
    else:
        print(
            "Docker adapter not registered: docker daemon unavailable"
        )
