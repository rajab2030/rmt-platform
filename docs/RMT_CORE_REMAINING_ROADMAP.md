# RMT Core Remaining Roadmap

## 1. Authority and Purpose

This document defines the finite implementation roadmap required to move the RMT Core from its verified current state to the finite Target State.

It is governed by:

* `docs/RMT_MASTER_DEFINITION.md`
* `docs/RMT_CORE_TARGET_STATE.md`
* `docs/RMT_CORE_GAP_MATRIX.md`

It is derived from the verified gaps identified against the Target State.

This document is an **implementation roadmap**. It does not redefine the RMT Core, expand its scope, or introduce capabilities outside the finite Target State.

The governing lifecycle remains:

**Understand → Decide → Govern → Authorize → Execute → Verify → Learn**

The roadmap ends at **Platform Validation and Platform Freeze**.

---

# 2. Roadmap Rules

Every remaining Core milestone must:

1. Close one or more verified Target-State gaps.
2. Have an explicit scope boundary.
3. Have a finite Definition of Done.
4. Preserve the Core/domain boundary.
5. Preserve existing valid contracts unless a justified contract change is required.
6. Include negative-path validation where governance or execution is involved.
7. Produce inspectable evidence.
8. Avoid introducing functionality merely because it is technically desirable.
9. Avoid creating new permanent Core responsibilities.
10. Be reviewed against the Target State before implementation begins.

A milestone is not complete because code exists.

A milestone is complete only when its required behavior is:

**implemented → connected → enforced → tested → evidenced**

---

# 3. Current Starting Point

The current RMT state contains a materially established intelligence foundation and a completed governed execution, durable-evidence, and post-execution-verification architecture.

RMT-C01 through RMT-C06 are CLOSED.

Verified post-C03 capabilities include:

* a single authoritative governed production mutation path
  (`execute_governed_action` → `execution_engine.execute` → adapter);
* action-level and execution-level policy/risk reconciliation;
* a complete approval lifecycle (automatic, manual hold, rejection, continuation, expiry);
* authorization provenance and validity, bound to action, target, and operation;
* durable governance evidence (authorization, approval/hold, approval record, audit, trace) surviving process restart;
* post-execution verification distinguishing verified success, state mismatch, observation unavailable, and verification failure, correlated to the execution and durably recorded;
* adapter access enforced so blocked paths never invoke an adapter.

The current state nevertheless contains important remaining gaps:

* missing final integrated platform validation (RMT-C07);
* direct module-registry `register_module()` access — explicitly deferred to RMT-C07;
* HTTP-level production-equivalent route validation — deferred to RMT-C07.

RMT-C04 (generalized Understand → Decide completion), RMT-C05 (controlled
self-management), and RMT-C06 (controlled platform evolution) are CLOSED and no
longer represent remaining gaps.

The roadmap below is now focused solely on the remaining milestone, RMT-C07.

---

# 4. Roadmap Overview

The remaining Core work is divided into the following finite milestones:

| Milestone | Capability                                 | Primary Target-State Coverage                  | Status |
| --------- | ------------------------------------------ | ---------------------------------------------- | ------ |
| RMT-C01   | Governed Execution Boundary                | Govern, Risk, Approval, Authorization, Execute | CLOSED |
| RMT-C02   | Durable Governance Evidence                | Approval, Authorization, Audit, Trace, History | CLOSED |
| RMT-C03   | Post-Execution Verification                | Verify, Audit, History                         | CLOSED |
| RMT-C04   | Generalized Understand → Decide Completion | Understand, Intelligence, Decisions            | CLOSED |
| RMT-C05   | Controlled Platform Self-Management        | Self-Management                                | CLOSED |
| RMT-C06   | Controlled Platform Evolution              | Controlled Evolution                           | CLOSED |
| RMT-C07   | Platform Validation and Freeze             | All Target-State Criteria                      | CLOSED |

These milestone identifiers are roadmap identifiers only.

They do not redefine the architecture or create new Target-State requirements.

---

# 5. Milestone RMT-C01 — Governed Execution Boundary

**Status: CLOSED**

## Objective

Make the governed execution lifecycle the single authoritative Core-scope production mutation path.

The target lifecycle is:

**Decision → Action → Policy → Risk → Approval → Authorization → Execution**

No equivalent production mutation path may bypass this boundary.

## Current gaps addressed

* `/execute` bypasses the decision/action/approval lifecycle.
* Direct Docker mutation paths remain outside the controlled lifecycle.
* Action policy and execution policy exist as separate governance layers.
* Risk semantics exist at more than one level.
* Manual approval does not currently provide an executable continuation.
* Authorization provenance is incomplete.
* Authorization validity/expiry is incomplete.

## Scope

This milestone covers:

* production execution entrypoint consolidation;
* authoritative governance path;
* policy/risk reconciliation;
* approval continuation boundary;
* authorization provenance and validity;
* adapter access enforcement;
* removal or reclassification of equivalent unmanaged mutation paths.

## Required behavior

Every Core-scope production mutation must:

1. originate from an accepted governed action/request;
2. receive risk assessment;
3. receive policy evaluation;
4. receive approval handling where required;
5. receive explicit authorization;
6. pass authorization validation;
7. pass execution risk/policy enforcement;
8. reach an adapter only after the above controls succeed.

Denied, rejected, held, missing-approval, invalid-authorization, and policy-failed requests must not reach an adapter.

## Important boundary

The adapter remains an executor.

It must not:

* decide authorization;
* override policy;
* create approval;
* redefine risk;
* conceal execution failure.

## Definition of Done

* [ ] One authoritative production mutation path exists.
* [ ] Existing equivalent mutation paths are removed, disabled, or explicitly reclassified outside Core production execution.
* [ ] Action-level and execution-level governance semantics are reconciled or explicitly bounded.
* [ ] Risk used by governance and execution is consistent and traceable.
* [ ] Automatic approval works through authorization to execution.
* [ ] Manual approval can safely hold work and provide a valid continuation path.
* [ ] Rejected approval cannot execute.
* [ ] Missing approval cannot execute.
* [ ] Invalid/expired authorization cannot execute.
* [ ] Authorization remains bound to action, target, and operation.
* [ ] Adapter invocation is impossible before the required control chain succeeds.
* [ ] Positive and negative integration tests prove the boundary.

## Validation evidence

At minimum:

* approved execution;
* denied policy;
* high-risk/manual approval;
* rejected approval;
* missing authorization;
* mismatched authorization;
* expired/invalid authorization;
* proof that blocked paths never invoke the adapter.

---

# 6. Milestone RMT-C02 — Durable Governance Evidence

**Status: CLOSED**

## Objective

Make governed lifecycle evidence durable, correlated, and recoverable beyond process memory.

## Current gaps addressed

* authorization storage is in-memory only;
* audit storage is in-memory only;
* trace storage is in-memory only;
* approval records are not persisted;
* lifecycle evidence cannot currently survive restart.

## Scope

This milestone covers the generic persistence boundary for:

* approval;
* authorization;
* execution audit;
* execution trace;
* lifecycle correlation;
* relevant history/evidence references.

## Required behavior

Governed evidence must preserve, where applicable:

* decision identity;
* action identity;
* target;
* operation;
* risk;
* policy result;
* approval result;
* authorization;
* execution result;
* verification result;
* timestamps;
* outcome;
* reasons;
* correlation identifiers.

Blocked, rejected, held, failed, and successful paths must produce appropriate evidence.

## Definition of Done

* [ ] Authorization records survive process restart.
* [ ] Approval records survive process restart.
* [ ] Audit records survive process restart.
* [ ] Trace records survive process restart.
* [ ] Records have stable correlation identifiers.
* [ ] Evidence can reconstruct an execution decision path.
* [ ] Evidence can reconstruct a blocked path.
* [ ] Persistence failure is represented safely and does not silently create false success.
* [ ] Existing RMT-020 boundary behavior remains valid.

## Validation evidence

A controlled execution is performed, the process is restarted, and the resulting evidence is retrieved and correlated.

A blocked request is similarly verified to retain its governance evidence.

---

# 7. Milestone RMT-C03 — Post-Execution Verification

**Status: CLOSED**

## Objective

Close the execution control loop by verifying observed state against the authorized expected outcome.

## Current gap

No verified post-execution verifier or connected verification call chain currently exists.

## Scope

This milestone covers the generic verification boundary.

It does not implement domain-specific verification rules.

## Required behavior

After an applicable execution:

**Execute → Observe → Verify → Record**

The verifier must distinguish at minimum:

* verified success;
* state mismatch;
* observation unavailable;
* verification failure.

An execution result must not automatically be treated as verified success.

## Definition of Done

* [ ] Verification contract exists.
* [ ] Expected outcome is represented.
* [ ] Observed state is represented.
* [ ] Verification is connected after applicable execution.
* [ ] Successful verification is recorded.
* [ ] State mismatch is recorded.
* [ ] Observation-unavailable state is recorded.
* [ ] Verifier failure is recorded.
* [ ] Verification evidence is correlated to the execution.
* [ ] Failed or unknown verification cannot be represented as successful completion.

## Validation evidence

At minimum:

1. successful execution + matching state;
2. execution + mismatching state;
3. execution + unavailable observation;
4. verifier failure.

All four outcomes must remain distinguishable in evidence.

---

# 8. Milestone RMT-C04 — Generalized Understand → Decide Completion

## Objective

Close the remaining Target-State evidence gaps in the understanding, intelligence, analysis, decision, and learning/history layers without rebuilding the existing intelligence foundation.

## Gaps closed

* D1 — generalized observation boundary (non-Docker source/test adapter);
* D2 — explicit stale/unknown/freshness semantics end to end;
* D3 — intelligence/analysis evidence for healthy, degraded/failed, stale, and unknown conditions with confidence/evidence;
* D4 — decision/recommendation evidence and the non-executing decision boundary;
* L1 — learning/history boundary consuming governed evidence.

## Current state

The intelligence architecture is substantially connected.

The remaining issue is Target-State completeness and evidence, especially around:

* generalized observation boundaries;
* stale state;
* unknown state;
* confidence/evidence;
* non-Docker observation representation;
* explicit decision semantics;
* learning/history consuming governed evidence.

## Scope

This milestone covers only the missing Target-State behavior required to validate:

**Understand → Intelligence → Analysis → Decide → Learn**

It does not expand intelligence into unrestricted predictive AI.

## Definition of Done

* [ ] Normalized observation/state contract is validated.
* [ ] Current state is represented.
* [ ] Historical state is represented.
* [ ] Freshness is explicit.
* [ ] Stale state is explicit.
* [ ] Unknown state is explicit.
* [ ] At least one representative non-Docker/test observation source proves the abstraction boundary.
* [ ] Intelligence preserves uncertainty when evidence is insufficient.
* [ ] Evaluation includes inspectable evidence and confidence.
* [ ] Decisions are evidence-backed.
* [ ] Recommendations remain separate from authorization.
* [ ] Decision creation cannot directly execute an action.
* [ ] Learning consumes recorded governed evidence (audit, trace, verification, approval) without bypassing governance or acquiring authorization authority.

## Validation evidence

At minimum:

* healthy condition;
* degraded/failed condition;
* stale/unknown condition;
* evidence-backed decision;
* uncertain condition that does not trigger unauthorized execution;
* learning consumes governed evidence without authorizing execution.

---

# 9. Milestone RMT-C05 — Controlled Platform Self-Management

## Objective

Enable RMT to govern bounded operations on itself using the same Core control architecture.

## Gaps closed

* E1 — no governed self-management mutation path.

## Current state

RMT can expose platform state and read-only platform information.

A complete governed self-management mutation path does not yet exist.

## Scope

This milestone covers only generic platform self-management mechanisms required by the Target State.

It does not turn RMT into an unrestricted autonomous administrator.

## Required lifecycle

**Understand RMT → Decide → Govern → Authorize → Execute → Verify → Audit**

## Definition of Done

* [ ] RMT platform identity/version state is observable.
* [ ] Platform capability state is observable.
* [ ] Configuration state is observable and validated.
* [ ] A bounded platform operation can be represented as a governed action.
* [ ] The operation passes risk/policy/approval/authorization.
* [ ] Execution occurs through the controlled boundary.
* [ ] Post-operation state is verified.
* [ ] Complete evidence is recorded.
* [ ] An unauthorized platform operation is blocked.
* [ ] Read-only observation remains distinct from mutation authority.

## Validation evidence

A representative controlled platform operation must demonstrate:

**observe → decide → govern → authorize → execute → verify → audit**

and a corresponding unauthorized operation must be blocked.

---

# 10. Milestone RMT-C06 — Controlled Platform Evolution

**Status: CLOSED**

## Objective

Provide a finite mechanism for governing necessary RMT platform changes without uncontrolled self-modification.

## Gaps closed

* F1 — no controlled platform-evolution lifecycle.

## Current gap

The repository contains structural module/evolution components but no verified complete governed change lifecycle.

## Scope

The Core provides only the generic mechanisms necessary to govern platform evolution.

Domain-product evolution remains above Core.

## Required lifecycle

**Change Proposal → Scope/Compatibility Assessment → Risk → Policy → Approval → Authorization → Execution → Verification → Audit**

## Required controls

A platform change must have:

* change identity;
* declared scope;
* compatibility assessment;
* risk assessment;
* policy decision;
* approval where required;
* explicit authorization;
* controlled execution;
* verification;
* audit evidence;
* safe failure or rollback where applicable.

## Definition of Done

* [ ] A change has a stable identity.
* [ ] Scope is explicit.
* [ ] Compatibility is assessed.
* [ ] Risk is assessed.
* [ ] Governance is evaluated.
* [ ] Approval requirements are enforced.
* [ ] Authorization is explicit.
* [ ] Change execution uses the controlled execution boundary.
* [ ] Post-change verification exists.
* [ ] Failure/safe handling exists for applicable changes.
* [ ] Complete change evidence is preserved.
* [ ] Unapproved changes are blocked.
* [ ] Out-of-scope changes are blocked.
* [ ] A change cannot modify its own governance boundary through implicit execution.

## Validation evidence

A representative approved change must complete the controlled lifecycle.

A rejected or out-of-scope change must be blocked before execution.

---

# 11. Milestone RMT-C07 — Platform Validation and Freeze

**Status: CLOSED**

## Objective

Prove that the complete finite RMT Core Target State is real, integrated, enforced, and free of known bypass paths.

This milestone is validation, not feature expansion.

## Gaps closed

* G1 — no integrated production-equivalent validation suite;
* G2 — final Core-boundary review / no-remaining-requirement confirmation.

## Closure

RMT-C07 is CLOSED. The finite platform-validation suite passes (122 tests,
including the C07 HTTP transport artifact and the D1 correction), the G2 final
Core-boundary review passed, and the RMT Core has reached **Platform Freeze**.
Direct module_registry.register_module() is an internal governed primitive, not a
bypass or missing Core requirement. execution/service.py::execute_action() is
unreachable dead-code housekeeping with no C07 impact.

## Preconditions

All preceding Core milestones must satisfy their respective Definitions of Done.

## Validation scope

The validation suite must cover:

### Understand

* current state;
* history;
* stale state;
* unknown state;
* normalized source abstraction.

### Decide

* evidence-backed decisions;
* recommendations;
* uncertainty;
* no direct authorization/execution.

### Govern

* allowed;
* denied;
* approval-required;
* unsupported;
* risk influence.

### Authorize

* valid;
* missing;
* expired/invalid;
* mismatched action;
* mismatched target;
* mismatched operation;
* invalid approval provenance.

### Execute

* controlled adapter invocation;
* adapter failure;
* blocked-before-adapter behavior;
* single production mutation boundary.

### Verify

* verified success;
* mismatch;
* unavailable observation;
* verifier failure.

### Learn / Evidence

* audit;
* trace;
* approval;
* authorization;
* execution;
* verification;
* history;
* restart/durability.

### Self-Management

* observable platform state;
* governed platform operation;
* blocked unauthorized operation;
* verified outcome.

### Controlled Evolution

* approved change;
* rejected change;
* out-of-scope change;
* verification;
* safe failure;
* audit.

### Core Boundary

* domain capabilities are not required for Core completion;
* provider-specific functionality is not silently promoted into Core;
* future capabilities remain classified outside the finite Target State.

## Definition of Done

* [ ] All Core Completion Criteria pass.
* [ ] All required positive paths pass.
* [ ] All required negative paths pass.
* [ ] Unknown states are represented safely.
* [ ] Verification failures are represented safely.
* [ ] Evidence is complete and correlated.
* [ ] Evidence survives the required persistence boundary.
* [ ] No known production mutation bypass remains.
* [ ] No adapter can become an alternative authorization boundary.
* [ ] No remaining required Core capability exists outside the Target State.
* [ ] Core/domain boundaries remain explicit.
* [ ] Validation is reproducible.
* [ ] Validation results are recorded.

## Platform Freeze condition

Only after the complete validation suite passes may RMT declare:

**RMT Core — Platform Freeze**

After Platform Freeze, future development is primarily:

* products;
* domain modules;
* integrations;
* adapters;
* applications.

Core modification requires evidence that the finite Target State or an existing Core contract is insufficient.

---

# 12. Dependency Model

The roadmap has the following principal dependencies:

```text
Existing Intelligence Foundation
            |
            v
RMT-C01 Governed Execution Boundary
            |
            +----------------------+
            |                      |
            v                      v
RMT-C02 Durable Evidence    RMT-C03 Verification
            |                      |
            +----------+-----------+
                       |
                       v
              RMT-C05 Self-Management
                       |
                       v
              RMT-C06 Platform Evolution
                       |
                       v
              RMT-C07 Validation
                       ^
                       |
              RMT-C04 Understand/Decide
```

RMT-C01 through RMT-C06 are CLOSED.

RMT-C07 is the next milestone. Direct module-registry `register_module()` access
is explicitly deferred to RMT-C07 and must not be represented as an RMT-C06
defect.

RMT-C02 and RMT-C03 have a strong relationship:

* verification produces lifecycle outcome evidence;
* durable evidence preserves that outcome.

Neither should be interpreted as replacing the other.

---

# 13. What This Roadmap Explicitly Does Not Authorize

This roadmap does not authorize implementation of:

* Banking Risk Management as a Core subsystem;
* Budget Control as a Core subsystem;
* AI Agent Governance as a Core subsystem;
* unrestricted Docker expansion;
* unlimited infrastructure adapters;
* unrestricted machine learning;
* uncontrolled autonomous self-modification;
* arbitrary UI development;
* enterprise IAM beyond demonstrated Core requirements;
* speculative future automation;
* indefinite Core architecture expansion.

Such proposals must be classified separately before implementation.

---

# 14. Milestone Acceptance Rule

A milestone may be declared complete only when:

**Implementation + Integration + Enforcement + Validation + Evidence = Complete**

If any of these is absent, the milestone remains incomplete.

A passing unit test does not override a missing production integration.

A connected path does not override a missing enforcement boundary.

An enforcement boundary does not override missing evidence.

Documentation does not substitute for executable behavior.

---

# 15. Final Roadmap Boundary

The roadmap is complete. RMT-C07 has established that the finite Core Target
State is satisfied, and the RMT Core has reached **Platform Freeze**.

There is intentionally no RMT-C08.

Any proposal after RMT-C07 must first answer:

> **Does this change prove that the finite Core Target State or an existing Core contract is insufficient?**

If the answer is no, the proposal belongs above the Core, in future backlog, or is unnecessary.

---

# 16. Final Statement

RMT is not being developed toward an indefinitely expanding architecture.

The remaining Core work is finite.

The objective is not to make the Core capable of everything.

The objective is to make the defined Core **complete, governed, enforceable, verifiable, observable, auditable, and capable of controlled evolution**.

The endpoint is:

**Understand → Decide → Govern → Authorize → Execute → Verify → Learn**

followed by:

**Platform Validation → Platform Freeze**

That boundary has been reached: the finite RMT Core Target State has been
validated and the RMT Core is frozen. Future development is primarily
above-Core/domain/product/integration/adapter/application work.
