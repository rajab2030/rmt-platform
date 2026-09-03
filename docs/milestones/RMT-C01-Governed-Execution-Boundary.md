# RMT-C01 — Governed Execution Boundary

## 1. Authority

This milestone contract is governed by:

* `docs/RMT_MASTER_DEFINITION.md`
* `docs/RMT_CORE_TARGET_STATE.md`
* `docs/RMT_CORE_GAP_MATRIX.md`
* `docs/RMT_CORE_REMAINING_ROADMAP.md`

This contract defines the implementation scope and acceptance criteria for:

> **RMT-C01 — Governed Execution Boundary**

It does not redefine the RMT Core Target State.

It does not authorize implementation of RMT-C02 through RMT-C07 functionality except where explicitly required as a dependency of C01.

---

## 2. Current Milestone

**Active milestone: RMT-C01 — Governed Execution Boundary**

Historical milestones, tags, commits, and frozen baselines are evidence only.

The historical RMT-019.11 baseline is not the current milestone.

The current working implementation must be evaluated from the repository state and the applicable C01 contract.

---

## 3. Objective

Establish a single authoritative governed execution boundary for Core-scope production mutations.

The required lifecycle is:

**Decision → Action → Policy → Risk → Approval → Authorization → Execution**

The fundamental invariant is:

> No Core-scope production mutation may reach an execution adapter unless the required governance, approval, and authorization controls have successfully completed.

C01 is therefore a **boundary-enforcement milestone**, not an execution-engine rewrite.

---

## 4. Verified Starting Point

RMT-020 established the execution authorization foundation currently present in the working tree.

The verified foundation includes:

* `ExecutionAuthorization`;
* action identity binding;
* target binding;
* operation binding;
* in-memory authorization storage;
* authorization creation from the governed decision path;
* authorization persistence within the current execution lifecycle;
* authorization existence validation;
* approval-state validation;
* action identity validation;
* target validation;
* operation validation;
* execution risk evaluation;
* execution policy evaluation;
* adapter registry;
* adapter bootstrap;
* execution trace generation;
* execution audit generation.

Existing RMT-020 behavior must be preserved unless C01 explicitly requires a justified contract change.

---

## 5. C01 Gaps

C01 addresses only the following verified gaps.

### 5.1 Alternative execution entrypoints

The repository contains execution paths that can call the execution engine independently of the complete governed lifecycle.

These paths must be resolved so that they cannot provide an equivalent uncontrolled Core production mutation path.

### 5.2 Direct mutation paths

Existing infrastructure mutation paths must be classified as:

* governed;
* genuinely non-mutating; or
* explicitly outside the Core production mutation surface.

A legacy mutation path may not remain available merely on the assumption that it will not be used.

### 5.3 Governance relationship

The relationship between action-level policy and execution-level policy must be explicit.

C01 must establish which decision is authoritative and how the layers relate.

### 5.4 Risk relationship

Risk used during governance and risk used during execution must have a coherent and traceable relationship.

### 5.5 Approval continuation

Automatic approval must continue safely to authorization.

Manual approval must produce a controlled hold state and a legitimate continuation mechanism.

Approval rejection must terminate the execution path.

### 5.6 Authorization validity and provenance

Authorization must represent a legitimate governed lifecycle result.

A caller must not be able to manufacture authorization merely by supplying an identifier.

---

## 6. Architectural Invariants

### INV-01 — Single Execution Authority

There is one authoritative Core production mutation boundary.

Every Core-scope production mutation must pass through it.

### INV-02 — Governance Before Execution

Required policy, risk, approval, and authorization controls must complete before adapter invocation.

### INV-03 — Authorization Binding

Authorization is bound to:

* action;
* target;
* operation.

### INV-04 — Approval Binding

Execution requiring approval cannot proceed without the required valid approval state.

### INV-05 — Manual Approval Is a Hold

Manual approval required is not authorization.

No adapter invocation may occur while approval remains outstanding.

### INV-06 — Policy Consistency

Policy layers must not independently produce conflicting execution permissions without explicit precedence or reconciliation.

### INV-07 — Risk Consistency

Risk classifications affecting governance and execution must be consistent or explicitly reconciled.

### INV-08 — Adapter Isolation

Adapters execute approved work.

Adapters do not:

* approve;
* authorize;
* override policy;
* redefine risk;
* manufacture governance evidence.

### INV-09 — Block Before Adapter

Every governance rejection must occur before adapter invocation.

### INV-10 — No Synthetic Authorization

A supplied authorization identifier is not sufficient.

The authorization must correspond to a legitimate governed lifecycle state.

---

## 7. Authoritative Lifecycle

The authoritative C01 path is conceptually:

```text
Decision
   |
   v
Action
   |
   v
Policy
   |
   v
Risk
   |
   v
Approval
   |
   v
Authorization
   |
   v
Execution Request
   |
   v
Authorization Enforcement
   |
   v
Execution Policy / Risk
   |
   v
Adapter Registry
   |
   v
Adapter
```

The exact internal implementation may differ where justified by the existing architecture.

The lifecycle ordering and enforcement properties may not be weakened.

---

## 8. Production Mutation Boundary

C01 must establish which application interfaces constitute Core-scope production mutation.

For each mutation-capable entrypoint, the implementation review must determine:

1. whether it mutates platform or managed resource state;
2. whether it is part of the Core production mutation surface;
3. whether it reaches an execution adapter directly or indirectly;
4. whether it passes through the authoritative governed lifecycle;
5. whether it must be removed, disabled, redirected, or explicitly reclassified.

The following are not acceptable as permanent reasoning:

* "the endpoint is legacy";
* "the endpoint is not normally used";
* "the caller is trusted";
* "the adapter itself is safe";
* "the endpoint is only for testing";
* "the frontend does not currently call it."

If a path can perform an equivalent Core production mutation, its architectural status must be explicit.

---

## 9. Execution Engine Boundary

The execution engine remains an enforcement boundary.

It must verify the authorization supplied to an execution request before allowing adapter invocation.

At minimum, authorization enforcement must establish:

* authorization exists;
* authorization is in an executable approved state;
* authorization corresponds to the expected action;
* authorization target matches the execution target;
* authorization operation matches the execution operation.

Where applicable, authorization validity must also include:

* provenance;
* expiration or validity state;
* approval relationship;
* lifecycle correlation.

A caller must not be able to create an execution request with arbitrary identifiers and thereby obtain execution authority.

---

## 10. Governance and Execution Policy Relationship

C01 must explicitly reconcile the existing action-level and execution-level policy layers.

The architecture must establish:

* what action policy decides;
* what execution policy decides;
* when each decision occurs;
* which decision has authority when they differ;
* how a policy denial is propagated;
* how approval requirements are propagated;
* how execution cannot reinterpret an earlier governance decision as permission.

Execution policy must not silently become a second independent authorization authority.

Likewise, action policy must not be treated as sufficient if the execution boundary requires additional enforcement.

The final relationship must be deterministic and inspectable.

---

## 11. Risk Relationship

C01 must establish a coherent relationship between governance risk and execution risk.

The implementation must determine whether:

* one risk classification is authoritative;
* execution risk is derived from governance risk;
* execution risk independently evaluates a request but cannot contradict a higher-level governance prohibition;
* or another explicit reconciliation mechanism is required.

The result must be traceable.

A request must not be classified as low risk in one layer and high risk in another without an explicit architectural reason and deterministic handling.

Risk classification must not itself grant execution authority.

Risk is an input to governance and enforcement, not a substitute for authorization.

---

## 12. Approval Lifecycle

Approval is part of the governed lifecycle.

### 12.1 Automatic approval

Where policy permits automatic approval:

```text
Policy
  ↓
Risk
  ↓
Automatic Approval
  ↓
Authorization
  ↓
Execution
```

The authorization must be created only from the legitimate approval result.

### 12.2 Manual approval

Where manual approval is required:

```text
Policy
  ↓
Risk
  ↓
Manual Approval Required
  ↓
HOLD
```

The request must not reach an adapter while approval is outstanding.

A valid continuation mechanism must allow the previously governed request to resume only after the required approval has been legitimately granted.

The continuation must not:

* create a new unrelated action merely to bypass the hold;
* manufacture a new authorization independently;
* skip policy;
* skip required risk evaluation;
* skip authorization enforcement.

### 12.3 Rejected approval

A rejected approval must terminate the execution path.

No adapter invocation may occur.

The rejection must remain distinguishable from:

* successful execution;
* manual hold;
* policy denial;
* authorization failure.

---

## 13. Authorization Provenance

Authorization must have an inspectable relationship to the governed lifecycle.

At minimum, the authorization must be traceable to the action that produced it.

Where the architecture already provides the relevant identifiers, the relationship should preserve:

* decision identity;
* action identity;
* approval identity;
* authorization identity;
* target;
* operation.

C01 does not require durable persistence.

Durability is addressed by RMT-C02.

However, C01 must ensure that the in-memory authorization currently used by the execution boundary cannot be replaced by a caller-supplied fabricated identifier.

---

## 14. Adapter Boundary

Adapters are execution mechanisms.

An adapter must receive work only after the required governance chain succeeds.

An adapter must not become an alternative governance boundary.

An adapter must not:

* approve a request;
* authorize a request;
* reinterpret authorization;
* override a policy denial;
* downgrade risk;
* manufacture approval;
* bypass the execution engine;
* provide an alternative production mutation path.

Provider-specific implementation may remain inside an adapter where appropriate.

The Core governance responsibility remains outside the adapter.

---

## 15. Direct Execution Paths

All direct calls to the execution engine must be inspected.

For each call, determine:

* caller;
* purpose;
* mutation capability;
* whether the request is Core production scope;
* whether governance has already occurred;
* whether authorization is legitimate;
* whether the call must remain;
* whether it must be redirected;
* whether it is test-only;
* whether it is validation-only.

A direct execution call is not automatically a violation.

A direct execution call becomes a C01 concern when it creates an alternative production mutation route that does not satisfy the authoritative lifecycle.

Test and validation utilities may remain when they are clearly isolated from production mutation surfaces and cannot be mistaken for production entrypoints.

---

## 16. Legacy and Non-Core Interfaces

Existing interfaces must not be deleted merely because they are old.

They must first be classified.

An interface may remain when it is demonstrably:

* read-only;
* diagnostic;
* test-only;
* validation-only;
* outside the Core production mutation surface.

A mutation-capable interface that remains available to production callers must either:

1. pass through the authoritative governed boundary; or
2. be explicitly reclassified outside Core production execution with a clear architectural reason and enforcement preventing it from becoming an equivalent Core path.

---

## 17. Required C01 Integration

C01 is complete only when the relevant layers are actually connected.

The expected integration is:

```text
Decision
   ↓
Action
   ↓
Action Policy
   ↓
Risk
   ↓
Approval
   ↓
Authorization
   ↓
Execution Translation
   ↓
Execution Engine
   ↓
Authorization Enforcement
   ↓
Execution Policy / Risk Enforcement
   ↓
Adapter Registry
   ↓
Adapter
```

The implementation must not merely contain these components independently.

The production path must demonstrate that the controls are connected and enforced in sequence.

---

## 18. Required Negative Paths

C01 requires explicit negative-path validation.

At minimum, the following must be blocked before adapter invocation:

### N01 — Policy denied

A policy-denied action must not execute.

### N02 — Approval rejected

A rejected approval must not execute.

### N03 — Approval missing

An action requiring approval must not execute without the required approval.

### N04 — Manual approval outstanding

A manually held action must not execute while approval remains outstanding.

### N05 — Missing authorization

An execution request without valid authorization must not reach the adapter.

### N06 — Non-approved authorization

An authorization that is not executable must not reach the adapter.

### N07 — Action mismatch

Authorization for one action must not authorize another action.

### N08 — Target mismatch

Authorization for one target must not authorize another target.

### N09 — Operation mismatch

Authorization for one operation must not authorize another operation.

### N10 — Invalid or expired authorization

Invalid authorization must not reach the adapter.

### N11 — Synthetic authorization

A caller-created or otherwise unproven authorization identifier must not grant execution authority.

### N12 — Governance bypass

A production mutation entrypoint that does not pass the authoritative governance boundary must not be able to invoke the production adapter.

---

## 19. Required Positive Paths

C01 must also demonstrate valid execution.

### P01 — Approved governed execution

A valid action must:

```text
Decision
→ Action
→ Policy
→ Risk
→ Approval
→ Authorization
→ Execution
→ Adapter
```

and produce the expected execution evidence.

### P02 — Valid authorization enforcement

A valid authorization bound to the correct action, target, and operation must permit execution.

### P03 — Legitimate continuation

Where manual approval is supported by the implementation, a legitimately approved held request must continue through authorization and execution without bypassing the governed lifecycle.

---

## 20. Adapter Invocation Proof

Negative tests must prove more than a returned failure status.

They must establish that the adapter was **not invoked**.

The validation strategy should therefore provide an observable adapter boundary, such as:

* a test adapter;
* an invocation counter;
* a controlled mock;
* an equivalent inspectable mechanism.

The evidence must distinguish:

```text
Blocked before adapter
```

from:

```text
Adapter invoked and failed
```

This distinction is mandatory for C01 acceptance.

---

## 21. Existing RMT-020 Compatibility

C01 must preserve the valid RMT-020 authorization boundary.

The following existing behavior must remain valid unless a deliberate C01 contract change is required:

* valid authorization permits the authorized operation;
* missing authorization is rejected;
* non-approved authorization is rejected;
* mismatched action authorization is rejected;
* mismatched target authorization is rejected;
* mismatched operation authorization is rejected;
* blocked execution produces appropriate trace evidence;
* successful execution produces appropriate execution evidence.

A C01 change that breaks an RMT-020 invariant must explicitly identify:

1. the invariant affected;
2. why the existing contract is insufficient;
3. why the C01 change is required;
4. what replaces the previous behavior;
5. how the new behavior is validated.

---

## 22. Out of Scope

The following are explicitly outside C01 unless required as a direct dependency for the C01 boundary:

* durable governance persistence;
* durable authorization storage;
* durable approval storage;
* durable audit storage;
* durable trace storage;
* post-execution verification;
* generalized non-Docker observation;
* platform self-management;
* controlled platform evolution;
* unrestricted autonomous execution;
* unrestricted agent governance;
* Banking Risk Management;
* Budget Control;
* domain-specific product capabilities;
* arbitrary UI development;
* speculative infrastructure expansion.

These belong to later roadmap milestones or to domain/product layers.

---

## 23. Required Inspection Before Implementation

Before modifying code, the implementation agent must inspect the relevant repository paths and establish the actual execution topology.

At minimum, inspect:

* application mutation entrypoints;
* execution engine;
* execution request model;
* execution translator;
* action models;
* action translator;
* action policy;
* approval policy;
* approval service;
* authorization model;
* authorization service;
* authorization storage;
* execution policy;
* execution risk;
* adapter registry;
* adapters;
* execution audit;
* execution trace;
* relevant tests.

The agent must identify every relevant production mutation path before proposing modifications.

---

## 24. Required Implementation Discipline

C01 implementation must follow:

**Inspect → Map → Identify Gap → Propose Smallest Change → Implement → Validate → Inspect Diff → Report**

Do not perform opportunistic refactoring.

Do not redesign unrelated layers.

Do not introduce a new subsystem merely because it appears cleaner.

Do not modify later-milestone functionality unless it is a necessary C01 dependency.

Every structural change must have a demonstrated responsibility and an integration reason.

---

## 25. Required Validation Suite

The C01 validation suite must include:

### Governance

* allowed action;
* denied action;
* approval-required action.

### Approval

* automatic approval;
* manual approval hold;
* approval rejection;
* legitimate approval continuation.

### Authorization

* valid authorization;
* missing authorization;
* non-approved authorization;
* action mismatch;
* target mismatch;
* operation mismatch;
* invalid/expired authorization;
* synthetic/unproven authorization.

### Execution

* valid adapter invocation;
* blocked-before-adapter;
* adapter failure;
* alternative execution path blocked or correctly reclassified.

### Regression

All existing relevant RMT-020 tests must continue to pass.

---

## 26. C01 Definition of Done

RMT-C01 may be declared complete only when all of the following are true:

* [ ] A single authoritative Core production mutation boundary exists.
* [ ] Every Core-scope production mutation reaches execution only through the governed lifecycle.
* [ ] Alternative production execution paths have been removed, redirected, disabled, or explicitly reclassified.
* [ ] Direct infrastructure mutation paths have been classified and controlled.
* [ ] Action-level and execution-level policy responsibilities are explicit.
* [ ] Policy precedence or reconciliation is deterministic.
* [ ] Governance risk and execution risk have a coherent, traceable relationship.
* [ ] Automatic approval continues safely to authorization.
* [ ] Manual approval produces a genuine hold state.
* [ ] Manual approval has a legitimate continuation mechanism where supported.
* [ ] Rejected approval cannot execute.
* [ ] Missing approval cannot execute.
* [ ] Authorization cannot be fabricated by supplying an identifier.
* [ ] Authorization remains bound to action, target, and operation.
* [ ] Authorization validity/provenance is enforced to the extent required by C01.
* [ ] Required authorization controls execute before adapter invocation.
* [ ] Execution policy/risk enforcement cannot bypass authorization.
* [ ] Adapters cannot become alternative authorization boundaries.
* [ ] Blocked paths are proven not to invoke the adapter.
* [ ] Positive governed execution is proven.
* [ ] Negative governance paths are proven.
* [ ] Existing RMT-020 authorization behavior remains valid.
* [ ] Relevant tests pass.
* [ ] The implementation has been inspected for remaining production bypasses.
* [ ] The resulting architecture remains within the RMT Core boundary.
* [ ] No C02–C07 capability has been introduced merely because it is desirable.
* [ ] Inspectable validation evidence exists for the completed boundary.

---

## 27. Required Acceptance Evidence

The C01 evidence package must contain, at minimum:

1. execution-entrypoint inventory;
2. mutation-path classification;
3. final authoritative lifecycle mapping;
4. policy relationship decision;
5. risk relationship decision;
6. approval lifecycle evidence;
7. authorization provenance evidence;
8. positive execution test evidence;
9. negative execution test evidence;
10. proof that blocked paths do not invoke adapters;
11. regression test results;
12. final repository diff inspection.

The evidence must be sufficient for an independent reviewer to determine whether C01 is actually enforced.

Documentation alone is not sufficient.

---

## 28. Completion Rule

The milestone is complete only when:

**Implementation + Integration + Enforcement + Validation + Evidence = Complete**

A passing unit test does not establish completion if a production bypass remains.

A connected component does not establish completion if the boundary is not enforced.

A documented boundary does not establish completion if executable behavior contradicts it.

A successful execution does not establish completion if unauthorized execution remains possible.

---

## 29. Final C01 Boundary

RMT-C01 ends at the point where the Core has one authoritative, enforceable production mutation boundary:

**Decision → Action → Policy → Risk → Approval → Authorization → Execution**

with:

**no known equivalent Core production mutation bypass.**

C01 does not require the Core to be fully complete.

C01 establishes the governed execution foundation on which the later finite milestones depend.

The next milestone is **RMT-C02 — Durable Governance Evidence**, but C02 must not be implemented merely because C01 has been completed.

C02 begins only under its own milestone contract and review gate.

---

## 30. Final Acceptance Statement

RMT-C01 may be declared accepted only when an independent review can answer **YES** to all of the following:

1. **Can every Core production mutation be traced to one authoritative governed boundary?**
2. **Can an unauthorized request be proven unable to reach an adapter?**
3. **Can a rejected, missing, or outstanding approval be proven unable to execute?**
4. **Can authorization be proven to belong to the governed action, target, and operation?**
5. **Can governance and execution policy decisions be explained without ambiguity?**
6. **Can governance and execution risk relationships be explained without contradiction?**
7. **Can alternative mutation paths be shown to be controlled or explicitly outside Core production execution?**
8. **Can valid governed execution be demonstrated end-to-end?**
9. **Can the boundary be demonstrated through executable validation rather than documentation alone?**
10. **Can the implementation be accepted without requiring C02–C07 functionality?**

If any answer is **NO**, RMT-C01 remains incomplete.
