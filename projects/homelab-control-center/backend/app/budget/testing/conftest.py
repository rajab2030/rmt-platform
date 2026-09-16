import pytest

from app.budget.bootstrap import register_budget_domain
from app.budget.storage import init_storage


@pytest.fixture
def budget_env(tmp_path, monkeypatch):
    monkeypatch.setenv("RMT_BUDGET_DB", str(tmp_path / "budget.db"))
    monkeypatch.setenv("RMT_BUDGET_BOOTSTRAP_PRINCIPAL", "admin")
    init_storage()
    register_budget_domain()
    return tmp_path
