"""B1a — the single `(adapter, operation) -> expected_state` mapping.

Every above-Core call site that does not already build its own `ExpectedOutcome`
(`app/homelab/remediation.py` does; `POST /execute` and the agent path do not)
resolves the post-condition to assert through this one table, so they agree.

The states are the verbatim Docker SDK status strings the verifier compares
against (`created`, `restarting`, `running`, `removing`, `paused`, `exited`,
`dead`), plus the synthetic `absent` produced by the observer's
reachable-and-gone extension (B1a) so `remove` is verifiable.
"""

_EXPECTED_STATE: dict[tuple[str, str], str] = {
    ("docker", "start"): "running",
    ("docker", "restart"): "running",
    ("docker", "create"): "running",
    ("docker", "stop"): "exited",
    ("docker", "remove"): "absent",
    # RMT-CAP-06 (C2/D-1): git-tag domain.
    ("git", "create"): "present",
    ("git", "remove"): "absent",
}


def expected_state_for(adapter_name: str, operation: str) -> str | None:
    """The expected post-execution state for an `(adapter, operation)`, or
    `None` when the pair has no defined post-condition (the caller then passes
    no `ExpectedOutcome` and the execution is treated as unverified)."""
    return _EXPECTED_STATE.get((adapter_name.lower(), operation.lower()))
