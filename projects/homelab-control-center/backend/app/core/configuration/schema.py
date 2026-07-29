from pydantic import BaseModel


class PlatformConfig(BaseModel):
    name: str
    version: str


class EnvironmentConfig(BaseModel):
    name: str
    debug: bool = False


class APIConfig(BaseModel):
    host: str
    port: int


class RuntimeConfig(BaseModel):
    engine: str


class Settings(BaseModel):
    platform: PlatformConfig
    environment: EnvironmentConfig
    api: APIConfig
    runtime: RuntimeConfig
