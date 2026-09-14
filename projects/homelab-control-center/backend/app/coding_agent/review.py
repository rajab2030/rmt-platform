"""RMT-CAP-10: assembles the three real evidence sources into a verdict.

No LLM anywhere here -- the reviewer only tallies real, checkable signals; it
never phrases, summarizes, or adds judgment beyond the fixed verdict rule
below. If a source has nothing to say, it contributes nothing, not a filler
claim.

Verdict: ``reject`` if any evidence item leans ``reject``; else ``approve``
if any leans ``approve`` and none leans ``reject``; else ``reject`` -- the
safe default when there is no real signal either way (absence of evidence is
not evidence of safety).
"""
from app.coding_agent.history import history_evidence
from app.coding_agent.models import EvidenceItem, Lean
from app.coding_agent.risk_rules import RiskRule
from app.coding_agent.situational import situational_evidence


def _rule_evidence(rule: RiskRule) -> EvidenceItem:
    leans: Lean = "reject" if rule.risk_level == "high" else "neutral"
    return EvidenceItem(
        source="policy_rule",
        claim=f"matched '{rule.name}' ({rule.risk_level} risk): {rule.description}",
        leans=leans,
    )


def _verdict(evidence: list[EvidenceItem]) -> Lean:
    leans = {item.leans for item in evidence}
    if "reject" in leans:
        return "reject"
    if "approve" in leans:
        return "approve"
    return "reject"


def assess(rule: RiskRule, cwd: str) -> tuple[list[EvidenceItem], Lean]:
    """Build the evidence list for a matched risk rule and compute the
    verdict. Every item traces to a real, checkable source."""
    evidence = [_rule_evidence(rule)]

    hist = history_evidence(rule.name)
    if hist is not None:
        evidence.append(hist)

    evidence.extend(situational_evidence(rule.name, cwd))

    return evidence, _verdict(evidence)
