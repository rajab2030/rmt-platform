"""RMT-CAP-10: evidence source 2 -- prior-decision history for a risk rule.

Tallies approved vs. rejected holds previously *decided* for the same risk
rule, read from the durable store. Absence of history is never treated as
either kind of evidence -- fail-open honesty, same discipline as
``evidence_chain.py``.
"""
from app.coding_agent.models import EvidenceItem, Lean
from app.coding_agent.store import command_hold_store


def history_evidence(risk_rule: str) -> EvidenceItem | None:
    """Return one :class:`EvidenceItem` tallying prior decisions for
    ``risk_rule``, or ``None`` when no decided hold exists yet for it."""
    decided = [
        h for h in command_hold_store.by_rule(risk_rule)
        if h.status in ("approved", "rejected")
    ]
    if not decided:
        return None

    approved = sum(1 for h in decided if h.status == "approved")
    rejected = len(decided) - approved

    leans: Lean
    if rejected > approved:
        leans = "reject"
    elif approved > rejected:
        leans = "approve"
    else:
        leans = "neutral"

    return EvidenceItem(
        source="history",
        claim=(
            f"{approved} approved / {rejected} rejected prior "
            f"'{risk_rule}' decision(s)"
        ),
        leans=leans,
    )
