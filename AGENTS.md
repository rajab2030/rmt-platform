# RMT Platform — Agent Contract

## 1. Purpose

This file defines the operating contract for AI coding agents working on the RMT Platform.

Agents must treat the repository as a governed engineering system, not as an open-ended coding workspace.

This file defines **how agents operate**. It does not define the RMT architecture, Target State, roadmap, or milestone scope.

Agents must derive the current architectural and implementation state from the current authoritative RMT documents and the repository itself.

---

## 2. Authority Hierarchy

The following hierarchy applies:

1. Current RMT authority documents
2. Current milestone implementation contract
3. Current repository architecture and code
4. Current validation evidence and tests
5. Historical documentation and archived baselines

Current RMT authority documents include, where applicable:

- `docs/RMT_MASTER_DEFINITION.md`
- `docs/RMT_CORE_TARGET_STATE.md`
- `docs/RMT_CORE_GAP_MATRIX.md`
- `docs/RMT_CORE_REMAINING_ROADMAP.md`
- applicable architecture and design documents
- applicable recovery and baseline documentation

When sources conflict:

**STOP.**

Inspect the repository, identify the conflict, and report it before modifying code.

Historical milestones, tags, commits, handovers, and archived documents must not be treated as the current state unless the current milestone contract explicitly designates them as relevant.

---

## 3. Current State Rule

Do not hard-code a milestone, tag, commit, or historical baseline into this contract.

The current milestone must be determined from the current project state and the applicable current milestone contract.

Do not infer the current milestone from:

- this file;
- an old handover;
- an old Git tag;
- an archived document;
- a previous conversation.

Before implementation, verify:

1. repository root;
2. current Git status;
3. current HEAD;
4. applicable current milestone contract;
5. relevant current implementation;
6. relevant tests and validation evidence.

Never rebuild the platform from zero.

---

## 4. Structural Discipline

RMT architecture is responsibility-driven.

Apply:

**One task → one layer → one responsibility → one validation**

Do not create a new component, layer, abstraction, or subsystem merely for convenience.

Before introducing a structural change, establish:

1. the responsibility being addressed;
2. why an existing component cannot appropriately own it;
3. the architectural boundary affected;
4. the integration point;
5. the validation that proves the change.

Do not collapse distinct responsibilities merely to reduce code.

Do not duplicate an existing responsibility under a new name.

---

## 5. Scenario-Driven Evolution

RMT evolves from demonstrated operational or architectural requirements.

The preferred sequence is:

**Scenario → Observe → Understand → Identify Gap → Determine Smallest Justified Change → Implement → Validate → Evidence → Accept or Reject**

Do not implement speculative capabilities.

Do not expand Core because a capability is technically desirable.

Every change must be traceable to:

- an accepted requirement;
- a verified gap;
- an applicable milestone contract;
- or a demonstrated insufficiency of an existing contract.

---

## 6. Unknown States

Unknown or previously unseen events are valid system states.

Do not force unknown information into an incorrect category merely to make processing continue.

When an unknown scenario appears:

1. preserve the evidence;
2. describe the observed context;
3. avoid unsafe automation;
4. determine whether the existing architecture can represent it;
5. extend an existing responsibility when appropriate;
6. introduce a new responsibility only when genuinely required.

Unknown does not automatically justify a new subsystem.

---

## 7. Production Code Changes

Before modifying production code:

1. inspect the complete relevant file;
2. inspect dependent interfaces and contracts;
3. identify all relevant callers;
4. check for existing components serving the same responsibility;
5. inspect relevant tests;
6. identify possible bypasses or alternate execution paths;
7. establish the smallest coherent change.

Preserve existing valid behavior unless the current milestone explicitly requires changing it.

Do not perform opportunistic refactoring.

Do not rewrite completed architectural foundations merely to simplify the current task.

---

## 8. Governed Execution Boundary

The current RMT governed lifecycle is:

**Understand → Decide → Govern → Authorize → Execute → Verify → Learn**

For production mutations within Core scope, governance is mandatory.

No production mutation may bypass the authoritative governed execution boundary.

Where execution is applicable, the required control relationship includes:

**Decision → Action → Policy → Risk → Approval → Authorization → Execution**

The execution adapter is an executor, not a governance mechanism.

Adapters must not:

- authorize;
- approve;
- override policy;
- redefine risk;
- manufacture governance evidence;
- create an alternative authorization boundary.

Rejected, denied, held, unauthorized, invalidly authorized, or otherwise disallowed work must not reach an execution adapter.

The exact requirements for the active milestone are defined by its current milestone contract.

---

## 9. Responsibility Boundaries

Preserve the separation of architectural responsibilities.

### Observability

Answers:

**What is happening?**

### Intelligence

Answers:

**What does it mean?**

### Decision

Determines:

**What should be considered or proposed based on evidence?**

### Policy

Determines:

**What is allowed?**

### Risk

Determines:

**What could happen and what governance restrictions apply?**

### Approval

Determines:

**Whether required human or automatic approval conditions have been satisfied.**

### Authorization

Establishes:

**Explicit permission for the intended execution under the required governance conditions.**

### Execution

Performs:

**The authorized operation.**

### Verification

Determines:

**Whether the observed result matches the expected authorized outcome.**

### Audit / Trace

Preserves:

**What occurred and why the lifecycle reached its outcome.**

Do not silently transfer one responsibility into another layer.

---

## 10. Frozen Foundations

Completed milestones are treated as stable foundations.

Future work must consume existing valid contracts rather than casually modifying completed layers.

A completed component may be changed only when:

1. a demonstrated requirement or scenario exists;
2. the existing contract is shown to be insufficient;
3. the change is within the active milestone scope;
4. the impact on existing behavior is understood;
5. validation evidence is defined.

Do not weaken a safety or governance boundary to make a test pass.

---

## 11. Validation Is Mandatory

Code existence is not completion.

A milestone or change is complete only when the required behavior is:

**implemented → connected → enforced → tested → evidenced**

For behavioral changes, use an appropriate sequence:

**Inspect → Implement → Compile → Targeted Test → Integration Test → Inspect Diff → Report Evidence**

Where governance or execution is involved, negative paths are mandatory.

A test result must distinguish:

- blocked before execution;
- adapter invoked and failed;
- successful execution;
- verification failure;
- unknown or unavailable state.

A passing unit test does not override missing production integration.

A connected path does not override a missing enforcement boundary.

Documentation does not substitute for executable behavior.

---

## 12. Change Scope

Agents must remain inside the active milestone contract.

Do not implement future milestone functionality unless the active contract explicitly requires it as a dependency.

Do not silently introduce:

- durable persistence when deferred;
- post-execution verification when deferred;
- self-management when deferred;
- controlled evolution when deferred;
- unrelated provider capabilities;
- speculative APIs;
- unrelated UI;
- opportunistic infrastructure.

If implementation reveals a requirement belonging to another milestone:

**STOP, document the dependency, and report it.**

---

## 13. Repository and Git Discipline

Before work:

```bash
git status
git log --oneline --decorate -15

Inspect the relevant repository state before modifying files.

Do not reset, rebase, delete, overwrite, or otherwise alter historical work unless explicitly authorized.

Do not modify a frozen or historical baseline merely because it is referenced by older documentation.

Changes must remain reviewable.

Before completion:

inspect the diff;
verify intended files only were changed;
run applicable validation;
report failures honestly;
preserve evidence.
14. Agent Modification Rule

Inspection and analysis are read-only by default.

An agent must not modify, create, delete, rename, or overwrite repository files unless the user has explicitly authorized implementation of the applicable change.

Before making an authorized change, the agent must state:

what will change;
why it is required;
which contract or invariant it satisfies;
what files are affected;
how it will be validated.

No system-level or destructive command may be executed without explicit authorization.

15. Conflict and Uncertainty Rule

When the repository, documentation, tests, or milestone contract disagree:

STOP.

Do not resolve the conflict by assumption.

Report:

the conflicting sources;
the observed repository behavior;
the requirement affected;
the decision that must be made.

When evidence is insufficient, state that it is unverified.

Never manufacture architectural intent.

16. Completion Rule

A change is accepted only when:

Implementation + Integration + Enforcement + Validation + Evidence = Complete

For milestone work, the milestone's Definition of Done is the final acceptance authority.

This file does not replace the milestone contract.

The active milestone contract does not replace the RMT architecture or defined Core boundary.

All implementation remains subordinate to the current RMT authority documents.
