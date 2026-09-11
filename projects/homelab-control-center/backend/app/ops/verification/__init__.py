"""B1a — above-Core post-execution verification layer.

The frozen Core verifier asserts a post-condition only for module creation
(`app/core/intelligence/verification/service.py::_resolve_trusted_observer`);
for every other governed operation it records `observation_unavailable` by
construction. This package adds an above-Core observer *registry* and a single
entrypoint — `verify_executed_action` — that resolves a read-only observer for
an `(adapter, operation)` pair, performs a short settling observation, and feeds
the result to the **frozen** `verifier.verify` + `verification_storage.save`.

It is NOT a second verification mechanism: same verifier, same storage. The
registry resolves observers only — read-only, as the Core does internally. The
frozen Core records are never suppressed or edited; B1a adds an above-Core
record where an observer exists.

See `docs/RMT_B1_PROPOSAL.md` and `docs/RMT_FROZEN_CORE_DEBT.md` row D3.
"""
from app.ops.verification.expected import expected_state_for
from app.ops.verification.registry import register_observer, resolve_observer
from app.ops.verification.service import verify_executed_action

# Importing this module registers the Docker observers (idempotent).
from app.ops.verification import docker_observers as _docker_observers  # noqa: F401

# RMT-CAP-06 (C2/D-1): registers the git-tag observers (idempotent).
from app.ops.verification import git_observers as _git_observers  # noqa: F401

__all__ = [
    "expected_state_for",
    "register_observer",
    "resolve_observer",
    "verify_executed_action",
]
