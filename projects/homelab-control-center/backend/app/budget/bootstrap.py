from app.budget.adapter import BudgetLedgerAdapter
from app.budget.evaluators import BudgetPolicyEvaluator, BudgetRiskEvaluator
from app.budget.models import ADAPTER_NAME, GOVERNANCE_DOMAIN
from app.budget.storage import init_storage
from app.core.intelligence.actions.assessment import assessment_registry
from app.core.intelligence.execution.adapters.registry import adapter_registry


def register_budget_domain() -> None:
    """Trusted startup registration; no caller-selectable registration surface."""
    init_storage()
    existing = assessment_registry.get(GOVERNANCE_DOMAIN)
    if existing is None:
        assessment_registry.register(
            domain=GOVERNANCE_DOMAIN,
            policy=BudgetPolicyEvaluator(),
            risk=BudgetRiskEvaluator(),
            operations={"create"},
            adapters={ADAPTER_NAME},
        )
    adapter_registry.register(ADAPTER_NAME, BudgetLedgerAdapter())
