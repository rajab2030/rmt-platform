# Agent Governance Gateway: recorded local walkthrough

Captured on 2026-09-18 using application and showcase source at
`b914ee160940870aead96c20a8193fbdd598ec29`.

The [README animation](agent-governance-demo.gif) presents excerpts from a
real local run, paced for readability. It is not a continuous screen recording
or a timing benchmark. Response fields are copied from the captured output;
headings and `CHECK` lines explain the scenario and independently checked Git
state. Approval inputs were automated for this recording.

[Full transcript](agent-governance-demo.txt) ·
[Original terminal capture (asciicast v2)](agent-governance-demo.cast) ·
[Validation and audit records](agent-governance-demo.json) ·
[Static image](agent-governance-demo.png)

## Observed outcomes

| Step | Backend response | Independently checked state |
| --- | --- | --- |
| Preview create | `preview`, medium risk, manual approval | No execution requested |
| Propose create | `hold`, `execution_id: None`, `verification_status: None` | Tag absent before approval |
| Approve create | `executed`, `success: True`, `verified_success` | Tag present at the subsequent removal hold |
| Reuse the earlier grant | `no_authority`, `grant_consumed` | No third execution audit record |
| Propose removal with a new grant | `hold` | Tag still present before approval |
| Approve removal | `executed`, `success: True`, `verified_success` | Tag absent afterward |

The isolated evidence database contains two completed execution audit records,
both using the real `git` adapter. An unauthenticated request to `/agent/status`
returned HTTP 401. The showcase process exited successfully. The backend was
stopped after capture.

## Setup used for this recording

The existing [showcase client](../../tools/rmt-showcase-agent/rmt_showcase.py)
ran unchanged against a separate Uvicorn process on a temporary loopback port.
Its backend `app/` and `config/` directories were copied to a temporary workspace;
the installed backend Python environment supplied its dependencies. A separate
scratch Git repository contained one initial commit and no tags.

| Setting | Value or purpose |
| --- | --- |
| `RMT_AUTH_ENABLED` | `true` |
| `RMT_OPERATOR_TOKENS` | One generated, temporary token for `demo-operator`; excluded from these assets |
| `RMT_AGENT_ENABLED` | `true` |
| `RMT_AGENT_DEFAULT_REQUIRES_APPROVAL` | `true`; both create and remove were held |
| `RMT_AGENT_GIT_REPO_PATH` | Disposable scratch repository |
| `RMT_AUTH_SEPARATION` | `false`; this example uses one operator identity |
| `RMT_RUNTIME_ENGINE` | `git` |
| `RMT_HOMELAB_LOOP_ENABLED` | `false` |
| `RMT_AGENT_LLM_ENABLED` | `false` |
| `RMT_CODING_AGENT_ENABLED` | `false` |
| `RMT_EVIDENCE_DB`, `RMT_BUDGET_DB` | Separate files in the temporary workspace |
| Observability database | Relative to the copied backend working directory |
| `DOCKER_HOST` | A nonexistent socket in the temporary workspace, excluding live Docker access |
| `RMT_SHOWCASE_TAG` | `rmt-demo-tag` |

The child processes used an explicit environment rather than inheriting live
RMT credentials or service configuration. The recorder ran the client in a
pseudo-terminal, checked Git state at each approval prompt, waited one second,
and sent Enter. No LLM generated the proposals, and no production service or
repository was a mutation target.

To try the same workflow, follow the
[showcase prerequisites and run instructions](../../tools/rmt-showcase-agent/README.md)
using a disposable local backend and scratch Git repository. For the behavior
recorded here, retain `RMT_AGENT_DEFAULT_REQUIRES_APPROVAL=true`; the create
proposal will wait for approval too. Use an interactive terminal and inspect
each proposal before pressing Enter. Exact IDs, timestamps, ports, and decisions
can differ with configuration.

## What this recording does not establish

- The approval inputs came from the recorder, not an independent human. The
  client uses the same operator token to grant authority, propose, and approve.
  The source transcript's narration about a human and self-approval must not be
  read as proof of separate approver identities.
- The client currently proceeds with approval after an `EOFError` at its prompt.
  This run sent explicit input through a pseudo-terminal and did not use EOF.
- This is a sequential walkthrough. It does not test concurrent approvals or
  establish exactly-once execution. The earlier security review reported a
  concurrent-approval race and invalid authentication-setting behavior; this
  documentation change does not remediate those findings.
- This run verifies Git-tag creation and removal. It does not establish that
  every domain or route can verify every outcome. An unavailable observation is
  not verified success.
- The refused reuse combines a consumed grant with an operation change. Its
  actual reason was `grant_consumed`; it is not an isolated scope-mismatch test.
  A pre-governance refusal is not a new governed execution receipt.

The 24-second animation uses six four-second scenes.
The full terminal capture retains the original elapsed output timestamps. The
static image and text transcript provide alternatives to the looping animation.
