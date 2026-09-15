# MCR Supervisory Contract

**Status:** Evidence-backed architectural contract
**Version:** 0.1
**Scope:** MCR ↔ governed child-system relationship
**Companion:** `MCR_ARCHITECTURAL_PRINCIPLE.md` — that document is the *principle* (intent / what & why); this document is the *compliance spec* (how a governed child demonstrates compliance).

---

## 1. Purpose

This contract defines the minimum supervisory relationship between an MCR and any independent system operating under its authority.

The contract is domain-agnostic.

A compliant child may be:

* an application;
* an infrastructure system;
* an AI agent;
* an operational platform;
* a business system;
* a cyber system;
* another autonomous system.

The child may contain its own intelligence and autonomy.

Compliance with this contract means that consequential operation remains subject to the MCR supervisory boundary.

---

# 2. Fundamental Rule

> **Anything operating under MCR must comply with the MCR governing boundary.**

The child may:

* reason;
* decide;
* optimize;
* propose;
* act within granted authority.

The child may not:

* redefine MCR authority;
* bypass MCR governance;
* create an ungoverned consequential path;
* treat technical capability as authorization;
* escape the supervisory boundary through an alternate interface.

MCR may adapt its understanding of the child.

The child does not thereby redefine the governing rules under which it operates.

---

# 3. Governing Relationship

The relationship is:

```text
MCR
 │
 │ supervises
 ▼
Child System
 │
 ├── observes
 ├── reasons
 ├── decides
 ├── proposes
 └── acts within granted authority
```

The child remains operationally independent inside its permitted authority.

MCR retains supervisory authority over consequential operation.

---

# 4. Required Child Contract Surface

A governed child must make sufficient information available for supervisory control.

The minimum conceptual surface is:

1. **Identity**
2. **Current State**
3. **Intent**
4. **Decision**
5. **Authority Context**
6. **Proposed Action**
7. **Outcome**

These do not require exposing private internal reasoning.

The requirement is supervisory observability, not disclosure of chain-of-thought or proprietary reasoning.

---

# 5. Identity

The child must be identifiable within the supervisory context.

At minimum MCR must be able to determine:

* which child is acting;
* which operational context applies;
* which authority context applies to the request.

An action without an attributable actor is not adequately governable.

---

# 6. State

The child must expose sufficient operational state for MCR to understand the condition relevant to a consequential action.

State may include:

* health;
* availability;
* configuration;
* resource condition;
* dependencies;
* operational mode;
* relevant environmental conditions.

The exact representation is domain-specific.

The supervisory requirement is not.

MCR must have enough evidence to distinguish known state from unknown state.

---

# 7. Intent

The child must distinguish what it intends to accomplish from the mechanism it intends to use.

For example:

```text
Intent:
Restore service availability.

Possible mechanisms:
restart
start
replace
repair
dependency recovery
```

This distinction is important because governance must not be limited to a specific tool name.

---

# 8. Decision

The child may make its own local decision.

MCR does not need to reproduce or replace the child's internal reasoning.

The contract therefore distinguishes:

```text
Child decision
      ↓
Supervisory assessment
      ↓
Supervisory decision
```

Child autonomy is preserved.

Supervisory authority remains external to that local decision.

---

# 9. Authority

Authority must be explicit enough to determine whether the proposed consequential operation is permitted.

The contract requires a distinction between:

```text
Capability ≠ Authority
```

A child may technically possess the ability to perform an operation without being authorized to perform it.

Authority may be:

* granted;
* restricted;
* conditional;
* time-limited;
* scoped to an operation;
* scoped to a target;
* subject to approval;
* revoked.

---

# 10. Proposed Action

Before a consequential action occurs, the supervisory boundary must be able to evaluate the proposed effect.

The request must identify sufficient information such as:

* operation;
* target;
* intended effect;
* relevant parameters;
* authority context;
* expected outcome where applicable.

The exact representation may differ by domain.

---

# 11. Supervisory Decisions

MCR may produce at least the following supervisory outcomes:

### ALLOW

The consequential operation is authorized to proceed within the applicable constraints.

### CONSTRAIN

The operation may proceed only within explicitly imposed limits.

### APPROVE

The operation requires an additional authorization/approval condition before execution.

### HOLD

Execution is suspended pending a required condition.

### ESCALATE

The operation requires higher-level supervisory consideration.

### DENY

The operation is not authorized and must not execute.

### STOP

An active or continuing operation must cease where the governing policy permits such intervention.

The exact decision vocabulary may be adapted to the implementation.

The authority semantics must not be weakened.

---

# 12. No Bypass

The child must not have an operational path that produces a consequential state transition without supervisory evaluation.

This applies regardless of:

* tool name;
* API;
* command;
* adapter;
* protocol;
* interface;
* helper;
* automation;
* alternate implementation;
* indirect mechanism.

The governing rule is:

> **If the effect is consequential, the effect is governed.**

---

# 13. Authoritative Mutation Boundary

All consequential state mutations must converge on an authoritative mutation boundary.

Conceptually:

```text
             ┌── tool A ──┐
             ├── tool B ──┤
Child ───────┼── adapter ──┼──→ MCR → Mutation Boundary → State
             ├── command ──┤
             └── alternate ┘
```

The mutation boundary must enforce the supervisory decision before state transition.

A registry or interface may assist in routing.

It is not sufficient by itself unless every consequential path is forced through it.

---

# 14. Effect-Based Governance

The supervisory contract applies to consequential effect, not merely declared operation name.

For example, the following must not become governance escapes merely because their interfaces differ:

```text
restart_service(web)

run_command(web, "restart")

adapter_restart(web)

compose(...)
```

If the mechanisms create an equivalent consequential effect, the effect remains under MCR authority.

---

# 15. Fail-Closed Requirement

When the supervisory boundary cannot establish sufficient authority, the consequential operation must not proceed.

Examples include:

* missing authorization;
* expired authorization;
* invalid target;
* invalid operation;
* contradictory authority;
* malformed request;
* unknown required condition;
* failed supervisory evaluation.

The default for unresolved consequential authority is:

> **Do not mutate.**

---

# 16. Verification

Authorization and outcome verification are separate obligations.

The contract requires:

```text
Request
  ↓
Supervisory Decision
  ↓
Execution
  ↓
Observation
  ↓
Verification
```

MCR must not treat:

> "allowed"

as equivalent to:

> "successful."

Where an expected outcome is defined, the resulting state must be evaluated against it.

---

# 17. Evidence and Audit

Consequential supervisory decisions must produce sufficient evidence to reconstruct:

* actor;
* request;
* intended effect;
* authority;
* supervisory decision;
* mutation attempt;
* execution result;
* resulting state;
* verification result.

Evidence must distinguish:

* requested;
* allowed;
* executed;
* observed;
* verified.

A request is not evidence of execution.

Execution is not evidence of success.

Success is not evidence of authorization.

---

# 18. Unknown-State Rule

The child and MCR must preserve the distinction between:

* observed;
* reported;
* inferred;
* verified;
* unknown.

Neither side may silently convert uncertainty into certainty.

Where a required supervisory fact is unknown and the policy requires certainty, the consequential action must fail closed or escalate according to policy.

---

# 19. Internal Reasoning Boundary

MCR does not require access to the child's private internal reasoning.

The contract governs:

* what the child proposes;
* what authority exists;
* what effect is requested;
* what risk applies;
* whether the operation is permitted;
* what happened afterward.

It does not require:

* chain-of-thought disclosure;
* replacement of local reasoning;
* centralization of domain intelligence.

This preserves child autonomy while maintaining supervisory authority.

---

# 20. Autonomy Within Authority

A compliant child may independently:

* observe;
* reason;
* select among permitted actions;
* optimize execution;
* recover from ordinary operational conditions;
* adapt to changing state.

Provided that consequential actions remain within the granted supervisory authority.

Therefore:

> **Autonomy is permitted inside authority.**

It is not a substitute for authority.

---

# 21. Dependency and Indirect Effects

Governance must account for consequential effects that arise indirectly.

An operation may be individually authorized while producing an unintended or restricted downstream effect through:

* dependencies;
* cascading state changes;
* composition;
* resource interactions;
* recovery chains.

Therefore the supervisory implementation must distinguish:

```text
Action authorization
```

from:

```text
Effect/policy completeness
```

A total mutation boundary prevents bypass.

It does not by itself guarantee that the policy correctly understands every possible consequential effect.

---

# 22. Replay and Temporal Authority

Where authorization is time-limited or single-use, reuse of expired or consumed authorization must not permit a new consequential mutation.

The supervisory boundary should validate, where applicable:

* validity;
* expiry;
* scope;
* target;
* operation;
* consumption state;
* contextual conditions.

---

# 23. Alternate Interfaces

Adding a new interface must not implicitly create a new authority boundary.

Any new mechanism capable of consequential mutation must converge on the same supervisory mutation boundary.

Therefore:

> **Adding a tool must not create a new path around governance.**

This rule applies equally to:

* adapters;
* APIs;
* command interfaces;
* background workers;
* automation;
* plugins;
* integration layers.

---

# 24. Direct State Access

A governed child must not be able to obtain an unrestricted mutable representation of consequential state and modify it outside the supervisory boundary.

Read access may be broad where appropriate.

Mutation access must remain controlled.

This distinction is essential:

```text
Read capability
      ≠
Mutation authority
```

---

# 25. Fixture and Administrative Authority

Test setup, initialization, recovery, migration, and administrative mechanisms may possess privileges that ordinary operational paths do not.

Such mechanisms must be explicitly classified.

A privileged fixture or administrative operation is not evidence of an operational bypass unless it is reachable from the governed operational surface.

However, if such a mechanism becomes operationally reachable, it becomes part of the supervisory attack surface and must comply with this contract.

---

# 26. Boundary Integrity vs Policy Completeness

These are separate requirements.

### Boundary Integrity

Can any consequential state transition occur without MCR?

### Policy Completeness

Does MCR correctly understand and govern all consequential effects?

A system must not claim that one property proves the other.

The MCR experiments demonstrated why this distinction matters.

---

# 27. Compliance Conditions

A child system is **MCR-compliant** only if the applicable implementation can demonstrate:

### C1 — Identity

The actor and operational context are attributable.

### C2 — Observability

Relevant state and intent are sufficiently observable.

### C3 — Authority

Capability and authority are distinguishable.

### C4 — Supervisory Decision

Consequential operations receive an applicable supervisory decision.

### C5 — Total Mutation Boundary

No reachable operational path can produce consequential mutation outside the boundary.

### C6 — Fail Closed

Missing or invalid authority cannot produce consequential mutation.

### C7 — Verification

Consequential outcomes can be observed and verified where required.

### C8 — Evidence

Supervisory decisions and consequential outcomes are auditable.

### C9 — Alternate-Path Resistance

Equivalent consequential effects cannot escape through alternate interfaces.

### C10 — Autonomy Preservation

The child may retain local intelligence and autonomous decision formation within granted authority.

---

# 28. Non-Compliance Conditions

A child is not compliant if it can:

* mutate consequential state directly;
* use an alternate adapter to escape governance;
* invoke a generic command mechanism that bypasses supervision;
* convert technical capability into unauthorized authority;
* replay invalid authority successfully;
* obtain mutable state references that permit uncontrolled mutation;
* create a consequential effect through an ungoverned composition;
* redefine the supervisory rules governing its own authority.

---

# 29. Minimum Lifecycle

The supervisory relationship may be represented as:

```text
OBSERVE
   ↓
UNDERSTAND
   ↓
ASSESS
   ↓
SUPERVISE
   ↓
ACT
   ↓
OBSERVE
   ↓
VERIFY
   ↓
LEARN
```

The exact implementation may vary.

The separation of concerns must remain intact.

---

# 30. Architectural Invariant

The governing invariant of this contract is:

> **No consequential state transition may occur without passing through the applicable MCR-controlled supervisory boundary.**

A stronger implementation claim may be made only when implementation inspection and evidence justify it.

Passing a test suite alone is insufficient.

---

# 31. Evidence Standard

Evidence for compliance should distinguish at least three levels of claim:

### Claim A — Tested

No tested attack produced a consequential bypass.

### Claim B — Reachable Operational Surface

Inspection and testing establish that no reachable operational path bypasses the supervisory boundary.

### Claim C — Absolute Implementation Guarantee

The implementation makes consequential bypass technically impossible within its execution model.

Claim C requires substantially stronger proof than Claim A or B.

The MCR experiments support Claims A and B for the tested isolated operational environment.

They deliberately do not claim universal Claim C.

---

# 32. Relationship to the Child's Internal Governance

A child may have its own:

* policies;
* authorization;
* safety controls;
* decision mechanisms;
* local governance.

These do not replace MCR authority when the child operates under MCR.

Multiple governance layers may therefore exist:

```text
MCR supervisory governance
          ↓
Child governance
          ↓
Child execution
```

The layers may cooperate.

The child layer must not bypass the higher supervisory authority.

---

# 33. Relationship to RMT

This contract describes a supervisory relationship that can be realized by RMT.

It does not authorize changes to RMT's governing architecture.

RMT remains subject to its own governing policy, authorization, execution, verification, evidence, and control boundaries.

Accordingly:

> **Any new capability or domain that cannot comply with RMT's policies, rules,
> architecture, and governed lifecycle does not belong to RMT.**

Such a capability or domain must not weaken or reopen Core, redefine RMT's
authority, or create an alternate governance or execution boundary. It must be
kept outside RMT, deferred, or rejected.

The contract therefore should not be interpreted as:

> "MCR is a new subsystem that must be added to RMT."

It should be interpreted as:

> "MCR is a supervisory architectural pattern that clarifies the role RMT can play over governed child systems."

---

# 34. Governing Statements

The contract is summarized by the following statements:

> **MCR does not need to contain the child's intelligence to govern its consequential actions.**

> **Capability does not create authority.**

> **The child may be autonomous within granted authority.**

> **Consequential effect, not tool identity, determines the need for supervision.**

> **Every consequential mutation must converge on the authoritative supervisory boundary.**

> **Authorization and verification are separate.**

> **Unknown remains unknown.**

> **No alternate interface may create an ungoverned consequential path.**

And finally:

> **One MCR. One governing model. Multiple intelligent, autonomous, compliant children.**
