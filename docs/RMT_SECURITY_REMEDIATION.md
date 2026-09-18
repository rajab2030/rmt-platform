# RMT security remediation — 2026-09-18

**Scope:** owner-requested remediation of the repository review, based on
`d66c9ce`. Above-Core application, operational configuration, tooling, and
dependency changes only. **No `app/core/**` changes.**

**Status:** repository fixes committed and published as `5466deb`. Backend and
Dozzle deployment verified on 2026-09-18 after the owner completed the privileged
unit installation and restart. The supported single-process deployment has the
reviewed mitigations; the residual limits below remain explicit.

The [Master Definition](RMT_MASTER_DEFINITION.md) and
[frozen-Core rules](RMT_FROZEN_CORE_DEBT.md) prohibit reopening Core and allow
above-Core compensating controls. This work adds no governance authority,
domain capability, persistence subsystem, or adapter bypass.

## Findings and disposition

| Finding | Repository change | Remaining condition |
| --- | --- | --- |
| Concurrent approvals execute one hold twice | Shared lock around `/approve` and `/homelab/approve`; unit and override explicitly select one worker; deployment verified | **Mitigated**, not repaired inside Core. One backend process only; direct concurrent Core callers are unsupported. |
| Invalid `RMT_AUTH_ENABLED` disables auth | Strict boolean parsing: blank/unknown values refuse startup; invalid values encountered at request time return 503; backend deployed | Explicit local-development false remains supported. |
| Dozzle logs exposed on an unauthenticated LAN port | Bind published port to `127.0.0.1:8888`; recreated and verified live | Local access is still trusted; Docker socket privilege remains. |
| Destructive command spellings bypass review | Match Git force-push with global options and recursive deletion with split/long options; remove the `/tmp` prefix exemption | A pattern-based review helper is not a shell sandbox. The hook's separately accepted outage/timeout fail-open policy is unchanged. |
| Vulnerable frontend build dependencies | Lock nanoid 3.3.19 and PostCSS 8.5.28; installed versions, audit, build, and lint verified | Use the updated lockfile in other build environments. |
| Restore filename becomes shell code | Pass filename as a positional argument to fixed shell code; mount backup source read-only; reject path/volume misuse; list archive before deleting | Operator must trust archive contents and the restore target. No production restore was performed. |
| Base backend unit exposes plaintext API on all interfaces | Base unit binds `127.0.0.1`, matching its override; installed files and actual listener verified | Preserve loopback binding in future deployments. |
| Showcase approves when stdin closes | EOF aborts the client without making an approval request | Explicit Enter remains the operator walkthrough action, not proof of independent approver identities. |

Advisories:
[nanoid GHSA-2v37-7h3g-55p8](https://github.com/advisories/GHSA-2v37-7h3g-55p8),
[PostCSS GHSA-fxqj-rqcc-2cmp](https://github.com/advisories/GHSA-fxqj-rqcc-2cmp).

## Approval boundary and its limits

The affected Core function checks `pending` before separately updating hold
status. The initial reproduction synchronized two threads between those steps
and observed two authorizations and two mock-adapter executions for one hold.

Both production HTTP continuation handlers now share a single process-local
lock. It surrounds the existing continuation, including rejection, without
changing its decision, identity, instruction binding, authorization creation,
or execution result. The second resolver sees Core's already-resolved result.
The existing routing layer owns this scheduling concern; no new subsystem is
needed. The cost is serializing even unrelated approval continuations until the
first returns, acceptable only within the existing low-volume, single-process
deployment scope.

Direct Core calls still have the original race. Separate backend processes do
not share this lock or their in-memory evidence views. Do not add workers,
replicas, alternate continuation entrypoints, or concurrent direct callers
without a compatible above-Core admission decision and validation. The existing
restart/reconcile limitation (D1) remains. This is not a general exactly-once
guarantee. The gap and disposition are recorded as
[D6](RMT_FROZEN_CORE_DEBT.md#d6--concurrent-manual-approval-continuation-is-not-atomic-in-core).

## Validation evidence

- Backend: **639 passed, 3 live-Docker tests deselected**, using
  `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider -m 'not e2e'`.
- Ruff: all checks passed. Changed Python files compiled without writing
  bytecode into the repository.
- The new concurrency suite invokes the real production handlers with actual
  threads, isolated evidence stores, and a mock adapter. It covers all four
  combinations of the two routes with approve/approve, approve/reject, and
  reject/approve; rejects invoke no adapter. This avoids the suite's synchronous
  ASGI test harness masking concurrency. Exception handling releases the lock.
- Auth tests cover invalid configuration at startup and on a running route,
  proving invalid settings cannot reach the governed action function. Explicit
  development opt-outs remain supported; existing 401 and identity tests pass.
- Classifier tests cover each reported bypass and confirm that the HTTP API
  creates holds. Commands are classified, not executed.
- Restore tests execute the real shell script with fake Docker/tar/rm commands.
  Shell metacharacters remain filename data; invalid archives never reach
  deletion; invalid paths/volumes never call Docker. No live volumes are used.
- Showcase tests prove EOF makes no HTTP approval call and explicit input still
  submits the intended request.
- `bash -n scripts/restore-volume.sh`, `docker compose -f
  docker/stacks/dozzle/docker-compose.yml config --quiet`, and `systemd-analyze
  verify` for the base unit passed. These validate files, not live deployment.
- Frontend: `npm run build` and `npm run lint` passed. `npm ls nanoid postcss`
  confirms installed nanoid 3.3.19 and PostCSS 8.5.28. `npm audit
  --package-lock-only --ignore-scripts --json` reports **zero known
  vulnerabilities** across the lockfile's 79 dependencies on this review date.
- Final diff inspection and `git diff --check` passed; changes remain limited
  to the above-Core fixes, regression tests, operational defaults, lockfile,
  and remediation documentation.

## Deployment and closure checklist

Deployment evidence from the authorized rollout:

- `5466deb` pushed to `origin/master`; the pre-push gate passed **642 tests**,
  including the three Docker tests excluded from the earlier isolated run.
- Dozzle alone was recreated with `--no-deps --pull never`. Docker inspection
  confirms `HostIp=127.0.0.1`, `HostPort=8888`; local HTTP returns 200.
- The initial backend installation required host sudo authentication. The owner
  completed installation and restart; subsequent verification confirms both
  installed unit files match the repository byte-for-byte. The backend started
  at **2026-09-18 10:47:07 UTC**, PID **22396**, active with zero automatic
  restarts and `--host 127.0.0.1 --port 8000 --workers 1`.
- Process inspection found one matching backend process. Socket inspection
  confirms ports 8000 and 8888 listen only on `127.0.0.1`.
- Post-restart smoke checks pass: health status `ok`, Docker adapter ready,
  metrics up with zero scrape errors, loop running, and unauthenticated
  `/execute` and `/agent/status` requests return 401. Both `/approve` and
  `/homelab/approve` also return 401 for unauthenticated requests using a
  nonexistent hold identifier. No real action was approved or rejected.
- Prior unit and loopback override copies are saved on the deployment host at
  `/tmp/rmt-security-deploy.bwMsry/`. Existing unrelated overrides were preserved.
- The rebuilt frontend toolchain is verified locally. The served static release
  remains unchanged; the dependency findings concern build tools.

Deployment checklist for subsequent installations (the backend and Dozzle steps
above are complete on this host):

1. Review the diff and retain exactly one backend process. Install the updated
   base service and `bind-loopback.conf` from
   `projects/homelab-control-center/deploy/systemd/`; reload systemd and restart
   the backend under the normal watched deployment procedure.
2. Verify the effective command includes `--host 127.0.0.1 --workers 1`, the
   backend answers health checks, and unauthenticated mutation requests return
   401. Never test destructive concurrency against production targets.
3. Recreate **only Dozzle** from `docker/stacks/dozzle/docker-compose.yml`.
   Confirm its port is published only on loopback. For remote access use an SSH
   tunnel, for example `ssh -N -L 18888:127.0.0.1:8888 user@host`, then open
   `http://127.0.0.1:18888`. No public or LAN plaintext log endpoint should remain.
4. Use the updated frontend lockfile for future builds. These advisories affect
   build dependencies; a backend restart alone does not update a build toolchain.
5. Distribute the corrected restore/showcase scripts to any operational copies.
6. Record actual deployment evidence and update this status. Do not mark the
   security review closed merely because repository tests pass.

No running container image vulnerability scan, comprehensive shell confinement,
host hardening reassessment, or public-network penetration test was performed.
The existing accepted coding-hook fail-open behavior, trusted-operator model,
and frozen-Core residual risks remain explicit limits.
