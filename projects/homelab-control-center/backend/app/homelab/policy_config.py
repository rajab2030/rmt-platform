"""RMT-CAP-14 (roadmap P-A, slice 1) -- homelab remediation policy as configuration.

Loads the CAP-04 remediation policy from a TOML file named by
``RMT_HOMELAB_REMEDIATION_POLICY_FILE``. Unset => the built-in policy in
``app/homelab/remediation.py``, unchanged. The file *replaces* the built-in
policy (one source of truth per run).

The loader, not only a unit test, enforces the CAP-04 T13 safe envelope
(``docs/RMT_T13_DISPOSITION.md``): every entry must be approval-gated and
independent. Any rule violation raises ``PolicyConfigError``; because
``app.homelab.remediation`` loads the policy at import, the backend then
refuses to start (fail-closed, proposal decision D1).

Only the *source* of the policy dict changes. The dict has exactly the shape
``REMEDIATION_POLICY`` always had, so ``build_remediation_action`` and the
operational loop are untouched. No ``app/core/**`` change: Core is only read
(enum values, the component-context registry).

See ``docs/RMT_CAP_14_PROPOSAL.md``.
"""
import hashlib
import logging
import os
import tomllib
from dataclasses import dataclass, field

from app.core.intelligence.actions.models import ActionType
from app.core.intelligence.context.registry import get_component_context
from app.core.intelligence.schemas import HealthStatus

ENV_VAR = "RMT_HOMELAB_REMEDIATION_POLICY_FILE"

# Slice 1 allow-lists (proposal §3b rules 4 and 5). Widening either is a
# separate owner decision, not a config edit.
ALLOWED_ACTIONS: dict[str, ActionType] = {"restart": ActionType.RESTART}
ALLOWED_TRIGGERS: dict[str, HealthStatus] = {
    "warning": HealthStatus.WARNING,
    "critical": HealthStatus.CRITICAL,
}

_REQUIRED_KEYS = ("action", "remediate_on", "expected_state", "requires_approval")
_DEPENDENCY_KEYS = ("depends_on", "dependencies")

logger = logging.getLogger("rmt.homelab.policy")


class PolicyConfigError(Exception):
    """A policy file that must not be loaded. ``errors`` lists every rule
    violation found (one line each), not just the first."""

    def __init__(self, path: str, errors: list[str]):
        self.path = path
        self.errors = list(errors)
        joined = "\n  - ".join(self.errors)
        super().__init__(f"invalid remediation policy {path}:\n  - {joined}")


@dataclass
class PolicySource:
    source: str  # "builtin" | "file"
    path: str | None = None
    sha256: str | None = None
    components: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "path": self.path,
            "sha256": self.sha256,
            "components": list(self.components),
        }


def _dependency_edges(component: str) -> tuple[list[str], set[str]]:
    # Imported lazily so this module stays importable on its own (the
    # offline checker) and always sees the current RMT_HOMELAB_DEPENDENCIES.
    from app.homelab.dependencies import dependencies_of, dependents_of

    return dependencies_of(component), dependents_of(component)


def validate_document(doc: dict) -> tuple[dict, list[str]]:
    """Validate a parsed TOML document. Returns ``(policy, errors)``; the
    policy is only meaningful when ``errors`` is empty."""
    errors: list[str] = []
    policy: dict = {}

    extra_top = sorted(set(doc) - {"components"})
    if extra_top:
        errors.append(f"unknown top-level key(s): {', '.join(extra_top)}")

    components = doc.get("components")
    if components is None:
        errors.append("missing [components] table")
        return policy, errors
    if not isinstance(components, dict):
        errors.append("[components] must be a table")
        return policy, errors

    for name, entry in components.items():
        where = f"components.{name}"
        if not isinstance(entry, dict):
            errors.append(f"{where}: must be a table")
            continue

        # Rule 2 (declared form) gets its own message before the generic
        # unknown-key rule, so the envelope reason is explicit.
        for dep_key in _DEPENDENCY_KEYS:
            if dep_key in entry:
                errors.append(
                    f"{where}: declares '{dep_key}'; remediation entries must be "
                    "independent (CAP-04 T13 safe envelope)"
                )
        unknown = sorted(set(entry) - set(_REQUIRED_KEYS) - set(_DEPENDENCY_KEYS))
        if unknown:
            errors.append(f"{where}: unknown key(s): {', '.join(unknown)}")
        missing = [k for k in _REQUIRED_KEYS if k not in entry]
        if missing:
            errors.append(f"{where}: missing key(s): {', '.join(missing)}")

        # Rule 1 -- approval. Absent is reported as missing above; anything
        # other than literal true is rejected.
        if "requires_approval" in entry and entry["requires_approval"] is not True:
            errors.append(
                f"{where}: requires_approval must be true "
                "(CAP-04 T13 safe envelope)"
            )

        # Rule 2 -- independence in the resolved dependency map.
        deps, dependents = _dependency_edges(name)
        if deps or dependents:
            errors.append(
                f"{where}: has dependency edges (depends on {sorted(deps)}, "
                f"depended on by {sorted(dependents)}); remediation entries must "
                "be independent (CAP-04 T13 safe envelope)"
            )

        # Rule 3 -- known component.
        if get_component_context(name) is None:
            errors.append(f"{where}: unknown component (no ComponentContext)")

        # Rule 4 -- action allow-list.
        action = entry.get("action")
        if "action" in entry and action not in ALLOWED_ACTIONS:
            errors.append(
                f"{where}: action {action!r} not allowed; "
                f"allowed: {', '.join(sorted(ALLOWED_ACTIONS))}"
            )

        # Rule 5 -- trigger states.
        triggers = entry.get("remediate_on")
        trigger_set: set[HealthStatus] = set()
        if "remediate_on" in entry:
            if not isinstance(triggers, list) or not triggers:
                errors.append(f"{where}: remediate_on must be a non-empty list")
            else:
                for t in triggers:
                    if t not in ALLOWED_TRIGGERS:
                        errors.append(
                            f"{where}: remediate_on value {t!r} not allowed; "
                            f"allowed: {', '.join(sorted(ALLOWED_TRIGGERS))}"
                        )
                    else:
                        trigger_set.add(ALLOWED_TRIGGERS[t])

        # Rule 6 -- expected state.
        expected = entry.get("expected_state")
        if "expected_state" in entry and (
            not isinstance(expected, str) or not expected.strip()
        ):
            errors.append(f"{where}: expected_state must be a non-empty string")

        if action in ALLOWED_ACTIONS and trigger_set and isinstance(expected, str):
            policy[name] = {
                "action_type": ALLOWED_ACTIONS[action],
                "remediate_on": trigger_set,
                "expected_state": expected.strip(),
                "requires_approval": True,
            }

    return policy, errors


def load_policy_file(path: str) -> tuple[dict, PolicySource]:
    """Read, parse and validate one policy file. Raises ``PolicyConfigError``
    on any problem (unreadable, not TOML, or any rule violation)."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        raise PolicyConfigError(path, [f"cannot read file: {exc}"]) from exc
    try:
        doc = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise PolicyConfigError(path, [f"not valid TOML: {exc}"]) from exc

    policy, errors = validate_document(doc)
    if errors:
        raise PolicyConfigError(path, errors)
    return policy, PolicySource(
        source="file",
        path=path,
        sha256=hashlib.sha256(raw).hexdigest(),
        components=list(policy.keys()),
    )


def resolve_policy(builtin: dict) -> tuple[dict, PolicySource]:
    """The policy in force: the file named by ``RMT_HOMELAB_REMEDIATION_POLICY_FILE``
    if set, otherwise ``builtin`` (returned as-is). Logs one
    ``homelab_remediation_policy_loaded`` event either way; raises
    ``PolicyConfigError`` for an invalid file (never falls back)."""
    from app.ops.logging_config import log_event

    path = os.environ.get(ENV_VAR, "").strip()
    if not path:
        source = PolicySource(source="builtin", components=list(builtin.keys()))
        log_event(logger, "homelab_remediation_policy_loaded", **source.as_dict())
        return builtin, source

    try:
        policy, source = load_policy_file(path)
    except PolicyConfigError as exc:
        log_event(
            logger,
            "homelab_remediation_policy_rejected",
            level=logging.ERROR,
            path=path,
            errors=exc.errors,
        )
        raise

    log_event(logger, "homelab_remediation_policy_loaded", **source.as_dict())
    if not policy:
        # Decision D4: allowed -- the loop observes but never remediates.
        log_event(
            logger,
            "homelab_remediation_policy_empty",
            level=logging.WARNING,
            path=path,
            detail="no components: the operational loop will never remediate",
        )
    return policy, source
