from pydantic import BaseModel


class Container(BaseModel):
    name: str
    image: str
    status: str
