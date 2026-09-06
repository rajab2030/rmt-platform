"""RMT-CAP-02 — Engineering Change-Impact & Risk Analysis service (above-Core).

Read-only, deterministic, evidence-backed. Consumes frozen Core read-only
primitives only. Never executes, authorizes, approves, mutates the
repository, or modifies governance.

Pipeline:
  Repository/System Evidence
    -> Engineering Understanding (component resolution + curated index)
    -> Impact Analysis
    -> Engineering-Change Risk (explicit deterministic rule)
    -> Recommendation (thin above-Core layer)
    -> Evidence-backed Result
"""
from app.core.module_registry.registry import get_modules
from app.core.intelligence.analysis.governed_history import get_governed_outcomes
from app.core.intelligence.memory.query import get_previous_failures
from app.core.intelligence.context.registry import get_component_context

from app.engineering.models import (
    ProposedChange,
    ResolutionStatus,
    AffectedComponent,
    RiskFactor,
    EngineeringChangeRisk,
    Recommendation,
    EvidenceItem,
    EngineeringChangeAssessment,
)
from app.engineering.repo_index import get_curated_metadata


# ---------------------------------------------------------------------------
# 1. Component resolution (exact/unique only; no fuzzy matching)
# ---------------------------------------------------------------------------
def resolve_component(target: str):
    """Resolve a target across module_id -> context name -> container name.

    Returns (ResolutionStatus, resolved_entity_or_None). Exact/unique only.
    Multiple distinct entities -> ambiguous; none -> unknown.
    """
    entities = set()

    for module in get_modules():
        if module.module_id == target:
            entities.add(module.module_id)
        if module.runtime.container == target:
            entities.add(module.module_id)

    if get_component_context(target) is not None:
        entities.add(target)

    if len(entities) == 0:
        return ResolutionStatus.UNKNOWN_COMPONENT, None
    if len(entities) > 1:
        return ResolutionStatus.AMBIGUOUS_COMPONENT, None
    return ResolutionStatus.RESOLVED, next(iter(entities))


# ---------------------------------------------------------------------------
# 2. Impact analysis (deterministic, evidence-backed)
# ---------------------------------------------------------------------------
def _module_dependencies(entity: str):
    """Return the dependency list for a resolved module entity, or []."""
    for module in get_modules():
        if module.module_id == entity:
            return list(module.dependencies or [])
    return []


def compute_impact(target: str, entity: str):
    """Return deduplicated affected components with relationship + evidence.

    Sources: module registry dependencies, governed outcomes, curated index.
    Does NOT manufacture dependencies that are not registered.
    """
    affected = {}

    def add(component, relationship, evidence_source):
        entry = affected.setdefault(
            component, {"relationships": set(), "sources": set()}
        )
        entry["relationships"].add(relationship)
        entry["sources"].add(evidence_source)

    # Target itself.
    add(entity, "target", "component_resolution")

    # Direct dependents from module registry dependencies.
    for module in get_modules():
        if entity in (module.dependencies or []):
            add(module.module_id, "dependent", "module_registry.dependencies")

    # Governed-evidence related components.
    for view in get_governed_outcomes():
        if view.component in (entity, target):
            add(view.component, "evidence_related", "governed_outcomes")

    # Curated source/test related.
    meta = get_curated_metadata(entity) or get_curated_metadata(target)
    if meta:
        if meta.get("source_files"):
            add(entity, "source_related", "curated_repo_index")
        if meta.get("test_files"):
            add(entity, "source_related", "curated_repo_index")

    return [
        AffectedComponent(
            component=component,
            relationship=",".join(sorted(entry["relationships"])),
            evidence_source=",".join(sorted(entry["sources"])),
        )
        for component, entry in sorted(affected.items())
    ]


# ---------------------------------------------------------------------------
# 3. Engineering-change risk (explicit deterministic rule, no arbitrary weights)
# ---------------------------------------------------------------------------
def compute_risk(target: str, entity: str, affected):
    """Derive engineering-change risk from deterministic, evidence-backed factors.

    Explicit rule (no weights):
      base = low
      elevate to medium if any of:
        - governance_boundary involved
        - historical_failures > 0
        - unknown/unregistered dependency information
        - criticality == high
        - dependency fan-out > 0
      elevate to high if:
        - (governance_boundary AND historical_failures > 0)
        - OR (criticality == high AND historical_failures > 0)
    """
    dependents = [a for a in affected if "dependent" in a.relationship]

    # Governed-outcome views for the target (evidence source for risk factors).
    governed_views = [
        v for v in get_governed_outcomes()
        if v.component in (entity, target)
    ]

    fan_out = len(dependents)
    governance_boundary = len(governed_views) > 0
    failures = get_previous_failures(entity or target)
    failure_count = len(failures)
    has_verification = any(v.verification_status for v in governed_views)
    deps = _module_dependencies(entity)
    unknown_dep = len(deps) == 0
    ctx = get_component_context(entity or target)
    criticality = ctx.criticality if ctx else "unknown"

    factors = [
        RiskFactor(name="dependency_fan_out", value=str(fan_out),
                   evidence_source="module_registry.dependencies"),
        RiskFactor(name="governance_boundary", value=str(governance_boundary),
                   evidence_source="governed_outcomes"),
        RiskFactor(name="historical_failures", value=str(failure_count),
                   evidence_source="memory.get_previous_failures"),
        RiskFactor(name="verification_coverage", value=str(has_verification),
                   evidence_source="verification_storage"),
        RiskFactor(name="unknown_dependency", value=str(unknown_dep),
                   evidence_source="module_registry.dependencies"),
        RiskFactor(name="criticality", value=criticality,
                   evidence_source="context_registry"),
    ]

    # Explicit deterministic rule.
    level = 0  # low
    explanation = []
    if governance_boundary:
        level = max(level, 1)
        explanation.append("governance_boundary involved")
    if failure_count > 0:
        level = max(level, 1)
        explanation.append("historical_failures present")
    if unknown_dep:
        level = max(level, 1)
        explanation.append("unknown/unregistered dependency information")
    if criticality == "high":
        level = max(level, 1)
        explanation.append("high criticality")
    if fan_out > 0:
        level = max(level, 1)
        explanation.append("dependency fan-out present")
    if (governance_boundary and failure_count > 0) or (
        criticality == "high" and failure_count > 0
    ):
        level = max(level, 2)
        explanation.append(
            "governance_boundary + historical_failures (or high criticality + failures)"
        )

    classification = {0: "low", 1: "medium", 2: "high"}[level]

    return EngineeringChangeRisk(
        classification=classification,
        factors=factors,
        explanation=explanation,
    )


# ---------------------------------------------------------------------------
# 4. Recommendation (thin above-Core layer; does not modify frozen engine)
# ---------------------------------------------------------------------------
def build_recommendation(target: str, entity: str, risk, affected):
    recs = []
    sources = []

    if any("source_related" in a.relationship for a in affected):
        recs.append("Verify dependent tests before applying the change")
        sources.append("curated_repo_index")

    if risk.classification in ("medium", "high"):
        recs.append("Review governed outcomes and prior failures before the change")
        sources.append("engineering_risk_factors")

    if risk.classification == "high":
        recs.append("Require explicit approval and staged rollout")
        sources.append("engineering_risk_factors")

    if not recs:
        recs.append("No elevated engineering-change risk identified")
        sources.append("engineering_risk_factors")

    return Recommendation(
        text="; ".join(recs),
        evidence_source=",".join(sorted(set(sources))),
    )


# ---------------------------------------------------------------------------
# 5. Evidence contract
# ---------------------------------------------------------------------------
def build_evidence(target, entity, affected, risk, recommendation):
    evidence = [
        EvidenceItem(
            claim=f"Target resolved to '{entity}'",
            source="component_resolution",
            detail="exact match across module_id/context/container namespaces",
        )
    ]
    for a in affected:
        evidence.append(
            EvidenceItem(
                claim=f"Component '{a.component}' affected ({a.relationship})",
                source=a.evidence_source,
                detail="relationship from deterministic impact analysis",
            )
        )
    for f in risk.factors:
        evidence.append(
            EvidenceItem(
                claim=f"Risk factor '{f.name}' = {f.value}",
                source=f.evidence_source,
                detail="deterministic factor from repository/evidence",
            )
        )
    evidence.append(
        EvidenceItem(
            claim=f"Engineering-change risk = {risk.classification}",
            source="engineering_risk_rule",
            detail="; ".join(risk.explanation),
        )
    )
    evidence.append(
        EvidenceItem(
            claim=f"Recommendation: {recommendation.text}",
            source=recommendation.evidence_source,
            detail="thin above-Core recommendation layer",
        )
    )
    return evidence


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
def assess_engineering_change(target_component: str, proposed_change: str):
    """Read-only engineering change-impact & risk assessment.

    Returns an EngineeringChangeAssessment. Never mutates anything.
    """
    status, entity = resolve_component(target_component)

    if status != ResolutionStatus.RESOLVED:
        return EngineeringChangeAssessment(
            target=target_component,
            proposed_change=proposed_change,
            resolution=status,
            evidence=[
                EvidenceItem(
                    claim=f"Component resolution = {status.value}",
                    source="component_resolution",
                    detail="exact/unique resolution only; no fuzzy matching",
                )
            ],
        )

    affected = compute_impact(target_component, entity)
    risk = compute_risk(target_component, entity, affected)
    recommendation = build_recommendation(
        target_component, entity, risk, affected
    )
    evidence = build_evidence(
        target_component, entity, affected, risk, recommendation
    )

    return EngineeringChangeAssessment(
        target=target_component,
        proposed_change=proposed_change,
        resolution=status,
        resolved_entity=entity,
        affected_components=affected,
        risk=risk,
        recommendation=recommendation,
        evidence=evidence,
    )
