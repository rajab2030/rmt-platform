"""B1a — `verify_executed_action`: the above-Core post-execution entrypoint.

A successfully executed governed action calls this. It:

  1. builds an `ExpectedOutcome` from `expected_state_for(...)` when the caller
     passed none;
  2. resolves a read-only observer for the `(adapter, operation)`;
  3. if none resolves — returns an `observation_unavailable` result **without**
     persisting a second record (the frozen Core already saved one). The
     effective-status index + `verification_inconclusive` notification for this
     branch land in B1b;
  4. if one resolves — performs a short *settling* observation (poll until the
     expected state is seen or `RMT_VERIFY_OBSERVE_TIMEOUT_S` elapses), then
     feeds the observation to the **frozen** `verifier.verify` and persists the
     result through the **frozen** `verification_storage.save`.

Before saving, `result.reason` is prefixed with a machine-readable token —
`[layer=above_core adapter=<name> supersedes=observation_unavailable]` (the
`supersedes=` clause only when a Core record with that status already exists for
the `execution_id`) — so a raw evidence read is unambiguous about which layer
wrote the record.

R10: `verification_storage` is dereferenced through its module at call time,
never bound as a local alias at import.
"""
import os
import time

from app.core.intelligence.verification.models import (
    ExpectedOutcome,
    VerificationResult,
    VerificationStatus,
)
from app.core.intelligence.verification.verifier import verifier
from app.core.intelligence.verification import storage as _verification_storage_module

from app.ops.verification.expected import expected_state_for
from app.ops.verification.registry import resolve_observer

# Ensure the Docker observers are registered regardless of import entry point
# (idempotent). The package __init__ also does this.
from app.ops.verification import docker_observers as _docker_observers  # noqa: F401

_DEFAULT_OBSERVE_TIMEOUT_S = 5.0
_POLL_INTERVAL_S = 0.5


def _observe_timeout_s() -> float:
    """`RMT_VERIFY_OBSERVE_TIMEOUT_S` — seconds to keep re-observing while the
    expected state has not been seen. Default 5; `0` = single-shot. Read
    dynamically so a drop-in edit takes effect without reimport."""
    raw = os.environ.get("RMT_VERIFY_OBSERVE_TIMEOUT_S")
    if raw is None:
        return _DEFAULT_OBSERVE_TIMEOUT_S
    try:
        return max(0.0, float(raw))
    except ValueError:
        return _DEFAULT_OBSERVE_TIMEOUT_S


def _settle(observer, expected_state, timeout_s):
    """Observe once; while the observation is missing or not yet the expected
    state, re-observe at ~0.5 s until it matches or `timeout_s` elapses. Returns
    the last observation (which the verifier then scores)."""
    observed = observer()
    if timeout_s <= 0 or expected_state is None:
        return observed
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if observed is not None and observed.state == expected_state:
            return observed
        time.sleep(_POLL_INTERVAL_S)
        observed = observer()
    return observed


def _core_observation_unavailable_exists(execution_id: str) -> bool:
    store = _verification_storage_module.verification_storage
    try:
        for record in store.get_all():
            if (
                record.execution_id == execution_id
                and record.status == VerificationStatus.OBSERVATION_UNAVAILABLE
            ):
                return True
    except Exception:
        return False
    return False


def verify_executed_action(
    execution_id: str,
    *,
    adapter_name: str,
    operation: str,
    target: str,
    expected: ExpectedOutcome | None = None,
) -> VerificationResult:
    """Verify a successfully executed governed action against observed state
    through the frozen verifier + storage. A caller-supplied `expected` wins."""
    if expected is None:
        state = expected_state_for(adapter_name, operation)
        if state is not None:
            expected = ExpectedOutcome(
                target=target, operation=operation, expected_state=state
            )

    observer = resolve_observer(adapter_name, operation, target)
    if observer is None:
        # No above-Core observer for this (adapter, operation). Record nothing
        # new — the frozen Core already saved its observation_unavailable.
        return VerificationResult(
            execution_id=execution_id,
            status=VerificationStatus.OBSERVATION_UNAVAILABLE,
            expected=expected,
            observed=None,
            reason=(
                f"[layer=above_core adapter={adapter_name}] "
                "no above-Core observer registered for this operation"
            ),
        )

    expected_state = expected.expected_state if expected is not None else None
    try:
        observed = _settle(observer, expected_state, _observe_timeout_s())
    except Exception:
        observed = None

    result = verifier.verify(execution_id, expected, observed)

    supersedes = (
        " supersedes=observation_unavailable"
        if _core_observation_unavailable_exists(execution_id)
        else ""
    )
    result.reason = (
        f"[layer=above_core adapter={adapter_name}{supersedes}] "
        f"{result.reason or ''}"
    ).rstrip()

    _verification_storage_module.verification_storage.save(result)
    return result
