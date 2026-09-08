"""RMT-PROD P2 (O4) -- Prometheus /metrics exposition."""
import pytest
from fastapi.testclient import TestClient

import app.main as main_app
from app.ops import metrics


@pytest.fixture
def client():
    with TestClient(main_app.app) as c:
        yield c


def test_metrics_endpoint_is_open_and_prometheus_text(client):
    r = client.get("/metrics")  # no auth header
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain; version=0.0.4")
    body = r.text

    for name in (
        "rmt_up",
        "rmt_loop_cycles_total",
        "rmt_loop_cycle_error",
        "rmt_approval_holds",
        "rmt_verifications_total",
        "rmt_executions_total",
        "rmt_authorizations_total",
        "rmt_agent_active_grants",
        "rmt_metrics_scrape_errors_total",
    ):
        assert f"# TYPE {name} " in body, name

    assert "\nrmt_up 1\n" in body
    # every non-comment line is `name value` or `name{labels} value`
    for line in body.splitlines():
        if not line or line.startswith("#"):
            continue
        assert line.rsplit(" ", 1)[1].lstrip("-").replace(".", "", 1).isdigit(), line


def test_scrape_errors_zero_on_healthy_stores(client):
    body = client.get("/metrics").text
    assert "rmt_metrics_scrape_errors_total 0" in body


def test_render_counts_holds_by_status(monkeypatch):
    class _H:
        def __init__(self, status):
            self.status = status

    monkeypatch.setattr(
        metrics.approval_hold_storage, "get_all",
        lambda: [_H("pending"), _H("pending"), _H("approved")],
    )
    out = metrics.render_prometheus()
    assert 'rmt_approval_holds{status="pending"} 2' in out
    assert 'rmt_approval_holds{status="approved"} 1' in out
    assert 'rmt_approval_holds{status="rejected"} 0' in out


def test_render_survives_a_broken_store(monkeypatch):
    def _boom():
        raise RuntimeError("store unreadable")

    monkeypatch.setattr(metrics.verification_storage, "get_all", _boom)
    out = metrics.render_prometheus()
    assert "rmt_metrics_scrape_errors_total 1" in out
    assert "rmt_up 1" in out  # the scrape still returns
