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
import asyncio
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
    os.environ.setdefault(
        "RMT_BUDGET_DB",
        os.path.join(_TEST_DATA_DIR, "budget.db"),
    )
    # B1a: single-shot observation in the suite so a deliberate state_mismatch
    # case does not spend the production 5 s settling budget. The dedicated
    # settling-poll test sets its own small non-zero value.
    os.environ.setdefault("RMT_VERIFY_OBSERVE_TIMEOUT_S", "0")

    # Starlette's synchronous TestClient depends on AnyIO's blocking portal,
    # which deadlocks in this execution environment before the ASGI lifespan
    # is entered. Preserve the existing synchronous test API while running the
    # documented httpx2 ASGITransport on one local asyncio.Runner instead.
    import fastapi.testclient
    import anyio.to_thread
    from httpx2 import ASGITransport, AsyncClient

    async def inline_test_run_sync(func, *args, **kwargs):  # noqa: ARG001
        """Run short synchronous route callables without the broken portal."""
        return func(*args)

    anyio.to_thread.run_sync = inline_test_run_sync

    class ASGITransportTestClient:
        __test__ = False

        def __init__(
            self,
            app,
            *,
            base_url="http://testserver",
            raise_server_exceptions=True,
            follow_redirects=True,
            headers=None,
            cookies=None,
            **kwargs,  # noqa: ARG002
        ):
            self.app = app
            self.base_url = base_url
            self.raise_server_exceptions = raise_server_exceptions
            self.follow_redirects = follow_redirects
            self.initial_headers = headers
            self.initial_cookies = cookies
            self._runner = None
            self._lifespan = None
            self._client = None

        async def _open(self, *, lifespan=False):
            if lifespan:
                self._lifespan = self.app.router.lifespan_context(self.app)
                await self._lifespan.__aenter__()
            self._client = AsyncClient(
                transport=ASGITransport(
                    app=self.app,
                    raise_app_exceptions=self.raise_server_exceptions,
                ),
                base_url=self.base_url,
                follow_redirects=self.follow_redirects,
                headers=self.initial_headers,
                cookies=self.initial_cookies,
            )
            await self._client.__aenter__()

        def _ensure_open(self, *, lifespan=False):
            if self._runner is None:
                self._runner = asyncio.Runner()
                self._runner.run(self._open(lifespan=lifespan))

        def request(self, method, url, **kwargs):
            self._ensure_open()
            return self._runner.run(self._client.request(method, url, **kwargs))

        def get(self, url, **kwargs):
            return self.request("GET", url, **kwargs)

        def post(self, url, **kwargs):
            return self.request("POST", url, **kwargs)

        def put(self, url, **kwargs):
            return self.request("PUT", url, **kwargs)

        def patch(self, url, **kwargs):
            return self.request("PATCH", url, **kwargs)

        def delete(self, url, **kwargs):
            return self.request("DELETE", url, **kwargs)

        def options(self, url, **kwargs):
            return self.request("OPTIONS", url, **kwargs)

        def head(self, url, **kwargs):
            return self.request("HEAD", url, **kwargs)

        def __enter__(self):
            self._ensure_open(lifespan=True)
            return self

        def __exit__(self, exc_type, exc, traceback):
            if self._runner is not None:
                self._runner.run(self._client.__aexit__(exc_type, exc, traceback))
                if self._lifespan is not None:
                    self._runner.run(
                        self._lifespan.__aexit__(exc_type, exc, traceback)
                    )
                self._runner.close()
                self._runner = None

    fastapi.testclient.TestClient = ASGITransportTestClient


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


@pytest.fixture(autouse=True)
def _isolate_background_collector(monkeypatch):
    """HTTP tests exercise routes, not the perpetual Docker polling task."""
    import app.main as main_app

    async def idle_collector():
        await asyncio.Event().wait()

    monkeypatch.setattr(main_app, "collect_metrics", idle_collector)
