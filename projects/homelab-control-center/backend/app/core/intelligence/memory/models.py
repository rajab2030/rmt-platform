from datetime import datetime

from pydantic import BaseModel


class MemoryRecord(BaseModel):
    component: str
    event_type: str
    timestamp: datetime
    data: dict = {}
