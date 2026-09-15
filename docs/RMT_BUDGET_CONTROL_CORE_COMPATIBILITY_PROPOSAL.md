# RMT Budget Control–Core Compatibility Proposal

**Version:** Draft 0.1, 2026-09-14.
**Status:** DIRECTION APPROVED 2026-09-15; implementation subsequently blocked
by the standing frozen-Core directive. No freeze exception or implementation
approved.
**Evidence baseline:** static inspection at HEAD `834ca3d`.

Companion: [product proposal](RMT_BUDGET_CONTROL_PROPOSAL.md).
Authority: [Master Definition](RMT_MASTER_DEFINITION.md),
[Core Target State](RMT_CORE_TARGET_STATE.md), [AGENTS.md](../AGENTS.md).
The [frozen-Core directive](RMT_FROZEN_CORE_DEBT.md#1-authority-and-rules)
records that no further freeze deviation is authorized. This proposal does not
override that restriction or create C08.

## 1. Decision requested

**Disposition update, 2026-09-15:** the owner approved preparation of the
recommended implementation contract, then required that it not conflict with
existing Core rules or architecture. The resulting authority audit found that
the necessary `app/core/**` changes conflict with the standing no-further-freeze-
deviation directive. The implementation contract is therefore blocked. The
original decision text below is retained as proposal history, not as an open or
implemented authorization.

Approve the direction of a bounded generic extension through which the existing
Core governance service resolves registered domain policy and risk evaluators.
Core retains enforcement, approval, authorization, and execution control. Budget
concepts stay above Core. If accepted, authorize a narrowly scoped implementation
contract for the identified freeze exception; code still requires approval of
that contract.

## 2. Concrete requirement

Reserve exactly 1,500 currency units from a budget with 2,000 available, leaving
500 after a successful commitment. An authorized budget owner must approve the
exact instruction. Concurrent requests/retries must not overspend or duplicate
the effect. Assessment and evidence must describe the actual financial operation.

| Stage | Required behavior |
|---|---|
| Understand | Read request version, budget, currency, permissions, and policy |
| Decide | Propose creation of one commitment for 1,500 |
| Govern | Budget evaluators assess eligibility/risk; Core enforces results |
| Approve | Authenticated budget owner approves the exact reviewed instruction |
| Authorize | Core binds permission to action and immutable instruction |
| Execute | Adapter atomically creates the entry if write preconditions hold |
| Verify | Independent read checks exact entry, amount, currency and balance |
| Evidence | Correlate assessment, approval, authorization, execution and outcome |

Changed budget conditions cause a stale-write failure and fresh governance;
the executor may not grant an exception.

## 3. Verified compatibility and insufficiency

Existing ActionRequest parameters, CREATE, approval continuation, authorization,
adapter and observer interfaces, and durable evidence provide useful foundations.
CREATE is a faithful candidate for creating an immutable commitment entry; a
new financial action enum is not required for this initial scenario.

However, the governed service directly calls fixed policy and simulation functions:

- [actions/service.py](../projects/homelab-control-center/backend/app/core/intelligence/actions/service.py)
  invokes `evaluate_action_policy(action)` and `simulate_action(action)`.
- [actions/simulation.py](../projects/homelab-control-center/backend/app/core/intelligence/actions/simulation.py)
  interprets every `create` as "Create new container", medium risk, rollback
  available. These are not evidence of a financial commitment's risk/reversibility.
- [actions/policy.py](../projects/homelab-control-center/backend/app/core/intelligence/actions/policy.py)
  applies a fixed vocabulary/confidence policy. No registered domain policy/risk
  resolver was found in the inspected app sources.
- [agent/preview.py](../projects/homelab-control-center/backend/app/agent/preview.py)
  also directly uses those functions; preview must remain consistent with execution.

An above-Core precheck could deny a request, but the authoritative Core approval
chain would still consume the fixed container-oriented simulation. A human
approval does not correct inaccurate assessment evidence. An adapter-only
integration therefore does not satisfy this proposal's requirement.

This is a demonstrated contract limitation for the proposed product; it is not
a claim that all previously accepted Core scenarios are invalid.

## 4. Proposed generic extension

Use separate registered policy and risk evaluators, resolved inside the existing
governance service. Do not move governance into the executor or introduce another
execution boundary.

- Trusted application configuration registers implementations; callers cannot
  upload evaluators, override assessments, or select a lower-risk policy.
- Server-controlled mapping binds the selected domain assessment to the intended
  adapter and supported operation. Budget requests cannot fall back to Docker
  assessment or a simulation executor.
- Policy output includes permission, approval requirements, reasons, and evidence
  references. Risk output includes risk level, impact, uncertainty, and accurately
  described recovery semantics.
- Core validates outputs and enforces them through existing approval mechanisms.
  Missing, malformed, unsupported, or unavailable assessments block execution.
- Domain evaluators cannot mint authorization, execute, or waive mandatory Core
  restrictions. Caller-supplied risk/confidence is not proof of safety; inputs
  and the treatment of existing confidence thresholds must be specified without
  inventing scores just to pass the gate.
- Bind and preserve assessment identity/version, evidence references, instruction
  identity, and approval basis across immediate and held execution. Policy or
  instruction changes require explicit freshness/review behavior.
- Preview and real governance share assessment resolution. Existing supported
  domain behavior must retain regression coverage.
- Cancellation requiring another governed operation is not automatic rollback.

Core owns generic interfaces, registration, resolution, result validation and
enforcement. Budget Control supplies domain rules and evidence. No budget,
currency, department, purchase, or banking concepts enter Core.

## 5. Remaining above-Core obligations

The extension alone does not complete Budget Control:

- Immutable instructions must bind exact amount/currency/budget/request version;
  substitution, replay, and adapter-redirection tests are required.
- Budget roles must be enforced on every reachable route, including generic
  approval/agent routes; missing provenance must not grant access.
- Durable business requests may outlast Core's 300-second holds. At decision time,
  reassess current conditions and use fresh Core governance; do not revive expired
  authorization or silently carry approval over changed review material.
- Domain transactions must atomically enforce balance/version preconditions and
  append financial records/receipts with unique instruction identities.
- Recovery must distinguish a committed financial effect with incomplete Core
  evidence from an unapplied instruction, without duplicating effects or
  manufacturing missing governance evidence.
- Independent verification must check exact financial outcomes and preserve
  mismatched, unavailable, and failed states.

These are design requirements, not guarantees established by this review.

## 6. Scope and validation

Potential implementation touches: existing action-governance service, generic
assessment contracts/registration, approval and evidence propagation, agent
preview, and their tests. Budget implementations belong above Core. Exact files,
data compatibility, migrations, authority binding and bypass controls must be
enumerated in the subsequent implementation contract. No broad workflow engine,
payment integration, banking rules, or unrelated refactoring is proposed.

Required evidence:

1. Approved 1,500 commitment leaves 500 and is independently verified.
2. Denied/unapproved work never invokes the adapter.
3. Unknown/failed/missing domain assessments block before execution.
4. Caller-forged risk, evaluator selection, or mismatched domain/adapter fails.
5. Changed amount/currency/instruction/adapter cannot alter an approved effect.
6. Changed relevant conditions require fresh governance and review as applicable.
7. Concurrent approvals/retries cannot double-reserve funds.
8. Restart/interruption produces a recoverable, accurately classified outcome.
9. Adapter success cannot manufacture verified success.
10. Existing Core/domain suites pass for immediate and held execution; regression
    evidence includes preview parity and alternate reachable HTTP routes.

No tests were run and no capability was implemented during this proposal session.

## 7. Alternatives and disposition

| Option | Assessment |
|---|---|
| Unchanged Core with container-oriented financial assessment | Does not meet the proposed requirement |
| Budget governance in the execution adapter | Violates responsibility boundaries |
| Independent financial authorization/execution path | Violates single governed boundary |
| Bounded generic assessment extension | Recommended; explicit freeze decision required |
| Preserve absolute freeze and defer governed Budget Control | Valid owner scope decision |

Suggested approval wording, **not an approval already given**:

> Approve the Budget Control compatibility direction and authorize a narrowly
> scoped implementation contract for generic domain policy/risk assessment
> integration. Budget rules remain above Core. This permits planning the
> identified freeze exception; code changes require approval of the resulting
> implementation contract.

**Next session:** present this pending decision. The owner's request to produce
and save this proposal does not approve its recommendation or lift the freeze.
