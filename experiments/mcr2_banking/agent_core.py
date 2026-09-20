"""Subordinate controller with local intent generation and no database access."""

import argparse
import os
import random
import uuid

import requests

CHANNELS = ["internal_transfer", "domestic_wire", "cross_border_wire"]
CHANNEL_WEIGHTS = [4, 4, 2]
COUNTERPARTIES = [
    "TRUSTED-DEMO-01",
    "HIGHRISK-DEMO-01",
    "SANCTIONED-DEMO-01",
    "ACME-CORP-042",
    "GLOBEX-018",
    "INITECH-007",
]
CORRESPONDENT_BANKS = [
    "CORR-APPROVED-01",
    "CORR-TIGHT-01",
    "CORR-UNAPPROVED-01",
    "CORR-SANCTIONED-01",
]
# USD included so cross-border proposals sometimes skip FX conversion entirely.
CROSS_BORDER_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CAD"]


def generate_intent(rng: random.Random, agent_id: str) -> dict:
    channel = rng.choices(CHANNELS, weights=CHANNEL_WEIGHTS)[0]
    is_cross_border = channel == "cross_border_wire"
    amount = rng.choice(["125.00", "2500.00", "4500.00", "8500.00"])
    payload = {
        "transaction_id": uuid.uuid4().hex,
        "amount": amount,
        "currency": rng.choice(CROSS_BORDER_CURRENCIES) if is_cross_border else "USD",
        "counterparty_id": rng.choice(COUNTERPARTIES),
    }
    if is_cross_border:
        payload["correspondent_bank_id"] = rng.choice(CORRESPONDENT_BANKS)
    proposal = {"agent_id": agent_id, "channel": channel, "payload": payload}
    if rng.random() < 0.2:
        if rng.choice([True, False]):
            del proposal["payload"]["counterparty_id"]
        else:
            proposal["payload"]["amount"] = "not-a-number"
    return proposal


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    url = os.environ.get("MCR_URL", "http://mcr-api:8000").rstrip("/")
    agent_id = os.environ.get("MCR_AGENT_ID", "demo-agent")
    token = os.environ["MCR_AGENT_TOKEN"]
    for _ in range(args.count):
        intent = generate_intent(rng, agent_id)
        try:
            response = requests.post(
                f"{url}/api/v1/supervise/propose-action",
                json=intent,
                headers={"Authorization": f"Bearer {token}"},
                timeout=5,
            )
            result = response.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"Execution Blocked by Supervisor (unavailable: {exc})", flush=True)
            continue
        if response.ok and result.get("decision") == "Authorized":
            print(f"Execution Proceeding (simulated release; audit_id={result['audit_id']})", flush=True)
        else:
            detail = result.get("detail", result)
            print(f"Execution Blocked by Supervisor ({detail})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
