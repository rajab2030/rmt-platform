from typing import Dict

from app.core.intelligence.execution.adapters.base import (
    ExecutionAdapter,
)


class AdapterRegistry:
    """
    Registry for execution adapters.

    Only approved adapter implementations
    can be registered.
    """

    def __init__(self):
        self._adapters: Dict[str, ExecutionAdapter] = {}

    def register(
        self,
        name: str,
        adapter: ExecutionAdapter,
    ):
        if not isinstance(adapter, ExecutionAdapter):
            raise TypeError(
                "Adapter must implement ExecutionAdapter"
            )

        self._adapters[name] = adapter

    def get(
        self,
        name: str,
    ):
        return self._adapters.get(name)


adapter_registry = AdapterRegistry()
