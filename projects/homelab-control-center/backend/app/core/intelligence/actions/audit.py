from datetime import datetime, timezone

from app.core.intelligence.actions.models import (
    ActionRequest,
)

from app.core.intelligence.memory.models import (
    MemoryRecord,
)


def action_to_memory(
    action: ActionRequest,
    event_type: str,
    details: dict | None = None,
):
    """
    Convert an action lifecycle event into
    an intelligence memory record.

    This does not store the record.
    It only creates the memory object.
    """

    return MemoryRecord(
        component=action.component,
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
        data={
            "action_id": action.action_id,
            "action_type": action.action_type.value,
            "status": action.status.value,
            "reason": action.reason,
            "confidence": action.confidence,
            **(details or {}),
        },
    )
