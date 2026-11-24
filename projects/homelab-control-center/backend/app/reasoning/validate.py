"""RMT-CAP-13 -- the fail-closed gate between model text and anything stored
or shown as an explanation.

Rules (proposal section 3b): one parseable JSON object; a claim survives only
if it cites at least one ref and *every* cited ref exists in the bundle the
model was shown; no surviving claim => ``no_grounded_explanation``;
``recurring`` needs >= 2 distinct cited ``failure#`` refs; the suggested action
must name a known component and a valid ``ActionType`` or it is stripped;
confidence must be an int 0-100 or the whole response is rejected.
"""
import json
from dataclasses import dataclass, field

from app.core.intelligence.actions.models import ActionType
from app.homelab.dependencies import HOMELAB_DEPENDENCIES

from app.reasoning.collect import Bundle

MAX_CLAIMS = 10
MAX_CLAIM_CHARS = 400
MAX_SUMMARY_CHARS = 600
MAX_REASON_CHARS = 300

_PATTERNS = {"one_off", "recurring", "unknown"}


class ExplainError(Exception):
    """``status`` is one of ``llm_error`` | ``llm_parse_error`` | ``invalid`` |
    ``no_grounded_explanation`` | ``no_evidence``."""

    def __init__(self, status: str, detail: str = ""):
        super().__init__(detail or status)
        self.status = status
        self.detail = detail


@dataclass
class Validated:
    summary: str
    claims: list = field(default_factory=list)
    pattern: str = "unknown"
    suggested_action: dict | None = None
    confidence: int = 0
    dropped_claims: int = 0
    notes: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "summary": self.summary,
            "claims": self.claims,
            "pattern": self.pattern,
            "suggested_action": self.suggested_action,
            "confidence": self.confidence,
            "dropped_claims": self.dropped_claims,
            "notes": self.notes,
        }


def extract_json(text: str) -> dict:
    """Exactly one top-level JSON object (surrounding prose tolerated)."""
    text = text or ""
    start = text.find("{")
    if start < 0:
        raise ExplainError("llm_parse_error", "no JSON object in model output")
    try:
        data, end = json.JSONDecoder().raw_decode(text, start)
    except json.JSONDecodeError as exc:
        raise ExplainError("llm_parse_error", f"bad JSON: {exc}")
    if not isinstance(data, dict):
        raise ExplainError("llm_parse_error", "model output is not an object")
    if "{" in text[end:]:
        raise ExplainError("llm_parse_error", "more than one JSON object in output")
    return data


def _clean_action(raw) -> tuple[dict | None, str | None]:
    if raw is None:
        return None, None
    if not isinstance(raw, dict):
        return None, "suggested_action stripped: not an object"
    target, mechanism = raw.get("target"), raw.get("mechanism")
    if target not in HOMELAB_DEPENDENCIES:
        return None, f"suggested_action stripped: unknown target {target!r}"
    if mechanism not in {t.value for t in ActionType}:
        return None, f"suggested_action stripped: invalid mechanism {mechanism!r}"
    reason = str(raw.get("reason") or "")[:MAX_REASON_CHARS]
    return {"target": target, "mechanism": mechanism, "reason": reason}, None


def validate(text: str, bundle: Bundle) -> Validated:
    data = extract_json(text)

    confidence = data.get("confidence")
    if (
        not isinstance(confidence, int)
        or isinstance(confidence, bool)
        or not 0 <= confidence <= 100
    ):
        raise ExplainError("invalid", f"confidence not int 0-100: {confidence!r}")

    raw_claims = data.get("claims")
    if not isinstance(raw_claims, list):
        raise ExplainError("invalid", "claims is not a list")

    kept, dropped = [], 0
    for claim in raw_claims[:MAX_CLAIMS]:
        refs = claim.get("evidence") if isinstance(claim, dict) else None
        text_ = claim.get("text") if isinstance(claim, dict) else None
        if (
            not isinstance(text_, str)
            or not text_.strip()
            or not isinstance(refs, list)
            or not refs
            or not all(isinstance(r, str) and r in bundle.refs for r in refs)
        ):
            dropped += 1
            continue
        kept.append({"text": text_.strip()[:MAX_CLAIM_CHARS], "evidence": list(dict.fromkeys(refs))})
    dropped += max(0, len(raw_claims) - MAX_CLAIMS)

    if not kept:
        raise ExplainError(
            "no_grounded_explanation",
            f"no claim cited existing evidence ({dropped} dropped)",
        )

    summary = data.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise ExplainError("invalid", "summary missing")

    notes = []
    pattern = data.get("pattern")
    if pattern not in _PATTERNS:
        pattern = "unknown"
        notes.append("pattern reset to unknown: not a valid value")
    if pattern == "recurring":
        cited_failures = {r for c in kept for r in c["evidence"] if r.startswith("failure#")}
        if len(cited_failures) < 2:
            pattern = "unknown"
            notes.append("pattern downgraded to unknown: fewer than two cited failures")

    action, note = _clean_action(data.get("suggested_action"))
    if note:
        notes.append(note)

    return Validated(
        summary=summary.strip()[:MAX_SUMMARY_CHARS],
        claims=kept,
        pattern=pattern,
        suggested_action=action,
        confidence=confidence,
        dropped_claims=dropped,
        notes=notes,
    )
