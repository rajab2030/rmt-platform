from pydantic import BaseModel


class GitState(BaseModel):
    branch: str
    commit: str


class ContainerState(BaseModel):
    running: int
    unhealthy: int


class DockerHealth(BaseModel):
    status: str


class BackupState(BaseModel):
    latest: str


class PlatformState(BaseModel):
    platform: str
    git: GitState
    containers: ContainerState
    health: DockerHealth
    backup: BackupState
