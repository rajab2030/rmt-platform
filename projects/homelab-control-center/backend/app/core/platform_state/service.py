import os
import subprocess

from app.schemas.platform import (
    PlatformState,
    GitState,
    ContainerState,
    DockerHealth,
    BackupState,
)

from app.docker_api import get_containers


BASE_PATH = os.path.expanduser("~/homelab")


def get_git_state():

    commit = subprocess.check_output(
        [
            "git",
            "-C",
            BASE_PATH,
            "rev-parse",
            "--short",
            "HEAD",
        ],
        text=True,
    ).strip()

    branch = subprocess.check_output(
        [
            "git",
            "-C",
            BASE_PATH,
            "branch",
            "--show-current",
        ],
        text=True,
    ).strip()

    return GitState(
        branch=branch,
        commit=commit,
    )


def get_container_state():

    containers = get_containers()

    running = len(
        [
            c for c in containers
            if c["status"] == "running"
        ]
    )

    unhealthy = len(
        [
            c for c in containers
            if "unhealthy" in c["status"]
        ]
    )

    return ContainerState(
        running=running,
        unhealthy=unhealthy,
    )


def get_docker_health():

    status = "unhealthy"

    result = subprocess.run(
        [
            "systemctl",
            "is-active",
            "docker",
        ],
        capture_output=True,
        text=True,
    )

    if result.stdout.strip() == "active":
        status = "healthy"

    return DockerHealth(
        status=status
    )


def get_backup_state():

    backup_path = os.path.join(
        BASE_PATH,
        "backups",
        "daily",
    )

    latest = "none"

    if os.path.exists(backup_path):

        backups = sorted(
            os.listdir(backup_path),
            reverse=True,
        )

        if backups:
            latest = backups[0]

    return BackupState(
        latest=latest
    )


def get_platform_state():

    return PlatformState(
        platform="RMT",
        git=get_git_state(),
        containers=get_container_state(),
        health=get_docker_health(),
        backup=get_backup_state(),
    )
