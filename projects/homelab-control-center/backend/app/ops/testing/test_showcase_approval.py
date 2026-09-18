"""The real showcase must never turn closed stdin into an approval request."""
import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def showcase():
    source = next(
        parent / "tools/rmt-showcase-agent/rmt_showcase.py"
        for parent in Path(__file__).resolve().parents
        if (parent / "tools/rmt-showcase-agent/rmt_showcase.py").is_file()
    )
    spec = importlib.util.spec_from_file_location("showcase_test_client", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_eof_leaves_action_held(showcase, monkeypatch):
    monkeypatch.setattr("builtins.input", Mock(side_effect=EOFError))
    call = Mock(side_effect=AssertionError("must not submit approval"))
    monkeypatch.setattr(showcase, "_call", call)
    with pytest.raises(SystemExit) as exc:
        showcase._approve("test-hold", "review the proposal")
    assert exc.value.code == 1
    call.assert_not_called()


def test_explicit_input_submits_approval(showcase, monkeypatch):
    monkeypatch.setattr("builtins.input", Mock(return_value=""))
    call = Mock(return_value={"status": "executed", "success": True})
    monkeypatch.setattr(showcase, "_call", call)
    showcase._approve("test-hold", "review the proposal")
    call.assert_called_once_with(
        "POST", "/homelab/approve?approval_id=test-hold&approved=true",
    )
