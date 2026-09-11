# RMT-CAP-06 — Second Domain End-to-End: Agent Governance Gateway (C2 / D-1) — Proposal

**Status:** APPROVED 2026-09-11. Implementation to follow this scope exactly.
**Classification:** Above-Core / domain. No C08. No frozen Core change. No
reopening of C01–C07.

---

## 1. Objective

Prove the frozen RMT Core actually generalizes — not just architecturally, but
demonstrably — by routing one real, consequential, **non-homelab** action
through the exact same governed lifecycle (`Understand → Decide → Govern →
Authorize → Execute → Verify → Learn`) that today only ever touches a Docker
container. This is `docs/RMT_IMPROVEMENT_ROADMAP.md` §5 C2, which is D-1 (AI
Agent Governance Gateway, `docs/RMT_ABOVE_CORE_ROADMAP.md` §6) productized:
the existing CAP-05 governed agent surface, extended with a second execution
target instead of a second copy of the homelab flow.

**Why now:** every other roadmap item is either done or homelab-flavored.
This is the one piece of work that actually tests the "domain-agnostic
control plane" claim in `RMT_MASTER_DEFINITION.md` rather than assuming it.

## 2. What already exists (reused unchanged)

| Piece | Location | Role here |
|---|---|---|
| `AgentIdentity` / `AgentIntent` / `AgentProposal` / `AgentOutcome` | `app/agent/contract.py` | MCR-shaped proposal contract. **`AgentIdentity.operational_context`** already exists for exactly this purpose (default `"homelab"`) but no caller has ever set it to anything else — this proposal is the first thing that uses it. |
| `AuthorityStore` (grant / check / consume) | `app/agent/authority.py` | Scoped, time-limited, single-use grants — target/operation strings, no homelab assumption. Reused as-is. |
| `POST /agent/act`, `GET /agent/status`, `GET /agent/authority` | `app/agent/api.py` | Generic already: `mechanism` is validated only against the shared `ActionType` enum, not a homelab allow-list. |
| `escalate_for_dependency_cascade` | `app/agent/dependency_guard.py` | Generic, string-keyed; an unrecognized target (any git-domain name) is a harmless no-op (`(False, "")`). No change needed. |
| `AdapterRegistry` / `ExecutionAdapter` ABC | `app/core/intelligence/execution/adapters/{registry,base}.py` | Frozen Core interface. Domains register their own adapter into the same registry — this is the intended extension point, not a Core edit. |
| B1a/B1b observer registry + effective-status index | `app/ops/verification/**` | The extension point "feeds B1" in the roadmap text refers to. |
| `ActionType.CREATE` / `ActionType.REMOVE` | `app/core/intelligence/actions/models.py` (frozen) | Already generic enough to mean "create/remove a governed resource" — no new Core enum member needed. |

## 3. What's actually new

### 3a. A real, low-blast-radius non-homelab target: **git tags in a dedicated scratch repository**

Chosen over the alternatives considered:
- **GitHub API (issues/PRs)** — rejected: needs a real token, produces a
  visible external side effect on a real repository other people may see.
  Wrong risk profile for a proof run.
- **Cloud / IaC / k8s** — explicitly Tier-2 items D-2/D-3, out of scope; real
  infra credentials, much larger surface.
- **A second homelab container action** — doesn't prove anything C1 didn't
  already prove.

A git tag is a genuinely consequential, real action (an actual CI/coding
agent proposing a release tag is exactly the AI-Agent-Governance example the
roadmap names), backed by a real local mutation with a real observable
post-condition (`git tag -l`), fully reversible (`git tag -d`), and — critical
for blast radius — it runs against a **dedicated scratch repository created
only for this proof**, not the live `homelab` project repo. `git` is already
present on this host (`shutil.which("git")`, surfaced today as
`runtime_info.git_available` — currently only a health-check flag; this gives
it an actual capability behind it).

**Owner decision needed:** confirm the scratch repo path (proposed:
`data/agent_git_target/`, a fresh `git init` inside this project's `data/`
directory, alongside the existing SQLite evidence stores — never the live
project's `.git`).

### 3b. New — `app/agent/git_adapter.py` (above-Core)

- `GitTagAdapter(ExecutionAdapter)` — `supports()` for `{"create", "remove"}`.
  `execute()` shells out to `git` with a fixed argument list (`["git", "tag",
  name]` / `["git", "tag", "-d", name]`, `cwd=<configured repo path>`, no
  shell interpolation) and returns `ExecutionResult`.
- `register_git_adapter()` — registers `"git"` into the existing
  `adapter_registry` **only if** `RMT_AGENT_GIT_REPO_PATH` is set and resolves
  to a directory containing a `.git`. Unset (default) → not registered, the
  same conditional-registration pattern Docker already uses
  (`bootstrap.py::register_default_adapters`), so the feature is inert unless
  explicitly configured.
- Called once from `app/main.py` `lifespan`, alongside the existing CAP-04/05
  wiring. Not a Core file; the Core's own `adapter_registry` object is a
  public, already-mutable singleton — registering into it from above-Core is
  the same mechanism `register_default_adapters` itself uses, just called
  from a different, above-Core call site.

### 3c. New — `app/ops/verification/git_observers.py` (above-Core)

Mirrors `docker_observers.py` exactly: a read-only `git rev-parse -q --verify
refs/tags/<name>` observer, registered for `("git", "create")` and `("git",
"remove")`. `app/ops/verification/expected.py` gains two table rows:
`("git","create") → "present"`, `("git","remove") → "absent"`. Zero change to
the registry, the frozen verifier, or verification storage — this is the
extension point B1a/B1b already built for exactly this.

### 3d. Modified — `app/agent/contract.py` / `app/agent/adapter.py` / `app/agent/api.py`

The one above-Core change this proof can't avoid: **`propose_and_govern`
(`app/agent/adapter.py`) currently resolves the execution adapter by
unconditionally importing `app.homelab.remediation.resolve_adapter_name`, and
hardcodes the post-execution verification call to `adapter_name="docker"`** —
i.e. every agent proposal today, regardless of target, executes and verifies
through the homelab/Docker path. This is invisible today because nothing has
ever proposed against a non-homelab target.

- `app/agent/api.py` — the `/agent/act` request body gains an optional
  `operational_context` field (default `"homelab"`, preserving every existing
  call byte-for-byte), threaded into the `AgentIdentity` it builds (today it
  is silently dropped).
- `app/agent/adapter.py` — a small dispatch replaces the unconditional
  homelab resolve: `operational_context == "git"` → `"git"` if registered,
  else `"simulation"` (same graceful-degradation shape `resolve_adapter_name`
  itself uses); any other context (including the default) → the existing,
  unmodified `resolve_adapter_name()` call. The verification call's
  `adapter_name` argument changes from the hardcoded `"docker"` to this same
  resolved name, fixing what would otherwise be a wrong observer lookup for
  every non-homelab domain.
- `llm_agent.py` / `reference_agent.py` — **not touched.** Both are
  homelab-specific by construction and neither is needed for this proof; the
  live exercise goes through `/agent/act` directly, exactly as an external
  caller would.

## 4. Explicitly OUT of scope

- No GitHub/remote git operation, no network call, no credential of any kind.
- No new Core `ActionType` member, no Core file touched.
- No change to `llm_agent.py`, `reference_agent.py`, or `dependency_guard.py`
  — all already either domain-agnostic or irrelevant to this proof.
- No autonomous loop for the git domain (no CAP-04-style supervised loop);
  every proposal is one-shot, human-approval-gated.
- No lowering of `AGENT_DEFAULT_REQUIRES_APPROVAL`.
- No fix to `AuthorityStore` being in-memory-only (grants don't survive a
  restart) — a real limitation, called out here rather than silently carried,
  but out of scope: it doesn't block this proof and isn't part of the D-1 DoD.
  Would need revisiting before CAP-06 is offered to a real external team.
- No third domain. One non-homelab target is what the roadmap's "Done when"
  asks for.

## 5. Boundary

- No `app/core/**` change (verified by `git diff --stat` before this is
  called done, same discipline as every prior capability).
- `AGENT_ENABLED` / `AGENT_LLM_ENABLED` semantics unchanged; the git adapter
  has its own independent inert-by-default gate (`RMT_AGENT_GIT_REPO_PATH`
  unset).
- Approval retained on every proposal; the agent never continues its own
  hold (same rule as CAP-04/05).
- The scratch repo is the only git target ever operated on — the adapter
  takes no path from the request, only the pre-configured one.

## 6. Done when (D-1 DoD, `RMT_ABOVE_CORE_ROADMAP.md` §6)

Two distinct external-agent calls against the git domain, both through
`POST /agent/act` (no code path other agents don't have):

1. **Benign agent** — granted `create` on a specific tag name; proposes it;
   held for approval (default); operator approves; executes via the `git`
   adapter; above-Core observer confirms `present`; Learn recorded.
2. **Over-reaching agent** — attempts an operation/target outside its grant
   (e.g. `remove` on a tag it was only granted `create` on, or any tag
   without a grant at all) → refused at the authority check, **never reaches
   the governed boundary** (`decision: no_authority`).

Evidence bundle (approval / authorization / trace / audit / verification /
Learn ids, correlated by `execution_id`) recorded in
`docs/RMT_CAPABILITIES_EVIDENCE.md`, same format as every prior capability.
Full backend suite green; no `app/core/**` diff.

## 7. Tests — `app/agent/testing/test_git_domain.py` (new, run-safe)

- `GitTagAdapter.supports()` / `.execute()` against a `tmp_path` git repo
  fixture (real `git`, disposable directory — no network, nothing persistent).
- `register_git_adapter()` no-ops when `RMT_AGENT_GIT_REPO_PATH` is unset
  (default-inert, mirrors `test_loop_disabled_by_default` /
  `test_agent_disabled_by_default` style checks elsewhere).
- `propose_and_govern` resolves `"git"` when `operational_context="git"` and
  the adapter is registered, `"simulation"` when it isn't, and is
  byte-identical to today for the default `"homelab"` context (regression
  guard on the one behavior change).
- Full proposal→hold→approve→execute→verify flow against the git domain with
  an isolated hold/auth/trace/audit/verification store setup (same isolation
  pattern as `test_remediation.py::_setup_isolation`), asserting
  `verified_success`.
- Grant-scope refusal: an unrelated/ungranted proposal against the git domain
  returns `decision: no_authority` before any adapter call.
- `app/ops/verification/testing/test_git_observers.py` — registry pair
  presence, `present`/`absent` observation against a real disposable tag.

## 8. Validation plan

- New focused tests pass; full backend suite (currently 459) grows and stays
  green.
- `ruff` (F, E9) clean; `import app.main` clean.
- `git diff --stat` confined to `app/agent/**`, `app/ops/verification/**`,
  `app/main.py`, `docs/**` — no `app/core/**`.
- Live exercise (owner-authorized, mirrors the C1 `:8001`-isolated-instance
  discipline): the two-agent proof above, run against the real (scratch-repo)
  git target, evidence bundle recorded.

## 9. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Scratch repo accidentally pointed at the live project | Path is explicit config, never request-supplied; recommended default lives under this project's own `data/` dir, distinct from the project's `.git` |
| Core has an undiscovered Docker-specific assumption in policy/risk | This is exactly what the proof is *for* — if it surfaces, it becomes a `RMT_FROZEN_CORE_DEBT.md` row (accept-and-record), never a Core edit |
| `operational_context` change breaks existing agent tests | Default value unchanged (`"homelab"`); regression test asserts byte-identical resolution for the default path |
| In-memory `AuthorityStore` loses grants on restart | Documented, out of scope (§4); acceptable for a proof, revisit before any real external team is onboarded |
| Shell-out to `git` | Fixed argument lists only, no shell string interpolation, `cwd` pinned to configured path, no request-supplied paths |

## 10. Decisions for the owner — APPROVED 2026-09-11

1. **Adapter choice** — **APPROVED**: git tag create/remove in a dedicated
   scratch repo (§3a).
2. **Scratch repo location** — **APPROVED**: `data/agent_git_target/`.
3. **Scope** — **APPROVED**: this proposal is D-1's DoD only (two-agent proof
   + new adapter/observer). The fuller D-1 list (multi-agent authority model
   beyond what CAP-05 already has, per-agent-class policy, a stable versioned
   external API) is deferred to a later, separate decision — same pattern as
   CAP-05's 5A/5B split.
