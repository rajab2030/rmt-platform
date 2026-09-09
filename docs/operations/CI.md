# RMT — CI Gate

RMT-PROD **V2**, hardened in **T0-4**. Above-Core / tooling.

The gate is one script — `projects/homelab-control-center/backend/scripts/ci.sh`
— run three ways, all identical:

| Where | Command | When |
|---|---|---|
| GitHub Actions | `.github/workflows/ci.yml` → `scripts/ci.sh` | every push (any branch) + PRs to `main`/`master` |
| Pre-push hook | `.githooks/pre-push` → `scripts/ci.sh --fast` | every `git push` (once you opt in — below) |
| By hand | `scripts/ci.sh` (clean) or `scripts/ci.sh --fast` (reuse `.venv`) | anytime |

## What it runs

1. **Reproducible install** — a throwaway venv built strictly from
   `requirements.lock.txt` (`--fast` reuses `backend/.venv` and skips this).
2. **Lint** — `ruff` errors-only (`ruff.toml`: `select F, E9`; `app/core`
   excluded). `ruff==0.14.2` is pinned in `ci.sh`, deliberately *not* in the
   lockfile (CI tooling, not a runtime dep).
3. **Import smoke** — `python -c "import app.main"`. Catches an import-time
   break the suite might mask.
4. **Full backend suite** — `pytest -q` over `app/` (includes the 122
   frozen-Core tests).

Exit `0` → **green = safe to merge / build on / deploy from**. Non-zero → the
last step printed is the failure; do **not** build on that commit — fix it or
revert first.

## Suite-time budget

~**7 minutes** (405 s). This is almost entirely *real-time waits*, not compute:
`app/homelab/testing/test_operational_loop.py` exercises the CAP-04 loop at its
real cadence, and several approval tests wait out the 300 s-scaled hold TTLs.
The GitHub job `timeout-minutes` is 20 (≈1 min build + ≈7 min suite + slack).
Do not "optimise" by mocking the loop cadence — the point is that the governed
timing behaviour is exercised.

## Opt in to the pre-push hook

```bash
git config core.hooksPath .githooks
```

Then every `git push` runs `ci.sh --fast` first and **refuses the push if it is
red**. A clone with no `backend/.venv` is not blocked (it prints how to make
one). Bypass a single push with `git push --no-verify`.

## Reading a failed Actions run

```bash
gh run list --limit 5
gh run view <run-id> --log-failed
```

The workflow uses a `concurrency` group per ref with `cancel-in-progress`, so a
rapid second push cancels the first run.

## Known follow-up — enforced "blocks on red"

GitHub branch protection (a *required* status check, and/or required PRs on
`master`) needs **GitHub Pro or a public repo** — unavailable on this free
private repo (`gh api …/branches/master/protection` → 403). Until the repo goes
Pro or public, the Actions run is the authoritative **visible** check and the
pre-push hook is the local enforcement. When that changes: add a branch
protection rule on `master` requiring the `CI` check.
