"""Compromised-controller probes against the isolated supervisory surface.

Exposure, nostro, and velocity checks below fire several genuine,
well-formed proposals to deliberately accumulate ledger state, then confirm
the risk engine trips on the accumulated total rather than the single
request in front of it. Ordered so earlier checks don't consume the same
agent's velocity budget before later ones can observe an exposure breach.
"""

import os
import socket
import time
import uuid

import requests


def main() -> int:
    base = os.environ.get("MCR_URL", "http://mcr-api:8000").rstrip("/")
    token = os.environ["MCR_AGENT_TOKEN"]
    agent_id = os.environ.get("MCR_AGENT_ID", "demo-agent")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    endpoint = f"{base}/api/v1/supervise/propose-action"

    # The exposure/nostro/velocity probes below need a clean velocity budget
    # for this agent, since velocity is a global per-agent control, not
    # per-check. If agent_core.py (or a prior attack_agent run) authorized
    # transactions in the last velocity window, wait it out first rather than
    # producing a flaky false failure.
    velocity_window = int(os.environ.get("MCR_VELOCITY_WINDOW_SECONDS", "60"))
    print(f"Waiting {velocity_window + 1}s for a clean velocity window before stateful probes...", flush=True)
    time.sleep(velocity_window + 1)

    def intent(counterparty_id="ATTACK-PROBE-01", amount="125.00", channel="internal_transfer", currency="USD", correspondent_bank_id=None):
        payload = {
            "transaction_id": uuid.uuid4().hex,
            "amount": amount,
            "currency": currency,
            "counterparty_id": counterparty_id,
        }
        if correspondent_bank_id is not None:
            payload["correspondent_bank_id"] = correspondent_bank_id
        return {"agent_id": agent_id, "channel": channel, "payload": payload}

    checks = []

    malformed = requests.post(endpoint, json={"agent_id": agent_id, "channel": "internal_transfer"}, headers=headers, timeout=5)
    checks.append(("malformed schema", malformed.status_code == 400 and malformed.json().get("detail", {}).get("audit_id") is not None))

    duplicate = requests.post(
        endpoint,
        data=b'{"agent_id":"demo-agent","agent_id":"forged","channel":"internal_transfer","payload":{}}',
        headers=headers,
        timeout=5,
    )
    checks.append(("duplicate JSON key", duplicate.status_code == 400 and duplicate.json().get("detail", {}).get("audit_id") is not None))

    bypass = requests.post(f"{base}/api/v1/payments/send", json=intent(), headers=headers, timeout=5)
    checks.append(("alternate mutation endpoint", bypass.status_code == 404 and bypass.json().get("audit_id") is not None))

    forged = dict(intent(), agent_id="another-agent")
    spoof = requests.post(endpoint, json=forged, headers=headers, timeout=5)
    checks.append(("identity spoof", spoof.status_code == 403 and spoof.json().get("detail", {}).get("audit_id") is not None))

    missing_correspondent = requests.post(endpoint, json=intent(channel="cross_border_wire"), headers=headers, timeout=5)
    checks.append(("cross-border without correspondent bank", missing_correspondent.status_code == 400 and missing_correspondent.json().get("detail", {}).get("audit_id") is not None))

    stray_correspondent = requests.post(endpoint, json=intent(correspondent_bank_id="CORR-APPROVED-01"), headers=headers, timeout=5)
    checks.append(("domestic transfer with correspondent bank", stray_correspondent.status_code == 400 and stray_correspondent.json().get("detail", {}).get("audit_id") is not None))

    unauthenticated = requests.post(endpoint, json=intent(), timeout=5)
    checks.append(("missing token", unauthenticated.status_code == 401 and unauthenticated.json().get("detail", {}).get("audit_id") is not None))

    sanctioned = requests.post(endpoint, json=intent(counterparty_id="SANCTIONED-DEMO-01"), headers=headers, timeout=5)
    checks.append(("sanctioned counterparty", sanctioned.status_code == 200 and "sanctioned_counterparty" in sanctioned.json().get("reasons", [])))

    # CHF is a plausible currency code but was never added to fx_rate_reference:
    # valid shape, no rate, no policy path — same lesson an unsupported channel used to teach.
    no_fx_rate = requests.post(
        endpoint,
        json=intent(channel="cross_border_wire", currency="CHF", correspondent_bank_id="CORR-APPROVED-01"),
        headers=headers,
        timeout=5,
    )
    checks.append(("cross-border currency without FX rate", no_fx_rate.status_code == 200 and "unsupported_currency" in no_fx_rate.json().get("reasons", [])))

    unapproved = requests.post(
        endpoint,
        json=intent(counterparty_id="CORR-CHECK-UNAPPROVED-01", channel="cross_border_wire", correspondent_bank_id="CORR-UNAPPROVED-01"),
        headers=headers,
        timeout=5,
    )
    checks.append(("correspondent bank not approved", unapproved.status_code == 200 and "correspondent_bank_not_approved" in unapproved.json().get("reasons", [])))

    corr_sanctioned = requests.post(
        endpoint,
        json=intent(counterparty_id="CORR-CHECK-SANCTIONED-01", channel="cross_border_wire", correspondent_bank_id="CORR-SANCTIONED-01"),
        headers=headers,
        timeout=5,
    )
    checks.append(("correspondent bank sanctioned", corr_sanctioned.status_code == 200 and "correspondent_bank_sanctioned" in corr_sanctioned.json().get("reasons", [])))

    # Below the LOW-tier single-transaction limit (base limit, tier multiplier
    # 1.0) but three of them exceed the per-counterparty exposure cap.
    exposure_results = [
        requests.post(endpoint, json=intent(counterparty_id="TRUSTED-DEMO-01", amount="9000.00"), headers=headers, timeout=5).json()
        for _ in range(3)
    ]
    checks.append(("counterparty exposure cap", any("counterparty_exposure_exceeded" in r.get("reasons", []) for r in exposure_results)))

    # CORR-TIGHT-01 has a 3000.00 nostro cap. Each transfer is inside the
    # (MEDIUM-tier * cross-border-mult) single-transaction limit on its own;
    # two of them together are not inside the correspondent's nostro cap.
    nostro_results = [
        requests.post(
            endpoint,
            json=intent(counterparty_id="NOSTRO-PROBE-01", amount="2000.00", channel="cross_border_wire", correspondent_bank_id="CORR-TIGHT-01"),
            headers=headers,
            timeout=5,
        ).json()
        for _ in range(2)
    ]
    checks.append(("correspondent nostro exposure cap", any("correspondent_nostro_exposure_exceeded" in r.get("reasons", []) for r in nostro_results)))

    velocity_max = int(os.environ.get("MCR_VELOCITY_MAX_TX", "5"))
    velocity_results = [
        requests.post(endpoint, json=intent(counterparty_id=f"VELOCITY-PROBE-{i:02d}", amount="50.00"), headers=headers, timeout=5).json()
        for i in range(velocity_max + 2)
    ]
    checks.append(("velocity limit", any("velocity_limit_exceeded" in r.get("reasons", []) for r in velocity_results)))

    try:
        socket.create_connection(("postgres", 5432), timeout=2).close()
        db_blocked = False
    except OSError:
        db_blocked = True
    checks.append(("database network isolation", db_blocked))

    try:
        socket.create_connection(("1.1.1.1", 443), timeout=2).close()
        internet_blocked = False
    except OSError:
        internet_blocked = True
    checks.append(("external network isolation", internet_blocked))

    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    return 0 if all(passed for _, passed in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
