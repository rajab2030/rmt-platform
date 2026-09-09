"""T1-2 -- operator-declarable homelab dependency edges.

``RMT_HOMELAB_DEPENDENCIES`` lets an operator add a real inter-component
dependency edge via a systemd drop-in (no code change). The env edges are
unioned into the static all-independent map by ``app/homelab/dependencies.py``;
a declared edge activates the T13 dependency-cascade escalation guard.

Run-safe: only environment variables are set; no store, container, or network
is touched.
"""
import pytest

from app.ops import ops_config
from app.homelab import dependencies as deps


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("RMT_HOMELAB_DEPENDENCIES", raising=False)
    yield


# --- parsing -------------------------------------------------------------

def test_unset_env_means_no_edges():
    assert ops_config.homelab_dependency_edges() == {}
    assert deps.dependency_sources()["env"] == {}


def test_parses_single_group(monkeypatch):
    monkeypatch.setenv("RMT_HOMELAB_DEPENDENCIES", "web:db")
    assert ops_config.homelab_dependency_edges() == {"web": ["db"]}


def test_parses_multiple_groups_and_multi_deps(monkeypatch):
    monkeypatch.setenv(
        "RMT_HOMELAB_DEPENDENCIES", " web : db, cache ; api:db "
    )
    assert ops_config.homelab_dependency_edges() == {
        "web": ["db", "cache"],
        "api": ["db"],
    }


def test_malformed_groups_are_skipped(monkeypatch):
    # no colon / empty component / no deps / trailing separators
    monkeypatch.setenv(
        "RMT_HOMELAB_DEPENDENCIES", "garbage;:db;web:;web:db;;"
    )
    assert ops_config.homelab_dependency_edges() == {"web": ["db"]}


def test_duplicate_deps_collapse(monkeypatch):
    monkeypatch.setenv("RMT_HOMELAB_DEPENDENCIES", "web:db,db,db")
    assert ops_config.homelab_dependency_edges() == {"web": ["db"]}


# --- union with the static map -----------------------------------------

def test_static_map_stays_all_independent():
    assert deps.HOMELAB_DEPENDENCIES == {
        "portainer": [],
        "dozzle": [],
        "uptime-kuma": [],
    }


def test_env_edge_unions_into_accessors(monkeypatch):
    monkeypatch.setenv("RMT_HOMELAB_DEPENDENCIES", "uptime-kuma:portainer")
    assert deps.dependencies_of("uptime-kuma") == ["portainer"]
    assert deps.dependents_of("portainer") == {"uptime-kuma"}
    assert deps.resolved_map()["uptime-kuma"] == ["portainer"]
    # a brand-new component introduced only by the env edge
    monkeypatch.setenv("RMT_HOMELAB_DEPENDENCIES", "web:db")
    assert deps.dependents_of("db") == {"web"}


def test_dependency_sources_splits_static_and_env(monkeypatch):
    monkeypatch.setenv("RMT_HOMELAB_DEPENDENCIES", "web:db")
    src = deps.dependency_sources()
    assert src["static"] == {
        "portainer": [],
        "dozzle": [],
        "uptime-kuma": [],
    }
    assert src["env"] == {"web": ["db"]}


def test_no_env_edge_keeps_map_independent():
    assert deps.dependents_of("portainer") == set()
    assert deps.dependents_of("dozzle") == set()
    assert deps.dependents_of("uptime-kuma") == set()
