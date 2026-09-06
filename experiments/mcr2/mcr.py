"""
MCR — supervisory layer (Experiment #2)
========================================
Supervises the world's mutation boundary. MCR is consulted by World.mutate()
for every consequential mutation attempt, regardless of which tool/interface/
mechanism caused it.

Responsibilities: policy, authority, risk/restriction, ALLOW/DENY/HOLD,
evidence, audit, verification.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

ALLOW = "ALLOW"
HOLD = "HOLD"
DENY = "DENY"
STOP = "STOP"


class Policy:
    """Classifies operations. Consequential operations are governed."""

    def __init__(self) -> None:
        # operation -> classification
        self._rules: Dict[str, str] = {
            "start": "allowed",
            "stop": "restricted",
            "restart": "restricted",
            "update_config": "restricted",
            "run_command": "restricted",   # consequential -> governed at the boundary
        }

    def classify(self, operation: str) -> str:
        return self._rules.get(operation, "denied")

    def is_consequential(self, operation: str) -> bool:
        return self.classify(operation) in ("allowed", "restricted")


class Authority:
    """Tracks authorization grants for an agent."""

    def __init__(self) -> None:
        self._grants: List[Dict[str, Any]] = []

    def request(self, agent: str, operation: str, target: str) -> Dict[str, Any]:
        grant = {
            "id": str(uuid.uuid4())[:8],
            "agent": agent, "operation": operation, "target": target,
            "status": "held", "created": time.time(),
        }
        self._grants.append(grant)
        return grant

    def has_valid(self, agent: str, operation: str, target: str) -> bool:
        return any(
            g["agent"] == agent and g["operation"] == operation
            and g["target"] == target and g["status"] == "approved"
            for g in self._grants
        )

    def approve(self, grant_id: str) -> bool:
        for g in self._grants:
            if g["id"] == grant_id:
                g["status"] = "approved"
                return True
        return False

    def snapshot(self) -> List[Dict[str, Any]]:
        return [dict(g) for g in self._grants]


class Evidence:
    """Durable machine-readable audit of every supervisory decision."""

    def __init__(self) -> None:
        self.records: List[Dict[str, Any]] = []

    def record(self, entry: Dict[str, Any]) -> None:
        entry = dict(entry)
        entry.setdefault("ts", time.time())
        entry.setdefault("evidence_id", str(uuid.uuid4())[:8])
        self.records.append(entry)

    def to_json(self) -> str:
        import json
        return json.dumps(self.records, indent=2, sort_keys=True)


class MCR:
    """Supervisory layer consulted at the world's mutation boundary."""

    def __init__(self, policy: Optional[Policy] = None, authority: Optional[Authority] = None) -> None:
        self.policy = policy or Policy()
        self.authority = authority or Authority()
        self.evidence = Evidence()

    def evaluate(
        self,
        operation: str,
        target: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        requester: str = "ATLAS",
        request_auth: bool = False,
        intent: str = "",
        observed: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Evaluate a mutation attempt at the boundary. Returns a decision."""
        params = params or {}
        classification = self.policy.classify(operation)

        if classification == "denied":
            self._audit(operation, target, params, DENY, requester, intent, observed,
                        "operation denied by policy")
            return {"decision": DENY, "operation": operation, "target": target,
                    "classification": classification, "message": "denied by policy"}

        if classification == "allowed":
            self._audit(operation, target, params, ALLOW, requester, intent, observed,
                        "allowed by policy")
            return {"decision": ALLOW, "operation": operation, "target": target,
                    "classification": classification, "message": "allowed by policy"}

        if classification == "restricted":
            if self.authority.has_valid(requester, operation, target):
                self._audit(operation, target, params, ALLOW, requester, intent, observed,
                            "authorized")
                return {"decision": ALLOW, "operation": operation, "target": target,
                        "classification": classification, "message": "authorized"}

            if request_auth:
                grant = self.authority.request(requester, operation, target)
                self._audit(operation, target, params, HOLD, requester, intent, observed,
                            f"held pending approval (grant {grant['id']})")
                return {"decision": HOLD, "operation": operation, "target": target,
                        "classification": classification, "grant_id": grant["id"],
                        "message": "held pending approval"}

            self._audit(operation, target, params, DENY, requester, intent, observed,
                        "no valid authorization")
            return {"decision": DENY, "operation": operation, "target": target,
                    "classification": classification, "message": "no valid authorization"}

        self._audit(operation, target, params, STOP, requester, intent, observed,
                    "unknown classification")
        return {"decision": STOP, "operation": operation, "target": target,
                "classification": classification, "message": "unknown classification"}

    def verify(self, expected: Dict[str, Any], actual: Dict[str, Any]) -> Dict[str, Any]:
        ok = True
        mismatches = []
        for k, ev in expected.items():
            av = actual.get(k)
            if av != ev:
                ok = False
                mismatches.append({"field": k, "expected": ev, "actual": av})
        result = {"verified": ok, "mismatches": mismatches}
        self.evidence.record({"kind": "verification", "expected": expected,
                              "actual": actual, "result": result})
        return result

    def _audit(self, operation, target, params, decision, requester, intent, observed, reason) -> None:
        clean = {k: v for k, v in params.items() if not k.startswith("_")}
        self.evidence.record({
            "kind": "mcr_decision",
            "agent": requester,
            "operation": operation,
            "target": target,
            "params": clean,
            "decision": decision,
            "stated_intent": intent,
            "observed_state": observed,
            "reason": reason,
        })
