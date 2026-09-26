# Technical post: evidence export / attestation bundles

Drafted 2026-09-22, per the suggested action in `docs/GROWTH_TRACKING.md`
(2026-09-21 entry). This is finished copy for dev.to or Hashnode, not
evidence that it has been published. Confirm the destination's current rules
before posting.

## Suggested title

What does an audit trail for an AI agent's action actually look like?

## Suggested tags

`opensource`, `ai`, `security`, `devops`

## Canonical URL

Leave blank, or set to `https://rajab2030.github.io/rmt-platform/` if the
platform asks for one — the site already carries the related engineering
walkthrough and this post references it rather than duplicating it.

## Body (Markdown, ready to paste)

A tool telling you "success" doesn't tell you who authorized it, what
evidence exists that it ran, or how you'd prove any of that to someone who
doesn't trust your database. That gap matters more once the thing calling
the tool is an AI agent instead of a human clicking a button — there's no
one to ask "wait, why did you do that?"

[RMT Platform](https://github.com/rajab2030/rmt-platform) is an open-source
control and governance layer I've been building: every consequential action
an agent proposes goes through one lifecycle — policy check, risk
classification, approval hold where required, execution, verification, and
a durable evidence record — before anything happens. I wrote about that
lifecycle with a recorded [Git-tag walkthrough
earlier](https://rajab2030.github.io/rmt-platform/agent-action-audit-trail.html).
This post is about a narrower problem I ran into once that evidence existed:
**how do you hand it to someone who isn't running your service?**

### The problem with "just query the API"

RMT already recorded a correlated evidence chain for every governed action —
authorization, approval, audit, trace, verification — queryable while the
service is up. That's fine for day-to-day operation. It's not fine for:

- an external auditor who shouldn't need API access to your production
  service to check one action,
- an incident review six months later, after the service has been
  redeployed a dozen times,
- a compliance handoff where "trust our database" isn't an acceptable
  answer.

What's needed is something you can hand over as a file: verifiable on its
own, without re-querying the live system or trusting whoever exported it.

### Signed, portable bundles

The implementation (`app/ops/attestation.py`) wraps the existing evidence
chain in a signed envelope — format version, generation timestamp, the
correlated records, and an HMAC-SHA256 signature computed over a
deterministic, sorted-key canonical JSON serialization. Stdlib only
(`hashlib` / `hmac`), no new dependency.

```
GET /ops/evidence/export?execution_id=<id>
```

returns the signed bundle. A small, dependency-free verifier script
(`rmt-attestation-verify.py`) checks it completely offline:

- exit 0, `VALID` — the bundle matches its signature
- exit 1, `INVALID` — wrong key, or any field was tampered with
- exit 2, `MALFORMED` — unparseable or unrecognizable input

No app import, no network call, no running service required to check a
bundle. That's the actual point: the recipient doesn't have to trust
anything except the key they were given out of band.

### What "tamper-detected" looked like in practice

Before deploying this, I ran it against a real governed action end-to-end
on an isolated instance: a `POST /execute?operation=restart&target=demo-svc`
call produced a genuine authorization → approval → audit → trace →
verification chain, exported it, and fed the bundle to the verifier three
ways —

- with the correct key: `VALID`
- with the wrong key: `INVALID`
- with one real field (`authorized_by`) edited in a copy of the bundle:
  `INVALID`

Then the same thing against a real production execution after deployment
(`execution_id 78eac35c-f4bf-4f96-b777-ea096fd5a783`): exported, verified
offline against the production signing key, `VALID`. That's the difference
between "the code passed its tests" and "it worked against something that
actually happened."

### What this doesn't claim

This is HMAC, a shared secret, not a public/private key pair — anyone who
can verify a bundle holds a key that could also have produced one. It's
suited to internal compliance and incident review where you control key
custody (the signing key follows the same systemd `LoadCredential=` pattern
already used for operator tokens — never a plaintext environment variable
in production), not to non-repudiation against a third party who shouldn't
be trusted with the key at all. If you need that property, you want
asymmetric signing, which this isn't.

It also only covers what RMT's own evidence chain already recorded. An
export can't manufacture evidence a governed action didn't produce, and an
unknown identifier still returns a validly-signed bundle with an empty
chain — a signature proves the bundle wasn't altered after export, not that
the underlying action happened the way you'd like it to have.

### Try it

The export endpoint and verifier are both in the repo, disabled by default
like every other capability here:
https://github.com/rajab2030/rmt-platform

If you're attaching agents to real tools and have opinions about what an
audit bundle should contain to be useful in an actual incident review, I'd
like to hear them — open an issue or a discussion.

---

*RMT Platform is open source. Source, setup instructions, and a recorded
walkthrough are at https://github.com/rajab2030/rmt-platform and
https://rajab2030.github.io/rmt-platform/.*

## Posting notes

- Do not claim asymmetric-signature/non-repudiation properties this feature
  doesn't have — the "What this doesn't claim" section is load-bearing, not
  optional boilerplate; keep it if this copy is trimmed for another platform.
- Cross-link back to the GitHub repo and the existing website walkthrough;
  don't restate the Git-tag walkthrough's content here, just point to it.
- No dev.to/Hashnode account connection has been confirmed in this session —
  this is copy only, not evidence of publication.
