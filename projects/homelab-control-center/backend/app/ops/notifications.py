"""RMT-PROD P0 (O2) -- held-action notifications.

Above-Core / operational. When a governed action enters
``manual_approval_required``, tell a human.

Guarantees:
  * **Fail-open** -- any transport / config problem is caught and logged; a
    notification failure never propagates into the governed path.
  * **Bounded** -- an optional per-key minimum interval stops an unattended
    loop from spamming the same hold.
  * **Safe before a sink exists** -- with ``RMT_NOTIFY_WEBHOOK_URL`` unset the
    call only writes a log line, so the hooks can land before a webhook is
    configured.
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

        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(
            req, timeout=ops_config.notify_timeout_seconds()
        ) as r:
            r.read()
        logger.info("held-for-approval notification sent: %s", key)
    except Exception as exc:  # fail-open -- never break the governed path
        logger.warning("held-for-approval notification failed: %r", exc)


def _reset_for_tests() -> None:
    _last_sent.clear()
