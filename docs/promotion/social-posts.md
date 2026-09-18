# RMT launch copy

Written on 2026-09-18. These are finished drafts, not evidence that a social
post has been published. Confirm the connected destination and its current
rules before posting. The project article is published separately on the
[website](https://rajab2030.github.io/rmt-platform/agent-action-audit-trail.html).

## LinkedIn

When an AI agent proposes a change, what would you want to inspect before approving it?

I'm building RMT Platform to make that decision easier to follow: policy checks, approval holds when required, and execution evidence for actions submitted through its gateway.

The local demo uses a disposable Git repository. It follows a tag creation proposal into an approval hold, shows the execution and verification result, refuses reuse of the earlier grant, and then walks through removal with a new grant.

You can try the Python client without an LLM. A configured local RMT backend is required.

The boundaries are explicit: one operator identity in this demo, automated approval inputs in the recording, and a supported single-process deployment. It does not govern arbitrary host access or promise exactly-once execution.

I've published the recorded example, setup instructions, and a technical walkthrough:
https://rajab2030.github.io/rmt-platform/

If you connect agents to real tools, I'd appreciate feedback on what information you need before approving a proposal or investigating an unexpected result.

Small documentation contributions are welcome too:
https://github.com/rajab2030/rmt-platform/contribute

#OpenSource #AIAgents #DevTools

Attachment: `docs/assets/agent-governance-demo.gif`. If the destination does not
support GIF upload, use the static PNG from the same directory or the website
link preview. Do not describe the paced excerpts as a timing benchmark.

## Short post

RMT's local demo follows a Git-tag proposal through policy preview, approval hold, and execution evidence. Open source; no LLM needed for the walkthrough. Setup and limits: https://rajab2030.github.io/rmt-platform/

## Community introduction

**Title: A local Git-tag demo of policy checks, approval holds, and agent-action evidence**

I'm the maintainer of RMT Platform, an open-source control and governance project. I'd like feedback on its agent-facing workflow from people connecting agents to tools.

The example is deliberately small: a deterministic Python client requests a scoped grant, previews a Git-tag proposal, submits it, handles a policy-dependent approval hold, and reads the execution and verification result. A later attempt to reuse the earlier grant is refused. The README includes recorded excerpts and a full transcript.

This is an operator walkthrough, not a model benchmark or a demonstration of separate approver identities. It uses one credential; approval inputs in the recording are automated. The supported deployment is single-process, with trusted operators, and governs actions submitted through the gateway.

What would make the first run easier, and what additional receipt fields would help you investigate an unexpected action?

Demo and article: https://rajab2030.github.io/rmt-platform/
Source: https://github.com/rajab2030/rmt-platform

Use only in a community that permits a relevant maintainer introduction. Do not
post this on Hacker News: its current rules prohibit generated/AI-edited text.
For r/selfhosted, verify project age and use its New Project Megathread when
required. No Reddit post has been submitted.

## Ready response: “Does this make agents safe?”

RMT provides controls and evidence for operations submitted through its gateway.
It does not control arbitrary host access, establish that every proposal is
safe, or provide a general exactly-once guarantee. The walkthrough uses one
operator identity. The current operating boundaries and security remediation
evidence are linked from the website.

## Ready response: “How do I try it?”

Start with the local Git-tag showcase:
https://github.com/rajab2030/rmt-platform/tree/master/tools/rmt-showcase-agent
It requires a configured backend, Python, and a disposable Git repository.
No LLM is required. Please use a scratch environment, not a production target.
