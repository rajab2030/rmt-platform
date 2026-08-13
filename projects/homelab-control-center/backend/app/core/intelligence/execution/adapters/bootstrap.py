from app.core.intelligence.execution.adapters.registry import (
    adapter_registry,
)

from app.core.intelligence.execution.adapters.simulation import (
    SimulationAdapter,
)


def register_default_adapters():
    """
    Register built-in execution adapters.
    """

    adapter_registry.register(
        "simulation",
        SimulationAdapter(),
    )
