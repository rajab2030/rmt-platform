"""RMT-PROD P0 (O2) + P1 (O3) -- operator notifications.

Above-Core / operational. Two "tell a human" hooks over one fail-open,
de-duped, stdlib-``urllib`` webhook sink (``RMT_NOTIFY_WEBHOOK_URL``):

  * ``notify_held``  (O2) -- a governed action entered
    ``manual_approval_required`` and awaits approval.
  * ``notify_ops``   (O3) -- an operational fault: the CAP-04 loop quarantined
    a component, or a loop cycle raised. (Service-down is out-of-band -- a
    down process cannot alert; see ``scripts/rmt-heartbeat.sh`` + the
    ``GET /health`` probe.)

Guarantees:
  * **Fail-open** -- any transport / config problem is caught and logged; a
    notification failure never propagates into the governed path.
  * **Bounded** -- an optional per-key minimum interval stops an unattended
    loop from spamming the same hold.
  * **Safe before a sink exists** -- with ``RMT_NOTIFY_WEBHOOK_URL`` unset the
    call only writes a log line, so the hooks can land before a webhook is
    configured.

T1-4 adds ``RMT_NOTIFY_FORMAT`` (``generic`` default / ``slack`` / ``ntfy``) so
the same webhook URL can point straight at a real channel. Escalation of a hold
that goes unactioned is handled out-of-process by
``backend/scripts/rmt-escalate.sh`` against the read-only ``GET /ops/holds``
route (the D4 / O3 external-check pattern -- no in-process timer here).
"""
import json
import logging
import time
import urllib.request

from app.ops import ops_config

logger = logging.getLogger("rmt.ops.notify")

# key -> monotonic timestamp of the last send
_last_sent: dict[str, float] = {}


def _key(kind: str, component: str, approval_id) -> str:
    return f"{kind}:{component}:{approval_id}"


def _post(url: str, payload: dict, *, summary: str, tags: str, priority: str) -> None:
    """POST ``payload`` to ``url`` shaped per ``RMT_NOTIFY_FORMAT`` (T1-4).

    ``generic`` (default) sends today's JSON object byte-for-byte; ``slack``
    sends ``{"text": summary}``; ``ntfy`` sends ``summary`` as a plain-text body
    with ``Title`` / ``Priority`` / ``Tags`` headers.
    """
    fmt = ops_config.notify_format()
    if fmt == "slack":
        data = json.dumps({"text": summary}).encode()
        headers = {"Content-Type": "application/json"}
    elif fmt == "ntfy":
        data = summary.encode()
        headers = {"Title": payload.get("event", "rmt"), "Priority": priority,
                   "Tags": tags}
    else:  # generic -- unchanged
        data = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"}

    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(
        req, timeout=ops_config.notify_timeout_seconds()
    ) as r:
        r.read()


def notify_held(
    *,
    kind: str,
    component: str,
    approval_id=None,
    detail: str = "",
    source: str = "",
) -> None:
    """Best-effort notification that an action awaits human approval.

    ``kind``: ``"remediation"`` | ``"agent_proposal"`` | ``"operator_execute"``.
    Never raises.
    """
    try:
        key = _key(kind, component, approval_id)
        now = time.monotonic()
        prev = _last_sent.get(key)
        interval = ops_config.notify_min_interval_seconds()
        if prev is not None and (now - prev) < interval:
            return
        _last_sent[key] = now

        payload = {
            "event": "held_for_approval",
            "kind": kind,
            "component": component,
            "approval_id": approval_id,
            "detail": detail,
            "source": source,
        }

        url = ops_config.notify_webhook_url()
        if url is None:
            logger.warning(
                "HELD FOR APPROVAL (no RMT_NOTIFY_WEBHOOK_URL configured): %s",
                payload,
            )
            return

        summary = (
            f"HELD FOR APPROVAL [{kind}] {component} "
            f"approval_id={approval_id}"
            + (f" -- {detail}" if detail else "")
        )
        _post(url, payload, summary=summary, tags="warning,hourglass",
              priority="high")
        logger.info("held-for-approval notification sent: %s", key)
    except Exception as exc:  # fail-open -- never break the governed path
        logger.warning("held-for-approval notification failed: %r", exc)


def notify_ops(
    *,
    kind: str,
    detail: str = "",
    key: str = "",
    source: str = "",
) -> None:
    """Best-effort notification of an operational fault (O3).

    ``kind``: ``"loop_quarantine"`` | ``"loop_cycle_error"`` (extensible).
    ``key``: de-dupe discriminator within the kind (e.g. the component name),
    so a persistently-failing loop alerts about once per ``notify_min_interval``
    rather than every cycle. Never raises.
    """
    try:
        dedupe = f"ops:{kind}:{key}"
        now = time.monotonic()
        prev = _last_sent.get(dedupe)
        interval = ops_config.notify_min_interval_seconds()
        if prev is not None and (now - prev) < interval:
            return
        _last_sent[dedupe] = now

        payload = {
            "event": "ops_alert",
            "kind": kind,
            "key": key,
            "detail": detail,
            "source": source,
        }

        url = ops_config.notify_webhook_url()
        if url is None:
            logger.warning(
                "OPS ALERT (no RMT_NOTIFY_WEBHOOK_URL configured): %s", payload
            )
            return

        summary = (
            f"OPS ALERT [{kind}] {key}" + (f" -- {detail}" if detail else "")
        )
        _post(url, payload, summary=summary, tags="rotating_light",
              priority="urgent")
        logger.info("ops-alert notification sent: %s", dedupe)
    except Exception as exc:  # fail-open -- never break the loop
        logger.warning("ops-alert notification failed: %r", exc)


def _reset_for_tests() -> None:
    _last_sent.clear()
