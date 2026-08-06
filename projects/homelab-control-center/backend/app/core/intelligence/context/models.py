from pydantic import BaseModel


class ComponentContext(BaseModel):
    name: str
    role: str
    criticality: str
    dependencies: list[str] = []
