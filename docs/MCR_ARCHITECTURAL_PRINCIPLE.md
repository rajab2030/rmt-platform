# MCR Architectural Principle

**Status:** Evidence-backed architectural principle
**Version:** 0.1
**Scope:** Supervisory architecture
**Relationship to RMT:** Architectural interpretation/pattern; not a new RMT subsystem
**Companion:** `MCR_SUPERVISORY_CONTRACT.md` — this document is the *principle* (intent / what & why); the contract is the *compliance spec* (how a governed child demonstrates compliance).

---

## 1. Purpose

This document defines the architectural principle represented by the **Master Control Room (MCR)** concept.

MCR originated as a real-world supervisory model: a central control room supervising multiple independent operational systems, where each subordinate system may have its own local controls, state, and operational intelligence.

The modern interpretation generalizes that model to software systems in which subordinate systems may themselves reason, decide, and act.

The principle is:

> **A supervisory control layer may govern multiple independent intelligent systems without replacing their local intelligence, provided consequential operations remain inside a common supervisory boundary.**

MCR is therefore a **supervisory architectural pattern**, not a requirement to build another application, service, or control subsystem.

---

## 2. Core Principle

The fundamental relationship is:

> **MCR does not become everything it controls.
> MCR controls what operates under it.**

A child system may retain:

* local intelligence
* local reasoning
* local decisions
* local optimization
* domain-specific knowledge
* autonomous operation

But when that system operates under MCR, its consequential actions remain subject to the governing supervisory boundary.

The child does not need to surrender its intelligence.

It does need to respect the authority boundary under which it operates.

---

## 3. One MCR, Many Intelligent Children

The intended topology is:

```text
                         MCR
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
     Child A           Child B           Child C
        │                 │                 │
   local intelligence local intelligence local intelligence
   local decisions     local decisions     local decisions
   local execution     local execution     local execution
```

The children do not need to be instances of the same technology.

A child may be:

* an application
* an infrastructure system
* an AI agent
* an operational platform
* a business system
* a cyber system
* another autonomous control system

MCR supervises the relationship rather than absorbing the child into itself.

---

## 4. What MCR Owns

MCR owns the supervisory concerns that must remain common across governed children:

* supervisory understanding
* cross-system context
* policy
* authority boundaries
* risk
* action constraints
* approval requirements
* escalation
* consequential action control
* outcome verification
* evidence
* audit

MCR does **not** need to own the child's internal reasoning process.

---

## 5. What the Child Owns

A governed child retains responsibility for:

* domain intelligence
* domain-specific reasoning
* local state interpretation
* local optimization
* local decision formation
* proposing actions
* execution inside granted authority

The child may be autonomous.

Autonomy, however, is bounded by supervisory authority.

Therefore:

> **Capability does not create authority.**

A child may possess a technical capability without possessing permission to exercise that capability in a particular context.

---

## 6. The Critical Boundary

The experiments established an important distinction between two possible enforcement locations.

### Weak boundary

```text
ATLAS
  ↓
Tool Registry
  ↓
MCR
  ↓
World
```

This is insufficient if another consequential tool can reach the world without passing through the registry.

Experiment #1 demonstrated exactly this failure: a generic `run_command` mechanism produced a restricted effect without MCR authorization.

### Strong boundary

```text
ATLAS
  ↓
Tools / Interfaces / Adapters / Commands
  ↓
        MCR
          ↓
Authoritative Mutation Boundary
          ↓
        State
```

The governing requirement is therefore:

> **Governance must be enforced at the authoritative consequential mutation boundary, not merely at the interface or tool boundary.**

Different interfaces may exist.

Different adapters may exist.

Different mechanisms may exist.

But consequential state change must converge on the same enforced boundary.

---

## 7. Effect, Not Interface

MCR governance must not depend exclusively on the name of the mechanism requesting an action.

The following may be different interfaces:

```text
restart_service(web)

run_command(web, "restart")

adapter_restart(web)

compose(...)
```

If they produce the same consequential effect, they must remain subject to the same supervisory authority.

Therefore:

> **The unit of governance is the consequential effect, not the tool name.**

This does not imply that every internal operation must be individually exposed to MCR.

It means that no consequential effect may acquire an ungoverned path merely because it is expressed through a different interface.

---

## 8. The Total Mutation Boundary

The supervisory boundary is considered operationally complete only when:

1. every consequential mutation reaches the authoritative boundary;
2. the boundary consults the governing authority before mutation;
3. unauthorized mutations cannot proceed;
4. restricted mutations cannot proceed without the required condition;
5. allowed mutations proceed only within the granted authority;
6. successful mutations can be verified;
7. evidence records the supervisory decision and resulting state;
8. alternate tools and interfaces cannot create an equivalent effect outside the boundary.

The phrase **single mutation boundary** refers to the architectural property that consequential state change has one authoritative enforcement point.

It does not necessarily require one physical process or one software function in every implementation.

---

## 9. Autonomy and Supervision

MCR does not require children to be passive.

A governed child may:

```text
OBSERVE
   ↓
REASON
   ↓
DECIDE
   ↓
PROPOSE / REQUEST
   ↓
MCR SUPERVISION
   ↓
ACT
```

The child therefore remains autonomous in cognition and decision formation while remaining subordinate in consequential authority.

This distinction is fundamental:

> **MCR governs what the child is authorized to do, not how the child is required to think.**

---

## 10. Verification Is Separate From Authorization

Authorization answers:

> "May this action occur?"

Verification answers:

> "Did the intended result actually occur?"

These are different questions.

A governed architecture must therefore distinguish:

```text
Decision
   ↓
Authorization
   ↓
Execution
   ↓
Observed Outcome
   ↓
Verification
```

An allowed action is not automatically a successful action.

Likewise, a successful outcome does not retroactively make an unauthorized action legitimate.

---

## 11. Unknown Must Remain Unknown

A supervisory layer must distinguish at least:

* observed
* reported
* inferred
* verified
* unknown

MCR must not manufacture certainty where evidence is absent.

If the child reports a state that MCR cannot independently establish, that state remains appropriately qualified.

This preserves the distinction between:

> **what happened, what was observed, what was inferred, and what was verified.**

---

## 12. Evidence From the Three Experiments

The MCR hypothesis was not accepted merely because an initial prototype behaved correctly.

The experiments followed a progressive pattern.

### Experiment #1 — Boundary Failure

A working supervisory path was deliberately challenged with an alternate generic tool.

ATLAS autonomously discovered `run_command` and used it to produce the restricted effect without MCR authorization.

Result:

**FAIL — genuine bypass discovered.**

The lesson was that a tool registry is not automatically a total execution boundary.

---

### Experiment #2 — Mutation Boundary

The experiment moved enforcement to the actual state-mutation boundary.

The same generic mechanism could no longer produce a consequential state transition without MCR evaluation.

The experiment also protected the underlying state against direct writes.

Result:

**T1–T5 PASS; no operational bypass.**

The important architectural change was not removing the generic tool.

It was ensuring that different mechanisms converged on one authoritative mutation boundary.

---

### Experiment #3 — Adversarial Campaign

The third experiment broadened the attack surface and allowed ATLAS to probe:

* generic commands
* raw mutation
* alternate adapters
* introspection
* composition
* replay
* reference/object escape
* indirect effects
* malformed requests
* multi-step operations
* broad autonomous exploration

The operational supervisory boundary survived the campaign.

However, two limitations were deliberately retained:

1. a policy-level dependency-cascade gap was discovered;
2. absolute Claim C — that Python implementation makes bypass technically impossible — was not claimed.

These limitations strengthen rather than weaken the evidence because the experiment distinguished **boundary enforcement**, **policy completeness**, and **language-level encapsulation** instead of conflating them.

---

## 13. What the Experiments Prove

The evidence supports the following architectural conclusion:

> **MCR can remain the supervisory authority over autonomous child systems when consequential state changes are forced through a total, authoritative supervisory mutation boundary.**

The evidence does **not** prove:

* that every possible implementation language provides absolute encapsulation;
* that every possible policy is complete;
* that every possible future implementation automatically preserves the boundary;
* that MCR eliminates the need for domain-specific governance.

Therefore the principle is intentionally narrower.

---

## 14. Architectural Invariant

The central invariant is:

> **No consequential state transition may occur without passing through the applicable supervisory boundary.**

This invariant is stronger than:

> "Every approved tool calls MCR."

It is also stronger than:

> "The tool registry is trusted."

The architecture must protect the consequential mutation itself.

---

## 15. Policy Is a Separate Concern

A total boundary does not automatically imply a complete policy.

Experiment #3 demonstrated that a consequential effect may emerge through an allowed dependency operation even when the mutation itself is correctly governed.

Therefore:

> **Boundary integrity and policy completeness are separate architectural properties.**

A system may have:

* a strong mutation boundary but incomplete policy;
* complete policy definitions but a bypassable mutation boundary.

Both must be addressed independently.

---

## 16. Non-Expansion Principle

The MCR principle does not imply that every newly discovered child requires a new control subsystem.

The intended architecture remains:

> **One MCR → Many Children**

The appearance of a new child system does not by itself justify creating another MCR layer.

Likewise, MCR should not absorb every child system's internal intelligence.

The principle is supervisory composition, not architectural duplication.

---

## 17. Relationship to RMT

MCR should be understood as a conceptual and architectural pattern for interpreting RMT's supervisory role.

It is not:

* a new milestone;
* a new subsystem automatically required by RMT;
* a replacement for RMT's existing governance architecture;
* permission to weaken existing policy;
* permission for RMT to govern itself outside its own rules.

The principle remains subordinate to the governing architecture and policies of the system in which it is applied.

---

## 18. Design Rules

When applying the MCR principle:

1. **Protect the governing boundary.**
2. **Govern consequential effects, not merely tool names.**
3. **Separate capability from authority.**
4. **Keep child intelligence local where appropriate.**
5. **Do not require access to internal child reasoning merely to supervise action.**
6. **Make consequential mutation converge on one authoritative boundary.**
7. **Fail closed when authority is absent or invalid.**
8. **Separate authorization from verification.**
9. **Preserve unknown as unknown.**
10. **Record evidence for consequential supervisory decisions.**
11. **Test alternate paths, not only intended paths.**
12. **Treat policy completeness separately from boundary integrity.**
13. **Do not introduce architectural duplication merely because another child exists.**

---

## 19. Governing Statement

> **MCR does not become everything it controls.
> MCR controls what operates under it.**

And the stronger enforcement statement is:

> **Every consequential state transition must pass through the authoritative supervisory boundary, regardless of the interface, tool, adapter, command, or mechanism that requests it.**

---

## 20. Final Position

The three experiments support MCR as a valid supervisory architectural pattern.

The first experiment found the weakness.

The second demonstrated the stronger boundary.

The third subjected that boundary to broader adversarial pressure.

The result is not a claim of mathematical impossibility.

It is a practical architectural principle:

> **Autonomous systems can remain autonomous while operating under a higher supervisory authority, provided consequential authority is enforced at the actual state-mutation boundary and no operational escape path exists.**

**One MCR.
One governing model.
Multiple intelligent, autonomous, compliant children.**
