"""RMT-PROD P1 (O1) -- structured logging: formatter shape, request-id
binding, the request middleware, and idempotent configuration."""
import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.ops import logging_config as lc


@pytest.fixture(autouse=True)
def _reset():
    lc._reset_for_tests()
    lc.request_id_var.set("-")
    yield
    lc._reset_for_tests()
    lc.request_id_var.set("-")


def _record(**extra):
    return logging.makeLogRecord(
        {
            "name": "rmt.test",
            "levelname": "INFO",
            "levelno": logging.INFO,
            "msg": "hello world",
            "created": 1_700_000_000.5,
            "msecs": 500.0,
            **extra,
        }
    )


# -- JSON formatter ----------------------------------------------------------

def test_json_formatter_has_the_core_keys():
    line = lc.JsonFormatter().format(_record())
    obj = json.loads(line)
    assert obj["level"] == "INFO"
    assert obj["logger"] == "rmt.test"
    assert obj["msg"] == "hello world"
    assert obj["request_id"] == "-"
    assert obj["ts"].endswith("Z")


def test_json_formatter_inlines_extra_fields():
    line = lc.JsonFormatter().format(
        _record(event="governed_execute", action_id="a1", principal="alice")
    )
    obj = json.loads(line)
    assert obj["event"] == "governed_execute"
    assert obj["action_id"] == "a1"
    assert obj["principal"] == "alice"


def test_json_formatter_carries_the_bound_request_id():
    lc.request_id_var.set("req-abc123")
    obj = json.loads(lc.JsonFormatter().format(_record()))
    assert obj["request_id"] == "req-abc123"


def test_json_formatter_is_single_line_valid_json():
    line = lc.JsonFormatter().format(_record(detail="a\nb"))
    assert "\n" not in line
    json.loads(line)  # must not raise


# -- text formatter --------------------------------------------------------

def test_text_formatter_used_when_json_disabled(monkeypatch):
    monkeypatch.setenv("RMT_LOG_JSON", "false")
    lc.configure_logging()
    handler = logging.getLogger("rmt").handlers[0]
    assert isinstance(handler.formatter, lc.TextFormatter)


# -- configure_logging ---------------------------------------------------

def test_configure_logging_is_idempotent():
    lc.configure_logging()
    lc.configure_logging()
    lc.configure_logging()
    assert len(logging.getLogger("rmt").handlers) == 1


def test_configure_logging_stops_propagation():
    lc.configure_logging()
    assert logging.getLogger("rmt").propagate is False


def test_configure_logging_reads_level_from_env(monkeypatch):
    monkeypatch.setenv("RMT_LOG_LEVEL", "warning")
    lc.configure_logging()
    assert logging.getLogger("rmt").level == logging.WARNING


def test_configure_logging_refreshes_level_on_recall(monkeypatch):
    lc.configure_logging()
    assert logging.getLogger("rmt").level == logging.INFO
    monkeypatch.setenv("RMT_LOG_LEVEL", "DEBUG")
    lc.configure_logging()
    assert logging.getLogger("rmt").level == logging.DEBUG
    assert len(logging.getLogger("rmt").handlers) == 1


# -- log_event -----------------------------------------------------------

def test_log_event_drops_none_and_reserved(caplog):
    logger = logging.getLogger("rmt.test.evt")
    with caplog.at_level(logging.INFO, logger="rmt.test.evt"):
        lc.log_event(
            logger,
            "my_event",
            action_id="x1",
            approval_id=None,        # dropped
            msg="should-not-clobber",  # reserved -> dropped
        )
    rec = caplog.records[-1]
    assert rec.message == "my_event"
    assert rec.event == "my_event"
    assert rec.action_id == "x1"
    assert not hasattr(rec, "approval_id")
    assert rec.msg == "my_event"  # not clobbered by the reserved kwarg


def test_log_event_respects_level(caplog):
    logger = logging.getLogger("rmt.test.lvl")
    with caplog.at_level(logging.DEBUG, logger="rmt.test.lvl"):
        lc.log_event(logger, "warn_event", level=logging.WARNING)
    assert caplog.records[-1].levelno == logging.WARNING


# -- RequestContextMiddleware -----------------------------------------

def _app_with_middleware():
    app = FastAPI()
    app.add_middleware(lc.RequestContextMiddleware)

    @app.get("/ping")
    def ping():
        return {"rid": lc.request_id_var.get()}

    @app.get("/boom")
    def boom():
        raise RuntimeError("kaboom")

    return app


def test_middleware_mints_and_echoes_a_request_id():
    client = TestClient(_app_with_middleware())
    r = client.get("/ping")
    assert r.status_code == 200
    rid = r.headers["x-request-id"]
    assert rid and rid != "-"
    assert r.json()["rid"] == rid  # the id was bound during the handler


def test_middleware_honours_an_inbound_request_id():
    client = TestClient(_app_with_middleware())
    r = client.get("/ping", headers={"X-Request-ID": "caller-supplied-42"})
    assert r.headers["x-request-id"] == "caller-supplied-42"
    assert r.json()["rid"] == "caller-supplied-42"


def test_middleware_logs_one_http_request_line(caplog):
    client = TestClient(_app_with_middleware())
    with caplog.at_level(logging.INFO, logger="rmt.http"):
        client.get("/ping")
    lines = [r for r in caplog.records if r.message == "http_request"]
    assert len(lines) == 1
    assert lines[0].method == "GET"
    assert lines[0].path == "/ping"
    assert lines[0].status == 200
    assert isinstance(lines[0].duration_ms, float)


def test_middleware_logs_and_reraises_on_handler_error(caplog):
    client = TestClient(_app_with_middleware(), raise_server_exceptions=False)
    with caplog.at_level(logging.ERROR, logger="rmt.http"):
        r = client.get("/boom")
    assert r.status_code == 500
    errs = [r for r in caplog.records if r.message == "http_request"]
    assert errs and errs[-1].status == 500
    assert errs[-1].levelno == logging.ERROR


def test_request_id_var_reset_after_request():
    client = TestClient(_app_with_middleware())
    client.get("/ping")
    assert lc.request_id_var.get() == "-"
