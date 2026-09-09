"""Test-session defaults.

Operator authentication (production-readiness P0, item S1) defaults to ON. The
existing suites exercise the governed lifecycle and the above-Core capabilities,
not the auth boundary, so unless a test opts in, run with auth disabled -- the
same ``RMT_AUTH_ENABLED=false`` local-dev escape hatch the app documents.

Auth enforcement itself is covered explicitly in
``app/ops/testing/test_auth.py``, which sets ``RMT_AUTH_ENABLED=true`` +
``RMT_OPERATOR_TOKENS`` for its own client.

SQLite substrate isolation:
  * The two observability stores (``container_metrics`` / ``intelligence_memory``
    in ``data/observability.db``) are redirected to a throwaway file and their
    schema created up front (``_isolate_sqlite_stores`` below).
  * The six governance-evidence stores share ``data/governance_evidence.db``
    (T0-1); ``RMT_EVIDENCE_DB`` is pointed at a throwaway file *before* any app
    import so the module singletons never touch the working tree.
So the suite is hermetic: it neither depends on nor writes the real ``data/``
stores. Mirrors the ``init_storage()`` calls in ``app/main.py``'s lifespan.
"""
import os
import tempfile

import pytest

_TEST_DATA_DIR = tempfile.mkdtemp(prefix="rmt-test-data-")


def pytest_configure(config):  # noqa: ARG001
    os.environ.setdefault("RMT_AUTH_ENABLED", "false")
    os.environ.setdefault(
        "RMT_EVIDENCE_DB",
        os.path.join(_TEST_DATA_DIR, "governance_evidence.db"),
    )


@pytest.fixture(scope="session", autouse=True)
def _isolate_sqlite_stores(tmp_path_factory):
    """Point the observability SQLite stores at a throwaway DB and create their
    schema. (The evidence stores are handled via RMT_EVIDENCE_DB in
    pytest_configure, since their singletons bind the path at import time.)"""
    import app.core.intelligence.memory.storage as intelligence_memory_storage
    import app.core.observability.storage as observability_storage

    db_path = tmp_path_factory.mktemp("rmt-sqlite") / "observability.db"

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(observability_storage, "DB_PATH", db_path)
        mp.setattr(intelligence_memory_storage, "DB_PATH", db_path)
        observability_storage.init_storage()
        intelligence_memory_storage.init_storage()
        yield
