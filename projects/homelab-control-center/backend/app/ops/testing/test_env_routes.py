"""RMT-PROD P2 (V3) -- the environment-dependent routes in both modes.

`/containers`, `/containers/{name}/stats` (Docker socket) and `/platform/state`
(the `git` executable) were previously validated only opportunistically. These
tests pin both the capability-present and capability-absent behaviour so a
future adapter-mode drift is caught.
"""
import pytest
from fastapi.testclient import TestClient

import app.main as main_app
import app.docker_api as docker_api
from app.core.platform_state import service as ps_service


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("RMT_AUTH_ENABLED", "false")
    with TestClient(main_app.app) as c:
        yield c


# --- /containers -----------------------------------------------------------

def test_containers_docker_present(client, monkeypatch):
    monkeypatch.setattr(
        docker_api, "get_containers",
        lambda: [{"name": "uptime-kuma", "image": "louislam/uptime-kuma:1", "status": "running"}],
    )
    r = client.get("/containers")
    assert r.status_code == 200
    assert r.json()[0]["name"] == "uptime-kuma"


def test_containers_docker_absent_is_503(client, monkeypatch):
    def _boom():
        raise RuntimeError("Error while fetching server API version: permission denied")

    monkeypatch.setattr(docker_api, "get_containers", _boom)
    r = client.get("/containers")
    assert r.status_code == 503
    assert "docker unavailable" in r.json()["detail"]


def test_container_stats_docker_absent_is_503(client, monkeypatch):
    def _boom(name):
        raise RuntimeError("permission denied")

    monkeypatch.setattr(docker_api, "get_container_stats", _boom)
    assert client.get("/containers/uptime-kuma/stats").status_code == 503


# --- /platform/state -----------------------------------------------------

def test_platform_state_git_present(client, monkeypatch):
    from app.schemas.platform import (
        BackupState,
        ContainerState,
        DockerHealth,
        GitState,
        PlatformState,
    )

    monkeypatch.setattr(
        main_app, "get_platform_state",
        lambda provider: PlatformState(
            platform="RMT",
            git=GitState(branch="main", commit="abc1234"),
            containers=ContainerState(running=3, unhealthy=0),
            health=DockerHealth(status="ok"),
            backup=BackupState(latest="2026-09-08_09-22"),
        ),
    )
    r = client.get("/platform/state")
    assert r.status_code == 200
    assert r.json()["git"]["branch"] == "main"


def test_platform_state_git_absent_is_503(client, monkeypatch):
    def _no_git():
        raise FileNotFoundError("[Errno 2] No such file or directory: 'git'")

    monkeypatch.setattr(ps_service, "get_git_state", _no_git)
    r = client.get("/platform/state")
    assert r.status_code == 503
    assert "git unavailable" in r.json()["detail"]
