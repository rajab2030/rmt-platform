"""RMT-CAP-05 (5A) -- the MCR child-contract surface as plain dataclasses.

`MCR_SUPERVISORY_CONTRACT.md` sect 4-11: Identity, State, Intent, Decision,
Authority, Proposed Action, Outcome. Intent (what) is kept distinct from
mechanism (how) so governance evaluates the consequential effect, not a tool
name.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.intelligence.actions.models import ActionType
from app.core.intelligence.verification.models import ExpectedOutcome


@dataclass(frozen=True)
class AgentIdentity:
    """MCR sect 5 -- who is acting, and in which context."""

    agent_id: str
    role: str = "operator"
    operational_context: str = "homelab"
    authority_context: str = "default"


@dataclass(frozen=True)
class AgentIntent:
    """MCR sect 7 -- WHAT the agent wants (`goal`) kept separate from HOW
    (`mechanism`)."""

    goal: str
    target: str
    mechanism: ActionType
    reason: str = ""
    confidence: int = 0


@dataclass(frozen=True)
class AgentProposal:
    """MCR sect 10 -- a concrete proposed consequential action, plus the
    authority grant the agent is invoking."""

    identity: AgentIdentity
    intent: AgentIntent
    expected_state: str = "running"
    grant_id: str | None = None

    def to_expected_outcome(self) -> ExpectedOutcome:
        return ExpectedOutcome(
            target=self.intent.target,
            operation=self.intent.mechanism.value,
            expected_state=self.expected_state,
        )


@dataclass
class AgentOutcome:
    """MCR sect 4 (Outcome) -- the supervisory result of a proposal.

    ``decision`` is the agent-surface verdict:
      disabled | no_authority | deny | rejected | hold | escalated_hold |
      allow | error
    ``governed_status`` is the raw status from ``execute_governed_action``.
    """

    proposal: AgentProposal
    decision: str
    governed_status: str | None = None
    execution_id: str | None = None
    approval_id: str | None = None
    verification_status: str | None = None
    escalated: bool = False
    learn_recorded: bool = False
    detail: str = ""
    at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def as_dict(self) -> dict:
        return {
            "decision": self.decision,
            "governed_status": self.governed_status,
            "agent_id": self.proposal.identity.agent_id,
            "goal": self.proposal.intent.goal,
            "target": self.proposal.intent.target,
            "mechanism": self.proposal.intent.mechanism.value,
            "execution_id": self.execution_id,
            "approval_id": self.approval_id,
            "verification_status": self.verification_status,
            "escalated": self.escalated,
            "learn_recorded": self.learn_recorded,
            "detail": self.detail,
            "at": self.at.isoformat(),
        }
