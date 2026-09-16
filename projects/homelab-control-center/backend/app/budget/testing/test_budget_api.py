from fastapi.testclient import TestClient

from app.main import app


def _auth_setup(tmp_path, monkeypatch):
    monkeypatch.setenv("RMT_BUDGET_DB", str(tmp_path / "budget.db"))
    monkeypatch.setenv("RMT_BUDGET_BOOTSTRAP_PRINCIPAL", "admin")
    monkeypatch.setenv("RMT_AUTH_ENABLED", "true")
    monkeypatch.setenv(
        "RMT_OPERATOR_TOKENS",
        "admin:admin-token,owner:owner-token,requester:requester-token",
    )


def test_budget_routes_require_auth_and_attribute_principals(
    tmp_path,
    monkeypatch,
):
    _auth_setup(tmp_path, monkeypatch)
    payload = {
        "organization_name": "Example Org",
        "budget_name": "Operations",
        "period_start": "2026-01-01",
        "period_end": "2026-12-31",
        "currency": "USD",
        "allocation_minor": 2000,
        "owner_principal": "owner",
        "requester_principal": "requester",
        "idempotency_key": "bootstrap-api-1",
    }
    with TestClient(app) as client:
        assert client.post("/budget/bootstrap", json=payload).status_code == 401
        boot = client.post(
            "/budget/bootstrap",
            json=payload,
            headers={"Authorization": "Bearer admin-token"},
        )
        assert boot.status_code == 200
        import json

        budget_id = json.loads(boot.json()["receipt"]["parameters_json"])["budget_id"]
        created = client.post(
            "/budget/requests",
            json={
                "budget_id": budget_id,
                "amount_minor": 1500,
                "currency": "USD",
                "purpose": "Equipment",
                "supporting_reference": "quote",
            },
            headers={"Authorization": "Bearer requester-token"},
        )
        assert created.status_code == 200
        assert created.json()["requester"] == "requester"
        forbidden = client.get(
            f"/budget/requests/{created.json()['id']}",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert forbidden.status_code == 403


def test_unauthenticated_budget_route_matrix(tmp_path, monkeypatch):
    _auth_setup(tmp_path, monkeypatch)
    routes = [
        ("get", "/budget/budgets", None),
        ("get", "/budget/requests", None),
        ("get", "/budget/approvals", None),
        ("get", "/budget/budgets/not-found/history", None),
        ("post", "/budget/requests/not-found/submit", None),
        ("post", "/budget/requests/not-found/commit", None),
        ("post", "/budget/reconcile/" + "0" * 64, None),
    ]
    with TestClient(app) as client:
        for method, path, body in routes:
            response = getattr(client, method)(path, json=body) if body else getattr(client, method)(path)
            assert response.status_code == 401, (method, path, response.text)
