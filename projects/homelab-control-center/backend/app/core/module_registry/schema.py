from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class RuntimeInfo(BaseModel):
    engine: str
    service: Optional[str] = None
    container: Optional[str] = None
    ports: List[int] = []


class HealthInfo(BaseModel):
    status: str = "unknown"
    endpoint: Optional[str] = None
    last_check: Optional[str] = None


class Module(BaseModel):
    module_id: str = Field(..., description="Unique module identifier")

    name: str

    description: str = ""

    version: str

    type: str

    status: str

    runtime: RuntimeInfo

    dependencies: List[str] = []

    configuration: Dict = {}

    health: HealthInfo
