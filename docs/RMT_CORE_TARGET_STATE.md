# RMT Core Target State

## Authority and Scope

This document defines the finite Target State of the generic RMT Core. It is governed by [`RMT_MASTER_DEFINITION.md`](RMT_MASTER_DEFINITION.md), the current repository architecture, the verified current-state audit, and the verified RMT-020 implementation/review.

The Target State is a completion boundary, not an implementation plan. It defines what must be true before the RMT Core may enter Platform Validation. It does not assign milestones, prescribe implementation order, or require any particular technology.

RMT remains a general-purpose intelligent control, execution, and governance platform. The Core is domain-agnostic and must support governed services, applications, systems, and AI agents without embedding the rules of a particular domain.

## Target-State Boundary

The RMT Core is complete when one governed lifecycle is real, connected, enforced, observable, verifiable, and evidenced:

**Understand → Decide → Govern → Authorize → Execute → Verify → Learn**

“Defined” means a contract or implementation exists. “Complete” additionally requires production integration, enforcement at the relevant boundary, and evidence that the behavior works. A class, module, or isolated test is not completion evidence by itself.

## Understand

### 1. Observability and Platform State

**Capability:** Collect and represent current state and relevant historical observations for governed resources and for the RMT platform itself.

**Purpose:** Provide trustworthy evidence for intelligence and governance without coupling the Core to one infrastructure provider.

**What must exist:** A normalized observation/state contract; collection and storage boundaries; current and historical access; freshness and unknown-state representation; and platform-state visibility sufficient to understand Core health, configuration, version, and managed capability state.

**What must be connected/enforced:** Supported observation sources must feed the normalized contract used by the lifecycle. Missing, stale, malformed, or unknown observations must remain explicit and must not be silently treated as healthy or safe.

**Evidence proving completion:** An integration scenario shows source data becoming normalized state, current/history queries returning it, stale/unknown state preserved, and the same contracts usable for a non-Docker source or test adapter.

**Classification:** REQUIRED RMT CORE capability.

### 2. Intelligence and Analysis

**Capability:** Interpret observations into health, condition, context, trends, deviations, history, and evidence-backed meaning.

**Purpose:** Turn state into reusable platform intelligence rather than source-specific reports.

**What must exist:** Domain-agnostic context and evaluation contracts; deterministic handling of healthy, degraded, failed, stale, and unknown conditions; analysis of relevant history and change; and explicit confidence/evidence.

**What must be connected/enforced:** The intelligence service must consume normalized observations and context, produce explainable evaluations, and preserve uncertainty where evidence is insufficient. Analysis must influence downstream decisions where applicable.

**Evidence proving completion:** A connected scenario demonstrates observation → context → evaluation → analysis, including a healthy case, a degraded/failed case, and an unknown or stale case with inspectable evidence and confidence.

**Classification:** REQUIRED RMT CORE capability.

## Decide

### 3. Decisions and Recommendations

**Capability:** Convert intelligence into explicit decisions and recommendations with reasons, priority, confidence, and a declared intended outcome.

**Purpose:** Separate interpretation from the choice of what should happen next.

**What must exist:** A decision contract; recommendation output; explicit handling of unsupported or uncertain conditions; and a stable boundary from which a governed action may be proposed.

**What must be connected/enforced:** Decisions must be derived from available evaluation/analysis evidence, must not bypass governance, and must not be treated as execution authorization. Unsupported decisions must be rejected or held safely.

**Evidence proving completion:** A connected scenario shows evidence-backed decisions and recommendations for normal, degraded, and uncertain conditions, with no direct execution from the decision layer.

**Classification:** REQUIRED RMT CORE capability.

## Govern

### 4. Policy and Governance

**Capability:** Determine what actions are permitted, denied, or require additional control.

**Purpose:** Establish the non-bypassable governance boundary between an intended action and authorization/execution.

**What must exist:** Domain-agnostic action and execution policy contracts; policy decisions with reasons; safe handling of unsupported actions; and a policy enforcement point in the execution path.

**What must be connected/enforced:** Every execution request must pass the applicable policy gate. Deny and requires-approval outcomes must prevent adapter invocation. Policy responsibility must remain separate from execution and audit.

**Evidence proving completion:** Tests and an integration scenario prove allowed, denied, unsupported, and approval-required requests produce the correct outcomes, and prove that blocked requests do not reach an adapter.

**Classification:** REQUIRED RMT CORE capability.

### 5. Risk

**Capability:** Assess the potential impact and risk of a proposed action or execution request.

**Purpose:** Supply an explicit risk basis for governance, approval, authorization, and audit.

**What must exist:** A risk contract with defined levels, reasons, and uncertainty handling; a risk assessment boundary independent of the executor; and a way to carry the result into the governed lifecycle.

**What must be connected/enforced:** Risk must be evaluated before authorization and execution. Risk must affect policy/approval decisions where required, and the assessed result must be retained as evidence.

**Evidence proving completion:** A scenario demonstrates different risk outcomes, shows the risk result influencing the control path, and confirms the executor cannot replace or bypass the risk assessment.

**Classification:** REQUIRED RMT CORE capability.

### 6. Approval

**Capability:** Resolve actions that require automatic approval, human approval, rejection, or safe holding.

**Purpose:** Provide controlled decision authority for actions that cannot proceed solely from automated evaluation.

**What must exist:** An approval decision contract; explicit automatic, manual, and rejected outcomes; approval identity/reason evidence; and a manual-approval boundary that can hold work without executing it.

**What must be connected/enforced:** Approval requirements must be derived from policy and risk. No action requiring approval may reach authorization or an adapter before approval is recorded and valid. Domain-specific approver roles and workflows remain outside the generic Core.

**Evidence proving completion:** Scenarios prove automatic approval, manual hold, rejection, expired/invalid approval, and absence of approval all result in the correct enforced boundary behavior.

**Classification:** REQUIRED RMT CORE capability.

## Authorize

### 7. Authorization

**Capability:** Issue and validate permission for one specific governed execution.

**Purpose:** Create the explicit trust boundary that permits an execution request to cross into controlled execution.

**What must exist:** An authorization record bound to the action, target, operation, decision/approval basis, issuer, status, validity period, and reason; storage/retrieval; and validation rules.

**What must be connected/enforced:** The execution boundary must reject missing, inactive, expired, mismatched, or otherwise invalid authorization before adapter lookup or invocation. Authorization must not be inferred from an untrusted request field.

**Evidence proving completion:** Tests prove valid authorization proceeds only for the bound request and prove missing, non-approved, expired, and action/target/operation-mismatched authorizations are blocked and evidenced.

**Classification:** REQUIRED RMT CORE capability.

## Execute

### 8. Controlled Execution

**Capability:** Execute an authorized request through a controlled execution boundary.

**Purpose:** Ensure infrastructure actions happen only after the complete governance and authorization chain succeeds.

**What must exist:** An execution request/result contract; a single orchestration boundary; lifecycle status and failure handling; and an adapter invocation boundary that does not make policy decisions.

**What must be connected/enforced:** All production mutations in Core scope must traverse risk, policy, approval where required, authorization, execution, audit, and trace. Direct unmanaged mutation paths must not remain available as equivalent production paths.

**Evidence proving completion:** An end-to-end scenario demonstrates an approved request reaching an adapter and a denied or invalid request being blocked before adapter invocation, with results and evidence linked by stable identifiers.

**Classification:** REQUIRED RMT CORE capability.

### 9. Adapters and Extensions

**Capability:** Provide a stable extension boundary for runtime and external-system implementations.

**Purpose:** Keep the Core domain-agnostic while allowing products and integrations to perform concrete work.

**What must exist:** An adapter contract, registration/selection mechanism, support checks, result contract, and safe failure behavior.

**What must be connected/enforced:** Adapters must receive only requests that have passed the Core control chain. They must not authorize, redefine policy, or conceal execution outcomes. At least one safe adapter and one representative non-Core integration path must validate the boundary.

**Evidence proving completion:** Contract tests prove registration, selection, unsupported-request handling, successful execution, failure reporting, and enforcement of the pre-execution control boundary.

**Classification:** REQUIRED RMT CORE capability. Concrete Docker, cloud, banking, budget, or other provider adapters are ABOVE-CORE / DOMAIN capability.

## Verify

### 10. Post-Execution Verification

**Capability:** Determine whether the observed result matches the authorized expected outcome.

**Purpose:** Close the control loop and prevent a reported execution result from being mistaken for a verified platform state.

**What must exist:** A verification contract; expected and observed state; valid, invalid, unknown, and verification-failed outcomes; and a boundary for obtaining post-execution observations.

**What must be connected/enforced:** Verification must run after execution where the action has an observable outcome. A failed or unknown verification must be represented as such, linked to the execution, and must not be reported as successful completion.

**Evidence proving completion:** Scenarios prove successful verification, state mismatch, unavailable observation, and verifier failure, with each outcome visible in the returned result and persisted evidence.

**Classification:** REQUIRED RMT CORE capability.

## Learn

### 11. Audit, Trace, and Evidence

**Capability:** Preserve what happened, why it was allowed or blocked, what risk/policy/approval/authorization applied, what executed, and what was verified.

**Purpose:** Make governed operation explainable, reviewable, and accountable.

**What must exist:** Durable audit and decision-trace contracts; correlation across observation, decision, action, approval, authorization, execution, verification, and outcome; blocked-decision evidence; query/access boundaries; and retention appropriate to the Core’s operation.

**What must be connected/enforced:** Successful, failed, denied, rejected, held, and unknown paths must produce the applicable evidence. Evidence must be written by the control flow, not reconstructed from logs after the fact, and audit must not become the policy decision-maker.

**Evidence proving completion:** End-to-end evidence can reconstruct an allowed execution and a blocked execution, including reasons, risk, policy, authorization, adapter/result, verification, and timestamps, across a process restart or durable storage boundary where required by the deployment.

**Classification:** REQUIRED RMT CORE capability.

### 12. Learning and History

**Capability:** Retain and query prior observations, evaluations, decisions, outcomes, and verification evidence so later intelligence can use validated history.

**Purpose:** Enable bounded improvement and recurring-condition awareness without turning learning into uncontrolled autonomy.

**What must exist:** A history/memory contract, query boundary, provenance, and explicit handling of insufficient or conflicting history.

**What must be connected/enforced:** Learning inputs must come from recorded evidence and must not silently rewrite authoritative audit records or bypass governance. Learned information may inform analysis and recommendations but cannot authorize execution by itself.

**Evidence proving completion:** A scenario records an event, retrieves it through the history boundary, uses it in analysis, and demonstrates that learning does not bypass policy, approval, authorization, or verification.

**Classification:** REQUIRED RMT CORE capability.

## Cross-Cutting Core Capabilities

### 13. Platform Self-Management

**Capability:** Observe and govern the operation, configuration, lifecycle, and known capabilities of the RMT platform itself.

**Purpose:** Allow RMT to manage its own platform state under the same controlled principles it applies to governed targets.

**What must exist:** Platform identity/version state; configuration visibility and validation; module/capability discovery; platform health; controlled platform operations; and self-management audit/evidence.

**What must be connected/enforced:** Self-management actions must use the same risk, policy, approval, authorization, execution, verification, and audit boundaries. Read-only visibility must remain distinct from mutation authority.

**Evidence proving completion:** A platform self-management scenario shows state discovery, a governed platform operation, blocked unauthorized operation, post-operation verification, and complete trace/evidence.

**Classification:** REQUIRED RMT CORE capability.

### 14. Controlled Platform Evolution

**Capability:** Change the finite RMT platform safely within governed, bounded evolution rules.

**Purpose:** Permit necessary evolution without allowing uncontrolled self-modification or indefinite Core expansion.

**What must exist:** A versioned change identity; compatibility/scope assessment; risk and policy evaluation; authorization; controlled execution; verification; rollback or safe failure for applicable changes; audit; and a boundary that distinguishes Core changes from above-Core extensions.

**What must be connected/enforced:** No platform change may be applied as an implicit side effect of learning or runtime operation. Evolution must be limited to an approved change and must not alter its own governance boundary without separately governed authorization.

**Evidence proving completion:** A representative controlled-change scenario demonstrates assessment, authorization, execution, verification, failure/safe handling, and audit, while an unapproved or out-of-scope change is blocked.

**Classification:** REQUIRED RMT CORE capability, limited to the finite mechanisms needed to govern Core evolution. Domain product evolution is ABOVE-CORE / DOMAIN capability.

### 15. Platform Validation

**Capability:** Validate the complete Core as an integrated governed platform.

**Purpose:** Establish objective evidence that the Target State is real before Platform Freeze.

**What must exist:** A finite validation suite covering the lifecycle, cross-cutting controls, positive and negative paths, unknown states, adapter boundaries, self-management, evolution controls, evidence completeness, and Core/domain separation.

**What must be connected/enforced:** Validation must exercise production-equivalent entrypoints and enforcement boundaries, not only isolated units. A passing result must be reproducible and must include evidence for every Core Completion Criterion.

**Evidence proving completion:** A recorded validation result shows all required scenarios passing, no known bypass path, complete evidence for allowed and blocked flows, and explicit confirmation that domain-specific capabilities are not required for Core completion.

**Classification:** REQUIRED RMT CORE capability.

## Core Boundary Classification

### REQUIRED RMT CORE CAPABILITY

The capabilities defined in the lifecycle and cross-cutting sections above are the complete finite Core Target State: normalized understanding, intelligence and analysis, decisions and recommendations, governance and risk, approval, authorization, controlled execution, adapter boundaries, verification, learning/history, audit/trace/evidence, self-management, controlled evolution, and platform validation.

### ABOVE-CORE / DOMAIN CAPABILITY

Banking Risk Management, Budget Control, AI Agent Governance, IT/Cloud Operations, and other domain products belong above the Core. Their domain rules, workflows, specialized policies, domain data models, user experiences, and provider-specific integrations are not Core completion requirements. Concrete Docker functionality is an integration/adapter concern, not a generic Core requirement.

### FUTURE CAPABILITY

Capabilities not required by this finite Target State may remain future backlog. They do not become Core requirements merely because they are useful, technically attractive, or possible. Examples include broader provider coverage, advanced predictive learning, additional products, and higher-order automation beyond the governed lifecycle.

### NOT REQUIRED FOR CORE COMPLETION

The Core does not require a particular domain product, a particular infrastructure provider, an unlimited set of adapters, uncontrolled autonomous modification, perfect prediction, a specific user interface, or indefinite expansion of Core responsibilities. It also does not require every possible workflow to be implemented before Platform Validation.

## Core Completion Criteria

All conditions below must be satisfied before RMT Core can enter Platform Validation:

- [ ] The finite Core boundary and Core-versus-domain classification are recorded and unambiguous.
- [ ] Understand produces normalized, current, historical, fresh, stale, and unknown state through connected observation and platform-state paths.
- [ ] Intelligence and analysis produce explainable evaluations with evidence, confidence, context, and history handling.
- [ ] Decisions and recommendations are connected to intelligence and cannot authorize or execute by themselves.
- [ ] Every execution path is governed by policy and risk, with deny and approval-required outcomes enforced before execution.
- [ ] Approval outcomes are explicit, and no action requiring approval can proceed without valid approval.
- [ ] Authorization is explicit, bound to the intended action/target/operation, validated at the execution boundary, and rejects invalid or missing permission.
- [ ] Controlled execution is the only production mutation boundary within Core scope.
- [ ] The adapter/extension contract is enforced and at least one safe representative adapter proves the boundary.
- [ ] Post-execution verification distinguishes verified success, mismatch, unavailable observation, and verification failure.
- [ ] Allowed, denied, rejected, held, failed, unknown, executed, and verified outcomes produce correlated audit/trace evidence.
- [ ] History/learning consumes recorded evidence and cannot bypass governance or authorization.
- [ ] Platform self-management uses the same control boundaries and has observable, verifiable evidence.
- [ ] Controlled platform evolution is bounded, authorized, verified, auditable, and cannot perform uncontrolled self-modification.
- [ ] The finite platform-validation suite passes against production-equivalent entrypoints and finds no known governance bypass.
- [ ] No remaining item is required for Core completion unless it is explicitly within this finite Target State.

## Platform Freeze Criteria

The RMT Core may be declared frozen only when:

- Platform Validation has passed all Core Completion Criteria with recorded evidence.
- The lifecycle is connected end to end: **Understand → Decide → Govern → Authorize → Execute → Verify → Learn**.
- Production-equivalent mutation paths cannot bypass policy, risk, approval, authorization, verification, audit, or trace boundaries.
- The Core’s contracts, responsibilities, and Core-versus-domain boundary are documented and accepted as finite.
- Known failures, denied decisions, unknown states, and verification failures are represented safely and remain auditable.
- The validated Core has no open requirement that would make the Target State incomplete.
- Future work has been classified as above-Core/domain capability, future backlog,
  or unnecessary. A claimed need for a Core contract change is not admissible
  after the final freeze.

After Platform Freeze, future growth occurs through products, domain modules,
integrations, adapters, and applications built on top of the frozen Core. The sole
final domain-compatibility amendment was accepted and re-frozen on 2026-09-15;
the amendment procedure is now permanently closed. No future Core amendment,
freeze deviation, Core milestone, or C08 is admissible. An incompatible capability
or domain is kept outside RMT, deferred, or rejected rather than reopening Core.
