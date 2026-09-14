#!/usr/bin/env python3
"""RMT Platform showcase agent -- a standalone, dependency-free client.

This is NOT part of the RMT backend. It imports nothing from it and speaks
only HTTP, exactly as any real external agent integrating with RMT would --
following `docs/operations/AGENT_API.md` to the letter. Its purpose is to let
someone with no RMT context watch the governed lifecycle
(Understand -> Decide -> Govern -> Authorize -> Execute -> Verify -> Learn)
happen for real, against a real (dev) instance, in one command.

The story it tells, five acts, against the pre-existing git-tag domain
(RMT-CAP-06) -- chosen because it needs nothing but a scratch git repo, no
homelab hardware, no Docker:

  1. Grant this agent narrow, single-use authority to create one tag.
  2. Preview the action -- see RMT's real predicted outcome, zero side effects.
  3. Propose it for real -- a benign, low-risk action executes and is verified.
  4. Attempt to over-reach the same grant (a destructive op it was never
     granted) -- refused before governance even runs.
  5. Get properly granted authority to remove the tag, propose it -- RMT's
     frozen risk engine holds a destructive op for a human; approve it as
     that human and watch the evidence receipt land.

Every outcome printed below is the real response from your RMT instance --
nothing here is scripted or guessed. If your instance's policy classifies
things differently than described, the script narrates whatever actually
happens rather than asserting a fixed script.

Prerequisites (see README.md in this directory):
  - A running RMT instance with RMT_AGENT_ENABLED=true.
  - RMT_AGENT_GIT_REPO_PATH set *on that instance* to a scratch git
    repository. This script never sends RMT a filesystem path -- only a tag
    name -- the repo is fixed server-side, by design (no path-injection
    surface).
  - An operator token from that instance's RMT_OPERATOR_TOKENS.

Configuration (env vars):
  RMT_URL                 RMT base URL (default http://127.0.0.1:8000)
  RMT_TOKEN                operator bearer token (required)
  RMT_SHOWCASE_AGENT_ID    this agent's id (default "showcase-bot")
  RMT_SHOWCASE_TAG         tag name to create/remove (default a timestamped
                            "showcase-<epoch>", so re-runs never collide)
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

RMT_URL = os.environ.get("RMT_URL", "http://127.0.0.1:8000").rstrip("/")
RMT_TOKEN = os.environ.get("RMT_TOKEN")
AGENT_ID = os.environ.get("RMT_SHOWCASE_AGENT_ID", "showcase-bot")
TAG_NAME = os.environ.get("RMT_SHOWCASE_TAG", f"showcase-{int(time.time())}")

_BOLD = "\033[1m"
_DIM = "\033[2m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_CYAN = "\033[36m"
_RESET = "\033[0m"


def _color(text: str, code: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{code}{text}{_RESET}"


def _step(n: int, title: str) -> None:
    print()
    print(_color(f"── Act {n}: {title} ──", _BOLD + _CYAN))


def _show(label: str, value) -> None:
    print(f"  {_color(label + ':', _DIM)} {value}")


def _die(message: str) -> None:
    print(_color(f"error: {message}", _RED), file=sys.stderr)
    sys.exit(1)


def _call(method: str, path: str, body: dict | None = None) -> dict:
    """Every call the agent makes to RMT. Raises on transport failure or a
    non-2xx status -- this script has no fail-open behavior of its own; it
    is a client, not a governance layer."""
    url = f"{RMT_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {RMT_TOKEN}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        _die(f"{method} {path} -> HTTP {e.code}: {detail}")
    except urllib.error.URLError as e:
        _die(f"could not reach {RMT_URL} ({e.reason}) -- is RMT running?")


def _approve(approval_id: str, prompt_note: str) -> dict:
    """Prompt the person running this script to act as the human approver,
    then show the *real* outcome -- including a failed execution, never
    hidden behind a verification field alone. RMT distinguishes "the adapter
    ran and failed" from "verified success" as separate evidence (E3); this
    script surfaces both rather than only the reassuring one."""
    print(_color(f"  {prompt_note}", _DIM))
    try:
        input(_color("\n  Press Enter to approve it as that human operator... ", _YELLOW))
    except EOFError:
        print()
    decided = _call("POST", f"/homelab/approve?approval_id={approval_id}&approved=true")
    _show("post-approval status", decided.get("status"))
    _show("execution success", decided.get("success"))
    if not decided.get("success"):
        print(_color(f"  message: {decided.get('message')}", _YELLOW))
    _show("verification_status", decided.get("docker_verification_status"))
    return decided


def _proposal(mechanism: str, expected_state: str, grant_id: str, reason: str) -> dict:
    return {
        "agent_id": AGENT_ID,
        "goal": f"{mechanism} tag {TAG_NAME}",
        "target": TAG_NAME,
        "mechanism": mechanism,
        "reason": reason,
        "confidence": 90,
        "expected_state": expected_state,
        "grant_id": grant_id,
        "operational_context": "git",
    }


def main() -> None:
    if not RMT_TOKEN:
        _die("RMT_TOKEN is required -- an operator token from RMT_OPERATOR_TOKENS")

    print(_color("RMT Platform -- Agent Governance Gateway showcase", _BOLD))
    print(_color(f"target: {RMT_URL}  |  agent_id: {AGENT_ID}  |  tag: {TAG_NAME}", _DIM))

    # --- Act 1: a scoped, single-use grant --------------------------------
    _step(1, "Get a scoped, single-use grant")
    grant = _call(
        "POST", "/agent/authority/grant",
        {"operation": "create", "target": TAG_NAME},
    )
    _show("grant_id", grant["grant_id"])
    _show("scope", f'{grant["operation"]} on {grant["target"]}')
    _show("expires_at", grant["expires_at"])
    print(_color("  capability != authority: this agent can name any operation,", _DIM))
    print(_color("  but may only act on the one it just received a grant for.", _DIM))

    # --- Act 2: preview -- zero side effects -------------------------------
    _step(2, "Preview the action (zero side effects)")
    preview_body = _proposal("create", "present", grant["grant_id"], "showcase: benign create")
    preview = _call("POST", "/agent/act/preview", preview_body)
    _show("decision", preview.get("decision"))
    predicted = preview.get("predicted", {})
    _show("predicted risk_level", predicted.get("risk_level"))
    _show("predicted approval_mode", predicted.get("approval_mode"))
    print(_color("  nothing was written -- no grant consumed, no hold created.", _DIM))

    # --- Act 3: propose for real --------------------------------------------
    _step(3, "Propose it for real")
    outcome = _call("POST", "/agent/act", preview_body)
    _show("decision", _color(outcome.get("decision"), _GREEN))
    _show("execution_id", outcome.get("execution_id"))
    _show("verification_status", outcome.get("verification_status"))
    _show("at", outcome.get("at"))
    if outcome.get("decision") in ("hold", "escalated_hold"):
        print(_color(
            f"  (this instance's policy holds '{TAG_NAME}' create for approval "
            f"rather than auto-allowing it -- detail: {outcome.get('detail')})", _YELLOW,
        ))
        _approve(
            outcome["approval_id"],
            "RMT held this create for a human before Act 5 can remove it for real.",
        )
    elif outcome.get("decision") != "allow":
        print(_color(
            f"  (this instance's policy took a different path than the "
            f"README's default story -- decision was '{outcome.get('decision')}', "
            f"detail: {outcome.get('detail')})", _YELLOW,
        ))

    # --- Act 4: over-reach the same (now-consumed) grant --------------------
    _step(4, "Attempt to over-reach the grant")
    overreach_body = _proposal(
        "remove", "absent", grant["grant_id"], "showcase: try to reuse a create grant to remove"
    )
    overreach = _call("POST", "/agent/act", overreach_body)
    _show("decision", _color(overreach.get("decision"), _RED))
    _show("detail", overreach.get("detail"))
    print(_color("  refused before governance even ran -- no policy call, no risk", _DIM))
    print(_color("  assessment, no evidence write. A grant is scope- and", _DIM))
    print(_color("  operation-bound, not a blanket authorization.", _DIM))

    # --- Act 5: a properly granted destructive action -----------------------
    _step(5, "Properly granted destructive action -> human approval")
    remove_grant = _call(
        "POST", "/agent/authority/grant",
        {"operation": "remove", "target": TAG_NAME},
    )
    _show("grant_id", remove_grant["grant_id"])
    remove_body = _proposal(
        "remove", "absent", remove_grant["grant_id"], "showcase: destructive removal"
    )
    remove_outcome = _call("POST", "/agent/act", remove_body)
    _show("decision", remove_outcome.get("decision"))

    if remove_outcome.get("decision") in ("hold", "escalated_hold"):
        approval_id = remove_outcome["approval_id"]
        _show("approval_id", approval_id)
        _approve(
            approval_id,
            "RMT's frozen risk engine held this for a human -- the agent "
            "cannot approve its own proposal.",
        )
    else:
        print(_color(
            f"  (no hold was created -- decision was "
            f"'{remove_outcome.get('decision')}'; nothing to approve)", _YELLOW,
        ))

    print()
    print(_color("Done. Every step above is a real call against your RMT instance --", _BOLD))
    print(_color("nothing was simulated. See docs/operations/AGENT_API.md for the full contract.", _BOLD))


if __name__ == "__main__":
    main()
