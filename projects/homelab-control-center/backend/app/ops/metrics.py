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
