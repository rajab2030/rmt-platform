from pydantic import BaseModel

from app.core.module_registry.schema import Module
from app.core.configuration.public import PublicConfiguration


class PlatformIdentity(BaseModel):
    """
    Read-only platform identity/version state.

    This is observation data only. It carries no mutation authority.
    """

    platform: str
    version: str


class SelfManagementState(BaseModel):
    """
    Read-only platform state view for self-management observation.

    Distinct from the mutation path: observing this state never creates
    authorization and never executes anything.
    """

    identity: PlatformIdentity
    capabilities: list[Module]
    configuration: PublicConfiguration
