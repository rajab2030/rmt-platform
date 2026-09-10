"""B1a — above-Core post-execution observer registry.

Registration is data: an `(adapter_name, operation)` pair maps to a *factory*
that, given a target, returns a zero-argument observer callable producing an
`ObservedState | None`. An unknown pair resolves to `None` — the caller then
records the execution as unverified (§2.4 of the proposal, B1b); it is never an
error.

An observer only *reads* state. It never mutates, authorizes, approves,
bypasses the frozen verifier, or becomes an execution path.
"""
from typing import Callable

from app.core.intelligence.verification.models import ObservedState

# factory: target -> (observe: () -> ObservedState | None)
ObserverFactory = Callable[[str], Callable[[], "ObservedState | None"]]

_REGISTRY: dict[tuple[str, str], ObserverFactory] = {}


def register_observer(
    adapter_name: str, operation: str, factory: ObserverFactory
) -> None:
    """Register (or replace) the observer factory for an `(adapter, operation)`.

    Idempotent: re-registering the same pair just overwrites it, so importing
    the observer modules more than once is harmless.
    """
    _REGISTRY[(adapter_name.lower(), operation.lower())] = factory


def resolve_observer(
    adapter_name: str, operation: str, target: str
) -> "Callable[[], ObservedState | None] | None":
    """Return a bound zero-arg observer for the target, or `None` when no
    factory is registered for the `(adapter, operation)` pair."""
    factory = _REGISTRY.get((adapter_name.lower(), operation.lower()))
    if factory is None:
        return None
    return factory(target)


def registered_pairs() -> list[tuple[str, str]]:
    """The registered `(adapter, operation)` pairs — for tests / introspection."""
    return sorted(_REGISTRY)
