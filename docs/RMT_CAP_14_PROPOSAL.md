# RMT-CAP-14 — Homelab Remediation Policy as Configuration (roadmap P-A, slice 1) — Proposal

**Status:** **APPROVED 2026-11-21 (owner).** Open decisions settled the same
session with the recommended options: D1 refuse to start on an invalid file,
D2 TOML, D3 the file replaces the built-in policy, D4 an empty policy is
allowed with a warning. D5 (a later coding-agent-rules slice) is not part of
this approval. Implementation proceeds against the scope below; isolated
exercise, commit-to-push, deployment and restart each remain subject to
separate owner authorization, as for CAP-04 .. CAP-13.

**Number:** **RMT-CAP-14** (owner, 2026-11-21).

**Classification:** Above-Core / product surface (roadmap `P-A`,
`docs/RMT_ABOVE_CORE_ROADMAP.md` §"P-A"). **No C08. No frozen Core change. No
reopening of C01–C07.** Confined to `app/homelab/**`, one read-only status
field, and a new stdlib-only checker script. The governed mutation path
(`execute_governed_action`, approval, authorization, verification) is unchanged.

---

## 1. Objective

Let an operator change *what the CAP-04 operational loop is allowed to
remediate, when, and how* by editing a validated configuration file and
restarting, with no code edit, while making it **impossible to load a policy
that leaves the CAP-04 safe envelope** (`docs/RMT_T13_DISPOSITION.md`): every
entry independent, every entry approval-gated.

Today the policy is a Python literal (`REMEDIATION_POLICY` in
`app/homelab/remediation.py`, two entries: `uptime-kuma`, `portainer`). The
envelope is enforced only by a unit test
(`test_remediation_policy_within_cap04_safe_envelope`), which protects code
edits but would not protect a config file. This slice moves the *values* to
config and moves the *envelope* from a test into the loader.

## 2. Why this slice, and why only this slice

The roadmap names three policy surfaces for P-A. A survey of the code on
2026-11-21 shows only one is still code-only and above Core:

| Surface | Where it lives | Status |
|---|---|---|
| Homelab remediation policy | `app/homelab/remediation.py::REMEDIATION_POLICY` | **Code-only, above Core → this proposal** |
| Dependency map | `app/homelab/dependencies.py` + `RMT_HOMELAB_DEPENDENCIES` | Already operator-configurable without code (T1-2) |
| Loop thresholds (cadence, flap window, cooldown, streak) | `app/homelab/loop_config.py`, `RMT_HOMELAB_LOOP_*` | Already env-configurable (CAP-04) |
| Approval / risk / execution policy | `app/core/intelligence/actions/{policy,approval_policy}.py`, `execution/policy.py` | **Frozen Core — out of scope, not admissible** |
| Coding-agent risk rules | `app/coding_agent/risk_rules.py::RULES` | Code-only; candidate for a later slice (§9) |

This also answers the 2026-09-20 concern that P-A "touches the live CAP-04
remediation-policy decision path and carries scope-creep risk across three
policy surfaces": the slice is one surface, and the decision *logic*
(`build_remediation_action`, the loop's cycle) does not change — only the
source of the dict it reads.

## 3. Design (in scope)

### 3a. Config file and how it is found

- Format: **TOML**, parsed with stdlib `tomllib` (Python 3.11+; no new
  dependency). Comments allowed, which matters for a file an operator edits.
- Location: `RMT_HOMELAB_REMEDIATION_POLICY_FILE` (absolute path). Live path
  `/etc/rmt-platform/remediation_policy.toml`, root-owned, mode `0644` (not
  secret), set by a new drop-in `cap14-policy.conf`. *Implementation
  correction 2026-11-21:* the draft named `/etc/rmt-control-center/`, but that
  directory is root-only (`0700`) secrets storage and the service runs as
  `rmt-lab`, which cannot read it.
- **Unset ⇒ the built-in policy, byte-for-byte today's behavior.** The
  built-in dict stays in `remediation.py` as the default and as the reference
  the existing tests use.
- The file **replaces** the built-in policy; it is not merged (one source of
  truth per run; see open decision D3).

Example (equivalent to today's built-in policy):

```toml
# RMT homelab remediation policy -- loaded once at startup.
# Every entry MUST keep requires_approval = true (CAP-04 safe envelope).

[components.uptime-kuma]
action = "restart"
remediate_on = ["critical"]
expected_state = "running"
requires_approval = true

[components.portainer]
action = "restart"
remediate_on = ["critical"]
expected_state = "running"
requires_approval = true
```

### 3b. Loader and validation (fail-closed)

New `app/homelab/policy_config.py` loads the file once at startup and returns a
dict in exactly the shape `REMEDIATION_POLICY` has today
(`action_type: ActionType`, `remediate_on: set[HealthStatus]`,
`expected_state: str`, `requires_approval: bool`), so every consumer
(`build_remediation_action`, the operational loop, loop status) is untouched.

A file is rejected unless **every** rule below holds; the error names the
component and the rule:

1. **Envelope — approval:** `requires_approval` is present and `true`.
   (Absent is rejected, not defaulted, so the file states it explicitly.)
2. **Envelope — independence:** the component has no dependency edge in
   either direction in the resolved dependency map (static ∪
   `RMT_HOMELAB_DEPENDENCIES`), and the entry declares no
   `depends_on`/`dependencies` key.
3. **Known component:** the component has a registered `ComponentContext`
   (read-only lookup in the Core context registry), so verification and Learn
   attribution can work for it.
4. **Action allow-list:** `action` ∈ {`restart`} in this slice — the only
   operation the current policy, the Docker adapter path and the above-Core
   verification are proven on. Widening it is a separate decision.
5. **Trigger states:** `remediate_on` is a non-empty subset of {`warning`,
   `critical`}. `healthy` and `unknown` are rejected (never act on a healthy
   or unobserved component).
6. **Expected state:** `expected_state` is a non-empty string.
7. **No unknown keys** at any level (catches typos such as
   `requires_aproval`, which would otherwise be silently ignored).
8. The file parses as TOML and has a `[components]` table.

On rejection the backend **refuses to start** and logs the reasons (open
decision D1). This is loud by design: a policy the operator believes is in
force but is not is worse than a down console. §3d keeps that from being a
surprise.

### 3c. Observability

- One structured startup log event `homelab_remediation_policy_loaded`:
  `source` (`builtin` | `file`), `path`, `sha256` of the file bytes,
  component list.
- `GET /homelab/loop/status` gains a read-only `policy_source` object with the
  same fields (it already returns `policy_components`). No new route.

The governed evidence chain does **not** gain a policy-version field: the
`ActionRequest` model is frozen Core. The startup log + status hash is the
record of which policy was in force. (Recorded limitation, §6.)

### 3d. Offline checker

`backend/scripts/rmt-policy-check.py <file>` runs the same validator without
starting the service and exits 0/1 with the same messages. The install
instructions in `cap14-policy.conf` say to run it before every restart, the
same pattern as `rmt-attestation-verify.py`.

## 4. Explicitly OUT of scope

- No change to `app/core/**`; no change to approval, risk, authorization,
  execution or verification behavior.
- No hot-reload; changes take effect on restart only.
- No API or UI to edit policy. Policy changes are a privileged host action
  (root-owned file + restart), same trust level as the systemd drop-ins.
- No change to the dependency map mechanism (T1-2) or the loop thresholds.
- No new remediation operation (`restart` only).
- Coding-agent risk rules (a later slice, §9).
- No change to the CAP-05 agent path: agent proposals are governed by 5A
  authority + governance, not by `REMEDIATION_POLICY`.

## 5. Boundary

- New: `app/homelab/policy_config.py`, `backend/scripts/rmt-policy-check.py`,
  `deploy/systemd/cap14-policy.conf`, an example
  `deploy/remediation_policy.example.toml`, tests.
- Changed: `app/homelab/remediation.py` (policy comes from the loader; the
  built-in dict stays as default), `app/homelab/operational_loop.py` (adds
  `policy_source` to status), docs (`docs/operations/CONFIG.md`,
  `deploy/systemd/README.md`, capability evidence, RMT_CONTEXT/HANDOFF).
- `app/main.py`: loading happens at import of `app.homelab.remediation`,
  which `main.py` already imports at startup. *Implementation correction
  2026-11-21:* the draft expected no `main.py` change, but the policy resolves
  before the lifespan's `configure_logging()`, so the INFO `loaded` event was
  dropped live. The lifespan now calls `log_policy_in_force()` right after
  logging is configured (7 lines). Rejections need no change: the traceback
  reaches stderr/journald and startup stops.
- Zero `app/core/**` diff, verified with `git diff --stat -- app/core`.

## 6. Risks and recorded limitations

- **A valid policy can still widen what the loop does** (for example adding
  `dozzle`, or remediating on `warning`). That is the point of the slice; the
  safety comes from the envelope (every action still holds for a human) and
  from the file being root-owned.
- **Bad file ⇒ backend down** under D1's recommended option. Mitigated by the
  offline checker and by `Restart=always` making the failure visible
  immediately in `systemctl status`.
- **No per-action policy version in the evidence chain** (frozen `ActionRequest`);
  the startup log + status hash is the record.
- The envelope test stays and keeps covering the built-in policy; the loader
  rules cover files.

## 7. Done when (Definition of Done)

1. With `RMT_HOMELAB_REMEDIATION_POLICY_FILE` unset, behavior and loop status
   are identical to today (apart from the new `policy_source: builtin` field);
   the full suite passes unchanged.
2. A file equivalent to the built-in policy loads, and the loop behaves
   identically.
3. An operator adds a component (e.g. `dozzle`) or changes a trigger via the
   file + restart, with no code edit, and loop status shows it with
   `source: file` and the file's hash.
4. Each rule in §3b has a rejecting test; a rejected file prevents startup and
   the reason is logged; the checker reports the same reasons.
5. Zero `app/core/**` diff; ruff, import smoke, full suite and `git diff
   --check` clean.

## 8. Tests and validation plan

**Tests** (`app/homelab/testing/test_policy_config.py`): unset ⇒ built-in;
equivalent file ⇒ same dict; one rejecting test per §3b rule (approval false,
approval absent, dependency edge via env, unknown component, `stop` action,
`healthy`/`unknown`/empty trigger, empty expected state, unknown key, bad TOML,
missing table); `policy_source` in loop status; checker exit codes. Existing
loop/remediation tests keep passing unmodified.

**Isolated exercise** (owner-authorized, the CAP-04/09/11/13 pattern): a
separate instance on a spare port with scratch DB copies and
`RMT_RUNTIME_ENGINE=simulation`; (a) a file adding `dozzle` ⇒ status shows it;
(b) a file with `requires_approval = false` ⇒ refuses to start with the
envelope message. Live `:8000` untouched.

**Live deployment** (separate authorization): install an equivalent-to-built-in
file + drop-in, check it with the checker, restart, confirm `source: file` and
unchanged behavior.

## 9. Decisions (settled 2026-11-21 unless noted)

- **D1 — invalid file at startup:** refuse to start (**recommended**,
  fail-closed) vs log an error and fall back to the built-in policy.
- **D2 — format:** TOML (**recommended**: stdlib, comments) vs JSON.
- **D3 — replace vs merge:** the file replaces the built-in policy
  (**recommended**: one source of truth) vs merges over it.
- **D4 — empty policy:** allow a file with zero components, meaning the loop
  observes but never remediates (**recommended**: allow, with a warning) vs
  reject.
- **D5 — later slice:** whether coding-agent risk rules
  (`app/coding_agent/risk_rules.py`) become the next P-A slice, under the same
  pattern. Not part of this approval.
