from app.core.intelligence.memory.models import (
    MemoryRecord,
)


_MEMORY: list[MemoryRecord] = []


def remember(record: MemoryRecord):

    _MEMORY.append(record)

    return record


def get_history(component: str):

    return [
        item
        for item in _MEMORY
        if item.component == component
    ]
