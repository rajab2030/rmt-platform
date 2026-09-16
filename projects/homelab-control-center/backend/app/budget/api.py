from fastapi import APIRouter, Depends, HTTPException

from app.budget.models import BudgetError
from app.budget.repository import budget_repository
from app.budget.schemas import (
    AdjustmentInput,
    BootstrapInput,
    CorrectionInput,
    DecisionInput,
    IdempotencyInput,
    PurchaseRequestInput,
    PurchaseRequestVersionInput,
    SettlementInput,
)
from app.budget.service import budget_service
from app.ops.auth import OperatorIdentity, require_operator


router = APIRouter(prefix="/budget", tags=["budget"])


def _raise_http(exc: BudgetError) -> None:
    if exc.code == "not_found":
        status = 404
    elif exc.code in {"forbidden", "self_approval", "separation_required"}:
        status = 403
    elif exc.code in {"validation", "wrong_currency"}:
        status = 422
    elif exc.code in {"database_busy", "database_error"}:
        status = 503
    else:
        status = 409
    raise HTTPException(
        status_code=status,
        detail={"code": exc.code, "message": exc.message},
    ) from exc


def _call(callable_, *args, **kwargs):
    try:
        return callable_(*args, **kwargs)
    except BudgetError as exc:
        _raise_http(exc)


@router.post("/bootstrap")
def bootstrap(
    data: BootstrapInput,
    operator: OperatorIdentity = Depends(require_operator),
):
    return _call(budget_service.bootstrap, operator.name, data)


@router.get("/budgets")
def budgets(operator: OperatorIdentity = Depends(require_operator)):
    return {"budgets": _call(budget_repository.list_budgets, operator.name)}


@router.get("/budgets/{budget_id}/history")
def spending_history(
    budget_id: str,
    operator: OperatorIdentity = Depends(require_operator),
):
    return {
        "entries": _call(
            budget_repository.budget_history,
            operator.name,
            budget_id,
        )
    }


@router.post("/budgets/{budget_id}/adjustments")
def adjust_budget(
    budget_id: str,
    data: AdjustmentInput,
    operator: OperatorIdentity = Depends(require_operator),
):
    return _call(budget_service.adjust, operator.name, budget_id, data)


@router.post("/budgets/{budget_id}/corrections")
def correct_budget_entry(
    budget_id: str,
    data: CorrectionInput,
    operator: OperatorIdentity = Depends(require_operator),
):
    return _call(budget_service.correct, operator.name, budget_id, data)


@router.get("/requests")
def requests(operator: OperatorIdentity = Depends(require_operator)):
    return {"requests": _call(budget_repository.list_requests, operator.name)}


@router.post("/requests")
def create_request(
    data: PurchaseRequestInput,
    operator: OperatorIdentity = Depends(require_operator),
):
    return _call(budget_service.create_request, operator.name, data)


@router.get("/requests/{request_id}")
def request_detail(
    request_id: str,
    operator: OperatorIdentity = Depends(require_operator),
):
    return _call(budget_repository.request_detail, operator.name, request_id)


@router.post("/requests/{request_id}/versions")
def add_request_version(
    request_id: str,
    data: PurchaseRequestVersionInput,
    operator: OperatorIdentity = Depends(require_operator),
):
    return _call(budget_service.add_request_version, operator.name, request_id, data)


@router.post("/requests/{request_id}/submit")
def submit_request(
    request_id: str,
    operator: OperatorIdentity = Depends(require_operator),
):
    return _call(budget_repository.submit_request, operator.name, request_id)


@router.get("/approvals")
def approvals(operator: OperatorIdentity = Depends(require_operator)):
    return {"requests": _call(budget_repository.approval_queue, operator.name)}


@router.post("/requests/{request_id}/decision")
def decide_request(
    request_id: str,
    data: DecisionInput,
    operator: OperatorIdentity = Depends(require_operator),
):
    return _call(budget_service.decide, operator.name, request_id, data)


@router.post("/requests/{request_id}/commit")
def commit_request(
    request_id: str,
    operator: OperatorIdentity = Depends(require_operator),
):
    return _call(budget_service.commit, operator.name, request_id)


@router.post("/requests/{request_id}/settle")
def settle_request(
    request_id: str,
    data: SettlementInput,
    operator: OperatorIdentity = Depends(require_operator),
):
    return _call(budget_service.settle, operator.name, request_id, data)


@router.post("/requests/{request_id}/cancel")
def cancel_request(
    request_id: str,
    data: IdempotencyInput,
    operator: OperatorIdentity = Depends(require_operator),
):
    return _call(budget_service.cancel, operator.name, request_id, data)


@router.post("/reconcile/{instruction_digest}")
def reconcile(
    instruction_digest: str,
    operator: OperatorIdentity = Depends(require_operator),
):
    return _call(budget_service.reconcile, operator.name, instruction_digest)
