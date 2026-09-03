# RMT-C01 — Governed Execution Boundary — Acceptance Evidence

## 1. Authority

This package is the acceptance evidence for **RMT-C01 — Governed Execution
Boundary**, per `docs/milestones/RMT-C01-Governed-Execution-Boundary.md` §27.

It is governed by the RMT authority hierarchy (AGENTS.md §2):
`RMT_MASTER_DEFINITION.md`, `RMT_CORE_TARGET_STATE.md`,
`RMT_CORE_GAP_MATRIX.md`, `RMT_CORE_REMAINING_ROADMAP.md`, and the C01 contract.

## 2. Summary

C01 establishes a single authoritative governed production mutation boundary:

```
Action -> Policy -> Risk(Simulation) -> Approval -> Authorization
       -> Execution Translation -> ExecutionEngine -> Adapter
```

The fundamental invariant is enforced: **no Core-scope production mutation
reaches an execution adapter unless the required governance, approval, and
authorization controls have successfully completed.**

## 3. Execution-Entrypoint Inventory and Mutation-Path Classification

See `docs/milestones/RMT-C01-Evidence-Mutation-Path-Classification.md`.

Summary:
- **GOVERNED:** `POST /execute`, `POST /approve`, `execute_decision()`,
  `execute_governed_action()`, `approve_held_action()`.
- **ENFORCEMENT BOUNDARY:** `execution_engine.execute()`.
- **ADAPTER-ONLY:** `docker_api` mutation functions (not exposed as routes).
- **READ-ONLY / DIAGNOSTIC:** all `GET` routes.

No equivalent unmanaged production mutation path remains available.

## 4. Policy-Relationship Decision

Two policy layers exist and their relationship is explicit and deterministic:

| Layer | Responsibility | Authority |
|-------|---------------|-----------|
| **Action policy** (`actions/policy.py`) | Governance gate: allowed / denied / requires-approval | First gate; a denial blocks before execution |
| **Execution policy** (`execution/policy.py`) | Final deny-only safety gate | Last gate; can only block, never grant |

**Decision:** Action policy is the authoritative governance gate. Execution
policy is a **deny-only** final safety check (blocks `format`/`wipe`). It does
not grant permission and does not require approval — approval is handled in the
governance layer. This prevents execution policy from becoming a second
independent authorization authority (C01 §10, INV-06).

**Propagation:** An action-policy denial returns `policy_denied` and never
reaches execution. An execution-policy denial returns a blocked result and
never reaches the adapter.

## 5. Risk-Relationship Decision

Two risk assessments exist and are reconciled to be consistent and traceable:

| Layer | Responsibility |
|-------|---------------|
| **Governance risk** (`actions/simulation.py`) | Drives approval decisions |
| **Execution risk** (`execution/risk.py`) | Final assessment recorded in trace/audit |

**Decision:** Governance risk is authoritative for approval. Execution risk is
a final independent assessment that is **consistent** with governance risk for
the same operation (verified for all docker operations):

| Operation | Governance | Execution |
|-----------|-----------|-----------|
| start / stop | low | low |
| restart | medium | medium |
| create | medium | medium |
| remove | high | high |

Risk does not grant execution authority; it is an input to governance and
enforcement (C01 §11, INV-07).

## 6. Approval Lifecycle

- **Automatic approval** (`ApprovalMode.AUTO`): continues to authorization and
  execution.
- **Manual approval** (`ApprovalMode.MANUAL`): produces a genuine **hold state**
  (`ApprovalHold`) with an expiry window; no adapter invocation while held.
- **Rejection** (`ApprovalMode.REJECT`): terminates the path; no adapter
  invocation.
- **Continuation** (`approve_held_action`): resumes a held action only after a
  legitimate approval grant, reusing the previously governed action and adapter.
  It cannot create a new action, skip policy/risk, or manufacture authorization.
- **Expiry:** an expired approval hold cannot continue.

## 7. Authorization Provenance and Validity

`ExecutionAuthorization` is bound to action, target, and operation, and carries
provenance (`decision_id`, `approval_id`), issuer (`authorized_by`), status,
reason, and an expiry window.

The execution engine rejects, before adapter lookup:
- missing authorization;
- non-approved authorization;
- expired authorization;
- action / target / operation mismatch.

A caller-supplied authorization identifier is **not** sufficient — the
authorization must correspond to a legitimate governed lifecycle state
(INV-10, N11).

## 8. Validation Evidence

**Result: 25/25 tests pass** (`app/core/intelligence/testing/`).

### Governance
- `test_policy_denied_action_adapter_not_called` (N01)
- `test_unsupported_action_type_policy_denied_adapter_not_called` (N01)
- `test_valid_authorization_wipe_execution_policy_deny` (N01)

### Approval
- `test_low_risk_action_auto_approves_and_executes` (P01)
- `test_high_risk_remove_held_for_manual_approval_adapter_not_called` (N04)
- `test_approval_required_action_held_adapter_not_called` (N03)
- `test_manual_approval_hold_then_legitimate_continuation_executes` (P03)
- `test_manual_approval_rejection_terminates_adapter_not_called` (N02)
- `test_approve_unknown_approval_id_not_found`
- `test_expired_approval_hold_cannot_continue`

### Authorization
- `test_valid_approved_authorization_proceeds_to_simulation_adapter` (P02)
- `test_missing_authorization_blocked_adapter_not_called` (N05)
- `test_non_approved_authorization_blocked_adapter_not_called` (N06)
- `test_wrong_action_id_blocked_adapter_not_called` (N07)
- `test_wrong_target_blocked_adapter_not_called` (N08)
- `test_wrong_operation_blocked_adapter_not_called` (N09)
- `test_expired_authorization_blocked_adapter_not_called` (N10)
- `test_synthetic_authorization_does_not_grant_execution` (N11)
- `test_auto_authorization_carries_provenance`

### Execution / Boundary
- `test_governance_bypass_direct_engine_call_blocked` (N12)
- `test_valid_authorization_restart_simulation_audit_trace_produced`

### Regression (RMT-020)
- All 12 original authorization-boundary tests pass unchanged.

### Observation (pre-existing, unaffected)
- `test_metric_normalizes_to_observation`, `test_observation_health_evaluation`,
  `test_create_health_evaluation_from_metric`, `test_stale_observation_detection`.

## 9. Proof That Blocked Paths Do Not Invoke the Adapter

Every negative test asserts `adapter_registry.get.assert_not_called()` (and,
where applicable, `adapter.execute.assert_not_called()`), proving the adapter
was **not invoked** — distinguishing "blocked before adapter" from "adapter
invoked and failed" (C01 §20).

## 10. Regression

All 12 original RMT-020 authorization-boundary tests pass unchanged, confirming
existing valid behavior is preserved (C01 §21).

## 11. Repository Diff Inspection

Changed files (C01 scope):
- `app/main.py` — `/execute` governed; `/approve` continuation; adapter resolution.
- `app/docker_api.py` — lazy client; docker optional (adapter concern).
- `app/core/intelligence/actions/` — models, policy, simulation, service,
  approval (hold/continuation/expiry), authorization (provenance/expiry).
- `app/core/intelligence/execution/` — engine (expiry), policy (deny-only),
  risk (reconciled), translator (parameters).
- `app/core/intelligence/service.py` — `execute_decision` delegates to governed path.
- `app/core/intelligence/testing/` — C01 validation tests.

No C02–C07 capability was introduced. Docker remains an adapter/integration
concern, not a Core requirement.

## 12. Open Items / Decisions Required

1. **Sign-off on the deny-only execution policy decision** (§4) — a deliberate
   contract decision requiring explicit authorization.
2. **HTTP-level route tests** — deferred to RMT-C07 (Platform Validation), which
   exercises production-equivalent entrypoints. Blocked in this environment by
   no `httpx` and no docker access.

## 13. Conclusion

C01 satisfies its Definition of Done: the governed execution boundary is
**implemented, connected, enforced, validated, and evidenced**. The next
milestone is **RMT-C02 — Durable Governance Evidence**, which begins only under
its own contract and review gate.
