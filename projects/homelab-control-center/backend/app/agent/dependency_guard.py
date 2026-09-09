"""RMT-CAP-05 -- T13 dependency-cascade escalation (above-Core).

`docs/RMT_T13_DISPOSITION.md`. MCR-EXP-3 T13: an *allowed* operation can achieve,
through a dependency cascade, the same consequential effect a *restricted*
operation would have needed approval for. Effect-based governance that inspects
only the direct operation misses it.

This guard runs in the agent layer BEFORE `execute_governed_action`. It changes
no Core policy. When an allowed-class operation on ``target`` would propagate to
a component that depends on ``target``, it forces ``requires_approval=True``.

Dependency edges are the **union** of:
  * the above-Core homelab map (`app/homelab/dependencies.py`) -- authoritative
    for the homelab domain, and
  * the frozen Core `ComponentContext.dependencies` -- future-proofing if Core
    ever populates it.

The current homelab map records all three services as independent, so this is a
no-op today; it escalates automatically the moment any edge is added to either
source.
"""
from app.core.intelligence.context.registry import (
    COMPONENT_CONTEXTS,
    get_component_context,
)
from app.homelab.dependencies import (
    dependents_of as _homelab_dependents_of,
    resolved_map as _homelab_map,
    dependency_sources as _homelab_sources,
)
from app.agent import loop_config


# Operation classes by consequential effect.
_ALLOWED_EFFECT_OPERATIONS = {"start", "create"}
_RESTRICTED_EFFECT_OPERATIONS = {"restart", "stop", "remove"}


def _dependents_of(target: str) -> set[str]:
    """Components that declare ``target`` as a dependency -- above-Core map
    unioned with the frozen Core context."""
    dependents = set(_homelab_dependents_of(target))
    for name in list(COMPONENT_CONTEXTS.keys()):
        ctx = get_component_context(name)
        if ctx is not None and target in (ctx.dependencies or []):
            dependents.add(name)
    return dependents


def dependency_view() -> dict:
    """Read-only snapshot of the resolved dependency sources (for status)."""
    core = {
        name: list((get_component_context(name).dependencies or []))
        for name in list(COMPONENT_CONTEXTS.keys())
    }
    return {
        "escalation_enabled": loop_config.AGENT_DEPENDENCY_ESCALATION,
        "homelab_map": _homelab_map(),
        "core_context": core,
        # T1-2: where each homelab edge came from (static map vs operator-declared
        # RMT_HOMELAB_DEPENDENCIES), plus the frozen-Core context for reference.
        "sources": {**_homelab_sources(), "core_context": core},
    }


def escalate_for_dependency_cascade(target: str, operation: str):
    """Return ``(escalate: bool, reason: str)``.

    Escalate only for an *allowed-class* operation whose target has at least one
    dependent component -- that is the T13 shape (restricted effect reached via
    an allowed op). A restricted-class operation is already governed directly
    and is not escalated here.
    """
    if not loop_config.AGENT_DEPENDENCY_ESCALATION:
        return False, ""
    if operation not in _ALLOWED_EFFECT_OPERATIONS:
        return False, ""
    dependents = _dependents_of(target)
    if not dependents:
        return False, ""
    return True, (
        f"T13: allowed op '{operation}' on '{target}' would propagate to "
        f"dependent(s) {sorted(dependents)} -- a restricted effect via "
        f"dependency cascade; escalated to human approval"
    )
