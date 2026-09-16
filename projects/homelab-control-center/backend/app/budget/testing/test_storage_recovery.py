import shutil
import sqlite3

import pytest

from app.budget.models import FinancialOutcome
from app.budget.observer import budget_observer
from app.budget.repository import budget_repository
from app.budget.schemas import BootstrapInput
from app.budget.service import budget_service
from app.budget.storage import init_storage


def test_clean_migration_restart_and_backup_restore(tmp_path, monkeypatch):
    source = tmp_path / "source.db"
    monkeypatch.setenv("RMT_BUDGET_DB", str(source))
    monkeypatch.setenv("RMT_BUDGET_BOOTSTRAP_PRINCIPAL", "admin")
    init_storage()
    result = budget_service.bootstrap(
        "admin",
        BootstrapInput(
            organization_name="Recovery Org",
            budget_name="Recovery Budget",
            period_start="2026-01-01",
            period_end="2026-12-31",
            currency="USD",
            allocation_minor=2000,
            owner_principal="owner",
            requester_principal="requester",
            idempotency_key="recovery-bootstrap",
        ),
    )
    import json

    budget_id = json.loads(result["receipt"]["parameters_json"])["budget_id"]
    init_storage()  # restart-equivalent idempotent migration
    assert budget_repository.available_minor(budget_id) == 2000

    restored = tmp_path / "restored.db"
    shutil.copy2(source, restored)
    monkeypatch.setenv("RMT_BUDGET_DB", str(restored))
    init_storage()
    assert budget_repository.available_minor(budget_id) == 2000


def test_newer_schema_fails_closed(tmp_path):
    path = tmp_path / "future.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE schema_version(version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_version VALUES (999)")
    with pytest.raises(RuntimeError, match="newer"):
        init_storage(path)


def test_observer_mismatch_and_unavailable_are_explicit(budget_env):
    result = budget_service.bootstrap(
        "admin",
        BootstrapInput(
            organization_name="Observer Org",
            budget_name="Observer Budget",
            period_start="2026-01-01",
            period_end="2026-12-31",
            currency="USD",
            allocation_minor=2000,
            owner_principal="owner",
            requester_principal="requester",
            idempotency_key="observer-bootstrap",
        ),
    )
    receipt = result["receipt"]
    import json

    expected = json.loads(receipt["parameters_json"])
    expected["expected_available_minor"] += 1
    mismatch = budget_observer.verify(
        execution_id=receipt["execution_id"],
        instruction_digest=receipt["instruction_digest"],
        expected=expected,
    )
    assert mismatch["status"] == FinancialOutcome.VERIFICATION_MISMATCH.value

    unavailable = budget_observer.verify(
        execution_id="missing",
        instruction_digest="0" * 64,
        expected=expected,
    )
    assert unavailable["status"] == FinancialOutcome.OUTCOME_UNKNOWN.value


def test_observer_persistence_error_remains_visibly_unknown(budget_env, monkeypatch):
    result = budget_service.bootstrap(
        "admin",
        BootstrapInput(
            organization_name="Persistence Org",
            budget_name="Persistence Budget",
            period_start="2026-01-01",
            period_end="2026-12-31",
            currency="USD",
            allocation_minor=2000,
            owner_principal="owner",
            requester_principal="requester",
            idempotency_key="persistence-bootstrap",
        ),
    )
    receipt = result["receipt"]
    import json

    expected = json.loads(receipt["parameters_json"])

    def fail_to_record(values):  # noqa: ARG001
        raise OSError("verification store unavailable")

    monkeypatch.setattr(budget_repository, "record_verification", fail_to_record)
    observed = budget_observer.verify(
        execution_id=receipt["execution_id"],
        instruction_digest=receipt["instruction_digest"],
        expected=expected,
    )
    assert observed["status"] == FinancialOutcome.OUTCOME_UNKNOWN.value
    assert observed["verification_id"] is None
