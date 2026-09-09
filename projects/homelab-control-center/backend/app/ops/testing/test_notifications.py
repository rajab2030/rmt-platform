"""RMT-PROD P0 (O2) -- held-action notifications: best-effort, fail-open."""
import pytest

from app.ops import notifications as notif


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    notif._reset_for_tests()
    # no dedupe suppression unless a test asks for it
    monkeypatch.setenv("RMT_NOTIFY_MIN_INTERVAL_SECONDS", "0")
    yield
    notif._reset_for_tests()


class _Resp:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return b"ok"


def test_webhook_posts_once_when_configured(monkeypatch):
    monkeypatch.setenv("RMT_NOTIFY_WEBHOOK_URL", "http://sink.local/hook")
    calls = []
    monkeypatch.setattr(
        notif.urllib.request,
        "urlopen",
        lambda req, timeout=None: calls.append(req) or _Resp(),
    )
    notif.notify_held(
        kind="remediation", component="uptime-kuma",
        approval_id="a1", detail="held", source="test",
    )
    assert len(calls) == 1
    assert calls[0].full_url == "http://sink.local/hook"
    assert b"uptime-kuma" in calls[0].data


def test_no_webhook_means_no_http(monkeypatch):
    monkeypatch.delenv("RMT_NOTIFY_WEBHOOK_URL", raising=False)
    called = []
    monkeypatch.setattr(
        notif.urllib.request,
        "urlopen",
        lambda *a, **k: called.append(1) or _Resp(),
    )
    notif.notify_held(kind="remediation", component="x", approval_id="a")
    assert called == []  # logged only


def test_transport_error_is_swallowed(monkeypatch):
    monkeypatch.setenv("RMT_NOTIFY_WEBHOOK_URL", "http://sink.local/hook")

    def boom(*a, **k):
        raise OSError("connection refused")

    monkeypatch.setattr(notif.urllib.request, "urlopen", boom)
    # must not raise
    notif.notify_held(kind="agent_proposal", component="x", approval_id="a")


def test_dedupe_within_interval(monkeypatch):
    monkeypatch.setenv("RMT_NOTIFY_WEBHOOK_URL", "http://sink.local/hook")
    monkeypatch.setenv("RMT_NOTIFY_MIN_INTERVAL_SECONDS", "3600")
    calls = []
    monkeypatch.setattr(
        notif.urllib.request,
        "urlopen",
        lambda req, timeout=None: calls.append(req) or _Resp(),
    )
    for _ in range(4):
        notif.notify_held(
            kind="remediation", component="c", approval_id="same", source="t"
        )
    assert len(calls) == 1  # only the first got through

    # a different hold key is not suppressed
    notif.notify_held(
        kind="remediation", component="c", approval_id="other", source="t"
    )
    assert len(calls) == 2


# --- T1-4: RMT_NOTIFY_FORMAT payload shaping ---------------------------


def _capture(monkeypatch):
    calls = []
    monkeypatch.setenv("RMT_NOTIFY_WEBHOOK_URL", "http://sink.local/hook")
    monkeypatch.setattr(
        notif.urllib.request,
        "urlopen",
        lambda req, timeout=None: calls.append(req) or _Resp(),
    )
    return calls


def test_generic_format_is_unchanged_json(monkeypatch):
    calls = _capture(monkeypatch)  # no RMT_NOTIFY_FORMAT -> generic
    notif.notify_held(
        kind="remediation", component="uptime-kuma", approval_id="a1",
        detail="held", source="t",
    )
    import json as _json
    body = _json.loads(calls[0].data)
    assert body["event"] == "held_for_approval"
    assert body["component"] == "uptime-kuma"
    assert calls[0].headers["Content-type"] == "application/json"


def test_slack_format_sends_text_object(monkeypatch):
    monkeypatch.setenv("RMT_NOTIFY_FORMAT", "slack")
    calls = _capture(monkeypatch)
    notif.notify_held(
        kind="agent_proposal", component="dozzle", approval_id="a9",
        detail="needs a human", source="t",
    )
    import json as _json
    body = _json.loads(calls[0].data)
    assert set(body) == {"text"}
    assert "dozzle" in body["text"] and "a9" in body["text"]


def test_ntfy_format_sends_plain_body_and_headers(monkeypatch):
    monkeypatch.setenv("RMT_NOTIFY_FORMAT", "ntfy")
    calls = _capture(monkeypatch)
    notif.notify_ops(kind="loop_quarantine", detail="3 held", key="uptime-kuma")
    req = calls[0]
    assert b"OPS ALERT" in req.data and b"uptime-kuma" in req.data
    assert req.headers.get("Tags") == "rotating_light"
    assert req.headers.get("Priority") == "urgent"


def test_unknown_format_falls_back_to_generic(monkeypatch):
    monkeypatch.setenv("RMT_NOTIFY_FORMAT", "carrier-pigeon")
    calls = _capture(monkeypatch)
    notif.notify_held(kind="remediation", component="x", approval_id="a")
    import json as _json
    assert _json.loads(calls[0].data)["event"] == "held_for_approval"


# --- O3: notify_ops ------------------------------------------------------


def test_notify_ops_posts_when_configured(monkeypatch):
    monkeypatch.setenv("RMT_NOTIFY_WEBHOOK_URL", "http://sink.local/hook")
    calls = []
    monkeypatch.setattr(
        notif.urllib.request,
        "urlopen",
        lambda req, timeout=None: calls.append(req) or _Resp(),
    )
    notif.notify_ops(
        kind="loop_quarantine", detail="3 held attempts", key="uptime-kuma",
        source="cap04_loop",
    )
    assert len(calls) == 1
    assert b"ops_alert" in calls[0].data
    assert b"loop_quarantine" in calls[0].data
    assert b"uptime-kuma" in calls[0].data


def test_notify_ops_no_webhook_is_log_only(monkeypatch):
    monkeypatch.delenv("RMT_NOTIFY_WEBHOOK_URL", raising=False)
    called = []
    monkeypatch.setattr(
        notif.urllib.request, "urlopen",
        lambda *a, **k: called.append(1) or _Resp(),
    )
    notif.notify_ops(kind="loop_cycle_error", detail="boom", key="run_cycle")
    assert called == []


def test_notify_ops_fail_open(monkeypatch):
    monkeypatch.setenv("RMT_NOTIFY_WEBHOOK_URL", "http://sink.local/hook")
    monkeypatch.setattr(
        notif.urllib.request, "urlopen",
        lambda *a, **k: (_ for _ in ()).throw(OSError("refused")),
    )
    notif.notify_ops(kind="loop_quarantine", key="x")  # must not raise


def test_notify_ops_dedupes_per_kind_and_key(monkeypatch):
    monkeypatch.setenv("RMT_NOTIFY_WEBHOOK_URL", "http://sink.local/hook")
    monkeypatch.setenv("RMT_NOTIFY_MIN_INTERVAL_SECONDS", "3600")
    calls = []
    monkeypatch.setattr(
        notif.urllib.request, "urlopen",
        lambda req, timeout=None: calls.append(req) or _Resp(),
    )
    for _ in range(3):
        notif.notify_ops(kind="loop_quarantine", key="uptime-kuma")
    assert len(calls) == 1
    notif.notify_ops(kind="loop_quarantine", key="dozzle")      # other key
    notif.notify_ops(kind="loop_cycle_error", key="uptime-kuma")  # other kind
    assert len(calls) == 3
