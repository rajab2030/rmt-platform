from app.core.intelligence.memory.models import (
    MemoryRecord,
)

from app.core.intelligence.memory.storage import (
    save_memory,
    get_memory_history,
)


def remember(record: MemoryRecord):

    return save_memory(
        record
)


def get_history(component: str):

    return get_memory_history(
        component
)
