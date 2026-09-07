"""Test-session defaults.

Operator authentication (production-readiness P0, item S1) defaults to ON. The
existing suites exercise the governed lifecycle and the above-Core capabilities,
not the auth boundary, so unless a test opts in, run with auth disabled -- the
same ``RMT_AUTH_ENABLED=false`` local-dev escape hatch the app documents.

Auth enforcement itself is covered explicitly in
``app/ops/testing/test_auth.py``, which sets ``RMT_AUTH_ENABLED=true`` +
``RMT_OPERATOR_TOKENS`` for its own client.
"""
import os


def pytest_configure(config):  # noqa: ARG001
    os.environ.setdefault("RMT_AUTH_ENABLED", "false")
