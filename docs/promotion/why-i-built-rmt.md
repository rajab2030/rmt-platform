# Post draft: why I built RMT

Draft 2026-09-28 for the public-readiness plan (finding 6). This is copy for
the owner to edit, not evidence that it has been published. Anything in
`[OWNER: …]` is a personal fact I could not verify from the repository. Fill it
in or delete it; don't publish with brackets left in.

Destinations: dev.to / Hashnode / the Discussions board. Confirm the destination's current rules before posting.

## Suggested title

An AI agent wants to run a risky command. Who decides?

## Suggested tags

`opensource`, `ai`, `devops`, `homelab`

## Body (Markdown, ready to paste)

RMT started as a homelab: one Ubuntu VM running Portainer, Uptime Kuma and
Dozzle, plus some backup scripts. The first commit was in July 2026. Nothing
in it was about AI.

[OWNER: one or two sentences on your background. For example, the
real-world control-room or operations experience that the "Master Control
Room" idea in the docs comes from, if that's accurate.]

Once the homelab could restart its own unhealthy services, I hit a question I
couldn't answer with a script: **when something automated wants to change a
real system, who decides whether it's allowed to, and how do you prove
afterwards what happened?**

For a restart script, the answer is "whoever wrote the script." For an AI
agent, it isn't. The agent chooses the action at runtime. It can name any
operation it likes. And the tool it calls will happily report "success"
without telling you who authorized it, what the risk was, or whether anything
checked the result.

### What I wanted

I didn't want to build another agent. I wanted the thing that sits between an
agent and a real system and does three things:

1. **Checks policy and risk before anything executes.** The agent can ask
   first ("what would happen if I did this?") and get the real predicted
   decision with no side effects.
2. **Holds risky actions for a human.** Nothing runs until an authenticated
   operator approves it.
3. **Leaves evidence.** Every decision, approval, execution and verification
   is recorded and linked together, and can be exported as a signed bundle
   that someone else can check offline.

That became RMT (Risk-Mitigated Transactions). Every consequential action, in
any domain, goes through one lifecycle: Understand → Decide → Govern →
Authorize → Execute → Verify → Learn.

### The homelab was the test, not the product

I built the governance Core against the homelab first, because it was real
but low-stakes. If a Docker restart went through the wrong path, I'd see it.
Once the Core held up, I froze it: it has its own test suite, and new
capabilities are built on top of it instead of changing it.

The first thing built on top that wasn't the homelab was an agent gateway. An
external agent gets a **grant** scoped to one operation on one target, used
once. With that grant it can create a Git tag. If it then tries to delete the
tag using the same grant, RMT refuses before policy even runs, because
**capability isn't authority**. That's the demo in the README, and you can run
it locally with only Git and Python.

### Then I pointed it at my own coding agent

[OWNER: keep or delete this section. It says you used an AI coding agent
while building RMT.]

While building RMT I used an AI coding agent, and at some point the obvious
question arrived: why is the tool that edits this repository the one thing
here that isn't governed?

So RMT-CAP-10 governs Claude Code's shell commands. A `PreToolUse` hook sends
each command to RMT first. If it matches a short, explicit list of risky
patterns (force-push, hard reset, recursive delete, `sudo`, service restarts),
it's held until I decide. The hold comes with an explanation built only from
checkable evidence, never from an LLM's opinion, because a recommendation is
only as trustworthy as what it cites.

### What it doesn't do

I'd rather you hear the limits from me than find them yourself:

- It's built for **trusted-operator** environments. It isn't a defence against
  a malicious admin on the same host.
- It only governs actions submitted **through RMT**. Anything that goes around
  the gateway, such as direct shell or host access, is outside the boundary.
- The local demo uses **one credential** to grant, propose and approve. It
  doesn't show independent approver identities.
- The Claude Code hook **fails open**: if RMT is unreachable, the command runs
  with a warning. It only covers the listed patterns.
- There's no general exactly-once guarantee, and not every action needs human
  approval. That depends on policy.

The full list, with the reasoning behind each one, is in
[Guarantees and limits](https://github.com/rajab2030/rmt-platform/blob/master/docs/RMT_GUARANTEES.md)
and the [threat model](https://github.com/rajab2030/rmt-platform/blob/master/docs/RMT_THREAT_MODEL.md).

### Try it, and tell me where it breaks

```bash
git clone https://github.com/rajab2030/rmt-platform.git
cd rmt-platform
docker compose run --rm showcase
```

You need Docker with Compose v2; press Enter when an action is held. To put
the Claude Code guard on your own project, see
[the install guide](https://github.com/rajab2030/rmt-platform/blob/master/tools/claude-code-guard/README.md).

I'm most interested in two kinds of feedback: setup reports (did it work on
your machine, and how long did it take?) and actions you'd want governed that
RMT can't represent today. Both are welcome in
[Discussions](https://github.com/rajab2030/rmt-platform/discussions).

RMT is MIT-licensed. [OWNER: optional sign-off: name, where to find you.]
