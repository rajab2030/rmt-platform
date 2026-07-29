from pydantic import BaseModel

from app.core.configuration.schema import Settings


class PublicConfiguration(BaseModel):
    platform_name: str
    platform_version: str

    environment: str

    api_host: str
    api_port: int

    runtime_engine: str


def create_public_config(
    settings: Settings
) -> PublicConfiguration:

    return PublicConfiguration(
        platform_name=settings.platform.name,
        platform_version=settings.platform.version,

        environment=settings.environment.name,

        api_host=settings.api.host,
        api_port=settings.api.port,

        runtime_engine=settings.runtime.engine
    )
