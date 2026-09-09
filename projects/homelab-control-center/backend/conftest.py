"""Test-session defaults.

Operator authentication (production-readiness P0, item S1) defaults to ON. The
existing suites exercise the governed lifecycle and the above-Core capabilities,
not the auth boundary, so unless a test opts in, run with auth disabled -- the
same ``RMT_AUTH_ENABLED=false`` local-dev escape hatch the app documents.

Auth enforcement itself is covered explicitly in
``app/ops/testing/test_auth.py``, which sets ``RMT_AUTH_ENABLED=true`` +
``RMT_OPERATOR_TOKENS`` for its own client.

The two SQLite stores (``container_metrics`` and ``intelligence_memory``, both
in ``data/observability.db``) are redirected to a throwaway per-run file and
their schema is created up front, so the suite is hermetic: it neither depends
on a leftover ``data/observability.db`` in the working tree nor writes into it.
This mirrors the ``init_storage()`` calls in ``app/main.py``'s lifespan.
"""
import os

import pytest


def pytest_configure(config):  # noqa: ARG001
    os.environ.setdefault("RMT_AUTH_ENABLED", "false")


@pytest.fixture(scope="session", autouse=True)
def _isolate_sqlite_stores(tmp_path_factory):
    """Point both SQLite stores at a throwaway DB and create their schema."""
    import app.core.intelligence.memory.storage as intelligence_memory_storage
    import app.core.observability.storage as observability_storage

    db_path = tmp_path_factory.mktemp("rmt-sqlite") / "observability.db"

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(observability_storage, "DB_PATH", db_path)
        mp.setattr(intelligence_memory_storage, "DB_PATH", db_path)
        observability_storage.init_storage()
        intelligence_memory_storage.init_storage()
        yield
