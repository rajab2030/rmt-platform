from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.budget.models import (
    BudgetError,
    BudgetRole,
    MutationReceipt,
    MutationType,
    RequestStatus,
)
from app.budget.storage import connect, immediate_transaction


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def content_digest(parameters: dict[str, Any]) -> str:
    encoded = json.dumps(
        parameters,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class BudgetRepository:
    def __init__(self, path: Path | None = None):
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        return connect(self.path)

    def initialized(self) -> bool:
        with self._connect() as connection:
            row = connection.execute("SELECT 1 FROM organizations LIMIT 1").fetchone()
            return row is not None

    def organization(self, connection: sqlite3.Connection | None = None) -> dict | None:
        owns = connection is None
        conn = connection or self._connect()
        try:
            row = conn.execute("SELECT * FROM organizations LIMIT 1").fetchone()
            return dict(row) if row else None
        finally:
            if owns:
                conn.close()

    def has_role(
        self,
        principal: str,
        role: BudgetRole | str,
        *,
        budget_id: str | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> bool:
        owns = connection is None
        conn = connection or self._connect()
        try:
            role_value = role.value if isinstance(role, BudgetRole) else role
            if budget_id is None:
                row = conn.execute(
                    "SELECT 1 FROM role_assignments "
                    "WHERE principal = ? AND role = ? LIMIT 1",
                    (principal, role_value),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT 1 FROM role_assignments "
                    "WHERE principal = ? AND role = ? AND budget_id = ? LIMIT 1",
                    (principal, role_value, budget_id),
                ).fetchone()
            return row is not None
        finally:
            if owns:
                conn.close()

    def require_role(
        self,
        principal: str,
        role: BudgetRole,
        *,
        budget_id: str | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        if not self.has_role(
            principal,
            role,
            budget_id=budget_id,
            connection=connection,
        ):
            raise BudgetError(
                "forbidden",
                f"Principal {principal!r} lacks {role.value} permission",
            )

    def available_minor(
        self,
        budget_id: str,
        connection: sqlite3.Connection | None = None,
    ) -> int:
        owns = connection is None
        conn = connection or self._connect()
        try:
            row = conn.execute(
                """
                SELECT
                  COALESCE(SUM(CASE WHEN entry_type = 'allocation'
                    THEN amount_minor ELSE 0 END), 0) AS allocations,
                  COALESCE(SUM(CASE WHEN entry_type IN ('adjustment', 'correction')
                    THEN amount_minor ELSE 0 END), 0) AS adjustments,
                  COALESCE(SUM(CASE WHEN entry_type = 'settlement'
                    THEN amount_minor ELSE 0 END), 0) AS settled
                FROM ledger_entries WHERE budget_id = ?
                """,
                (budget_id,),
            ).fetchone()
            open_commitments = conn.execute(
                """
                SELECT COALESCE(SUM(c.amount_minor), 0) AS total
                FROM ledger_entries c
                WHERE c.budget_id = ? AND c.entry_type = 'commitment'
                  AND NOT EXISTS (
                    SELECT 1 FROM ledger_entries terminal
                    WHERE terminal.related_entry_id = c.id
                      AND terminal.entry_type IN ('settlement', 'cancellation')
                  )
                """,
                (budget_id,),
            ).fetchone()
            return (
                int(row["allocations"])
                + int(row["adjustments"])
                - int(row["settled"])
                - int(open_commitments["total"])
            )
        finally:
            if owns:
                conn.close()

    def available_minor_at(
        self,
        budget_id: str,
        at: str,
        connection: sqlite3.Connection | None = None,
    ) -> int:
        owns = connection is None
        conn = connection or self._connect()
        try:
            row = conn.execute(
                """
                SELECT
                  COALESCE(SUM(CASE WHEN entry_type = 'allocation'
                    THEN amount_minor ELSE 0 END), 0) AS allocations,
                  COALESCE(SUM(CASE WHEN entry_type IN ('adjustment', 'correction')
                    THEN amount_minor ELSE 0 END), 0) AS adjustments,
                  COALESCE(SUM(CASE WHEN entry_type = 'settlement'
                    THEN amount_minor ELSE 0 END), 0) AS settled
                FROM ledger_entries WHERE budget_id = ? AND created_at <= ?
                """,
                (budget_id, at),
            ).fetchone()
            open_commitments = conn.execute(
                """
                SELECT COALESCE(SUM(c.amount_minor), 0) AS total
                FROM ledger_entries c
                WHERE c.budget_id = ? AND c.entry_type = 'commitment'
                  AND c.created_at <= ?
                  AND NOT EXISTS (
                    SELECT 1 FROM ledger_entries terminal
                    WHERE terminal.related_entry_id = c.id
                      AND terminal.entry_type IN ('settlement', 'cancellation')
                      AND terminal.created_at <= ?
                  )
                """,
                (budget_id, at, at),
            ).fetchone()
            return (
                int(row["allocations"])
                + int(row["adjustments"])
                - int(row["settled"])
                - int(open_commitments["total"])
            )
        finally:
            if owns:
                conn.close()

    def list_budgets(self, principal: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT b.*
                FROM budgets b
                JOIN role_assignments r
                  ON r.budget_id = b.id AND r.principal = ?
                ORDER BY b.period_start DESC, b.name
                """,
                (principal,),
            ).fetchall()
            return [self._budget_view(connection, row) for row in rows]

    def _budget_view(self, connection: sqlite3.Connection, row: sqlite3.Row) -> dict:
        data = dict(row)
        data["available_minor"] = self.available_minor(row["id"], connection)
        data["roles"] = [
            dict(role)
            for role in connection.execute(
                "SELECT principal, role FROM role_assignments "
                "WHERE budget_id = ? ORDER BY role, principal",
                (row["id"],),
            ).fetchall()
        ]
        return data

    def budget_history(self, principal: str, budget_id: str) -> list[dict]:
        with self._connect() as connection:
            if not (
                self.has_role(
                    principal,
                    BudgetRole.BUDGET_OWNER,
                    budget_id=budget_id,
                    connection=connection,
                )
                or self.has_role(
                    principal,
                    BudgetRole.REQUESTER,
                    budget_id=budget_id,
                    connection=connection,
                )
            ):
                raise BudgetError("forbidden", "Budget history is not permitted")
            if self.has_role(
                principal,
                BudgetRole.BUDGET_OWNER,
                budget_id=budget_id,
                connection=connection,
            ):
                rows = connection.execute(
                    "SELECT * FROM ledger_entries WHERE budget_id = ? "
                    "ORDER BY created_at, id",
                    (budget_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT ledger.* FROM ledger_entries ledger
                    LEFT JOIN purchase_requests request ON request.id = ledger.request_id
                    WHERE ledger.budget_id = ?
                      AND request.requester = ?
                    ORDER BY ledger.created_at, ledger.id
                    """,
                    (budget_id, principal),
                ).fetchall()
            return [dict(row) for row in rows]

    def create_request(
        self,
        *,
        actor: str,
        budget_id: str,
        amount_minor: int,
        currency: str,
        purpose: str,
        supporting_reference: str,
    ) -> dict:
        if amount_minor <= 0:
            raise BudgetError("validation", "Request amount must be positive")
        if not purpose.strip():
            raise BudgetError("validation", "Purpose is required")
        with immediate_transaction(self.path) as connection:
            self.require_role(
                actor,
                BudgetRole.REQUESTER,
                budget_id=budget_id,
                connection=connection,
            )
            budget = self._budget(connection, budget_id)
            if budget["currency"] != currency.upper():
                raise BudgetError("wrong_currency", "Request currency does not match budget")
            self._require_open_period(budget)
            request_id = str(uuid4())
            now = utc_now()
            connection.execute(
                "INSERT INTO purchase_requests VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    request_id,
                    budget["organization_id"],
                    budget_id,
                    actor,
                    RequestStatus.DRAFT.value,
                    1,
                    now,
                    now,
                ),
            )
            connection.execute(
                "INSERT INTO purchase_request_versions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    request_id,
                    1,
                    amount_minor,
                    currency.upper(),
                    purpose.strip(),
                    supporting_reference.strip(),
                    actor,
                    now,
                ),
            )
        return self.request_detail(actor, request_id)

    def add_request_version(
        self,
        *,
        actor: str,
        request_id: str,
        amount_minor: int,
        currency: str,
        purpose: str,
        supporting_reference: str,
    ) -> dict:
        if amount_minor <= 0 or not purpose.strip():
            raise BudgetError("validation", "Positive amount and purpose are required")
        with immediate_transaction(self.path) as connection:
            request = self._request(connection, request_id)
            if request["requester"] != actor:
                raise BudgetError("forbidden", "Only the requester may create a new version")
            if request["status"] in {
                RequestStatus.COMMITTED.value,
                RequestStatus.SETTLED.value,
                RequestStatus.CANCELLED.value,
            }:
                raise BudgetError("invalid_transition", "Financially applied request is immutable")
            budget = self._budget(connection, request["budget_id"])
            if budget["currency"] != currency.upper():
                raise BudgetError("wrong_currency", "Request currency does not match budget")
            version = int(request["current_version"]) + 1
            now = utc_now()
            connection.execute(
                "INSERT INTO purchase_request_versions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    request_id,
                    version,
                    amount_minor,
                    currency.upper(),
                    purpose.strip(),
                    supporting_reference.strip(),
                    actor,
                    now,
                ),
            )
            connection.execute(
                "UPDATE purchase_requests SET current_version = ?, status = 'draft', "
                "updated_at = ? WHERE id = ?",
                (version, now, request_id),
            )
        return self.request_detail(actor, request_id)

    def submit_request(self, actor: str, request_id: str) -> dict:
        with immediate_transaction(self.path) as connection:
            request = self._request(connection, request_id)
            if request["requester"] != actor:
                raise BudgetError("forbidden", "Only the requester may submit")
            if request["status"] != RequestStatus.DRAFT.value:
                raise BudgetError("invalid_transition", "Only a draft may be submitted")
            connection.execute(
                "UPDATE purchase_requests SET status = 'submitted', updated_at = ? "
                "WHERE id = ?",
                (utc_now(), request_id),
            )
        return self.request_detail(actor, request_id)

    def save_decision(
        self,
        *,
        decision_id: str,
        actor: str,
        request_id: str,
        decision: str,
        reason: str,
        instruction_digest: str | None,
        action_json: str | None,
        balance_evidence_minor: int | None,
    ) -> dict:
        with immediate_transaction(self.path) as connection:
            request = self._request(connection, request_id)
            self.require_role(
                actor,
                BudgetRole.BUDGET_OWNER,
                budget_id=request["budget_id"],
                connection=connection,
            )
            if request["requester"] == actor:
                raise BudgetError("self_approval", "A requester cannot approve their own request")
            if request["status"] != RequestStatus.SUBMITTED.value:
                raise BudgetError("stale_version", "Only the current submitted version may be decided")
            if decision not in {"approved", "rejected"}:
                raise BudgetError("validation", "Decision must be approved or rejected")
            connection.execute(
                """
                INSERT INTO domain_decisions(
                    id, request_id, request_version, decision, decided_by, reason,
                    instruction_digest, action_json, balance_evidence_minor, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    request_id,
                    request["current_version"],
                    decision,
                    actor,
                    reason.strip(),
                    instruction_digest,
                    action_json,
                    balance_evidence_minor,
                    utc_now(),
                ),
            )
            connection.execute(
                "UPDATE purchase_requests SET status = ?, updated_at = ? WHERE id = ?",
                (decision, utc_now(), request_id),
            )
        return self.request_detail(actor, request_id)

    def request_detail(self, actor: str, request_id: str) -> dict:
        with self._connect() as connection:
            request = self._request(connection, request_id)
            can_view = request["requester"] == actor or self.has_role(
                actor,
                BudgetRole.BUDGET_OWNER,
                budget_id=request["budget_id"],
                connection=connection,
            )
            if not can_view:
                raise BudgetError("forbidden", "Purchase request is not permitted")
            return self._request_view(connection, request)

    def list_requests(self, actor: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT request.* FROM purchase_requests request
                LEFT JOIN role_assignments role
                  ON role.budget_id = request.budget_id
                 AND role.principal = ? AND role.role = 'budget_owner'
                WHERE request.requester = ? OR role.id IS NOT NULL
                ORDER BY request.updated_at DESC
                """,
                (actor, actor),
            ).fetchall()
            return [self._request_view(connection, row) for row in rows]

    def approval_queue(self, actor: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT request.* FROM purchase_requests request
                JOIN role_assignments role
                  ON role.budget_id = request.budget_id
                 AND role.principal = ? AND role.role = 'budget_owner'
                WHERE request.status = 'submitted' AND request.requester != ?
                ORDER BY request.updated_at
                """,
                (actor, actor),
            ).fetchall()
            return [self._request_view(connection, row) for row in rows]

    def approved_action(self, actor: str, request_id: str) -> str:
        with self._connect() as connection:
            request = self._request(connection, request_id)
            self.require_role(
                actor,
                BudgetRole.BUDGET_OWNER,
                budget_id=request["budget_id"],
                connection=connection,
            )
            row = connection.execute(
                """
                SELECT * FROM domain_decisions
                WHERE request_id = ? AND request_version = ? AND decision = 'approved'
                ORDER BY created_at DESC LIMIT 1
                """,
                (request_id, request["current_version"]),
            ).fetchone()
            if row is None or not row["action_json"]:
                raise BudgetError("approval_required", "Current version has no approval")
            if row["decided_by"] != actor:
                raise BudgetError("forbidden", "The deciding owner must apply the commitment")
            return str(row["action_json"])

    def validate_mutation(
        self,
        parameters: dict[str, Any],
        instruction_digest: str | None = None,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> dict[str, Any]:
        owns = connection is None
        conn = connection or self._connect()
        try:
            mutation = self._mutation(parameters)
            actor = self._text(parameters, "actor")
            currency = self._currency(parameters)
            if instruction_digest:
                existing = self._receipt_by_digest(conn, instruction_digest)
                if existing is not None:
                    if (
                        existing.content_digest != content_digest(parameters)
                        or existing.idempotency_key != parameters.get("idempotency_key")
                    ):
                        raise BudgetError(
                            "idempotency_conflict",
                            "Existing instruction content does not match",
                        )
                    return {
                        "mutation_type": existing.mutation_type,
                        "budget_id": parameters["budget_id"],
                        "currency": existing.currency,
                        "amount_minor": parameters.get(
                            "amount_minor", parameters.get("allocation_minor")
                        ),
                        "available_before": existing.available_minor,
                        "available_after": existing.available_minor,
                        "evidence": (
                            f"budget:receipt:{existing.instruction_digest}",
                            "budget:idempotent-replay",
                        ),
                    }
            if mutation == MutationType.BOOTSTRAP:
                if conn.execute("SELECT 1 FROM organizations LIMIT 1").fetchone():
                    raise BudgetError("already_initialized", "Budget Control is already initialized")
                configured = os.environ.get("RMT_BUDGET_BOOTSTRAP_PRINCIPAL", "")
                if not configured or actor != configured:
                    raise BudgetError("forbidden", "Actor is not the configured bootstrap principal")
                amount = self._positive_int(parameters, "allocation_minor")
                if self._text(parameters, "owner_principal") == self._text(
                    parameters, "requester_principal"
                ):
                    raise BudgetError("separation_required", "Owner and requester must differ")
                if parameters.get("owner_type") not in {"department", "project"}:
                    raise BudgetError(
                        "validation",
                        "Budget owner_type must be department or project",
                    )
                self._text(parameters, "owner_name")
                return {
                    "mutation_type": mutation.value,
                    "currency": currency,
                    "amount_minor": amount,
                    "available_before": 0,
                    "available_after": amount,
                    "evidence": ("budget:bootstrap:uninitialized",),
                }

            budget_id = self._text(parameters, "budget_id")
            budget = self._budget(conn, budget_id)
            if budget["currency"] != currency:
                raise BudgetError("wrong_currency", "Mutation currency does not match budget")
            self._require_open_period(budget)
            self.require_role(
                actor,
                BudgetRole.BUDGET_OWNER,
                budget_id=budget_id,
                connection=conn,
            )
            before = self.available_minor(budget_id, conn)

            if mutation in {MutationType.ADJUSTMENT, MutationType.CORRECTION}:
                amount = self._integer(parameters, "amount_minor")
                if amount == 0:
                    raise BudgetError("validation", "Balance change cannot be zero")
                if mutation == MutationType.CORRECTION:
                    correction_of = self._text(parameters, "correction_of")
                    original = conn.execute(
                        "SELECT * FROM ledger_entries WHERE id = ? AND budget_id = ?",
                        (correction_of, budget_id),
                    ).fetchone()
                    if original is None:
                        raise BudgetError("not_found", "Correction target not found")
                    if original["entry_type"] not in {"allocation", "adjustment"}:
                        raise BudgetError(
                            "invalid_transition",
                            "Commitments use settlement or cancellation, not correction",
                        )
                    if conn.execute(
                        "SELECT 1 FROM ledger_entries WHERE correction_of = ?",
                        (correction_of,),
                    ).fetchone():
                        raise BudgetError("conflict", "Ledger entry is already corrected")
                after = before + amount
                if after < 0:
                    raise BudgetError("insufficient_funds", "Adjustment would make funds negative")
            else:
                request_id = self._text(parameters, "request_id")
                request = self._request(conn, request_id)
                if request["budget_id"] != budget_id:
                    raise BudgetError("conflict", "Request does not belong to budget")
                version = self._positive_int(parameters, "request_version")
                if int(request["current_version"]) != version:
                    raise BudgetError("stale_version", "Purchase request version changed")
                version_row = self._version(conn, request_id, version)
                amount = self._positive_int(parameters, "amount_minor")

                if mutation == MutationType.COMMITMENT:
                    if request["status"] != RequestStatus.APPROVED.value:
                        raise BudgetError("invalid_transition", "Request is not approved")
                    if amount != int(version_row["amount_minor"]):
                        raise BudgetError("changed_instruction", "Approved amount changed")
                    decision_id = self._text(parameters, "domain_approval_id")
                    decision = conn.execute(
                        "SELECT * FROM domain_decisions WHERE id = ?",
                        (decision_id,),
                    ).fetchone()
                    if (
                        decision is None
                        or decision["decision"] != "approved"
                        or decision["request_id"] != request_id
                        or int(decision["request_version"]) != version
                        or decision["decided_by"] != actor
                        or not instruction_digest
                        or decision["instruction_digest"] != instruction_digest
                    ):
                        raise BudgetError("approval_invalid", "Domain approval binding is invalid")
                    if int(decision["balance_evidence_minor"]) != before:
                        raise BudgetError("stale_evidence", "Available balance changed after approval")
                    if before < amount:
                        raise BudgetError("insufficient_funds", "Insufficient available funds")
                    after = before - amount
                elif mutation == MutationType.SETTLEMENT:
                    if request["status"] != RequestStatus.COMMITTED.value:
                        raise BudgetError("invalid_transition", "Request is not committed")
                    commitment = self._open_commitment(conn, request_id, version)
                    if amount > int(commitment["amount_minor"]):
                        raise BudgetError("over_settlement", "Settlement exceeds approved amount")
                    after = before + int(commitment["amount_minor"]) - amount
                elif mutation == MutationType.CANCELLATION:
                    if request["status"] != RequestStatus.COMMITTED.value:
                        raise BudgetError("invalid_transition", "Request is not committed")
                    commitment = self._open_commitment(conn, request_id, version)
                    if amount != int(commitment["amount_minor"]):
                        raise BudgetError("changed_instruction", "Cancellation amount changed")
                    after = before + amount
                else:  # pragma: no cover - enum exhaustiveness
                    raise BudgetError("unsupported_operation", "Unsupported mutation")

            return {
                "mutation_type": mutation.value,
                "budget_id": budget_id,
                "currency": currency,
                "amount_minor": amount,
                "available_before": before,
                "available_after": after,
                "evidence": (
                    f"budget:{budget_id}",
                    f"balance:{before}",
                    f"mutation:{mutation.value}",
                ),
            }
        finally:
            if owns:
                conn.close()

    def apply_mutation(
        self,
        *,
        parameters: dict[str, Any],
        instruction_digest: str,
        execution_id: str,
    ) -> MutationReceipt:
        key = self._text(parameters, "idempotency_key")
        digest = content_digest(parameters)
        with immediate_transaction(self.path) as connection:
            existing = self._receipt_by_digest(connection, instruction_digest)
            if existing:
                if existing.content_digest != digest or existing.idempotency_key != key:
                    raise BudgetError("idempotency_conflict", "Instruction digest was reused")
                return existing
            reused_key = connection.execute(
                "SELECT * FROM idempotency_receipts WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
            if reused_key is not None:
                raise BudgetError("idempotency_conflict", "Idempotency key was reused")

            evidence = self.validate_mutation(
                parameters,
                instruction_digest,
                connection=connection,
            )
            mutation = MutationType(evidence["mutation_type"])
            now = utc_now()
            ledger_id = str(uuid4())
            request_id = parameters.get("request_id")
            request_version = parameters.get("request_version")
            related_entry_id = None
            correction_of = None

            if mutation == MutationType.BOOTSTRAP:
                organization_id = self._text(parameters, "organization_id")
                budget_id = self._text(parameters, "budget_id")
                actor = self._text(parameters, "actor")
                connection.execute(
                    "INSERT INTO organizations VALUES (?, ?, ?, ?, ?)",
                    (
                        organization_id,
                        self._text(parameters, "organization_name"),
                        evidence["currency"],
                        actor,
                        now,
                    ),
                )
                connection.execute(
                    "INSERT INTO budgets VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)",
                    (
                        budget_id,
                        organization_id,
                        self._text(parameters, "budget_name"),
                        self._text(parameters, "owner_type"),
                        self._text(parameters, "owner_name"),
                        self._text(parameters, "period_start"),
                        self._text(parameters, "period_end"),
                        evidence["currency"],
                        now,
                    ),
                )
                roles = (
                    (actor, BudgetRole.BOOTSTRAP_ADMIN.value, None),
                    (
                        self._text(parameters, "owner_principal"),
                        BudgetRole.BUDGET_OWNER.value,
                        budget_id,
                    ),
                    (
                        self._text(parameters, "requester_principal"),
                        BudgetRole.REQUESTER.value,
                        budget_id,
                    ),
                )
                for principal, role, scoped_budget in roles:
                    connection.execute(
                        "INSERT INTO role_assignments VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            str(uuid4()),
                            organization_id,
                            scoped_budget,
                            principal,
                            role,
                            now,
                        ),
                    )
                entry_type = "allocation"
                amount = evidence["amount_minor"]
            else:
                budget_id = evidence["budget_id"]
                budget = self._budget(connection, budget_id)
                organization_id = budget["organization_id"]
                actor = self._text(parameters, "actor")
                amount = evidence["amount_minor"]
                entry_type = mutation.value
                if mutation == MutationType.CORRECTION:
                    correction_of = self._text(parameters, "correction_of")
                if mutation in {MutationType.SETTLEMENT, MutationType.CANCELLATION}:
                    commitment = self._open_commitment(
                        connection,
                        str(request_id),
                        int(request_version),
                    )
                    related_entry_id = commitment["id"]

            connection.execute(
                """
                INSERT INTO ledger_entries(
                    id, organization_id, budget_id, entry_type, amount_minor,
                    currency, request_id, request_version, related_entry_id,
                    correction_of, instruction_digest, execution_id, actor, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ledger_id,
                    organization_id,
                    budget_id,
                    entry_type,
                    amount,
                    evidence["currency"],
                    request_id,
                    request_version,
                    related_entry_id,
                    correction_of,
                    instruction_digest,
                    execution_id,
                    actor,
                    now,
                ),
            )

            if mutation == MutationType.COMMITMENT:
                self._transition(connection, str(request_id), "approved", "committed")
            elif mutation == MutationType.SETTLEMENT:
                self._transition(connection, str(request_id), "committed", "settled")
            elif mutation == MutationType.CANCELLATION:
                self._transition(connection, str(request_id), "committed", "cancelled")

            observed_available = self.available_minor(budget_id, connection)
            if observed_available != evidence["available_after"]:
                raise BudgetError("invariant_failure", "Balance invariant did not hold")
            receipt = MutationReceipt(
                instruction_digest=instruction_digest,
                idempotency_key=key,
                content_digest=digest,
                parameters_json=json.dumps(
                    parameters,
                    allow_nan=False,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                execution_id=execution_id,
                ledger_entry_id=ledger_id,
                mutation_type=mutation.value,
                request_id=str(request_id) if request_id else None,
                request_version=int(request_version) if request_version else None,
                available_minor=observed_available,
                currency=evidence["currency"],
                created_at=now,
            )
            connection.execute(
                "INSERT INTO idempotency_receipts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                tuple(receipt.as_dict().values()),
            )
            return receipt

    def receipt(self, instruction_digest: str) -> MutationReceipt | None:
        with self._connect() as connection:
            return self._receipt_by_digest(connection, instruction_digest)

    def receipt_by_execution(self, execution_id: str) -> MutationReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM idempotency_receipts WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
            return MutationReceipt(**dict(row)) if row else None

    def receipt_by_key(self, idempotency_key: str) -> MutationReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM idempotency_receipts WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            return MutationReceipt(**dict(row)) if row else None

    def record_verification(self, values: dict[str, Any]) -> dict[str, Any]:
        with immediate_transaction(self.path) as connection:
            verification_id = str(uuid4())
            connection.execute(
                """
                INSERT INTO financial_verifications VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    verification_id,
                    values["execution_id"],
                    values["instruction_digest"],
                    values["status"],
                    values["reason"],
                    values.get("expected_available_minor"),
                    values.get("observed_available_minor"),
                    values.get("ledger_entry_id"),
                    utc_now(),
                ),
            )
        return {"verification_id": verification_id, **values}

    def _request_view(self, connection: sqlite3.Connection, request: sqlite3.Row) -> dict:
        data = dict(request)
        versions = connection.execute(
            "SELECT * FROM purchase_request_versions WHERE request_id = ? "
            "ORDER BY version",
            (request["id"],),
        ).fetchall()
        decisions = connection.execute(
            "SELECT id, request_version, decision, decided_by, reason, created_at "
            "FROM domain_decisions WHERE request_id = ? ORDER BY created_at",
            (request["id"],),
        ).fetchall()
        data["versions"] = [dict(row) for row in versions]
        data["decisions"] = [dict(row) for row in decisions]
        return data

    def _receipt_by_digest(
        self,
        connection: sqlite3.Connection,
        instruction_digest: str,
    ) -> MutationReceipt | None:
        row = connection.execute(
            "SELECT * FROM idempotency_receipts WHERE instruction_digest = ?",
            (instruction_digest,),
        ).fetchone()
        return MutationReceipt(**dict(row)) if row else None

    @staticmethod
    def _request(connection: sqlite3.Connection, request_id: str) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM purchase_requests WHERE id = ?",
            (request_id,),
        ).fetchone()
        if row is None:
            raise BudgetError("not_found", "Purchase request not found")
        return row

    @staticmethod
    def _version(
        connection: sqlite3.Connection,
        request_id: str,
        version: int,
    ) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM purchase_request_versions WHERE request_id = ? AND version = ?",
            (request_id, version),
        ).fetchone()
        if row is None:
            raise BudgetError("stale_version", "Purchase request version not found")
        return row

    @staticmethod
    def _budget(connection: sqlite3.Connection, budget_id: str) -> sqlite3.Row:
        row = connection.execute("SELECT * FROM budgets WHERE id = ?", (budget_id,)).fetchone()
        if row is None:
            raise BudgetError("not_found", "Budget not found")
        return row

    @staticmethod
    def _open_commitment(
        connection: sqlite3.Connection,
        request_id: str,
        version: int,
    ) -> sqlite3.Row:
        row = connection.execute(
            """
            SELECT commitment.* FROM ledger_entries commitment
            WHERE commitment.request_id = ? AND commitment.request_version = ?
              AND commitment.entry_type = 'commitment'
              AND NOT EXISTS (
                SELECT 1 FROM ledger_entries terminal
                WHERE terminal.related_entry_id = commitment.id
                  AND terminal.entry_type IN ('settlement', 'cancellation')
              )
            LIMIT 1
            """,
            (request_id, version),
        ).fetchone()
        if row is None:
            raise BudgetError("invalid_transition", "Open commitment not found")
        return row

    @staticmethod
    def _transition(
        connection: sqlite3.Connection,
        request_id: str,
        expected: str,
        target: str,
    ) -> None:
        cursor = connection.execute(
            "UPDATE purchase_requests SET status = ?, updated_at = ? "
            "WHERE id = ? AND status = ?",
            (target, utc_now(), request_id, expected),
        )
        if cursor.rowcount != 1:
            raise BudgetError("invalid_transition", "Purchase request transition failed")

    @staticmethod
    def _require_open_period(budget: sqlite3.Row) -> None:
        today = date.today().isoformat()
        if budget["status"] != "open" or not (
            budget["period_start"] <= today <= budget["period_end"]
        ):
            raise BudgetError("closed_period", "Budget period is not open")

    @staticmethod
    def _mutation(parameters: dict[str, Any]) -> MutationType:
        try:
            return MutationType(parameters.get("mutation_type"))
        except (TypeError, ValueError) as exc:
            raise BudgetError("unsupported_operation", "Unsupported Budget mutation") from exc

    @staticmethod
    def _text(parameters: dict[str, Any], key: str) -> str:
        value = parameters.get(key)
        if not isinstance(value, str) or not value.strip():
            raise BudgetError("validation", f"{key} is required")
        return value.strip()

    @staticmethod
    def _integer(parameters: dict[str, Any], key: str) -> int:
        value = parameters.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise BudgetError("validation", f"{key} must be an integer minor-unit amount")
        return value

    @classmethod
    def _positive_int(cls, parameters: dict[str, Any], key: str) -> int:
        value = cls._integer(parameters, key)
        if value <= 0:
            raise BudgetError("validation", f"{key} must be positive")
        return value

    @staticmethod
    def _currency(parameters: dict[str, Any]) -> str:
        value = parameters.get("currency")
        if not isinstance(value, str) or len(value) != 3 or not value.isalpha():
            raise BudgetError("validation", "currency must be a three-letter ISO-4217 code")
        return value.upper()


budget_repository = BudgetRepository()
