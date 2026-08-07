from datetime import datetime

from pydantic import BaseModel, Field


class ComponentObservation(BaseModel):
    """
    Generic observation model consumed by Intelligence Core.

    Intelligence should not depend on the original data source
    (Docker, systemd, VM, Kubernetes, etc.).
    """

    component: str

    source: str

    state: str

    timestamp: datetime

    signals: dict[str, float] = Field(
        default_factory=dict
    )

    metadata: dict[str, str] = Field(
        default_factory=dict
    )
