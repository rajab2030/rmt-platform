"""RMT-CAP-14 (P-A, slice 1) -- remediation policy as configuration.

Covers docs/RMT_CAP_14_PROPOSAL.md §3b (one rejecting test per rule), the
unset => built-in default, file-replaces-built-in (D3), empty policy allowed
(D4), fail-closed module load (D1), the loop status ``policy_source`` field,
and the offline checker. Nothing here touches a real container or store.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from app.core.intelligence.actions.models import ActionType
from app.core.intelligence.schemas import HealthStatus
from app.homelab import policy_config
from app.homelab.policy_config import (
    ENV_VAR,
    PolicyConfigError,
    load_policy_file,
    resolve_policy,
)
from app.homelab.remediation import BUILTIN_REMEDIATION_POLICY

BACKEND = Path(__file__).resolve().parents[3]
EXAMPLE = BACKEND.parent / "deploy" / "remediation_policy.example.toml"
CHECKER = BACKEND / "scripts" / "rmt-policy-check.py"

GOOD_ENTRY = """
[components.{name}]
action = "restart"
remediate_on = ["critical"]
expected_state = "running"
requires_approval = true
"""


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.delenv("RMT_HOMELAB_DEPENDENCIES", raising=False)


def _write(tmp_path, text, name="policy.toml"):
    p = tmp_path / name
    p.write_text(text)
    return str(p)


def _errors(tmp_path, text):
    with pytest.raises(PolicyConfigError) as exc:
        load_policy_file(_write(tmp_path, text))
    return "\n".join(exc.value.errors)


# -- defaults and the happy path ----------------------------------------------


def test_unset_env_returns_builtin_unchanged():
    policy, source = resolve_policy(BUILTIN_REMEDIATION_POLICY)
    assert policy is BUILTIN_REMEDIATION_POLICY
    assert source.source == "builtin"
    assert source.path is None and source.sha256 is None
    assert source.components == list(BUILTIN_REMEDIATION_POLICY)


def test_example_file_is_equivalent_to_builtin():
    policy, source = load_policy_file(str(EXAMPLE))
    assert policy == BUILTIN_REMEDIATION_POLICY
    assert source.source == "file"
    assert len(source.sha256) == 64


def test_env_file_replaces_builtin(tmp_path, monkeypatch):
    """D3: the file replaces the built-in policy -- portainer is absent."""
    path = _write(
        tmp_path,
        GOOD_ENTRY.format(name="dozzle")
        + '\n[components.uptime-kuma]\naction = "restart"\n'
        'remediate_on = ["warning", "critical"]\nexpected_state = "running"\n'
        "requires_approval = true\n",
    )
    monkeypatch.setenv(ENV_VAR, path)
    policy, source = resolve_policy(BUILTIN_REMEDIATION_POLICY)
    assert set(policy) == {"dozzle", "uptime-kuma"}
    assert policy["uptime-kuma"]["remediate_on"] == {
        HealthStatus.WARNING,
        HealthStatus.CRITICAL,
    }
    assert policy["dozzle"]["action_type"] is ActionType.RESTART
    assert policy["dozzle"]["requires_approval"] is True
    assert source.source == "file" and source.path == path


def test_empty_policy_allowed_with_warning(tmp_path, monkeypatch, caplog):
    """D4: an empty [components] table loads; the loop never remediates."""
    monkeypatch.setenv(ENV_VAR, _write(tmp_path, "[components]\n"))
    with caplog.at_level("WARNING", logger="rmt.homelab.policy"):
        policy, source = resolve_policy(BUILTIN_REMEDIATION_POLICY)
    assert policy == {}
    assert source.components == []
    assert any(
        getattr(r, "event", "") == "homelab_remediation_policy_empty"
        for r in caplog.records
    )


def test_sha256_tracks_file_bytes(tmp_path):
    a = load_policy_file(_write(tmp_path, GOOD_ENTRY.format(name="dozzle"), "a.toml"))
    b = load_policy_file(
        _write(tmp_path, "# edited\n" + GOOD_ENTRY.format(name="dozzle"), "b.toml")
    )
    assert a[0] == b[0]
    assert a[1].sha256 != b[1].sha256


# -- one rejecting test per §3b rule ------------------------------------------


def test_rule1_requires_approval_false_rejected(tmp_path):
    text = GOOD_ENTRY.format(name="dozzle").replace(
        "requires_approval = true", "requires_approval = false"
    )
    assert "requires_approval must be true" in _errors(tmp_path, text)


def test_rule1_requires_approval_absent_rejected(tmp_path):
    text = GOOD_ENTRY.format(name="dozzle").replace("requires_approval = true\n", "")
    assert "missing key(s): requires_approval" in _errors(tmp_path, text)


def test_rule1_requires_approval_truthy_non_bool_rejected(tmp_path):
    text = GOOD_ENTRY.format(name="dozzle").replace(
        "requires_approval = true", "requires_approval = 1"
    )
    assert "requires_approval must be true" in _errors(tmp_path, text)


def test_rule2_dependency_edge_via_env_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("RMT_HOMELAB_DEPENDENCIES", "uptime-kuma:dozzle")
    errs = _errors(tmp_path, GOOD_ENTRY.format(name="dozzle"))
    assert "has dependency edges" in errs
    assert "depended on by ['uptime-kuma']" in errs


def test_rule2_declared_depends_on_rejected(tmp_path):
    text = GOOD_ENTRY.format(name="dozzle") + 'depends_on = ["portainer"]\n'
    errs = _errors(tmp_path, text)
    assert "declares 'depends_on'" in errs
    assert "safe envelope" in errs


def test_rule3_unknown_component_rejected(tmp_path):
    assert "unknown component" in _errors(
        tmp_path, GOOD_ENTRY.format(name="not-a-service")
    )


def test_rule4_action_outside_allow_list_rejected(tmp_path):
    text = GOOD_ENTRY.format(name="dozzle").replace('"restart"', '"stop"')
    assert "action 'stop' not allowed" in _errors(tmp_path, text)


@pytest.mark.parametrize("trigger", ["healthy", "unknown"])
def test_rule5_healthy_or_unknown_trigger_rejected(tmp_path, trigger):
    text = GOOD_ENTRY.format(name="dozzle").replace('["critical"]', f'["{trigger}"]')
    assert f"remediate_on value '{trigger}' not allowed" in _errors(tmp_path, text)


def test_rule5_empty_trigger_list_rejected(tmp_path):
    text = GOOD_ENTRY.format(name="dozzle").replace('["critical"]', "[]")
    assert "remediate_on must be a non-empty list" in _errors(tmp_path, text)


def test_rule6_blank_expected_state_rejected(tmp_path):
    text = GOOD_ENTRY.format(name="dozzle").replace('"running"', '"  "')
    assert "expected_state must be a non-empty string" in _errors(tmp_path, text)


def test_rule7_misspelled_key_rejected(tmp_path):
    text = GOOD_ENTRY.format(name="dozzle") + "requires_aproval = true\n"
    assert "unknown key(s): requires_aproval" in _errors(tmp_path, text)


def test_rule7_unknown_top_level_key_rejected(tmp_path):
    text = 'version = 2\n' + GOOD_ENTRY.format(name="dozzle")
    assert "unknown top-level key(s): version" in _errors(tmp_path, text)


def test_rule8_invalid_toml_rejected(tmp_path):
    assert "not valid TOML" in _errors(tmp_path, "[components.dozzle\n")


def test_rule8_missing_components_table_rejected(tmp_path):
    assert "missing [components] table" in _errors(tmp_path, "")


def test_unreadable_file_rejected(tmp_path):
    with pytest.raises(PolicyConfigError) as exc:
        load_policy_file(str(tmp_path / "missing.toml"))
    assert "cannot read file" in exc.value.errors[0]


def test_all_violations_reported_not_just_first(tmp_path):
    text = (
        GOOD_ENTRY.format(name="dozzle").replace("true", "false")
        + GOOD_ENTRY.format(name="ghost").replace('"restart"', '"remove"')
    )
    errs = _errors(tmp_path, text)
    assert "components.dozzle: requires_approval must be true" in errs
    assert "components.ghost: unknown component" in errs
    assert "components.ghost: action 'remove' not allowed" in errs


# -- D1: fail-closed at module load -------------------------------------------


def test_invalid_file_stops_remediation_module_load(tmp_path, monkeypatch):
    """D1: with an invalid file, loading app/homelab/remediation.py raises --
    so app.main (which imports it via the operational loop) cannot start.
    Executed under a throwaway module name so the real module is untouched."""
    text = GOOD_ENTRY.format(name="dozzle").replace("true", "false")
    monkeypatch.setenv(ENV_VAR, _write(tmp_path, text))
    spec = importlib.util.spec_from_file_location(
        "_cap14_remediation_under_test",
        BACKEND / "app" / "homelab" / "remediation.py",
    )
    module = importlib.util.module_from_spec(spec)
    with pytest.raises(PolicyConfigError, match="requires_approval must be true"):
        spec.loader.exec_module(module)


def test_rejection_is_logged(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv(ENV_VAR, _write(tmp_path, "[components.ghost]\n"))
    with caplog.at_level("ERROR", logger="rmt.homelab.policy"):
        with pytest.raises(PolicyConfigError):
            resolve_policy(BUILTIN_REMEDIATION_POLICY)
    assert any(
        getattr(r, "event", "") == "homelab_remediation_policy_rejected"
        for r in caplog.records
    )


# -- observability -----------------------------------------------------------


def test_loop_status_reports_policy_source():
    from app.homelab.operational_loop import HomelabOperationalLoop

    status = HomelabOperationalLoop().get_status()
    assert status["policy_source"]["source"] == "builtin"
    assert status["policy_source"]["components"] == status["policy_components"]


def test_policy_source_matches_module_state():
    from app.homelab import remediation

    assert remediation.REMEDIATION_POLICY_SOURCE.components == list(
        remediation.REMEDIATION_POLICY
    )


# -- offline checker ---------------------------------------------------------


def _check(path, env_extra=None):
    import os

    env = {k: v for k, v in os.environ.items() if k != "RMT_HOMELAB_DEPENDENCIES"}
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, str(CHECKER), path],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def test_checker_valid_exit_0():
    r = _check(str(EXAMPLE))
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("VALID")
    assert "uptime-kuma: restart on critical" in r.stdout


def test_checker_invalid_exit_1(tmp_path):
    text = GOOD_ENTRY.format(name="dozzle").replace("true", "false")
    r = _check(_write(tmp_path, text))
    assert r.returncode == 1, r.stderr
    assert r.stdout.startswith("INVALID")
    assert "requires_approval must be true" in r.stdout


def test_checker_uses_shell_dependency_env(tmp_path):
    path = _write(tmp_path, GOOD_ENTRY.format(name="dozzle"))
    assert _check(path).returncode == 0
    r = _check(path, {"RMT_HOMELAB_DEPENDENCIES": "dozzle:portainer"})
    assert r.returncode == 1
    assert "has dependency edges" in r.stdout


def test_module_constants_are_the_slice1_allow_lists():
    assert set(policy_config.ALLOWED_ACTIONS) == {"restart"}
    assert set(policy_config.ALLOWED_TRIGGERS) == {"warning", "critical"}
