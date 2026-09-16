from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from app.budget.models import (
    ADAPTER_NAME,
    GOVERNANCE_DOMAIN,
    BudgetError,
    BudgetRole,
    FinancialOutcome,
    MutationType,
)
from app.budget.observer import budget_observer
from app.budget.repository import budget_repository
from app.core.intelligence.actions.approval_storage import approval_record_storage
from app.core.intelligence.actions.authorization_storage import (
    execution_authorization_storage,
)
from app.core.intelligence.actions.binding import bind_action
from app.core.intelligence.actions.models import ActionRequest, ActionType
from app.core.intelligence.actions.service import execute_governed_action
from app.core.intelligence.verification.models import ExpectedOutcome
from app.core.intelligence.verification.storage import verification_storage


class BudgetService:
    def bootstrap(self, actor: str, data) -> dict:
        replay = self._replay(
            data.idempotency_key,
            MutationType.BOOTSTRAP,
            {
                "organization_name": data.organization_name.strip(),
                "budget_name": data.budget_name.strip(),
                "owner_type": data.owner_type,
                "owner_name": data.owner_name.strip() or data.budget_name.strip(),
                "period_start": data.period_start.isoformat(),
                "period_end": data.period_end.isoformat(),
                "currency": data.currency,
                "allocation_minor": data.allocation_minor,
                "owner_principal": data.owner_principal.strip(),
                "requester_principal": data.requester_principal.strip(),
                "actor": actor,
            },
        )
        if replay:
            return replay
        organization_id = str(uuid4())
        budget_id = str(uuid4())
        parameters = {
            "mutation_type": MutationType.BOOTSTRAP.value,
            "organization_id": organization_id,
            "organization_name": data.organization_name.strip(),
            "budget_id": budget_id,
            "budget_name": data.budget_name.strip(),
            "owner_type": data.owner_type,
            "owner_name": data.owner_name.strip() or data.budget_name.strip(),
            "period_start": data.period_start.isoformat(),
            "period_end": data.period_end.isoformat(),
            "currency": data.currency,
            "allocation_minor": data.allocation_minor,
            "owner_principal": data.owner_principal.strip(),
            "requester_principal": data.requester_principal.strip(),
            "actor": actor,
            "idempotency_key": data.idempotency_key,
            "expected_available_minor": data.allocation_minor,
        }
        action = self._action(
            parameters,
            decision_id=f"budget-bootstrap-{uuid4()}",
            component=budget_id,
            reason=f"Initialize Budget Control for {data.organization_name}",
        )
        return self._execute(action)

    def create_request(self, actor: str, data) -> dict:
        return budget_repository.create_request(
            actor=actor,
            budget_id=data.budget_id,
            amount_minor=data.amount_minor,
            currency=data.currency,
            purpose=data.purpose,
            supporting_reference=data.supporting_reference,
        )

    def add_request_version(self, actor: str, request_id: str, data) -> dict:
        return budget_repository.add_request_version(
            actor=actor,
            request_id=request_id,
            amount_minor=data.amount_minor,
            currency=data.currency,
            purpose=data.purpose,
            supporting_reference=data.supporting_reference,
        )

    def decide(self, actor: str, request_id: str, data) -> dict:
        request = budget_repository.request_detail(actor, request_id)
        decision_id = str(uuid4())
        if data.decision == "rejected":
            return budget_repository.save_decision(
                decision_id=decision_id,
                actor=actor,
                request_id=request_id,
                decision="rejected",
                reason=data.reason,
                instruction_digest=None,
                action_json=None,
                balance_evidence_minor=None,
            )
        current = self._current_version(request)
        available = budget_repository.available_minor(request["budget_id"])
        parameters = {
            "mutation_type": MutationType.COMMITMENT.value,
            "organization_id": request["organization_id"],
            "budget_id": request["budget_id"],
            "request_id": request_id,
            "request_version": request["current_version"],
            "currency": current["currency"],
            "amount_minor": current["amount_minor"],
            "actor": actor,
            "domain_approval_id": decision_id,
            "idempotency_key": f"commit:{decision_id}",
            "balance_evidence_minor": available,
            "expected_available_minor": available - current["amount_minor"],
        }
        action = self._action(
            parameters,
            action_id=str(uuid4()),
            decision_id=decision_id,
            component=request["budget_id"],
            reason=f"Commit approved purchase request {request_id}",
        )
        instruction_digest, _ = bind_action(action, ADAPTER_NAME)
        return budget_repository.save_decision(
            decision_id=decision_id,
            actor=actor,
            request_id=request_id,
            decision="approved",
            reason=data.reason,
            instruction_digest=instruction_digest,
            action_json=action.model_dump_json(),
            balance_evidence_minor=available,
        )

    def commit(self, actor: str, request_id: str) -> dict:
        action_json = budget_repository.approved_action(actor, request_id)
        action = ActionRequest.model_validate_json(action_json)
        return self._execute(action)

    def settle(self, actor: str, request_id: str, data) -> dict:
        replay = self._replay(
            data.idempotency_key,
            MutationType.SETTLEMENT,
            {"request_id": request_id, "amount_minor": data.amount_minor, "actor": actor},
        )
        if replay:
            return replay
        request = budget_repository.request_detail(actor, request_id)
        current = self._current_version(request)
        parameters = {
            "mutation_type": MutationType.SETTLEMENT.value,
            "organization_id": request["organization_id"],
            "budget_id": request["budget_id"],
            "request_id": request_id,
            "request_version": request["current_version"],
            "currency": current["currency"],
            "amount_minor": data.amount_minor,
            "actor": actor,
            "domain_approval_id": self._approved_decision_id(request),
            "idempotency_key": data.idempotency_key,
        }
        evidence = budget_repository.validate_mutation(parameters)
        parameters["expected_available_minor"] = evidence["available_after"]
        return self._execute(
            self._action(
                parameters,
                decision_id=f"budget-settle-{uuid4()}",
                component=request["budget_id"],
                reason=f"Settle purchase request {request_id}",
            )
        )

    def cancel(self, actor: str, request_id: str, data) -> dict:
        replay = self._replay(
            data.idempotency_key,
            MutationType.CANCELLATION,
            {"request_id": request_id, "actor": actor},
        )
        if replay:
            return replay
        request = budget_repository.request_detail(actor, request_id)
        current = self._current_version(request)
        parameters = {
            "mutation_type": MutationType.CANCELLATION.value,
            "organization_id": request["organization_id"],
            "budget_id": request["budget_id"],
            "request_id": request_id,
            "request_version": request["current_version"],
            "currency": current["currency"],
            "amount_minor": current["amount_minor"],
            "actor": actor,
            "domain_approval_id": self._approved_decision_id(request),
            "idempotency_key": data.idempotency_key,
        }
        evidence = budget_repository.validate_mutation(parameters)
        parameters["expected_available_minor"] = evidence["available_after"]
        return self._execute(
            self._action(
                parameters,
                decision_id=f"budget-cancel-{uuid4()}",
                component=request["budget_id"],
                reason=f"Cancel purchase request {request_id}",
            )
        )

    def adjust(self, actor: str, budget_id: str, data) -> dict:
        replay = self._replay(
            data.idempotency_key,
            MutationType.ADJUSTMENT,
            {
                "budget_id": budget_id,
                "currency": data.currency,
                "amount_minor": data.amount_minor,
                "reason": data.reason,
                "actor": actor,
            },
        )
        if replay:
            return replay
        organization = budget_repository.organization()
        if organization is None:
            raise BudgetError("not_initialized", "Budget Control is not initialized")
        parameters = {
            "mutation_type": MutationType.ADJUSTMENT.value,
            "organization_id": organization["id"],
            "budget_id": budget_id,
            "currency": data.currency,
            "amount_minor": data.amount_minor,
            "reason": data.reason,
            "actor": actor,
            "idempotency_key": data.idempotency_key,
        }
        evidence = budget_repository.validate_mutation(parameters)
        parameters["expected_available_minor"] = evidence["available_after"]
        return self._execute(
            self._action(
                parameters,
                decision_id=f"budget-adjust-{uuid4()}",
                component=budget_id,
                reason=f"Adjust budget {budget_id}: {data.reason}",
            )
        )

    def correct(self, actor: str, budget_id: str, data) -> dict:
        replay = self._replay(
            data.idempotency_key,
            MutationType.CORRECTION,
            {
                "budget_id": budget_id,
                "currency": data.currency,
                "amount_minor": data.amount_minor,
                "reason": data.reason,
                "correction_of": data.correction_of,
                "actor": actor,
            },
        )
        if replay:
            return replay
        organization = budget_repository.organization()
        if organization is None:
            raise BudgetError("not_initialized", "Budget Control is not initialized")
        parameters = {
            "mutation_type": MutationType.CORRECTION.value,
            "organization_id": organization["id"],
            "budget_id": budget_id,
            "currency": data.currency,
            "amount_minor": data.amount_minor,
            "reason": data.reason,
            "correction_of": data.correction_of,
            "actor": actor,
            "idempotency_key": data.idempotency_key,
        }
        evidence = budget_repository.validate_mutation(parameters)
        parameters["expected_available_minor"] = evidence["available_after"]
        return self._execute(
            self._action(
                parameters,
                decision_id=f"budget-correct-{uuid4()}",
                component=budget_id,
                reason=f"Correct ledger entry {data.correction_of}: {data.reason}",
            )
        )

    def reconcile(self, actor: str, instruction_digest: str) -> dict:
        receipt = budget_repository.receipt(instruction_digest)
        if receipt is None:
            return {
                "financial_status": FinancialOutcome.ADAPTER_FAILED_NO_EFFECT.value,
                "reason": "No durable receipt exists; absence established",
                "instruction_digest": instruction_digest,
            }
        parameters = json.loads(receipt.parameters_json)
        budget_repository.require_role(
            actor,
            BudgetRole.BUDGET_OWNER,
            budget_id=parameters["budget_id"],
        )
        verification = budget_observer.verify(
            execution_id=receipt.execution_id,
            instruction_digest=receipt.instruction_digest,
            expected=parameters,
        )
        return {
            "financial_status": verification["status"],
            "receipt": receipt.as_dict(),
            "financial_verification": verification,
        }

    def _execute(self, action: ActionRequest) -> dict:
        instruction_digest, _ = bind_action(action, ADAPTER_NAME)
        result = execute_governed_action(action, adapter_name=ADAPTER_NAME)
        response: dict[str, Any] = {
            "action_id": action.action_id,
            "domain_decision_id": action.decision_id,
            "instruction_digest": instruction_digest,
            "governed_status": result.get("status"),
            "core": result,
        }
        if result.get("status") != "executed":
            response["financial_status"] = FinancialOutcome.BLOCKED_BEFORE_EXECUTION.value
            return self._with_correlations(response, action.action_id, None)
        execution_id = result.get("execution_id")
        response["execution_id"] = execution_id
        receipt = budget_repository.receipt(instruction_digest)
        if not result.get("success"):
            response["financial_status"] = (
                FinancialOutcome.APPLIED_UNVERIFIED.value
                if receipt
                else FinancialOutcome.ADAPTER_FAILED_NO_EFFECT.value
            )
            if "unknown" in str(result.get("message", "")).lower():
                response["financial_status"] = FinancialOutcome.OUTCOME_UNKNOWN.value
            return self._with_correlations(response, action.action_id, execution_id)
        if receipt is None:
            response["financial_status"] = FinancialOutcome.OUTCOME_UNKNOWN.value
            return self._with_correlations(response, action.action_id, execution_id)
        verification = budget_observer.verify(
            execution_id=receipt.execution_id,
            instruction_digest=instruction_digest,
            expected=action.parameters,
        )
        response.update(
            financial_status=verification["status"],
            financial_execution_id=receipt.execution_id,
            receipt=receipt.as_dict(),
            financial_verification=verification,
        )
        return self._with_correlations(response, action.action_id, execution_id)

    @staticmethod
    def _with_correlations(
        response: dict[str, Any],
        action_id: str,
        execution_id: str | None,
    ) -> dict[str, Any]:
        approvals = [
            row for row in approval_record_storage.get_all() if row.action_id == action_id
        ]
        authorizations = [
            row
            for row in execution_authorization_storage.get_all()
            if row.action_id == action_id
        ]
        core_verification = (
            verification_storage.get_by_execution_id(execution_id)
            if execution_id
            else None
        )
        response["approval_id"] = approvals[-1].approval_id if approvals else None
        response["authorization_id"] = (
            authorizations[-1].authorization_id if authorizations else None
        )
        response["core_verification_id"] = (
            core_verification.verification_id if core_verification else None
        )
        return response

    def _replay(
        self,
        key: str,
        expected_mutation: MutationType,
        expected_fields: dict[str, Any],
    ) -> dict | None:
        receipt = budget_repository.receipt_by_key(key)
        if receipt is None:
            return None
        if receipt.mutation_type != expected_mutation.value:
            raise BudgetError("idempotency_conflict", "Idempotency key belongs to another mutation")
        parameters = json.loads(receipt.parameters_json)
        if any(parameters.get(name) != value for name, value in expected_fields.items()):
            raise BudgetError(
                "idempotency_conflict",
                "Idempotency key was reused with different content",
            )
        verification = budget_observer.verify(
            execution_id=receipt.execution_id,
            instruction_digest=receipt.instruction_digest,
            expected=parameters,
        )
        return {
            "action_id": None,
            "instruction_digest": receipt.instruction_digest,
            "execution_id": receipt.execution_id,
            "governed_status": "executed",
            "financial_status": verification["status"],
            "receipt": receipt.as_dict(),
            "financial_verification": verification,
            "replayed": True,
        }

    @staticmethod
    def _action(
        parameters: dict[str, Any],
        *,
        decision_id: str,
        component: str,
        reason: str,
        action_id: str | None = None,
    ) -> ActionRequest:
        expected_state = json.dumps(
            {
                "mutation_type": parameters["mutation_type"],
                "budget_id": parameters["budget_id"],
                "request_id": parameters.get("request_id"),
                "request_version": parameters.get("request_version"),
                "currency": parameters["currency"],
                "available_minor": parameters["expected_available_minor"],
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        values = {
            "decision_id": decision_id,
            "governance_domain": GOVERNANCE_DOMAIN,
            "component": component,
            "action_type": ActionType.CREATE,
            "reason": reason,
            "confidence": 100,
            "requires_approval": False,
            "rollback_required": True,
            "parameters": parameters,
            "expected_outcome": ExpectedOutcome(
                target=component,
                operation="create",
                expected_state=expected_state,
            ),
        }
        if action_id:
            values["action_id"] = action_id
        return ActionRequest(**values)

    @staticmethod
    def _current_version(request: dict) -> dict:
        for version in request["versions"]:
            if version["version"] == request["current_version"]:
                return version
        raise BudgetError("stale_version", "Current purchase request version is missing")

    @staticmethod
    def _approved_decision_id(request: dict) -> str:
        for decision in reversed(request["decisions"]):
            if (
                decision["decision"] == "approved"
                and decision["request_version"] == request["current_version"]
            ):
                return decision["id"]
        raise BudgetError("approval_required", "Approved decision is missing")


budget_service = BudgetService()
