"""RMT-CAP-05 (5A) -- T13 dependency-cascade escalation (above-Core).

`docs/RMT_T13_DISPOSITION.md` sect 3c. MCR-EXP-3 T13: an *allowed* operation can
achieve, through a dependency cascade, the same consequential effect that a
*restricted* operation would have needed approval for. Effect-based governance
that inspects only the direct operation misses it.

This guard runs in the agent layer BEFORE `execute_governed_action`. It changes
no Core policy. When an allowed-class operation on ``target`` would propagate to
a component that depends on ``target``, it forces ``requires_approval=True``.

It reads ``ComponentContext.dependencies``. Today every homelab component's
dependency list is empty, so this is a no-op -- but it is wired and tested, so
a deliberately widened envelope (populated dependencies, a lowered
``AGENT_DEFAULT_REQUIRES_APPROVAL``) is safe by construction.
"""
from app.core.intelligence.context.registry import (
    COMPONENT_CONTEXTS,
    get_component_context,
)
from app.agent import loop_config


# Operation classes by consequential effect.
_ALLOWED_EFFECT_OPERATIONS = {"start", "create"}
_RESTRICTED_EFFECT_OPERATIONS = {"restart", "stop", "remove"}


def _dependents_of(target: str) -> set[str]:
    """Components whose context lists ``target`` as a dependency."""
    dependents = set()
    for name in list(COMPONENT_CONTEXTS.keys()):
        ctx = get_component_context(name)
        if ctx is not None and target in (ctx.dependencies or []):
            dependents.add(name)
    return dependents


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
