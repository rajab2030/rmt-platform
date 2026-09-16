from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


GOVERNANCE_DOMAIN = "rmt.budget.v1"
ADAPTER_NAME = "budget-ledger"


class BudgetRole(str, Enum):
    BOOTSTRAP_ADMIN = "bootstrap_admin"
    BUDGET_OWNER = "budget_owner"
    REQUESTER = "requester"


class RequestStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMMITTED = "committed"
    SETTLED = "settled"
    CANCELLED = "cancelled"


class MutationType(str, Enum):
    BOOTSTRAP = "bootstrap"
    ADJUSTMENT = "adjustment"
    COMMITMENT = "commitment"
    SETTLEMENT = "settlement"
    CANCELLATION = "cancellation"
    CORRECTION = "correction"


class FinancialOutcome(str, Enum):
    BLOCKED_BEFORE_EXECUTION = "blocked_before_execution"
    ADAPTER_FAILED_NO_EFFECT = "adapter_failed_no_effect"
    APPLIED_UNVERIFIED = "applied_unverified"
    VERIFIED_SUCCESS = "verified_success"
    VERIFICATION_MISMATCH = "verification_mismatch"
    OUTCOME_UNKNOWN = "outcome_unknown"


class BudgetError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class MutationReceipt:
    instruction_digest: str
    idempotency_key: str
    content_digest: str
    parameters_json: str
    execution_id: str
    ledger_entry_id: str
    mutation_type: str
    request_id: str | None
    request_version: int | None
    available_minor: int
    currency: str
    created_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "instruction_digest": self.instruction_digest,
            "idempotency_key": self.idempotency_key,
            "content_digest": self.content_digest,
            "parameters_json": self.parameters_json,
            "execution_id": self.execution_id,
            "ledger_entry_id": self.ledger_entry_id,
            "mutation_type": self.mutation_type,
            "request_id": self.request_id,
            "request_version": self.request_version,
            "available_minor": self.available_minor,
            "currency": self.currency,
            "created_at": self.created_at,
        }
