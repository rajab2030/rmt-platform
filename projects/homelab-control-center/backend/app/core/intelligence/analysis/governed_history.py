"""L1 - read-only governed-history aggregation boundary.

Learning consumes evidence about what happened. It NEVER decides that something
should happen next.

This module is STRICTLY READ-ONLY with respect to governed execution:
  * it consumes only existing read-only query/history interfaces;
  * it NEVER calls execute_governed_action / execution_engine.execute;
  * it NEVER mints authorization;
  * it NEVER mutates approval/authorization/audit/trace/verification records;
  * it NEVER invokes adapters and NEVER creates a second mutation boundary.

Correlation follows the approved C04-L1 contract:
  primary   : action_id
  secondary : execution_id
  further   : approval_id, authorization_id (provenance only)

Provenance/source classification remains inspectable so observation/evaluation
history and governed lifecycle evidence are never flattened together.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

# Read-only interfaces only. Importing a store's reader is not importing its
# mutation service, and we never call any save/write method here.
from app.core.intelligence.execution.history import execution_history
from app.core.intelligence.execution.trace_history import execution_trace_history
from app.core.intelligence.verification.storage import verification_storage
from app.core.intelligence.actions.approval_storage import (
    approval_record_storage,
)
from app.core.intelligence.actions.authorization_storage import (
    execution_authorization_storage,
)


class GovernedOutcomeView(BaseModel):
    """Normalized read model of one correlated governed action/episode."""

    action_id: str
    execution_id: Optional[str] = None
    component: str = ""
    operation: str = ""

    # Provenance / contextual evidence (never an authorization source).
    decision_provenance: str = ""
    policy_decision: str = ""
    risk_level: str = ""
    approval_type: str = ""
    approval_decision: str = ""
    authorization_status: str = ""

    # Outcome evidence.
    execution_status: str = ""
    verification_status: str = ""
    outcome: str = ""  # e.g. "blocked", "completed", adapter status

    created_at: Optional[datetime] = None

    # Source classification: which durable stores contributed to this view.
    sources: List[str] = []


def _earliest(candidates):
    dates = [c for c in candidates if c is not None]
    return min(dates) if dates else None


def get_governed_outcomes(
    component: Optional[str] = None,
) -> List[GovernedOutcomeView]:
    """
    Aggregate correlated governed lifecycle evidence into read-model views.

    Returns a new list of GovernedOutcomeView (derived, not persisted). No
    record is written; no mutation boundary is touched. If `component` is given,
    only views attributable to that component are returned.
    """
    audits = list(execution_history.get_all())
    traces = list(execution_trace_history.get_all())
    verifications = list(verification_storage.get_all())
    approvals = list(approval_record_storage.get_all())
    authorizations = list(execution_authorization_storage.get_all())

    verif_by_exec = {v.execution_id: v for v in verifications}
    authz_by_action = {a.action_id: a for a in authorizations}
    approvals_by_action = {}
    for ap in approvals:
        approvals_by_action.setdefault(ap.action_id, []).append(ap)

    # Discover every correlated action episode.
    action_ids = set()
    for r in audits:
        action_ids.add(r.action_id)
    for t in traces:
        action_ids.add(t.action_id)
    for a in authorizations:
        action_ids.add(a.action_id)
    for ap in approvals:
        action_ids.add(ap.action_id)

    views = []

    for action_id in sorted(action_ids):
        a_traces = [t for t in traces if t.action_id == action_id]
        a_audits = [x for x in audits if x.action_id == action_id]
        a_authz = authz_by_action.get(action_id)
        a_approvals = approvals_by_action.get(action_id, [])

        execution_ids = {t.execution_id for t in a_traces if t.execution_id}
        execution_ids.update(x.execution_id for x in a_audits)
        a_verifs = [
            verif_by_exec[eid]
            for eid in execution_ids
            if eid in verif_by_exec
        ]

        # Outcome evidence.
        outcome = ""
        exec_status = ""
        policy_decision = ""
        risk_level = ""

        if a_audits:
            # Audit exists -> this reached the adapter (completed outcome).
            last_audit = max(a_audits, key=lambda x: x.created_at)
            exec_status = last_audit.status
            outcome = "completed"
            sources = ["audit"]
        else:
            # No audit -> possibly a blocked/denied path. Use trace evidence.
            sources = []
            if a_traces:
                last_trace = max(a_traces, key=lambda x: x.created_at)
                outcome = last_trace.outcome  # e.g. "blocked"
                exec_status = last_trace.outcome
                sources.append("trace")

        # policy/risk: prefer trace (it carries the explicit policy decision),
        # fall back to audit evidence otherwise.
        if a_traces:
            last_trace = max(a_traces, key=lambda x: x.created_at)
            policy_decision = last_trace.policy_decision or ""
            risk_level = last_trace.risk_level or ""
        elif a_audits:
            last_audit = max(a_audits, key=lambda x: x.created_at)
            policy_decision = last_audit.decision_reason or ""
            risk_level = last_audit.risk_level or ""

        # A correlated trace is itself consulted evidence (policy/risk/outcome).
        if a_traces and "trace" not in sources:
            sources.append("trace")

        # Verification outcome (secondary correlation by execution_id).
        verification_status = ""
        if a_verifs:
            verification_status = a_verifs[-1].status
            sources.append("verification")

        # Component/operation/target attribution.
        component_name = ""
        operation = ""
        if a_authz:
            component_name = a_authz.target or ""
            operation = a_authz.operation or ""
            sources.append("authorization")
        elif a_audits and a_audits[0].message:
            # audit has no component; component best-effort from verification
            pass

        # Approval provenance (contextual only).
        approval_type = ""
        approval_decision = ""
        if a_approvals:
            approval_type = ";".join(sorted({ap.decision for ap in a_approvals}))
            approval_decision = approval_type
            sources.append("approval")

        authorization_status = a_authz.status if a_authz else ""

        decision_provenance = a_authz.decision_id or "" if a_authz else ""

        created_at = _earliest(
            [r.created_at for r in a_audits]
            + [r.created_at for r in a_traces]
            + [r.created_at for r in a_verifs]
            + [r.created_at for r in a_approvals]
            + ([a_authz.created_at] if a_authz else [])
        )

        view = GovernedOutcomeView(
            action_id=action_id,
            execution_id=(
                next(iter(execution_ids)) if execution_ids else None
            ),
            component=component_name,
            operation=operation,
            decision_provenance=decision_provenance,
            policy_decision=policy_decision,
            risk_level=risk_level,
            approval_type=approval_type,
            approval_decision=approval_decision,
            authorization_status=authorization_status,
            execution_status=exec_status,
            verification_status=verification_status,
            outcome=outcome,
            created_at=created_at,
            sources=sorted(set(sources)),
        )

        if component and view.component != component:
            continue

        views.append(view)

    return views
