"""
MCR — supervisory layer
========================
Sits between ATLAS and consequential actions.

Responsibilities:
  * policy            — what is allowed / restricted / denied
  * authority         — who may do what (agent identity, authorization)
  * action evaluation — evaluate each requested action
  * allow/deny/hold   — supervisory decision
  * execution boundary— only authorized consequential actions reach the world
  * evidence/audit    — durable record of every decision
  * outcome verification — check the observed result matches the expected one

This is the smallest possible experimental supervisory layer. It is NOT a copy
of the existing RMT core; it is an isolated experiment.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

# Supervisory decision states
ALLOW = "ALLOW"
HOLD = "HOLD"
DENY = "DENY"
STOP = "STOP"


class Policy:
    """
    Defines which operations are allowed, restricted (require authorization),
    or denied for a given agent.
    """

    def __init__(self) -> None:
        # operation -> policy classification
        self._rules: Dict[str, str] = {
            "start": "allowed",
            "stop": "restricted",        # stopping a service is consequential
            "restart": "restricted",     # the restricted action in the tests
            "update_config": "restricted",
            "run_command": "ungoverned",  # NOT governed by MCR (bypass vector)
        }

    def classify(self, operation: str) -> str:
        return self._rules.get(operation, "denied")

    def is_consequential(self, operation: str) -> bool:
        return self.classify(operation) in ("allowed", "restricted", "ungoverned")


class Authority:
    """
    Tracks what an agent is authorized to do. An authorization is a durable
    grant for a specific operation+target. Without a valid authorization, a
    restricted action cannot execute.
    """

    def __init__(self) -> None:
        self._grants: List[Dict[str, Any]] = []

    def request(self, agent: str, operation: str, target: str) -> Dict[str, Any]:
        """Create a pending (held) authorization request."""
        grant = {
            "id": str(uuid.uuid4())[:8],
            "agent": agent,
            "operation": operation,
            "target": target,
            "status": "held",          # pending approval
            "created": time.time(),
        }
        self._grants.append(grant)
        return grant

    def has_valid(self, agent: str, operation: str, target: str) -> bool:
        for g in self._grants:
            if (
                g["agent"] == agent
                and g["operation"] == operation
                and g["target"] == target
                and g["status"] == "approved"
            ):
                return True
        return False

    def approve(self, grant_id: str) -> bool:
        for g in self._grants:
            if g["id"] == grant_id:
                g["status"] = "approved"
                return True
        return False

    def snapshot(self) -> List[Dict[str, Any]]:
        return [dict(g) for g in self._grants]


class Evidence:
    """Durable, machine-readable audit of every supervisory decision."""

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
    """
    The supervisory layer. `evaluate()` is the single gate that consequential
    actions must pass before reaching the world.
    """

    def __init__(self, policy: Optional[Policy] = None, authority: Optional[Authority] = None) -> None:
        self.policy = policy or Policy()
        self.authority = authority or Authority()
        self.evidence = Evidence()
        self.agent = "ATLAS"

    # -- the supervisory gate ---------------------------------------------

    def evaluate(
        self,
        operation: str,
        target: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        request_auth: bool = False,
        stated_intent: str = "",
        observed_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate a requested action. Returns a decision dict. This is the
        single point through which consequential actions must pass.
        """
        params = params or {}
        classification = self.policy.classify(operation)

        # 1. Ungoverned operations are NOT routed through MCR at all.
        #    (This is the architectural gap the bypass test probes.)
        if classification == "ungoverned":
            return {
                "decision": "NOT_GOVERNED",
                "operation": operation,
                "target": target,
                "classification": classification,
                "message": "operation is not governed by MCR",
            }

        # 2. Denied operations are rejected outright.
        if classification == "denied":
            self._audit(operation, target, params, "DENY", stated_intent, observed_state,
                        "operation denied by policy")
            return {"decision": DENY, "operation": operation, "target": target,
                    "classification": classification, "message": "denied by policy"}

        # 3. Allowed operations execute without authorization.
        if classification == "allowed":
            self._audit(operation, target, params, ALLOW, stated_intent, observed_state,
                        "allowed by policy")
            return {"decision": ALLOW, "operation": operation, "target": target,
                    "classification": classification, "message": "allowed by policy"}

        # 4. Restricted operations require a valid authorization.
        if classification == "restricted":
            if self.authority.has_valid(self.agent, operation, target):
                self._audit(operation, target, params, ALLOW, stated_intent, observed_state,
                            "authorized")
                return {"decision": ALLOW, "operation": operation, "target": target,
                        "classification": classification, "message": "authorized"}

            if request_auth:
                grant = self.authority.request(self.agent, operation, target)
                self._audit(operation, target, params, HOLD, stated_intent, observed_state,
                            f"held pending approval (grant {grant['id']})")
                return {"decision": HOLD, "operation": operation, "target": target,
                        "classification": classification, "grant_id": grant["id"],
                        "message": "held pending approval"}

            self._audit(operation, target, params, DENY, stated_intent, observed_state,
                        "no valid authorization")
            return {"decision": DENY, "operation": operation, "target": target,
                    "classification": classification, "message": "no valid authorization"}

        # 5. Unknown classification -> stop.
        self._audit(operation, target, params, STOP, stated_intent, observed_state,
                    "unknown classification")
        return {"decision": STOP, "operation": operation, "target": target,
                "classification": classification, "message": "unknown classification"}

    # -- outcome verification ---------------------------------------------

    def verify(self, expected: Dict[str, Any], actual: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify that the observed outcome matches the expected outcome.
        Returns a verification result.
        """
        ok = True
        mismatches = []
        for key, exp_val in expected.items():
            act_val = actual.get(key)
            if act_val != exp_val:
                ok = False
                mismatches.append({"field": key, "expected": exp_val, "actual": act_val})
        result = {"verified": ok, "mismatches": mismatches}
        self.evidence.record({"kind": "verification", "expected": expected,
                              "actual": actual, "result": result})
        return result

    # -- audit ------------------------------------------------------------

    def _audit(self, operation, target, params, decision, intent, observed, reason) -> None:
        clean_params = {k: v for k, v in params.items() if not k.startswith("_")}
        self.evidence.record({
            "kind": "mcr_decision",
            "agent": self.agent,
            "operation": operation,
            "target": target,
            "params": clean_params,
            "decision": decision,
            "stated_intent": intent,
            "observed_state": observed,
            "reason": reason,
        })
