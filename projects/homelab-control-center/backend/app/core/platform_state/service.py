import os
import subprocess

from app.schemas.platform import (
    PlatformState,
    GitState,
    BackupState,
)

from app.core.platform_state.provider import PlatformStateProvider


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


def get_platform_state(
    provider: PlatformStateProvider,
) -> PlatformState:

    return PlatformState(
        platform="RMT",
        git=get_git_state(),
        containers=provider.get_container_state(),
        health=provider.get_docker_health(),
        backup=get_backup_state(),
    )
