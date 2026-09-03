from app.core.intelligence.decision.models import IntelligenceDecision
from app.core.intelligence.actions.translator import decision_to_action
from app.core.intelligence.actions.service import execute_governed_action
from app.core.intelligence.actions.approval_service import (
    record_approval_decision,
)
from app.core.intelligence.actions.approval_policy import (
    ApprovalDecision,
    ApprovalMode,
)
from app.core.module_registry.registry import get_modules
from app.core.configuration.settings import load_settings
from app.core.configuration.public import create_public_config
from app.core.self_management.models import (
    SelfManagementState,
    PlatformIdentity,
)


# The finite set of bounded self-management operations the Core will govern.
# Only these operations may be routed into the governed action flow.
SUPPORTED_SELF_MANAGEMENT_OPERATIONS = {"restart_component"}


class SelfManagementService:
    """
    Bounded platform self-management.

    Two distinct responsibilities:
      * observe_platform_state -> read-only platform state (no mutation)
      * execute_self_management_decision -> route a bounded, permitted
        self-management decision into the existing governed action flow.

    This layer does NOT create a second decision engine, execution boundary,
    authorization system, policy/risk/approval system, or persistence
    mechanism. It reuses the existing Core machinery.
    """

    def observe_platform_state(self) -> SelfManagementState:
        """
        Read-only platform identity/version, capability, and configuration.

        Observing this state never creates authorization and never executes
        anything.
        """
        modules = get_modules()
        settings = load_settings()
        config = create_public_config(settings)

        return SelfManagementState(
            identity=PlatformIdentity(
                platform=config.platform_name,
                version=config.platform_version,
            ),
            capabilities=modules,
            configuration=config,
        )

    def _permitted_targets(self) -> set:
        """
        Registered platform components that may be self-managed.

        The bounded-target set comes from the existing module registry, so a
        caller cannot turn an arbitrary target into an executable operation.
        """
        return {
            m.runtime.container
            for m in get_modules()
            if m.runtime.container
        }

    def execute_self_management_decision(
        self,
        decision: IntelligenceDecision,
        adapter_name: str = "simulation",
    ):
        """
        Route a bounded self-management decision through the existing governed
        action flow (execute_governed_action).

        The decision must be an IntelligenceDecision produced by the existing
        decision layer, must be a supported bounded operation, and must target
        a permitted/registered platform component. Out-of-bound targets are
        rejected here and never reach the governed mutation boundary.

        Post-change verification is resolved internally by the verification
        layer; it is never caller-controlled.
        """
        if not isinstance(decision, IntelligenceDecision):
            return {
                "status": "blocked",
                "reason": "Not an IntelligenceDecision",
                "action_id": None,
            }

        if decision.action not in SUPPORTED_SELF_MANAGEMENT_OPERATIONS:
            return {
                "status": "blocked",
                "reason": "Operation not supported for self-management",
                "action_id": None,
            }

        action = decision_to_action(decision)
        if action is None:
            return {
                "status": "blocked",
                "reason": (
                    "Decision not translatable to a governed action"
                ),
                "action_id": None,
            }

        if decision.component not in self._permitted_targets():
            self._record_blocked(
                action,
                "Target not a permitted self-management component",
            )
            return {
                "status": "blocked",
                "reason": (
                    "Target not a permitted self-management component"
                ),
                "action_id": action.action_id,
            }

        # Bounded, low-risk, permitted self-management operation: it does not
        # require manual approval. It still passes through the existing
        # policy/risk/approval/authorization/execution/verification/audit flow.
        action.requires_approval = False

        return execute_governed_action(
            action,
            adapter_name=adapter_name,
        )

    def _record_blocked(self, action, reason):
        """
        Record deny evidence through the existing approval-record store.

        This is the same durable evidence mechanism used by the governed
        approval flow; it is not a new persistence mechanism.
        """
        approval_decision = ApprovalDecision(
            action_id=action.action_id,
            mode=ApprovalMode.REJECT,
            approved=False,
            reason=reason,
        )
        record_approval_decision(
            action,
            approval_decision,
            decision="rejected",
            approved_by="self_management_boundary",
        )


self_management_service = SelfManagementService()
