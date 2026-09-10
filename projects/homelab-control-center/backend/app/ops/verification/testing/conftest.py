"""Shared isolation for the above-Core verification-layer tests.

The effective-status index (`app/ops/verification/index.py`) and the
notification de-dupe map (`app/ops/notifications.py`) are module-global; reset
both around every test so rows / de-dupe state never leak between them.
"""
import pytest

from app.ops import notifications
from app.ops.verification import index


@pytest.fixture(autouse=True)
def _reset_verification_layer():
    index.reset()
    notifications._reset_for_tests()
    yield
    index.reset()
    notifications._reset_for_tests()
