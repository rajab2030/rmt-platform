"""D6: real threads at both production continuation handlers, isolated Core stores.

The suite's ASGI client runs sync handlers inline. Use threads explicitly here
to exercise production concurrency rather than inheriting that serialization.
"""
from concurrent.futures import ThreadPoolExecutor, wait
from threading import Event

import pytest

import app.main as main
import app.core.intelligence.actions.approval_service as approval
import app.core.intelligence.actions.service as actions
from app.core.intelligence.actions.models import ActionType
from app.core.intelligence.testing.test_governed_approval import (
    _make_action,
    _setup_isolation,
)
from app.ops.auth import OperatorIdentity


@pytest.mark.parametrize("first_route,second_route", [
    (main.approve, main.approve),
    (main.approve, main.homelab_approve),
    (main.homelab_approve, main.approve),
    (main.homelab_approve, main.homelab_approve),
])
@pytest.mark.parametrize("first_decision,second_decision", [
    (True, True), (True, False), (False, True),
])
def test_one_resolution_across_both_routes(
    monkeypatch, first_route, second_route, first_decision, second_decision,
):
    auth, _, _, _, registry = _setup_isolation(monkeypatch)
    monkeypatch.setenv("RMT_AUTH_SEPARATION", "false")
    held = actions.execute_governed_action(
        _make_action(ActionType.REMOVE), adapter_name="simulation",
    )
    assert held["status"] == "manual_approval_required"
    entered, release, attempted = Event(), Event(), Event()
    # Pause approval after its pending check, precisely where the original
    # race lets another resolver enter. Rejections have no binding step.
    target = approval if first_decision else approval.approval_record_storage
    name = "bind_action" if first_decision else "update"
    original = getattr(target, name)

    def paused(*args, **kwargs):
        entered.set()
        assert release.wait(5), "test did not release the first resolver"
        return original(*args, **kwargs)

    monkeypatch.setattr(target, name, paused)

    def resolve(route, approved, *, second=False):
        if second:
            attempted.set()
        return route(
            held["approval_id"], approved=approved,
            operator=OperatorIdentity(name="test-operator"),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(resolve, first_route, first_decision)
        try:
            assert entered.wait(5)
            second = pool.submit(resolve, second_route, second_decision, second=True)
            assert attempted.wait(5)
            # A concurrent rejection must not finish while approval is pending.
            # A second approval must not pass its own pending check either.
            assert not wait([second], timeout=0.1).done
        finally:
            release.set()
        results = [first.result(timeout=5), second.result(timeout=5)]

    assert results[0]["status"] == ("executed" if first_decision else "rejected")
    assert results[1]["status"] == "approval_already_resolved"
    assert len(auth.get_all()) == int(first_decision)
    assert registry.get.return_value.execute.call_count == int(first_decision)


def test_continuation_exception_releases_http_lock(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("test failure before continuation")

    monkeypatch.setattr(main, "approve_held_action", fail)
    with pytest.raises(RuntimeError, match="test failure"):
        main.approve("missing", operator=OperatorIdentity(name="test-operator"))
    assert main._approval_continuation_lock.acquire(blocking=False)
    main._approval_continuation_lock.release()
