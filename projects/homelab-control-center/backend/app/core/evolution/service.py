from app.core.intelligence.actions.models import (
    ActionRequest,
    ActionType,
)
from app.core.intelligence.actions.service import (
    execute_governed_action,
)
from app.core.intelligence.actions.approval_service import (
    record_approval_decision,
)
from app.core.intelligence.actions.approval_policy import (
    ApprovalDecision,
    ApprovalMode,
)
from app.core.module_registry.registry import get_modules
from app.core.evolution.models import (
    ChangeProposal,
    CompatibilityAssessment,
    ChangeResult,
)


# The finite set of bounded evolution operations the Core will govern.
# Only these operations may be routed into the governed action flow.
SUPPORTED_EVOLUTION_OPERATIONS = {"register_module"}


class EvolutionService:
    """
    Bounded controlled platform evolution.

    Two distinct responsibilities:
      * assess_change -> read-only scope/compatibility assessment (no mutation)
      * execute_governed_change -> route a bounded, permitted change proposal
        into the existing governed action flow.

    This layer does NOT create a second mutation boundary, decision engine,
    authorization system, policy/risk/approval system, or persistence
    mechanism. Actual mutation reaches execute_governed_action ->
    execution_engine -> adapter.
    """

    def assess_change(
        self,
        proposal: ChangeProposal,
    ) -> CompatibilityAssessment:
        """
        Read-only scope/compatibility assessment.

        Never authorizes, approves, executes, invokes an adapter, or mutates
        governance/module state.
        """
        if not isinstance(proposal, ChangeProposal):
            return CompatibilityAssessment(
                change_id=None,
                compatible=False,
                reason="Not a ChangeProposal",
                scope="",
            )

        if proposal.operation not in SUPPORTED_EVOLUTION_OPERATIONS:
            return CompatibilityAssessment(
                change_id=proposal.change_id,
                compatible=False,
                reason="Unsupported evolution operation",
                scope=proposal.scope,
            )

        modules = get_modules()
        if any(
            m.name == proposal.target
            or m.runtime.container == proposal.target
            for m in modules
        ):
            return CompatibilityAssessment(
                change_id=proposal.change_id,
                compatible=False,
                reason="Module already registered",
                scope=proposal.scope,
            )

        return CompatibilityAssessment(
            change_id=proposal.change_id,
            compatible=True,
            reason="In scope and compatible",
            scope=proposal.scope,
        )

    def execute_governed_change(
        self,
        proposal: ChangeProposal,
        adapter_name: str = "module_change",
    ) -> ChangeResult:
        """
        Route a bounded, permitted change proposal through the existing
        governed action flow (execute_governed_action).

        The change must be a ChangeProposal, must be a supported bounded
        evolution operation, and must pass the read-only scope/compatibility
        assessment. Out-of-scope or unsupported changes are rejected here and
        never reach the governed mutation boundary.

        Post-change verification is resolved internally by the verification
        layer from the execution request; it is never caller-controlled.
        """
        if not isinstance(proposal, ChangeProposal):
            return ChangeResult(
                change_id=None,
                status="blocked",
                message="Not a ChangeProposal",
            )

        # The evolution mutation path is bound to the module_change adapter.
        # A caller cannot redirect a module-registration evolution to Docker or
        # any other adapter; doing so is rejected before governance/execution.
        if adapter_name != "module_change":
            action = self._build_action(proposal)
            self._record_blocked(action, "Unsupported evolution adapter")
            return ChangeResult(
                change_id=proposal.change_id,
                status="blocked",
                message="Unsupported evolution adapter",
                action_id=action.action_id,
            )

        if proposal.operation not in SUPPORTED_EVOLUTION_OPERATIONS:
            action = self._build_action(proposal)
            self._record_blocked(action, "Unsupported evolution operation")
            return ChangeResult(
                change_id=proposal.change_id,
                status="blocked",
                message="Unsupported evolution operation",
                action_id=action.action_id,
            )

        assessment = self.assess_change(proposal)
        if not assessment.compatible:
            action = self._build_action(proposal)
            self._record_blocked(action, assessment.reason)
            return ChangeResult(
                change_id=proposal.change_id,
                status="blocked",
                message=assessment.reason,
                action_id=action.action_id,
            )

        action = self._build_action(proposal)
        result = execute_governed_action(
            action,
            adapter_name=adapter_name,
        )

        return ChangeResult(
            change_id=proposal.change_id,
            status=result.get("status", "unknown"),
            action_id=action.action_id,
            execution_id=result.get("execution_id"),
            verification_status=result.get("verification_status"),
            verification_reason=result.get("verification_reason", ""),
            message=result.get("message", ""),
        )

    def _build_action(
        self,
        proposal: ChangeProposal,
    ) -> ActionRequest:
        """
        Translate a bounded change proposal into a governed ActionRequest.

        The change identity is carried as decision_id so it remains correlated
        through the governed lifecycle evidence (authorization.decision_id).
        """
        return ActionRequest(
            decision_id=proposal.change_id,
            component=proposal.target,
            action_type=ActionType.CREATE,
            reason=proposal.reason,
            confidence=proposal.confidence,
            requires_approval=proposal.requires_approval,
            expected_outcome=proposal.expected_outcome,
            parameters={
                "module_name": proposal.target,
                "version": proposal.version,
                "scope": proposal.scope,
            },
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
            approved_by="evolution_boundary",
        )


evolution_service = EvolutionService()
