import json

from app.budget.adapter import BudgetLedgerAdapter
from app.budget.models import BudgetError
from app.budget.repository import budget_repository
from app.budget.schemas import BootstrapInput, DecisionInput, PurchaseRequestInput
from app.budget.service import budget_service
from app.core.intelligence.actions.binding import bind_action
from app.core.intelligence.actions.models import ActionRequest
from app.core.intelligence.execution.models import ExecutionRequest


def _approved_action():
    bootstrap = budget_service.bootstrap(
        "admin",
        BootstrapInput(
            organization_name="Adapter Org",
            budget_name="Adapter Budget",
            period_start="2026-01-01",
            period_end="2026-12-31",
            currency="USD",
            allocation_minor=2000,
            owner_principal="owner",
            requester_principal="requester",
            idempotency_key="adapter-bootstrap",
        ),
    )
    budget_id = json.loads(bootstrap["receipt"]["parameters_json"])["budget_id"]
    request = budget_service.create_request(
        "requester",
        PurchaseRequestInput(
            budget_id=budget_id,
            amount_minor=1500,
            currency="USD",
            purpose="Recovery test",
            supporting_reference="quote",
        ),
    )
    budget_repository.submit_request("requester", request["id"])
    budget_service.decide(
        "owner",
        request["id"],
        DecisionInput(decision="approved", reason="approved"),
    )
    action = ActionRequest.model_validate_json(
        budget_repository.approved_action("owner", request["id"])
    )
    digest, _ = bind_action(action, "budget-ledger")
    execution = ExecutionRequest(
        authorization_id="test-only",
        action_id=action.action_id,
        decision_id=action.decision_id,
        governance_domain=action.governance_domain,
        target=action.component,
        operation=action.action_type.value,
        parameters=action.parameters,
        expected_outcome=action.expected_outcome,
        adapter_name="budget-ledger",
        instruction_digest=digest,
    )
    return budget_id, request["id"], execution


def test_adapter_failure_before_commit_has_no_effect(budget_env, monkeypatch):
    budget_id, _, execution = _approved_action()

    def fail_before_commit(**kwargs):  # noqa: ARG001
        raise BudgetError("database_error", "injected before commit")

    monkeypatch.setattr(budget_repository, "apply_mutation", fail_before_commit)
    result = BudgetLedgerAdapter().execute(execution)
    assert result.success is False
    assert result.output["financial_outcome"] == "adapter_failed_no_effect"
    assert budget_repository.receipt(str(execution.instruction_digest)) is None
    assert budget_repository.available_minor(budget_id) == 2000


def test_ambiguous_after_commit_recovers_exactly_one_effect(budget_env, monkeypatch):
    budget_id, _, execution = _approved_action()
    original = budget_repository.apply_mutation

    def commit_then_lose_response(**kwargs):
        original(**kwargs)
        raise RuntimeError("injected lost response")

    monkeypatch.setattr(
        budget_repository,
        "apply_mutation",
        commit_then_lose_response,
    )
    result = BudgetLedgerAdapter().execute(execution)
    assert result.success is True
    assert result.output["recovered"] is True
    assert budget_repository.available_minor(budget_id) == 500
    history = budget_repository.budget_history("owner", budget_id)
    assert sum(row["entry_type"] == "commitment" for row in history) == 1


def test_unresolvable_adapter_error_remains_unknown(budget_env, monkeypatch):
    _, _, execution = _approved_action()

    def fail(**kwargs):  # noqa: ARG001
        raise RuntimeError("injected failure")

    def observation_fails(instruction_digest):  # noqa: ARG001
        raise OSError("storage unavailable")

    monkeypatch.setattr(budget_repository, "apply_mutation", fail)
    monkeypatch.setattr(budget_repository, "receipt", observation_fails)
    result = BudgetLedgerAdapter().execute(execution)
    assert result.success is False
    assert result.output["financial_outcome"] == "outcome_unknown"
