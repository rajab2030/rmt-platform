from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.budget.models import BudgetError


SCHEMA_VERSION = 1


def configured_db_path() -> Path:
    configured = os.environ.get("RMT_BUDGET_DB")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "data" / "budget.db"


def connect(path: Path | None = None) -> sqlite3.Connection:
    db_path = path or configured_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        db_path,
        timeout=5,
        isolation_level=None,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def init_storage(path: Path | None = None) -> None:
    with connect(path) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_version "
            "(version INTEGER NOT NULL)"
        )
        row = connection.execute(
            "SELECT version FROM schema_version LIMIT 1"
        ).fetchone()
        if row is not None and int(row["version"]) > SCHEMA_VERSION:
            raise RuntimeError(
                f"Budget database schema {row['version']} is newer than "
                f"supported schema {SCHEMA_VERSION}"
            )
        if row is None:
            connection.execute("INSERT INTO schema_version(version) VALUES (0)")
            current = 0
        else:
            current = int(row["version"])
        if current < 1:
            _migrate_v1(connection)
            connection.execute("UPDATE schema_version SET version = 1")


def _migrate_v1(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE organizations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            currency TEXT NOT NULL CHECK(length(currency) = 3),
            bootstrap_principal TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE budgets (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL REFERENCES organizations(id),
            name TEXT NOT NULL,
            owner_type TEXT NOT NULL CHECK(owner_type IN ('department', 'project')),
            owner_name TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            currency TEXT NOT NULL CHECK(length(currency) = 3),
            status TEXT NOT NULL CHECK(status IN ('open', 'closed')),
            created_at TEXT NOT NULL,
            CHECK(period_start <= period_end)
        );

        CREATE TABLE role_assignments (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL REFERENCES organizations(id),
            budget_id TEXT REFERENCES budgets(id),
            principal TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN (
                'bootstrap_admin', 'budget_owner', 'requester'
            )),
            created_at TEXT NOT NULL,
            UNIQUE(organization_id, budget_id, principal, role)
        );

        CREATE TABLE purchase_requests (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL REFERENCES organizations(id),
            budget_id TEXT NOT NULL REFERENCES budgets(id),
            requester TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN (
                'draft', 'submitted', 'approved', 'rejected',
                'committed', 'settled', 'cancelled'
            )),
            current_version INTEGER NOT NULL CHECK(current_version > 0),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE purchase_request_versions (
            request_id TEXT NOT NULL REFERENCES purchase_requests(id),
            version INTEGER NOT NULL CHECK(version > 0),
            amount_minor INTEGER NOT NULL CHECK(amount_minor > 0),
            currency TEXT NOT NULL CHECK(length(currency) = 3),
            purpose TEXT NOT NULL,
            supporting_reference TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(request_id, version)
        );

        CREATE TABLE domain_decisions (
            id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            request_version INTEGER NOT NULL,
            decision TEXT NOT NULL CHECK(decision IN ('approved', 'rejected')),
            decided_by TEXT NOT NULL,
            reason TEXT NOT NULL,
            instruction_digest TEXT,
            action_json TEXT,
            balance_evidence_minor INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(request_id, request_version)
                REFERENCES purchase_request_versions(request_id, version)
        );

        CREATE TABLE ledger_entries (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL REFERENCES organizations(id),
            budget_id TEXT NOT NULL REFERENCES budgets(id),
            entry_type TEXT NOT NULL CHECK(entry_type IN (
                'allocation', 'adjustment', 'commitment', 'settlement',
                'cancellation', 'correction'
            )),
            amount_minor INTEGER NOT NULL,
            currency TEXT NOT NULL CHECK(length(currency) = 3),
            request_id TEXT REFERENCES purchase_requests(id),
            request_version INTEGER,
            related_entry_id TEXT REFERENCES ledger_entries(id),
            correction_of TEXT REFERENCES ledger_entries(id),
            instruction_digest TEXT NOT NULL UNIQUE,
            execution_id TEXT NOT NULL,
            actor TEXT NOT NULL,
            created_at TEXT NOT NULL,
            CHECK(entry_type IN ('adjustment', 'correction') OR amount_minor > 0)
        );

        CREATE TABLE idempotency_receipts (
            instruction_digest TEXT PRIMARY KEY,
            idempotency_key TEXT NOT NULL UNIQUE,
            content_digest TEXT NOT NULL,
            parameters_json TEXT NOT NULL,
            execution_id TEXT NOT NULL,
            ledger_entry_id TEXT NOT NULL REFERENCES ledger_entries(id),
            mutation_type TEXT NOT NULL,
            request_id TEXT,
            request_version INTEGER,
            available_minor INTEGER NOT NULL,
            currency TEXT NOT NULL CHECK(length(currency) = 3),
            created_at TEXT NOT NULL
        );

        CREATE TABLE financial_verifications (
            id TEXT PRIMARY KEY,
            execution_id TEXT NOT NULL,
            instruction_digest TEXT NOT NULL,
            status TEXT NOT NULL,
            reason TEXT NOT NULL,
            expected_available_minor INTEGER,
            observed_available_minor INTEGER,
            ledger_entry_id TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX idx_roles_principal ON role_assignments(principal);
        CREATE INDEX idx_requests_budget ON purchase_requests(budget_id);
        CREATE INDEX idx_decisions_request ON domain_decisions(request_id, request_version);
        CREATE INDEX idx_ledger_budget ON ledger_entries(budget_id, created_at);
        CREATE UNIQUE INDEX idx_one_correction
          ON ledger_entries(correction_of) WHERE correction_of IS NOT NULL;
        CREATE INDEX idx_receipts_execution ON idempotency_receipts(execution_id);
        """
    )


@contextmanager
def immediate_transaction(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    connection = connect(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.execute("COMMIT")
    except sqlite3.OperationalError as exc:
        try:
            connection.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        code = "database_busy" if "locked" in str(exc).lower() else "database_error"
        raise BudgetError(code, f"Budget transaction failed: {exc}") from exc
    except Exception:
        try:
            connection.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        connection.close()
