"""RMT-PROD P2 (O4) -- Prometheus /metrics exposition."""
from datetime import datetime, timedelta, timezone

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


def test_executed_actions_counters_from_index(monkeypatch):
    """B1b: the four rmt_executed_actions* counters come from the index
    projection, labelled by adapter + operation."""
    from app.ops.verification import index

    index.reset()
    index.record(
        "m1", action_id="a1", adapter="docker", operation="restart",
        target="svc", core_status="observation_unavailable",
        above_core_status="verified_success",
    )
    index.record(
        "m2", action_id="a2", adapter="docker", operation="restart",
        target="svc", core_status="observation_unavailable",
        above_core_status="state_mismatch",
    )
    index.record(
        "m3", action_id="a3", adapter="simulation", operation="restart",
        target="svc", core_status="observation_unavailable", above_core_status=None,
    )
    try:
        out = metrics.render_prometheus()
    finally:
        index.reset()

    assert 'rmt_executed_actions_total{adapter="docker",operation="restart"} 2' in out
    assert 'rmt_executed_actions_verified_total{adapter="docker",operation="restart"} 1' in out
    assert 'rmt_executed_actions_state_mismatch_total{adapter="docker",operation="restart"} 1' in out
    assert 'rmt_executed_actions_unverified_total{adapter="simulation",operation="restart"} 1' in out
    assert "rmt_metrics_scrape_errors_total 0" in out


def test_render_computes_approval_latency(monkeypatch):
    class _H:
        def __init__(self, approval_id, created_at):
            self.approval_id = approval_id
            self.created_at = created_at

    class _R:
        def __init__(self, approval_id, decision, created_at):
            self.approval_id = approval_id
            self.decision = decision
            self.created_at = created_at

    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(
        metrics.approval_hold_storage, "get_all",
        lambda: [_H("h1", t0), _H("h2", t0)],
    )
    monkeypatch.setattr(
        metrics.approval_record_storage, "get_all",
        lambda: [
            _R("h1", "approved", t0 + timedelta(seconds=30)),
            _R("h2", "rejected", t0 + timedelta(seconds=10)),
        ],
    )
    out = metrics.render_prometheus()
    assert 'rmt_approval_latency_seconds_sum{decision="approved"} 30.0' in out
    assert 'rmt_approval_latency_seconds_count{decision="approved"} 1' in out
    assert 'rmt_approval_latency_seconds_sum{decision="rejected"} 10.0' in out
    assert 'rmt_approval_latency_seconds_count{decision="rejected"} 1' in out


def test_latency_excludes_records_without_a_matching_hold(monkeypatch):
    class _R:
        def __init__(self, approval_id, decision, created_at):
            self.approval_id = approval_id
            self.decision = decision
            self.created_at = created_at

    monkeypatch.setattr(metrics.approval_hold_storage, "get_all", lambda: [])
    monkeypatch.setattr(
        metrics.approval_record_storage, "get_all",
        lambda: [_R("no-hold", "approved", datetime.now(timezone.utc))],
    )
    out = metrics.render_prometheus()
    assert "rmt_approval_latency_seconds_sum{" not in out
    assert "rmt_approval_latency_seconds_count{" not in out


def test_latency_survives_a_broken_store(monkeypatch):
    def _boom():
        raise RuntimeError("store unreadable")

    monkeypatch.setattr(metrics.approval_hold_storage, "get_all", _boom)
    out = metrics.render_prometheus()
    # approval_hold_storage backs both the holds-by-status section and the
    # new latency section, so a broken store fails both independently.
    assert "rmt_metrics_scrape_errors_total 2" in out
    assert "rmt_up 1" in out
    assert "rmt_approval_latency_seconds_sum" not in out
