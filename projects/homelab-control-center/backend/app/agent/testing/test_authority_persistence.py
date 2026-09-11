"""RMT-CAP-08 -- authority grants survive a process restart (run-safe).

Every test here uses a disposable ``tmp_path`` SQLite file -- never the real
``data/governance_evidence.db`` the live service reads. "Restart" is
simulated the same way every other durable-store test in this codebase
simulates it: construct a fresh instance pointed at the same file.
"""
from datetime import datetime, timedelta, timezone

from app.agent.authority import AuthorityGrant, AuthorityGrantStorage, AuthorityStore


def _store(tmp_path, name="evidence.db"):
    return AuthorityStore(AuthorityGrantStorage(file_path=tmp_path / name))


def test_grant_survives_a_simulated_restart(tmp_path):
    s1 = _store(tmp_path)
    g = s1.grant(operation="create", target="proof", granted_by="op")

    s2 = _store(tmp_path)  # fresh instance, same file == "restart"
    ok, why = s2.check(g.grant_id, "create", "proof")
    assert (ok, why) == (True, "ok")


def test_consume_persists_across_a_simulated_restart(tmp_path):
    s1 = _store(tmp_path)
    g = s1.grant(operation="create", target="proof", granted_by="op")
    s1.consume(g.grant_id)

    s2 = _store(tmp_path)
    reloaded = s2.get(g.grant_id)
    assert reloaded.consumed is True
    assert reloaded.consumed_at is not None

    ok, why = s2.check(g.grant_id, "create", "proof")
    assert (ok, why) == (False, "grant_consumed")


def test_reset_only_clears_the_instance_it_is_called_on(tmp_path):
    """reset() wipes the storage it's bound to -- an isolated in-memory
    instance never touches a file-backed one."""
    file_store = _store(tmp_path)
    file_store.grant(operation="create", target="proof", granted_by="op")

    memory_store = AuthorityStore(AuthorityGrantStorage(file_path=None))
    memory_store.grant(operation="create", target="other", granted_by="op")
    memory_store.reset()

    assert memory_store.list_active() == []
    # The file-backed store (a different instance) is untouched.
    assert len(_store(tmp_path).list_active()) == 1


def test_reset_on_the_same_file_backed_instance_clears_it(tmp_path):
    s1 = _store(tmp_path)
    s1.grant(operation="create", target="proof", granted_by="op")
    s1.reset()

    s2 = _store(tmp_path)  # fresh instance, same file
    assert s2.list_active() == []


def test_scope_and_expiry_checks_unchanged(tmp_path):
    """Regression: the persistence change didn't alter check() semantics."""
    s = _store(tmp_path)

    assert s.check(None, "create", "x") == (False, "no_grant")
    assert s.check("does-not-exist", "create", "x") == (False, "no_grant")

    g = s.grant(operation="create", target="proof", granted_by="op")
    assert s.check(g.grant_id, "remove", "proof") == (False, "grant_scope_mismatch")
    assert s.check(g.grant_id, "create", "other") == (False, "grant_scope_mismatch")
    assert s.check(g.grant_id, "create", "proof") == (True, "ok")


def test_list_active_excludes_consumed(tmp_path):
    s = _store(tmp_path)
    to_consume = s.grant(operation="create", target="a", granted_by="op")
    stays_active = s.grant(operation="create", target="b", granted_by="op")
    assert {g.grant_id for g in s.list_active()} == {
        to_consume.grant_id, stays_active.grant_id
    }

    s.consume(to_consume.grant_id)
    remaining = s.list_active()
    assert [g.grant_id for g in remaining] == [stays_active.grant_id]


def test_expired_grant_is_not_active_and_fails_check(tmp_path):
    storage = AuthorityGrantStorage(file_path=tmp_path / "evidence.db")
    expired = AuthorityGrant(
        grant_id="expired-1",
        operation="create",
        target="proof",
        granted_by="op",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    storage.save(expired)
    s = AuthorityStore(storage)

    assert s.check("expired-1", "create", "proof") == (False, "grant_expired")
    assert "expired-1" not in {g.grant_id for g in s.list_active()}
