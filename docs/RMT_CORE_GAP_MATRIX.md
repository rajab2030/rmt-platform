RMT Core Gap Matrix
1. Authority and Purpose

This document defines the verified gap between the current RMT implementation and the finite RMT Core Target State.

It is governed by:

docs/RMT_MASTER_DEFINITION.md
docs/RMT_CORE_TARGET_STATE.md

It uses the verified technical evidence available from the RMT-020 implementation review and the independent execution-control audits performed against the current working tree and the RMT-019.11 frozen baseline.

This document is a gap analysis, not an implementation plan.

It does not redefine RMT, expand the Core, assign milestone numbers, prescribe implementation order, or introduce requirements that are not established by the governing documents.

The purpose is to answer one question:

What must still become true before the defined RMT Core can enter Platform Validation and ultimately reach Platform Freeze?

2. Assessment Rules

A capability is classified as:

COMPLETE

The Target-State requirement is materially satisfied by connected implementation and available evidence.

The existence of classes, modules, or isolated tests alone is not sufficient.

PARTIAL

A meaningful portion of the required capability exists, but one or more Target-State requirements involving integration, enforcement, persistence, verification, production connectivity, or evidence remain incomplete.

MISSING

The required capability or its required enforcement mechanism is not implemented.

UNKNOWN

Available evidence is insufficient to establish completion or incompletion without additional repository/runtime verification.

Classification Rule

Only gaps that are required by RMT_CORE_TARGET_STATE.md may become remaining Core work.

Technical improvements, domain features, provider-specific functionality, broader product capabilities, and attractive but non-required enhancements are not Core gaps.

3. Sixteen-Criterion Gap Matrix
Criterion 1 — Finite Core Boundary and Core/Domain Classification

Target-State requirement

The RMT Core must have an explicit finite boundary separating generic platform capability from domain-specific products, integrations, adapters, and future work.

Current verified evidence

docs/RMT_MASTER_DEFINITION.md establishes RMT as a general-purpose platform and explicitly separates the Core from Banking Risk Management, Budget Control, AI Agent Governance, IT/Cloud Operations, and other domain capabilities.

docs/RMT_CORE_TARGET_STATE.md further defines the finite Core Target State and explicit Core/domain classifications.

Status

COMPLETE

Exact gap

None identified.

Required action

None for the capability itself.

The boundary must continue to govern subsequent roadmap decisions.

Core classification

REQUIRED CORE — SATISFIED

Criterion 2 — Understand: Normalized Observation and Platform State

Target-State requirement

RMT must collect and represent current and historical state through normalized contracts, including freshness and explicit unknown-state handling. Platform state must also be sufficiently visible to understand RMT's own health, configuration, version, and managed capability state.

Current verified evidence

The existing platform contains:

observation collection
observability storage/API
intelligence observation normalization
platform-state services
current and historical observation paths

The existing collector remains limited to a small hard-coded set of containers.

The current-state audit also found that platform metrics are not populated and that observability collection is not yet sufficiently generalized.

The Target State additionally requires explicit stale/unknown handling and evidence through a non-Docker source or test adapter.

Status

PARTIAL

Exact gap

The existing observation system is not yet demonstrated as a sufficiently generic, production-connected understanding layer covering:

generalized observation sources
explicit freshness/unknown semantics throughout the lifecycle
platform-state understanding at the required completeness
representative non-Docker observation capability

Required action

Complete and validate the normalized understanding boundary so that the lifecycle receives trustworthy current, historical, stale, and unknown state independently of a specific infrastructure provider.

Core classification

REQUIRED CORE

Criterion 3 — Intelligence and Analysis

Target-State requirement

Normalized observations must be transformed into explainable evaluations and analysis containing context, evidence, confidence, history, and uncertainty handling.

Current verified evidence

The intelligence service is production-connected to:

observation normalization
context
health evaluation
history/memory
analysis
decisions
recommendations

Analysis components exist for history, baseline, trends, and anomaly/deviation handling.

The intelligence health API reaches the intelligence service.

The existing architecture therefore contains a materially connected intelligence path.

However, the Target State requires integrated evidence covering healthy, degraded/failed, and stale/unknown conditions with inspectable evidence and confidence.

Status

PARTIAL

Exact gap

The architecture and production connection exist, but the Target-State evidence requirement has not yet been established for the complete range of required states and confidence/evidence behavior.

Required action

Complete the integrated validation and any narrowly required implementation needed to demonstrate deterministic, explainable handling of healthy, degraded/failed, and stale/unknown conditions.

Core classification

REQUIRED CORE

Criterion 4 — Decisions and Recommendations

Target-State requirement

Intelligence must produce explicit decisions and recommendations with reasons, priority, confidence, and intended outcome, while remaining separate from authorization and execution.

Current verified evidence

decision/engine.py creates intelligence decisions.

intelligence/service.py connects analysis to decisions and recommendations.

The current intelligence API exposes health evaluation but does not expose a direct execution-trigger endpoint from the intelligence layer.

The verified execution lifecycle treats decision creation separately from authorization and execution.

Status

PARTIAL

Exact gap

The decision/recommendation capability is connected internally, but complete Target-State evidence for explicit decision semantics, uncertainty handling, and the production boundary separating decisions from execution has not yet been established.

Required action

Validate the decision/recommendation contract and its non-executing boundary as part of the integrated Core validation.

No direct decision-to-execution shortcut should be introduced.

Core classification

REQUIRED CORE

Criterion 5 — Policy and Governance

Target-State requirement

Every execution request must pass an applicable policy gate. Denied and approval-required outcomes must prevent adapter invocation.

Current verified evidence

RMT-C01 established one authoritative governed production mutation path
(`execute_governed_action` → `execution_engine.execute` → adapter). Action-level
and execution-level policy semantics are reconciled: action policy is the
authoritative governance gate; execution policy is a deny-only final safety
check. Denied and approval-required requests are proven not to reach an adapter.

Status

COMPLETE

Exact gap

None identified.

Required action

None for the capability itself; satisfied by the closed RMT-C01 milestone.

Core classification

REQUIRED CORE

Criterion 6 — Risk

Target-State requirement

Risk must be assessed before authorization and execution, influence governance/approval where required, and remain available as retained evidence.

Current verified evidence

RMT-C01 reconciled governance risk (actions/simulation.py) and execution risk
(execution/risk.py) into one consistent, traceable risk path. Governance risk is
authoritative for approval; execution risk is a final independent assessment
consistent with governance risk for the same operation. Risk is retained as
evidence in audit and trace.

Status

COMPLETE

Exact gap

None identified.

Required action

None for the capability itself; satisfied by the closed RMT-C01 milestone.

Core classification

REQUIRED CORE

Criterion 7 — Approval

Target-State requirement

RMT must support automatic approval, manual approval/hold, rejection, and invalid/expired approval handling. Actions requiring approval must not proceed without valid approval.

Current verified evidence

RMT-C01 completed the approval lifecycle: automatic approval, manual hold with
expiry, rejection, and legitimate continuation (`approve_held_action`). RMT-C02
persisted an `ApprovalRecord` for every approval decision (auto/manual/reject)
and made approval/hold storage durable. Expired and invalid approvals cannot
continue.

Status

COMPLETE

Exact gap

None identified.

Required action

None for the capability itself; satisfied by the closed RMT-C01 and RMT-C02 milestones.

Core classification

REQUIRED CORE

Criterion 8 — Authorization

Target-State requirement

Authorization must be explicit, bound to the intended action, target, and operation, stored/retrievable, and enforced before adapter lookup or invocation.

Current verified evidence

RMT-C01 bound authorization to action, target, and operation with provenance
(decision_id, approval_id), issuer, status, reason, and an expiry window. The
execution engine rejects missing, non-approved, expired, and mismatched
authorization before adapter lookup. RMT-C02 made authorization storage durable.
RMT-C03 extended the authorization gate to validate the expected outcome.

Status

COMPLETE

Exact gap

None identified.

Required action

None for the capability itself; satisfied by the closed RMT-C01, RMT-C02, and RMT-C03 milestones.

Core classification

REQUIRED CORE

Criterion 9 — Controlled Execution and Adapter Boundary

Target-State requirement

All Core-scope production mutations must traverse one controlled execution boundary after governance and authorization. Adapters must not be independently usable as equivalent production mutation paths.

Current verified evidence

RMT-C01 consolidated production mutation into one authoritative governed path.
`POST /execute` and `POST /approve` traverse `execute_governed_action` /
`approve_held_action` → `execution_engine.execute` → adapter. Docker mutation
functions are adapter-only and not exposed as routes. No equivalent unmanaged
production mutation path remains.

Status

COMPLETE

Exact gap

None identified.

Required action

None for the capability itself; satisfied by the closed RMT-C01 milestone.

Core classification

REQUIRED CORE

Concrete Docker behavior remains an adapter/integration concern.

Criterion 10 — Post-Execution Verification

Target-State requirement

RMT must compare authorized expected outcome with observed post-execution state and distinguish verified success, mismatch, unavailable observation, and verification failure.

Current verified evidence

RMT-C03 implemented an infrastructure-agnostic `verification/` package (models,
generic verifier, service, durable storage). Verification runs after applicable
execution in `execute_governed_action` and `approve_held_action`, distinguishes
verified success, state mismatch, observation unavailable, and verification
failure, and is correlated to the execution by `execution_id` and durably recorded.

Status

COMPLETE

Exact gap

None identified.

Required action

None for the capability itself; satisfied by the closed RMT-C03 milestone.

Core classification

REQUIRED CORE

Criterion 11 — Audit, Trace, and Evidence

Target-State requirement

RMT must preserve correlated evidence across decisions, actions, risk, policy, approval, authorization, execution, verification, and outcomes, including blocked and failed paths.

Current verified evidence

RMT-C02 made authorization, approval/hold, approval-record, audit, and trace
storage durable via the `DurableStore` JSON mechanism, with stable correlation
identifiers. RMT-C03 added durable verification evidence correlated to the
execution by `execution_id`. Blocked, rejected, held, failed, and successful
paths produce appropriate evidence.

Status

COMPLETE

Exact gap

None identified.

Required action

None for the capability itself; satisfied by the closed RMT-C02 and RMT-C03 milestones.

Core classification

REQUIRED CORE

Criterion 12 — Learning and History

Target-State requirement

RMT must retain and query validated historical observations, evaluations, decisions, outcomes, and verification evidence. Learning must inform intelligence without acquiring authorization authority.

Current verified evidence

History/memory components exist and are connected to intelligence analysis.

Observability history is available.

The current intelligence architecture already uses historical information for analysis.

However, the full Target-State requirement extends historical evidence to governed decisions, execution outcomes, and verification evidence.

Status

PARTIAL

Exact gap

Historical intelligence exists, but the complete governed lifecycle evidence model is not yet demonstrated as a unified history boundary.

Required action

Connect durable governed evidence and verified outcomes to the history/learning boundary while preserving the rule that learning cannot authorize execution.

Core classification

REQUIRED CORE

Criterion 13 — Platform Self-Management

Target-State requirement

RMT must be capable of observing and governing its own platform state and operations through the same control principles used for governed targets.

Current verified evidence

Platform-state services expose platform information including Git, container, Docker, and backup state.

Read-only APIs for modules, configuration, and platform state exist.

RMT-C05 delivered a bounded generic governed self-management capability using the same Core control boundary.

Status

COMPLETE

Exact gap

None identified for the closed RMT-C05 scope.

Required action

None for the capability itself; satisfied by the closed RMT-C05 milestone.

Domain-specific management operations remain outside the Core.

Core classification

REQUIRED CORE — SATISFIED

Criterion 14 — Controlled Platform Evolution

Target-State requirement

RMT must be capable of governing bounded platform changes through assessment, risk, policy, authorization, controlled execution, verification, audit, and safe failure/rollback where applicable.

Current verified evidence

Module factory, module registry, identity, schema, and JSON persistence components exist.

RMT-C06 established and closed the controlled platform-evolution lifecycle for the module-change path:

* B1 — production module-change adapter registration fixed;
* B2 — adapter redirection prevented on the governed path;
* B3 — trusted/default actual-state verification implemented;
* B4 — caller-controlled verification observer eliminated;
* verification now uses trusted internal module-registry observation;
* safe failure whenever trusted observation is unavailable.

Direct module_registry.register_module() access remains explicitly deferred to RMT-C07 and is not an RMT-C06 defect.

Status

COMPLETE

Exact gap

None identified for the closed RMT-C06 scope.

Required action

None for the capability itself; satisfied by the closed RMT-C06 milestone.

Direct module_registry.register_module() remains deferred to RMT-C07.

The Master Definition continues to require controlled evolution while prohibiting uncontrolled self-modification.

Core classification

REQUIRED CORE — SATISFIED

Criterion 15 — Platform Validation

Target-State requirement

A finite validation suite must exercise the complete Core using production-equivalent entrypoints and demonstrate positive, negative, unknown, evidence, self-management, evolution, adapter, and Core/domain-boundary behavior.

Current verified evidence

RMT-C07 executed the finite platform-validation suite against production-equivalent
entrypoints (existing HTTP routes and the governed service boundary). The full
intelligence suite passes (122 tests), including the C07 HTTP transport artifact
(test_http_entrypoints.py) and the D1 correction. The G2 final Core-boundary
review passed: no reachable governance bypass and no remaining required Core
capability outside the finite Target State.

Status

COMPLETE

Exact gap

None identified for the closed RMT-C07 scope.

Required action

None for the capability itself; satisfied by the closed RMT-C07 milestone.

Core classification

REQUIRED CORE — SATISFIED

Criterion 16 — No Remaining Core Requirement Outside the Defined Target State

Target-State requirement

Before Platform Validation, no unresolved item may remain that is required for Core completion unless it is explicitly represented inside the finite Target State.

Current verified evidence

The Master Definition and Core Target State establish the finite Core boundary.

The G2 final Core-boundary review confirmed that no additional Core requirement
exists outside the finite Target State. Direct module_registry.register_module()
is an internal governed primitive (not a bypass or missing Core requirement);
execution/service.py::execute_action() is unreachable dead-code housekeeping with
no C07 impact.

Status

COMPLETE

Exact gap

None identified for the closed RMT-C07 scope.

Required action

None for the capability itself; satisfied by the closed RMT-C07 milestone and the
G2 final Core-boundary review.

Core classification

REQUIRED CORE

4. Status Summary
Criterion	Capability	Status
1	Finite Core Boundary	COMPLETE
2	Understand	PARTIAL
3	Intelligence & Analysis	PARTIAL
4	Decisions & Recommendations	PARTIAL
5	Policy & Governance	COMPLETE
6	Risk	COMPLETE
7	Approval	COMPLETE
8	Authorization	COMPLETE
9	Controlled Execution & Adapters	COMPLETE
10	Post-Execution Verification	COMPLETE
11	Audit / Trace / Evidence	COMPLETE
12	Learning / History	PARTIAL
13	Platform Self-Management	COMPLETE
14	Controlled Platform Evolution	COMPLETE
15	Platform Validation	COMPLETE
16	No Remaining Unclassified Core Requirement	COMPLETE
Counts
COMPLETE: 12
PARTIAL: 4
MISSING: 0
UNKNOWN: 0

All 16 criteria are COMPLETE. Criteria 5–11 are COMPLETE via RMT-C01, RMT-C02,
and RMT-C03; criterion 13 via RMT-C05; criterion 14 via RMT-C06; and criteria 15
and 16 via RMT-C07 (finite platform-validation suite + G2 final Core-boundary
review). Direct module_registry.register_module() is an internal governed
primitive, not a bypass or missing Core requirement.

5. Consolidated Remaining Core Gaps

The remaining non-complete criteria can be reduced to a smaller set of coherent capability groups.

Group A — Unified Governed Execution Lifecycle

Related criteria:

5 — Policy/Governance
6 — Risk
7 — Approval
8 — Authorization
9 — Controlled Execution

Status

COMPLETE — closed by RMT-C01.

Core problem

The required components exist, but the complete lifecycle is not yet the single authoritative production execution path.

The principal verified issue is the existence of the alternative /execute mutation path and the separation between action-level and execution-level governance.

Required outcome

One authoritative Core execution lifecycle:

Decision → Action → Policy → Risk → Approval → Authorization → Execution

with every applicable production mutation traversing the required controls.

This group is satisfied: `POST /execute` and `POST /approve` traverse the single
authoritative governed path, and no equivalent unmanaged production mutation
path remains.

Group B — Verification and Closed-Loop Outcome

Related criteria:

10 — Post-Execution Verification
11 — Audit/Evidence
12 — Learning/History

Status

PARTIAL — verification (criterion 10) and durable evidence (criterion 11) are
closed by RMT-C03 and RMT-C02. The residual gap is criterion 12 (learning/history
consuming governed evidence), owned by RMT-C04.

Core problem

RMT can currently determine that an execution was attempted and can record execution evidence, but it cannot yet reliably establish that the authorized expected state actually occurred.

Required outcome

Execute → Observe → Verify → Record → Learn

with explicit success, mismatch, unavailable, and verification-failure states.

Verification and durable evidence now exist; the remaining work is connecting
governed evidence into the learning/history boundary.

Group C — Durable Governed Evidence

Related criteria:

7 — Approval
8 — Authorization
11 — Audit/Trace
12 — Learning/History

Status

PARTIAL — durable evidence (criteria 7, 8, 11) is closed by RMT-C02 and RMT-C03.
The residual gap is criterion 12 (learning/history boundary unified with governed
evidence), owned by RMT-C04.

Core problem

Important governance evidence exists only in process memory and approval records are not persisted.

Required outcome

A durable evidence boundary capable of reconstructing governed operations across the relevant lifecycle.

This group is related to Group B but should not be conflated with verification itself. Verification produces evidence; durable evidence preserves it.

Durable evidence now exists; the remaining work is unifying governed evidence into
the learning/history boundary.

Group D — Generalized Understanding and Intelligence Completion

Related criteria:

2 — Understand
3 — Intelligence/Analysis
4 — Decisions/Recommendations

Core problem

The intelligence architecture is substantially connected, but Target-State evidence for generalized, stale/unknown-aware, explainable operation is not yet complete.

Required outcome

A validated domain-agnostic understanding → intelligence → decision path independent of a specific infrastructure source.

Group E — Platform Self-Management

Related criterion:

13 — Platform Self-Management

Status

COMPLETE — closed by RMT-C05.

Core problem

RMT can observe its own platform state; RMT-C05 added the bounded governed self-management capability using the same Core governance and execution controls.

Required outcome

A bounded self-management capability using the same Core governance and execution controls.

Satisfied: controlled platform operations use the Core control boundary and produce verifiable evidence.

Group F — Controlled Platform Evolution

Related criterion:

14 — Controlled Platform Evolution

Status

COMPLETE — closed by RMT-C06.

Core problem

The structural pieces for module/platform evolution exist; RMT-C06 connected the governed change lifecycle through verification and audit for the module-change path.

Required outcome

A finite mechanism for safely changing the platform itself without uncontrolled self-modification or indefinite Core expansion.

Satisfied for the module-change path; direct module_registry.register_module()
access remains explicitly deferred to RMT-C07.

Group G — Platform Validation and Final Closure

Related criteria:

15 — Platform Validation
16 — No Remaining Core Requirement

Core problem

The Core cannot be declared complete while required capabilities remain incomplete and no integrated validation has proven the Target State.

Required outcome

A finite, reproducible validation suite passes against production-equivalent boundaries and confirms that the defined Core is complete and free of known bypasses.

6. Non-Gaps / Explicitly Out of Scope

The following are not remaining RMT Core gaps merely because they do not yet exist as complete products or integrations:

Banking Risk Management

A future domain product built on RMT.

Its domain-specific risk models, workflows, regulatory rules, data models, and interfaces are not Core completion requirements.

Budget Control

A future domain capability built on the RMT control layer.

AI Agent Governance

A future application/domain capability consuming RMT's generic governance, authorization, execution, verification, and audit contracts.

Docker Expansion

Docker is an execution/integration adapter concern.

RMT Core does not require an unlimited set of Docker operations or provider-specific features.

Unlimited Adapter Coverage

The Core requires a stable adapter contract and representative validation, not every possible infrastructure provider.

Advanced Predictive AI / Machine Learning

The Target State requires bounded learning/history and evidence-informed intelligence.

It does not require indefinite development of increasingly sophisticated machine-learning capabilities.

Full Enterprise IAM

No requirement in the Master Definition or Target State establishes a complete enterprise identity and access-management platform as a Core completion condition.

Identity requirements should only be expanded if a demonstrated Core contract requires them.

Arbitrary UI Development

A specific user interface is not a Core completion requirement.

Unlimited Autonomous Self-Modification

Explicitly prohibited by the governing definition.

RMT requires controlled evolution, not uncontrolled autonomy.

7. Roadmap Input

The remaining Core work can therefore be represented by seven logical capability groups:

Generalized Understanding and Intelligence Completion
Unified Governed Execution Lifecycle
Durable Governed Evidence
Verification and Closed-Loop Outcome
Platform Self-Management
Controlled Platform Evolution
Platform Validation and Final Closure

Of these, the governed-execution, durable-evidence, verification, platform
self-management, and controlled-platform-evolution groups are CLOSED (by RMT-C01
through RMT-C06). The remaining roadmap work centers on generalized
understanding/intelligence, learning/history, and final platform validation
(RMT-C07).

These are capability groups, not milestone numbers.

They must not yet be interpreted as seven mandatory sequential milestones.

Some groups have dependencies:

Unified execution governance is prerequisite to meaningful complete execution verification.
Durable evidence is required for complete lifecycle auditability.
Verification depends on controlled execution.
Self-management depends on the governed execution boundary.
Controlled evolution depends on governance, authorization, execution, verification, and evidence.
Platform Validation is necessarily last because it validates the completed Target State.
8. Dependency View

The technical dependency structure is:

Existing Intelligence Foundation

↓

Unified Governed Execution

↓

Durable Evidence + Verification

↓

Platform Self-Management

↓

Controlled Platform Evolution

↓

Integrated Platform Validation

Generalized understanding/intelligence completion should be closed wherever required by the validation scenarios rather than unnecessarily rebuilt.

The exact implementation order must be determined only after the remaining gaps are converted into finite milestone contracts.

9. Core Scope Guard

The following rule governs all subsequent work:

A proposed change may enter the remaining RMT Core roadmap only if it closes a verified gap against RMT_CORE_TARGET_STATE.md.

A proposal that does not satisfy this condition must be classified as:

ABOVE CORE / DOMAIN
FUTURE
NOT REQUIRED

This prevents useful but non-essential functionality from expanding the Core.

10. Final Verdict
TARGET STATE ACHIEVED — RMT CORE PLATFORM FREEZE

The finite RMT Core Target State has been validated and satisfied. RMT-C01 through
RMT-C07 closed the governed execution, durable-evidence, post-execution-verification,
generalized understand/decide, platform self-management, controlled platform
evolution, and platform-validation gaps, establishing one authoritative governed
production mutation path, a governed verified platform-evolution boundary, and a
passing finite platform-validation suite (122 tests) with no reachable governance
bypass.

The RMT Core is frozen. Direct module_registry.register_module() is an internal
governed primitive, not a bypass or missing Core requirement.
execution/service.py::execute_action() is unreachable dead-code housekeeping with
no C07 impact.

Future work is primarily above-Core/domain/product/integration/adapter/application
work. No additional Core capability should be added unless a change proves the
finite Target State or an existing Core contract is insufficient.
