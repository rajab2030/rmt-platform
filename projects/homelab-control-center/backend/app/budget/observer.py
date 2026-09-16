from __future__ import annotations

from typing import Any

from app.budget.models import FinancialOutcome
from app.budget.repository import budget_repository


class BudgetObserver:
    """Independent financial observer; never trusts adapter success alone."""

    def verify(
        self,
        *,
        execution_id: str,
        instruction_digest: str,
        expected: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            receipt = budget_repository.receipt(instruction_digest)
            if receipt is None:
                return self._record(
                    execution_id,
                    instruction_digest,
                    FinancialOutcome.OUTCOME_UNKNOWN,
                    "Durable receipt is unavailable",
                    expected,
                )
            observed = budget_repository.available_minor_at(
                expected["budget_id"],
                receipt.created_at,
            )
            mismatches = []
            if receipt.execution_id != execution_id:
                mismatches.append("execution identity")
            if receipt.currency != expected["currency"]:
                mismatches.append("currency")
            if receipt.mutation_type != expected["mutation_type"]:
                mismatches.append("mutation type")
            if receipt.request_id != expected.get("request_id"):
                mismatches.append("request identity")
            if receipt.request_version != expected.get("request_version"):
                mismatches.append("request version")
            if receipt.available_minor != expected["expected_available_minor"]:
                mismatches.append("receipt balance")
            if observed != expected["expected_available_minor"]:
                mismatches.append("recomputed balance")
            if mismatches:
                return self._record(
                    execution_id,
                    instruction_digest,
                    FinancialOutcome.VERIFICATION_MISMATCH,
                    "Financial evidence mismatch: " + ", ".join(mismatches),
                    expected,
                    observed=observed,
                    ledger_entry_id=receipt.ledger_entry_id,
                )
            return self._record(
                execution_id,
                instruction_digest,
                FinancialOutcome.VERIFIED_SUCCESS,
                "Receipt, ledger linkage, and recomputed balance match",
                expected,
                observed=observed,
                ledger_entry_id=receipt.ledger_entry_id,
            )
        except Exception as exc:
            return self._record(
                execution_id,
                instruction_digest,
                FinancialOutcome.OUTCOME_UNKNOWN,
                f"Financial observation unavailable: {type(exc).__name__}",
                expected,
            )

    @staticmethod
    def _record(
        execution_id: str,
        instruction_digest: str,
        status: FinancialOutcome,
        reason: str,
        expected: dict[str, Any],
        *,
        observed: int | None = None,
        ledger_entry_id: str | None = None,
    ) -> dict[str, Any]:
        values = {
            "execution_id": execution_id,
            "instruction_digest": instruction_digest,
            "status": status.value,
            "reason": reason,
            "expected_available_minor": expected.get("expected_available_minor"),
            "observed_available_minor": observed,
            "ledger_entry_id": ledger_entry_id,
        }
        try:
            return budget_repository.record_verification(values)
        except Exception as exc:
            return {
                "verification_id": None,
                **values,
                "status": FinancialOutcome.OUTCOME_UNKNOWN.value,
                "reason": (
                    f"{reason}; verification evidence could not be persisted: "
                    f"{type(exc).__name__}"
                ),
            }


budget_observer = BudgetObserver()
