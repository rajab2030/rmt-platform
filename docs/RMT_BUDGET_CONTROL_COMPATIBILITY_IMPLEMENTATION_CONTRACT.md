# RMT Budget Control Compatibility — Implementation Contract

**Version:** Draft 0.1, 2026-09-15.
**Status:** IMPLEMENTED, VALIDATED AND ACCEPTED IN WORKTREE — not committed or
deployed. The bounded Core exception is re-frozen at this contract boundary.
**Baseline:** `834ca3d` (`master`, `origin/master` at contract inspection).
**Classification:** bounded Core freeze exception enabling above-Core domains.

Companions: [product proposal](RMT_BUDGET_CONTROL_PROPOSAL.md) and
[compatibility proposal](RMT_BUDGET_CONTROL_CORE_COMPATIBILITY_PROPOSAL.md).
Authority: [Master Definition](RMT_MASTER_DEFINITION.md),
[Core Target State](RMT_CORE_TARGET_STATE.md), and [AGENTS.md](../AGENTS.md).

## 1. Decision and authorization boundary

The owner approved preparation of this contract. That decision accepts the
recommended compatibility direction but does **not** authorize production-code
implementation or generally reopen frozen Core.

Implementation requires a separate approval of this contract. If approved, the
freeze exception is limited to:

1. generic trusted policy/risk assessment contracts and registration;
2. server-controlled resolution bound to an action domain and adapter;
3. validated assessment provenance through immediate and held governance;
4. exact immutable execution-instruction and destination binding; and
5. preview parity and regression evidence for existing behavior.

No C08 is created. No budget, currency, purchase, department, banking, payment,
role-management, ledger, or business-workflow concept may enter Core.

### Conflict audit — 2026-09-15

This draft cannot proceed under the owner's added non-conflict requirement and
the current authority hierarchy:

- `RMT_FROZEN_CORE_DEBT.md` §1 records that a frozen-Core gap receives an
  above-Core mitigation or explicit accept-and-record disposition, **never a
  freeze deviation**, and that no further deviation is authorized.
- `RMT_ABOVE_CORE_ROADMAP.md` §6 says a new domain landing with zero
  `app/core/**` edits is the proof that the freeze holds.
- This draft proposes edits to existing Core policy, risk, approval,
  authorization and execution contracts. Even if designed additively and with
  regression tests, those edits are a freeze deviation and therefore conflict
  with the current directive.

The Master Definition permits reconsideration when existing contracts are shown
insufficient, but it does not itself override the later, explicit no-deviation
owner directive. The repository evidence therefore cannot support representing
this contract as compatible with current governance.

**Disposition:** stopped before implementation. The remainder of this document
is retained only as the rejected/deferred candidate design and must not be used
as implementation authorization. The valid next choices are either (a) preserve
the freeze and defer governed Budget Control because the current assessment is
not financially accurate, or (b) issue an explicit owner governance decision
that supersedes the no-deviation directive before reconsidering a bounded Core
change. Choice (b) would deliberately change existing governance and therefore
does not satisfy a requirement of “no conflict with existing Core.”

### Governance disposition update — 2026-09-15

The owner subsequently approved choice (b): supersede the absolute no-deviation
directive with a controlled exceptional-change procedure and admit this bounded
contract to implementation review. `RMT_FROZEN_CORE_DEBT.md` §1 now records that
procedure, and `RMT_ABOVE_CORE_ROADMAP.md` §6 retains zero-Core-edit delivery as
the normal rule while referencing the exception gate.

This resolves the documentary authority conflict; it does not prove technical
safety and does not authorize production-code implementation. Sections 2–9 are
the proposed implementation contract to be reviewed against the new gate.

## 2. Demonstrated requirement and insufficiency

The acceptance scenario is creation of one commitment for exactly 1,500 units
against 2,000 available, leaving 500. The authoritative governance evidence must
describe that financial operation, and authorization must permit only its exact
immutable instruction and registered destination.

At the inspected baseline:

- `actions/service.py` directly calls fixed `evaluate_action_policy()` and
  `simulate_action()` functions;
- `simulation.py` describes every `create` as container creation, medium risk,
  with rollback available;
- no trusted domain assessment registry/resolver exists;
- `ExecutionAuthorization` binds action id, target, operation and expected outcome,
  but not the execution `parameters` or destination adapter;
- `approve_held_action()` reuses the held action, adapter and risk result without
  resolving assessment again; and
- `agent/preview.py` calls the fixed policy/simulation functions directly.

An adapter-owned precheck would not repair the inaccurate authoritative evidence
and cannot be allowed to become governance. The smallest coherent remedy is a
generic assessment resolution boundary inside the existing governed lifecycle,
plus the binding necessary to prevent the approved instruction or destination
from changing before adapter invocation.

## 3. Preserved invariants

Implementation must preserve all of the following:

- `execute_governed_action()` remains the single authoritative Core mutation path.
- Core resolves, validates and enforces policy/risk; adapters only execute.
- Decisions, evaluators and callers cannot mint approval or authorization.
- Denied, unknown, malformed, unavailable, mismatched, expired or unauthorized
  work never invokes an adapter.
- Existing action types remain unchanged for this slice; `CREATE` may represent
  creation of a domain object when the registered domain contract allows it.
- Existing unclassified actions retain their current default policy/simulation
  behavior and test expectations.
- Preview is read-only and uses the same resolver as real governance.
- Execution-level policy remains a deny-only final safety check.
- Existing durable evidence remains readable without destructive migration.

## 4. Contract model

### 4.1 Trusted domain identity

Add a server-assigned `governance_domain` to `ActionRequest`. The default is the
existing platform/container domain so old serialized actions and callers retain
their behavior. Domain identity is not inferred from arbitrary parameters.

Only trusted application code/configuration may register a domain. HTTP or agent
callers cannot register evaluators, name an evaluator implementation, select a
lower-risk result, or redirect an action to another domain.

### 4.2 Assessment inputs and outputs

Define separate policy and risk protocols. Both receive an immutable assessment
input containing the action id, decision id, governance domain, target, operation,
canonical instruction digest, intended adapter name, and the domain evidence
provided by trusted application integration.

Policy output contains: decision (`allow`, `deny`, or `requires_approval`), stable
reason, evaluator identity/version, assessed-at time, and evidence references.
Risk output contains: validated risk level, impact, uncertainty, recovery semantics,
evaluator identity/version, assessed-at time, and evidence references.

The resolver produces one `GovernanceAssessment` combining those outputs and its
input bindings. Core validates all required fields and recognized enum values.
Exceptions, missing registration, unsupported operation, malformed output,
domain/adapter mismatch, and unknown/unavailable assessment produce a fail-closed
outcome before approval or authorization.

Evaluators may require human approval or deny work. They cannot approve work,
mint authorization, waive Core validation, choose an adapter, or execute.

### 4.3 Registration and resolution

Add a Core-owned assessment registry analogous in shape, but not responsibility,
to the adapter registry. Registration maps a unique domain to:

- one policy evaluator;
- one risk evaluator;
- an allowlist of action operations; and
- an allowlist of adapter names.

Duplicate registration fails. No runtime replacement is permitted after startup.
Resolution is by the server-controlled `governance_domain`; the requested adapter
must match the domain registration. The existing default evaluators are registered
as the default domain and wrap current fixed behavior.

Budget Control later supplies and registers its evaluators above Core. Their
implementation and all financial behavior are outside this contract.

### 4.4 Canonical immutable instruction

Before assessment, Core serializes the execution-relevant instruction using a
single deterministic canonical JSON definition (UTF-8, sorted object keys,
preserved array order, no non-JSON values) and computes a versioned SHA-256 digest.
The digest covers at least:

- governance domain;
- action id and decision id;
- target and operation;
- complete parameters;
- expected outcome; and
- intended adapter name.

The canonicalization version and digest are stored in the assessment,
`ApprovalHold`, `ExecutionAuthorization`, and `ExecutionRequest`. The engine
recomputes and compares the digest immediately before policy/risk enforcement and
adapter lookup. It separately compares the authorization's adapter name with the
requested adapter. Any mismatch blocks before `adapter.supports()` or `execute()`.

Parameters used for translation must be a validated snapshot, not a mutable
reference whose contents can change after assessment. Unsupported parameter
values fail before governance rather than being stringified ambiguously.

### 4.5 Approval and held continuation

Approval decisions consume the resolved assessment rather than calling a second
risk implementation. Holds persist the complete assessment provenance, canonical
instruction binding, domain, adapter and expiry.

Within the existing five-minute hold window, continuation validates:

- the hold is pending and unexpired;
- action/instruction/destination still match the stored binding;
- the registered evaluator identities/versions still match; and
- the authenticated approval identity is supplied by the trusted route layer.

Any failure blocks without authorization or adapter invocation. This contract does
not turn Core holds into durable business requests or extend their TTL. Budget
Control must later reload current financial evidence and submit a fresh governed
action after its own long-lived human workflow. Whether a changed domain condition
inside an otherwise valid short Core hold requires reassessment is domain policy;
the initial Budget integration contract must choose fail-closed fresh assessment.

### 4.6 Evidence propagation

Durable approval, authorization, trace and audit evidence must retain or reference:
domain, assessment/evaluator identity and version, evidence references,
canonicalization version, instruction digest, and intended adapter.

Existing records missing these fields remain readable as legacy default-domain
records. A new execution may not use missing bindings: new authorizations and
holds must contain them. Evidence schemas use additive optional fields for read
compatibility; new writes populate them mandatorily.

## 5. Concrete implementation surface

The implementation proposal may change only the following responsibility areas.
Exact filenames may be adjusted during implementation inspection only if the same
responsibilities and scope are preserved and the deviation is reported.

| Responsibility | Expected files |
|---|---|
| Action domain and binding fields | `app/core/intelligence/actions/models.py` |
| Generic assessment contracts, registry, resolver, canonical binding | new focused modules under `app/core/intelligence/actions/` |
| Default compatibility evaluators | `actions/policy.py`, `actions/simulation.py`, registration/bootstrap module |
| Authoritative resolution/enforcement | `actions/service.py` |
| Held assessment/binding continuity | `actions/approval.py`, `actions/approval_service.py`, storage compatibility tests |
| Authorization binding | `actions/authorization.py`, `actions/authorization_service.py` |
| Execution request propagation and final enforcement | `execution/models.py`, `execution/translator.py`, `execution/engine.py` |
| Preview parity | `app/agent/preview.py` and its tests |
| Trusted startup registration | `app/main.py` or a narrowly scoped bootstrap called from lifespan |

Existing routes/callers that reach `execute_governed_action()` must be inspected
and regression-tested, including `/execute`, `/approve`, Homelab remediation and
continuation, operational loop, agent execution/preview, self-management and
evolution. This contract does not authorize new Budget API routes or UI.

## 6. Explicit exclusions

This implementation must not add:

- Budget Control domain models, evaluators, database, routes or UI;
- business RBAC or long-lived approval workflow;
- ledger transactions, concurrency controls or recovery mechanisms;
- payment/bank integration;
- caller-defined evaluator selection or dynamic evaluator upload;
- a second authorization/execution path;
- changes to action vocabulary merely to label financial operations;
- broad refactoring, durable-store replacement or unrelated status cleanup; or
- automatic migration that rewrites historical evidence.

Those Budget obligations require a later above-Core implementation contract after
this compatibility slice is implemented and evidenced.

## 7. Implementation sequence

1. Add contracts, canonical instruction binding, registry and default wrappers.
2. Resolve one assessment in `execute_governed_action()` and drive policy, risk
   and approval from it while retaining default behavior.
3. Propagate provenance/binding through holds, authorization and execution.
4. Enforce digest and adapter binding in `ExecutionEngine` before adapter access.
5. Route preview through the read-only shared resolver.
6. Add migration-compatible serialization and all targeted negative tests.
7. Run targeted suites, HTTP/alternate-route integration, then the full backend
   suite; inspect the final diff and record evidence.

Each step must remain reviewable and must not introduce a temporarily reachable
unbound domain execution route.

## 8. Required validation

### Contract and unit evidence

- deterministic digest for equivalent instructions; changed parameter, expected
  outcome, domain, target, operation or adapter changes the digest;
- unsupported/non-JSON parameters fail closed;
- duplicate/unknown/unavailable/malformed evaluator registration or output blocks;
- caller cannot choose evaluator or forge returned risk/policy;
- domain/operation/adapter allowlist mismatch blocks;
- default evaluator results match all existing action cases;
- old evidence deserializes while new executable records require bindings.

### Governed-boundary evidence

- automatic and manual default-domain execution still succeed as before;
- policy deny, risk unknown, assessment failure, rejected/expired hold, invalid
  authorization, instruction mismatch and adapter mismatch never invoke adapter;
- parameters changed after authorization are blocked;
- held action preserves the exact assessment and instruction provenance;
- evaluator/version mismatch on continuation blocks;
- execution trace distinguishes pre-adapter block from adapter failure;
- adapter success alone does not manufacture verification success.

### Integration and alternate-route evidence

- preview and actual governance resolve identical results without preview writes;
- `/execute` and `/approve` retain current behavior and authenticated attribution;
- Homelab, agent, self-management and evolution callers retain their governed
  behavior and cannot bypass assessment/binding;
- a test-only registered non-default domain reaches its adapter only through the
  full policy → risk → approval → authorization chain;
- HTTP tests cover forged domain/evaluator/adapter inputs and held continuation;
- full backend suite passes with no reduction of existing assertions.

The Budget example itself is not an acceptance test for this Core-only slice;
it becomes mandatory in the later above-Core Budget implementation. This slice
must nevertheless prove the generic mechanism with a test domain whose assessment
describes its actual non-container operation.

## 9. Definition of Done

This compatibility change is complete only when:

- the generic responsibility is implemented without domain leakage;
- every governed entrypoint is connected to the resolver;
- exact instruction and adapter binding is enforced immediately before adapter
  access for automatic and held paths;
- all fail-closed and regression tests above pass;
- new and legacy evidence behavior is documented and tested;
- the full backend test result and inspected diff are recorded as evidence; and
- no Budget capability is claimed implemented.

Failure of any item rejects the change; partial wiring is not completion.

## 10. Approval requested

Approve this contract as the first narrowly bounded exception under the controlled
post-freeze change procedure and authorize its production-code implementation.
Approval would not authorize Budget Control implementation, deployment, service
restart, migration beyond additive compatibility, commit, or push. Any newly
discovered conflict or inability to preserve existing behavior requires stopping
and reporting before implementation continues.

## 11. Implementation checkpoint — 2026-09-15

The owner approved this updated contract for implementation. The worktree now
contains the bounded generic assessment registry/resolver, default compatibility
evaluators, versioned canonical instruction and adapter binding, held-flow and
authorization propagation, pre-adapter enforcement, preview parity, additive
evidence fields, and focused tests. No Budget domain implementation was added.

Validation completed:

- Python compilation: pass;
- focused Ruff errors-only check over affected sources/tests: pass;
- all test files not importing FastAPI `TestClient`: **335 passed**;
- focused assessment, authorization, approval and governed-chain cases are included
  in that result, including a registered non-default test domain and parameter,
  adapter and held-instruction substitution blocks;
- HTTP-facing subset: **239 passed, 3 skipped**;
- full backend collection: **574 passed, 3 skipped** (**577 collected**);
- final compilation and `git diff --check`: pass.

The separately authorized harness investigation retained no dependency change.
The test-only root `conftest.py` now substitutes an `httpx2.AsyncClient` plus
`ASGITransport` compatibility client for the environment-blocked Starlette
blocking portal. Short synchronous FastAPI route callables execute inline in this
test harness; context-manager use still enters/exits the real application lifespan,
server exceptions retain their configured behavior, and non-context use does not
start lifespan tasks. One existing verification-index test now scopes its deliberate
module-state corruption so fixture teardown sees the restored dictionary. No
production startup, authentication, dependency, route, or application behavior was
weakened to make the suite pass.

The contract's Implementation + Integration + Enforcement + Validation + Evidence
gate is satisfied. The generic exception is accepted and immediately re-frozen at
the boundary defined here; this does not authorize further Core amendments or
Budget-domain implementation. No deployment, service restart, commit or push was
performed.

**Final freeze closure:** by subsequent owner directive, the exceptional-change
procedure is closed permanently. This contract records the sole final admitted
Core amendment and cannot serve as precedent or authority for another amendment.
All Budget Control implementation must remain above Core and consume these frozen
contracts unchanged.
