"""RMT-PROD P2 (O4) -- platform self-metrics in Prometheus text format.

Above-Core / operational. **Read-only** derivation from state the platform
already keeps (the operational-loop status object and the six durable evidence
stores) -- no new evidence category, no ``app/core/**`` change, no write path.

``render_prometheus()`` returns a ``text/plain; version=0.0.4`` exposition body
for ``GET /metrics``. Every store read is wrapped: a read failure increments
``rmt_metrics_scrape_errors_total`` and is skipped rather than failing the whole
scrape.
"""
from collections import Counter

from app.core.intelligence.actions.approval_storage import (
    approval_hold_storage,
    approval_record_storage,
)
from app.core.intelligence.actions.authorization_storage import (
    execution_authorization_storage,
)
from app.core.intelligence.execution.storage import execution_audit_storage
from app.core.intelligence.verification.storage import verification_storage

CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


def _line(name: str, value, labels: dict | None = None) -> str:
    if labels:
        inner = ",".join(f'{k}="{_escape(str(v))}"' for k, v in labels.items())
        return f"{name}{{{inner}}} {value}"
    return f"{name} {value}"


def _escape(v: str) -> str:
    return v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def render_prometheus() -> str:
    from app.homelab.operational_loop import operational_loop

    out: list[str] = []
    errors = 0

    out.append("# HELP rmt_up 1 while the RMT process is serving.")
    out.append("# TYPE rmt_up gauge")
    out.append(_line("rmt_up", 1))

    # --- operational loop -----------------------------------------------------
    try:
        loop = operational_loop.get_status()
        out.append("# TYPE rmt_loop_enabled gauge")
        out.append(_line("rmt_loop_enabled", int(bool(loop.get("enabled")))))
        out.append("# TYPE rmt_loop_running gauge")
        out.append(_line("rmt_loop_running", int(bool(loop.get("running")))))
        out.append("# TYPE rmt_loop_cycles_total counter")
        out.append(_line("rmt_loop_cycles_total", int(loop.get("cycle_count") or 0)))
        out.append("# TYPE rmt_loop_cycle_error gauge")
        out.append(_line("rmt_loop_cycle_error", int(loop.get("last_cycle_error") is not None)))
        quarantined = [
            n for n, s in (loop.get("components") or {}).items() if s.get("quarantined")
        ]
        out.append("# TYPE rmt_loop_quarantined_components gauge")
        out.append(_line("rmt_loop_quarantined_components", len(quarantined)))
    except Exception:
        errors += 1

    # --- approval holds (queue depth) --------------------------------------
    try:
        holds = Counter(getattr(h, "status", "unknown") for h in approval_hold_storage.get_all())
        holds_str = {str(getattr(k, "value", k)): v for k, v in holds.items()}
        out.append("# HELP rmt_approval_holds Approval holds on disk by status.")
        out.append("# TYPE rmt_approval_holds gauge")
        for status in ("pending", "approved", "rejected"):
            out.append(_line("rmt_approval_holds", holds_str.get(status, 0), {"status": status}))
    except Exception:
        errors += 1

    # --- approval decisions --------------------------------------------------
    try:
        recs = Counter(
            getattr(r, "decision", "unknown") for r in approval_record_storage.get_all()
        )
        out.append("# TYPE rmt_approval_records_total counter")
        for decision, n in sorted(recs.items()):
            out.append(_line("rmt_approval_records_total", n, {"decision": str(decision)}))
    except Exception:
        errors += 1

    # --- verification outcomes -------------------------------------------
    try:
        vers = Counter(getattr(v, "status", "unknown") for v in verification_storage.get_all())
        out.append("# HELP rmt_verifications_total Post-execution verification outcomes.")
        out.append("# TYPE rmt_verifications_total counter")
        for status, n in sorted(vers.items()):
            out.append(_line("rmt_verifications_total", n, {"status": str(status)}))
    except Exception:
        errors += 1

    # --- executions that reached an adapter ------------------------------
    try:
        audit = execution_audit_storage.get_all()
        by_adapter = Counter(getattr(a, "adapter", "unknown") for a in audit)
        out.append("# HELP rmt_executions_total Governed executions that reached an adapter.")
        out.append("# TYPE rmt_executions_total counter")
        for adapter, n in sorted(by_adapter.items()):
            out.append(_line("rmt_executions_total", n, {"adapter": str(adapter)}))
    except Exception:
        errors += 1

    # --- authorizations issued -----------------------------------------
    try:
        out.append("# TYPE rmt_authorizations_total counter")
        out.append(
            _line("rmt_authorizations_total", len(execution_authorization_storage.get_all()))
        )
    except Exception:
        errors += 1

    # --- executed actions vs verified (B1b effective-status index) --------
    # Values come from the index projection (one row per execution_id), not the
    # raw verification store -- so a single executed action is counted once even
    # though B1a can leave two records (Core observation_unavailable + the
    # above-Core record) for it. Labelled by adapter + operation (bounded).
    try:
        from app.ops.verification.index import snapshot as _vindex_snapshot

        agg: dict = {}
        for r in _vindex_snapshot():
            k = (r.adapter or "unknown", r.operation or "unknown")
            a = agg.setdefault(
                k, {"total": 0, "verified": 0, "unverified": 0, "state_mismatch": 0}
            )
            a["total"] += 1
            if r.verified:
                a["verified"] += 1
            if r.effective_status == "unverified":
                a["unverified"] += 1
            if r.effective_status == "state_mismatch":
                a["state_mismatch"] += 1
        out.append(
            "# HELP rmt_executed_actions_total Executed governed actions in the "
            "above-Core verification index."
        )
        out.append("# TYPE rmt_executed_actions_total counter")
        out.append("# TYPE rmt_executed_actions_verified_total counter")
        out.append("# TYPE rmt_executed_actions_unverified_total counter")
        out.append("# TYPE rmt_executed_actions_state_mismatch_total counter")
        for (adapter, operation), a in sorted(agg.items()):
            lbl = {"adapter": adapter, "operation": operation}
            out.append(_line("rmt_executed_actions_total", a["total"], lbl))
            out.append(_line("rmt_executed_actions_verified_total", a["verified"], lbl))
            out.append(_line("rmt_executed_actions_unverified_total", a["unverified"], lbl))
            out.append(
                _line("rmt_executed_actions_state_mismatch_total", a["state_mismatch"], lbl)
            )
    except Exception:
        errors += 1

    # --- approval latency (T0-3): hold.created_at -> record.created_at ------
    # Only records whose approval_id matches an actual hold count -- an
    # auto-approval never held, so it has no latency to measure.
    try:
        holds_by_id = {h.approval_id: h for h in approval_hold_storage.get_all()}
        latency = Counter()
        count = Counter()
        for r in approval_record_storage.get_all():
            hold = holds_by_id.get(r.approval_id)
            if hold is None:
                continue
            seconds = (r.created_at - hold.created_at).total_seconds()
            latency[str(r.decision)] += seconds
            count[str(r.decision)] += 1
        out.append(
            "# HELP rmt_approval_latency_seconds Time from hold creation to "
            "approval decision, by decision."
        )
        out.append("# TYPE rmt_approval_latency_seconds_sum counter")
        out.append("# TYPE rmt_approval_latency_seconds_count counter")
        for decision in sorted(count):
            lbl = {"decision": decision}
            out.append(_line("rmt_approval_latency_seconds_sum", latency[decision], lbl))
            out.append(_line("rmt_approval_latency_seconds_count", count[decision], lbl))
    except Exception:
        errors += 1

    # --- agent surface ------------------------------------------------------
    try:
        from app.agent.authority import authority_store
        from app.agent import loop_config as agent_cfg

        out.append("# TYPE rmt_agent_enabled gauge")
        out.append(_line("rmt_agent_enabled", int(bool(agent_cfg.AGENT_ENABLED))))
        out.append("# TYPE rmt_agent_active_grants gauge")
        out.append(_line("rmt_agent_active_grants", len(authority_store.list_active())))
    except Exception:
        errors += 1

    out.append("# TYPE rmt_metrics_scrape_errors_total counter")
    out.append(_line("rmt_metrics_scrape_errors_total", errors))

    return "\n".join(out) + "\n"
