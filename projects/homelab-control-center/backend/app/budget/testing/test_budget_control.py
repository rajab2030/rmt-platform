from concurrent.futures import ThreadPoolExecutor

import pytest

from app.budget.models import BudgetError
from app.budget.repository import budget_repository
from app.budget.schemas import (
    AdjustmentInput,
    BootstrapInput,
    DecisionInput,
    IdempotencyInput,
    PurchaseRequestInput,
    PurchaseRequestVersionInput,
    SettlementInput,
    CorrectionInput,
)
from app.budget.service import budget_service


def _bootstrap():
    result = budget_service.bootstrap(
        "admin",
        BootstrapInput(
            organization_name="Example Org",
            budget_name="Operations",
            period_start="2026-01-01",
            period_end="2026-12-31",
            currency="usd",
            allocation_minor=2000,
            owner_principal="owner",
            requester_principal="requester",
            idempotency_key="bootstrap-0001",
        ),
    )
    budget_id = result["receipt"]["parameters_json"]
    import json

    return result, json.loads(budget_id)["budget_id"]


def _submitted(budget_id: str, amount: int = 1500):
    request = budget_service.create_request(
        "requester",
        PurchaseRequestInput(
            budget_id=budget_id,
            amount_minor=amount,
            currency="USD",
            purpose="Approved equipment",
            supporting_reference="quote-1",
        ),
    )
    return budget_repository.submit_request("requester", request["id"])


def test_approved_2000_commit_1500_leaves_500_and_full_evidence(budget_env):
    bootstrap, budget_id = _bootstrap()
    assert bootstrap["financial_status"] == "verified_success"
    assert budget_repository.available_minor(budget_id) == 2000

    request = _submitted(budget_id)
    approved = budget_service.decide(
        "owner",
        request["id"],
        DecisionInput(decision="approved", reason="within plan"),
    )
    assert approved["status"] == "approved"

    result = budget_service.commit("owner", request["id"])
    assert result["financial_status"] == "verified_success"
    assert result["approval_id"]
    assert result["authorization_id"]
    assert result["execution_id"]
    assert result["core_verification_id"]
    assert result["financial_verification"]["verification_id"]
    assert budget_repository.available_minor(budget_id) == 500
    assert budget_repository.request_detail("owner", request["id"])["status"] == "committed"


def test_concurrent_1500_commitments_produce_exactly_one_effect(budget_env):
    _, budget_id = _bootstrap()
    first = _submitted(budget_id)
    second = _submitted(budget_id)
    for request in (first, second):
        budget_service.decide(
            "owner",
            request["id"],
            DecisionInput(decision="approved", reason="candidate"),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda request_id: budget_service.commit("owner", request_id),
                (first["id"], second["id"]),
            )
        )

    assert [r["financial_status"] for r in results].count("verified_success") == 1
    losing = [r["financial_status"] for r in results if r["financial_status"] != "verified_success"]
    assert losing == ["adapter_failed_no_effect"]
    assert budget_repository.available_minor(budget_id) == 500
    history = budget_repository.budget_history("owner", budget_id)
    assert sum(row["entry_type"] == "commitment" for row in history) == 1


def test_settlement_replaces_commitment_and_replay_is_idempotent(budget_env):
    _, budget_id = _bootstrap()
    request = _submitted(budget_id)
    budget_service.decide(
        "owner",
        request["id"],
        DecisionInput(decision="approved", reason="approved"),
    )
    budget_service.commit("owner", request["id"])

    data = SettlementInput(amount_minor=1200, idempotency_key="settlement-0001")
    settled = budget_service.settle("owner", request["id"], data)
    replay = budget_service.settle("owner", request["id"], data)

    assert settled["financial_status"] == "verified_success"
    assert replay["replayed"] is True
    assert budget_repository.available_minor(budget_id) == 800
    history = budget_repository.budget_history("owner", budget_id)
    assert sum(row["entry_type"] == "settlement" for row in history) == 1


def test_cancellation_releases_open_commitment(budget_env):
    _, budget_id = _bootstrap()
    request = _submitted(budget_id)
    budget_service.decide(
        "owner",
        request["id"],
        DecisionInput(decision="approved", reason="approved"),
    )
    budget_service.commit("owner", request["id"])

    result = budget_service.cancel(
        "owner",
        request["id"],
        IdempotencyInput(idempotency_key="cancel-0001"),
    )
    assert result["financial_status"] == "verified_success"
    assert budget_repository.available_minor(budget_id) == 2000


def test_changed_version_invalidates_prior_approval(budget_env):
    _, budget_id = _bootstrap()
    request = _submitted(budget_id)
    budget_service.decide(
        "owner",
        request["id"],
        DecisionInput(decision="approved", reason="approved v1"),
    )
    changed = budget_service.add_request_version(
        "requester",
        request["id"],
        PurchaseRequestVersionInput(
            amount_minor=1600,
            currency="USD",
            purpose="Changed equipment",
            supporting_reference="quote-2",
        ),
    )
    assert changed["status"] == "draft"
    with pytest.raises(BudgetError, match="no approval"):
        budget_service.commit("owner", request["id"])
    assert budget_repository.available_minor(budget_id) == 2000


def test_permissions_and_self_service_boundaries_fail_closed(budget_env):
    _, budget_id = _bootstrap()
    request = _submitted(budget_id)
    with pytest.raises(BudgetError) as denied:
        budget_service.decide(
            "requester",
            request["id"],
            DecisionInput(decision="approved", reason="self"),
        )
    assert denied.value.code in {"forbidden", "self_approval"}
    with pytest.raises(BudgetError) as read_denied:
        budget_repository.request_detail("stranger", request["id"])
    assert read_denied.value.code == "forbidden"
    assert budget_repository.available_minor(budget_id) == 2000


def test_adjustment_and_linked_correction_are_append_only(budget_env):
    _, budget_id = _bootstrap()
    adjusted = budget_service.adjust(
        "owner",
        budget_id,
        AdjustmentInput(
            amount_minor=300,
            currency="USD",
            reason="approved increase",
            idempotency_key="adjustment-0001",
        ),
    )
    assert adjusted["financial_status"] == "verified_success"
    entry_id = adjusted["receipt"]["ledger_entry_id"]
    corrected = budget_service.correct(
        "owner",
        budget_id,
        CorrectionInput(
            amount_minor=-300,
            currency="USD",
            reason="reverse mistaken increase",
            correction_of=entry_id,
            idempotency_key="correction-0001",
        ),
    )
    assert corrected["financial_status"] == "verified_success"
    assert budget_repository.available_minor(budget_id) == 2000
    history = budget_repository.budget_history("owner", budget_id)
    assert [row["entry_type"] for row in history] == [
        "allocation",
        "adjustment",
        "correction",
    ]
    with pytest.raises(BudgetError) as duplicate:
        budget_service.correct(
            "owner",
            budget_id,
            CorrectionInput(
                amount_minor=-300,
                currency="USD",
                reason="second rewrite attempt",
                correction_of=entry_id,
                idempotency_key="correction-0002",
            ),
        )
    assert duplicate.value.code == "conflict"


def test_changed_balance_after_approval_blocks_before_adapter(budget_env):
    _, budget_id = _bootstrap()
    request = _submitted(budget_id)
    budget_service.decide(
        "owner",
        request["id"],
        DecisionInput(decision="approved", reason="approved at 2000"),
    )
    budget_service.adjust(
        "owner",
        budget_id,
        AdjustmentInput(
            amount_minor=100,
            currency="USD",
            reason="new evidence",
            idempotency_key="adjustment-stale",
        ),
    )
    result = budget_service.commit("owner", request["id"])
    assert result["financial_status"] == "blocked_before_execution"
    assert "execution_id" not in result
    history = budget_repository.budget_history("owner", budget_id)
    assert not any(row["entry_type"] == "commitment" for row in history)


def test_exact_commit_replay_returns_receipt_without_duplicate_ledger(budget_env):
    _, budget_id = _bootstrap()
    request = _submitted(budget_id)
    budget_service.decide(
        "owner",
        request["id"],
        DecisionInput(decision="approved", reason="approved"),
    )
    first = budget_service.commit("owner", request["id"])
    second = budget_service.commit("owner", request["id"])
    assert first["instruction_digest"] == second["instruction_digest"]
    assert second["financial_status"] == "verified_success"
    history = budget_repository.budget_history("owner", budget_id)
    assert sum(row["entry_type"] == "commitment" for row in history) == 1


def test_reused_idempotency_key_with_changed_content_is_rejected(budget_env):
    _, budget_id = _bootstrap()
    budget_service.adjust(
        "owner",
        budget_id,
        AdjustmentInput(
            amount_minor=100,
            currency="USD",
            reason="first",
            idempotency_key="same-key-0001",
        ),
    )
    with pytest.raises(BudgetError) as conflict:
        budget_service.adjust(
            "owner",
            budget_id,
            AdjustmentInput(
                amount_minor=200,
                currency="USD",
                reason="changed",
                idempotency_key="same-key-0001",
            ),
        )
    assert conflict.value.code == "idempotency_conflict"
