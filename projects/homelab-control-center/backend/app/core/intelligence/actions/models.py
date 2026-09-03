from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.intelligence.verification.models import ExpectedOutcome


class ActionType(str, Enum):

    RESTART_COMPONENT = "restart_component"

    CREATE_CHECKPOINT = "create_checkpoint"

    SCALE_DOWN = "scale_down"

    ISOLATE_COMPONENT = "isolate_component"

    START = "start"

    STOP = "stop"

    RESTART = "restart"

    CREATE = "create"

    REMOVE = "remove"


class ActionStatus(str, Enum):

    PENDING = "pending"

    VALIDATING = "validating"

    APPROVED = "approved"

    REJECTED = "rejected"

    COMPLETED = "completed"

    FAILED = "failed"


class ActionRequest(BaseModel):

    action_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    decision_id: str

    component: str

    action_type: ActionType

    status: ActionStatus = ActionStatus.PENDING

    reason: str

    confidence: int = 0

    requires_approval: bool = True

    rollback_required: bool = True

    parameters: dict = Field(default_factory=dict)

    expected_outcome: ExpectedOutcome | None = None
