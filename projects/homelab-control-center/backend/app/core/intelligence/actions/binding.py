import hashlib
import json
from typing import Any

from app.core.intelligence.actions.models import ActionRequest


CANONICALIZATION_VERSION = "rmt-instruction-v1"


class InvalidInstruction(ValueError):
    pass


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise InvalidInstruction(f"Instruction is not canonical JSON: {exc}") from exc


def instruction_payload(
    *,
    governance_domain: str,
    action_id: str,
    decision_id: str,
    target: str,
    operation: str,
    parameters: dict,
    expected_outcome: Any,
    adapter_name: str,
) -> dict:
    if not governance_domain or not adapter_name:
        raise InvalidInstruction("Governance domain and adapter are required")
    if not isinstance(parameters, dict):
        raise InvalidInstruction("Instruction parameters must be an object")
    if hasattr(expected_outcome, "model_dump"):
        expected_outcome = expected_outcome.model_dump(mode="json")
    return {
        "canonicalization_version": CANONICALIZATION_VERSION,
        "governance_domain": governance_domain,
        "action_id": action_id,
        "decision_id": decision_id,
        "target": target,
        "operation": operation,
        "parameters": parameters,
        "expected_outcome": expected_outcome,
        "adapter_name": adapter_name,
    }


def digest_payload(payload: dict) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def bind_action(action: ActionRequest, adapter_name: str) -> tuple[str, dict]:
    payload = instruction_payload(
        governance_domain=action.governance_domain,
        action_id=action.action_id,
        decision_id=action.decision_id,
        target=action.component,
        operation=action.action_type.value,
        parameters=action.model_copy(deep=True).parameters,
        expected_outcome=action.expected_outcome,
        adapter_name=adapter_name,
    )
    return digest_payload(payload), payload


def bind_execution_request(request, adapter_name: str) -> tuple[str, dict]:
    payload = instruction_payload(
        governance_domain=request.governance_domain,
        action_id=request.action_id,
        decision_id=request.decision_id,
        target=request.target,
        operation=request.operation,
        parameters=request.model_copy(deep=True).parameters,
        expected_outcome=request.expected_outcome,
        adapter_name=adapter_name,
    )
    return digest_payload(payload), payload
