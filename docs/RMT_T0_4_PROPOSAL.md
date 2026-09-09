# RMT — T0-4: CI gate — finish & harden — Proposal

**Status:** APPROVED 2026-09-09 — **Option A** (tracked pre-push hook +
`docs/operations/CI.md`; GitHub workflow stays the authoritative visible check;
branch protection is a follow-up for if/when the repo goes Pro or public).
Implementation proceeds per §3.
**Implementation deviation (2026-09-09):** §3's `on.push.branches: ['**']` was
tried (`4b5d549`) and reverted (`df3d36c`) — GitHub silently stopped triggering
the workflow (no run / check-suite; `actionlint` clean). Trigger stays
`[main, master]`; everything else in §3 shipped.
**Classification:** tooling / CI only. No `app/core/**`, no `app/**` runtime
change. No C08.

Governing refs: `docs/RMT_ABOVE_CORE_ROADMAP.md` §5 (T0-4), `AGENTS.md` §13,
`docs/RMT_PRODUCTION_READINESS.md` (V1 / V2).

---

## 0. Recon findings (verified against the repo + the live GitHub repo, 2026-09-09)

| # | Finding |
|---|---|
| R1 | **V1 + V2 are DONE and live.** `backend/scripts/ci.sh` (throwaway venv from `requirements.lock.txt` → errors-only `ruff` → full `pytest`) and `.github/workflows/ci.yml` calling it. It has run **green on every push since the repo went to GitHub** (`8b1d7d6` era locally; runs `343330…`, `343350…`, `343392…`, `343438…`). `pytest==9.1.1` + all test deps are in `requirements.lock.txt`; `ruff==0.14.2` is pinned in `ci.sh` (deliberately not in the lockfile). |
| R2 | **Nothing *enforces* the gate.** `ci.yml` triggers on `push` + `pull_request` to `main`/`master`, but there is **no branch protection** and `gh api …/branches/master/protection` returns **403 — "Upgrade to GitHub Pro or make this repository public"**. On the free plan a **private** repo cannot mark a status check "required". So today the gate is *visible* (red/green on every push) but a red push still lands on `master`. |
| R3 | **Workflow gaps vs the T0-4 DoD.** No explicit `import app.main` smoke step (only transitive, via the TestClient tests); no `concurrency` group (rapid pushes run stale jobs to completion — ~8 min each); `push` is filtered to `main`/`master` only, so a future feature branch gets no CI until a PR exists; actions are pinned by tag (`@v4`/`@v5`), not SHA. |
| R4 | **DoD wording is stale.** "the 4.5-minute suite budget is documented" — the suite is **~6:45** (405 s), dominated by `test_operational_loop` cadence sleeps and approval-hold-TTL waits. Not documented anywhere durable; there is no "green = mergeable" gate doc. |
| R5 | No `.githooks` dir and `core.hooksPath` is unset — a repo-tracked pre-push hook is available if we want local enforcement. |

---

## 1. Remaining scope vs the DoD

| DoD clause | State | This proposal |
|---|---|---|
| CI runs on a branch | ✅ (push + PR) | widen `push` to all branches |
| **blocks on red** | ❌ — no branch protection possible on a free private repo | **owner decision — §2** |
| suite-time budget documented | ❌ | new `docs/operations/CI.md` + `ci.sh` header |
| "green = mergeable" gate documented | ❌ | `docs/operations/CI.md` |
| workflow: suite + lockfile build + `import app.main` | suite ✅ / lockfile ✅ / import ⚠️ transitive | explicit smoke step in `ci.sh` |

---

## 2. The enforcement decision (owner call)

"Blocks on red" needs a *required status check*, which GitHub gates behind Pro
(or a public repo). Pick one:

- **A — repo-tracked pre-push hook + doc** (recommended for a solo/direct-to-master
  flow). Add `backend/scripts/ci-prepush.sh` + a tracked `.githooks/pre-push`
  that runs `ci.sh --fast` and **refuses the push on red**; `git config
  core.hooksPath .githooks` is a one-line opt-in per clone (documented, and set
  in this working copy now). Local, bypassable with `--no-verify`, but it makes
  "don't push red" the default. The GitHub workflow stays as the authoritative
  visible check.
- **B — advisory only + doc.** No hook. `docs/operations/CI.md` states the rule
  ("a red `CI` run = do not build on it; fix or revert first") and branch
  protection is listed as a follow-up for *if* the repo goes Pro or public.
  Lowest friction, zero enforcement.
- **C — make the repo public** to unlock free branch protection, then add a
  required-check + (optionally) required-PR rule on `master`. Not a CI decision —
  it exposes the whole homelab-control codebase. Out of scope for T0-4 unless the
  owner wants it.

**This proposal assumes A.** B is a one-line reduction of it; C is a separate
call.

---

## 3. Concrete changes (Option A)

- **`backend/scripts/ci.sh`** — add a step, after install, before the suite:
  `PYTHONPATH=. "$PY" -c "import app.main"` (fails fast on an import-time break
  the suite might mask). Update the header comment: 3 steps → 4; note the
  **~7-minute** suite budget and why.
- **`.github/workflows/ci.yml`** —
  - `on.push.branches: ['**']` (every branch gets CI on push; PR trigger
    unchanged);
  - a `concurrency:` group keyed on the ref, `cancel-in-progress: true`;
  - pin `actions/checkout` and `actions/setup-python` to commit SHAs (comment
    with the version);
  - `timeout-minutes: 20` unchanged (build ~1 min + suite ~7 min).
- **`.githooks/pre-push`** (new, tracked, executable) — runs
  `projects/homelab-control-center/backend/scripts/ci.sh --fast`; non-zero →
  print "CI gate red — push refused (override: git push --no-verify)" and exit 1.
- **This working copy** — `git config core.hooksPath .githooks` (local only;
  documented for other clones).
- **`docs/operations/CI.md`** (new) — the gate: what `ci.sh` runs, "green =
  mergeable / safe to build on", the ~7-min budget and its cause, the pre-push
  hook opt-in, how to read a failed Actions run (`gh run view --log-failed`),
  and branch-protection-when-Pro/public as a known follow-up.
- **Doc ticks** — `RMT_ABOVE_CORE_ROADMAP.md` §5/§9/§10 (T0-4 done, DoD wording
  corrected), `RMT_PRODUCTION_READINESS.md` (V2 note), `HANDOFF.md`.

---

## 4. Validation

- `ci.sh` locally (throwaway venv) — green, and the new `import app.main` step
  visibly runs.
- `bash -n` the hook + `ci-prepush` path; a deliberate red (temporarily break a
  test) → `git push` refused by the hook, `--no-verify` bypasses; revert.
- Push the real change → the GitHub `CI` run is green; confirm the
  `concurrency` cancel works by pushing twice quickly.
- Diff review: `.github/`, `backend/scripts/`, `.githooks/`, `docs/` only.

---

## 5. Non-goals

- Frontend CI (its own `oxlint`; a separate item if wanted).
- pip/venv caching — V2's whole point is a *clean* lockfile build; caching would
  undermine the reproducibility check.
- A matrix (Python versions / OS) — the platform targets one runtime (3.12).
- Making the repo public / paying for Pro — owner's call, tracked as a follow-up.
- Deploy/release automation — not part of T0-4.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01P5af6Eq9D3zWrztvPegANU
