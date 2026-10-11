"""RMT-CAP-13 -- build the evidence bundle the model is shown.

Read-only. Reuses ``evidence_chain()`` (CAP-09) and the frozen Core's read-only
``get_previous_failures`` unchanged. Every record gets a stable ref
(``audit#0``, ``failure#2`` ...) -- the only things a claim may cite. Fail-open:
a failing source degrades to fewer records, never an exception.
"""
import hashlib
import json
import logging
from dataclasses import dataclass, field

from app.reasoning import config

logger = logging.getLogger("rmt.reasoning")

# evidence_chain() section -> ref prefix
_SECTIONS = (
    ("authorizations", "authorization"),
    ("approvals", "approval"),
    ("holds", "hold"),
    ("audit", "audit"),
    ("traces", "trace"),
    ("verifications", "verification"),
)
_TARGET_SECTIONS = ("audit", "traces", "authorizations", "holds", "approvals")


@dataclass
class Bundle:
    incident_ref: str
    component: str | None
    refs: dict = field(default_factory=dict)  # ref -> record (JSON-safe dict)

    @property
    def is_empty(self) -> bool:
        return not self.refs

    def canonical_json(self) -> str:
        return json.dumps(self.refs, sort_keys=True, separators=(",", ":"), default=str)

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode()).hexdigest()


def _truncate(value, limit: int):
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + "...[truncated]"
    if isinstance(value, dict):
        return {str(k): _truncate(v, limit) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_truncate(v, limit) for v in value]
    return value


def _component_of(chain: dict) -> str | None:
    for section in _TARGET_SECTIONS:
        for rec in chain.get(section) or []:
            if isinstance(rec, dict) and isinstance(rec.get("target"), str):
                return rec["target"]
    return None


def _prior_failures(component: str, limit: int) -> list[dict]:
    try:
        from app.core.intelligence.memory.query import get_previous_failures

        items = list(get_previous_failures(component))
        items.sort(key=lambda i: i.timestamp, reverse=True)
        return [
            {
                "component": i.component,
                "event_type": i.event_type,
                "timestamp": i.timestamp.isoformat(),
                "data": dict(i.data or {}),
            }
            for i in items[:limit]
        ]
    except Exception as exc:  # noqa: BLE001 -- read-only, fail-open
        logger.warning("reasoning.collect: prior failures unavailable: %r", exc)
        return []


def build_bundle(*, incident_ref: str, action_id=None, approval_id=None, execution_id=None) -> Bundle:
    from app.ops.evidence_chain import evidence_chain

    limit = config.field_max_chars()
    chain = evidence_chain(
        action_id=action_id, approval_id=approval_id, execution_id=execution_id
    )
    component = _component_of(chain)
    bundle = Bundle(incident_ref=incident_ref, component=component)

    for section, prefix in _SECTIONS:
        for i, rec in enumerate(chain.get(section) or []):
            bundle.refs[f"{prefix}#{i}"] = _truncate(rec, limit)

    # Failures only make sense alongside at least one record of this incident.
    if component and bundle.refs:
        for i, rec in enumerate(_prior_failures(component, config.max_prior_failures())):
            bundle.refs[f"failure#{i}"] = _truncate(rec, limit)
    return bundle
