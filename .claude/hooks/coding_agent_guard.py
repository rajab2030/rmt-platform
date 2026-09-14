#!/usr/bin/env python3
"""RMT-CAP-10: Claude Code PreToolUse hook -- proposes a Bash command to the
RMT coding-agent governance surface before it runs.

Project-scoped: registered only in this repository's .claude/settings.json,
not a user-global config, so it governs Claude Code sessions in this repo
only.

Decision mechanism (the exit-code path only -- deliberately not the
richer/unverified stdout-JSON extras): exit 0 lets the command proceed,
exit 2 blocks it and Claude Code shows our stderr text as the reason.

Fail-open by design, not by accident (docs/RMT_CAP_10_PROPOSAL.md SS3d): if
the backend is unreachable, misconfigured, or a poll times out, the command
is allowed through with a warning on stderr. A governance layer that can
brick the tool it governs is worse than one that occasionally lets a command
through unreviewed while loudly saying so.

Configuration (env, all optional):
  RMT_CODING_AGENT_URL            -- base URL of the RMT backend
                                      (default http://127.0.0.1:8000)
  RMT_CODING_AGENT_TOKEN          -- operator bearer token (needed only if
                                      the backend has RMT_AUTH_ENABLED on)
  RMT_CODING_AGENT_POLL_TIMEOUT_S -- max seconds to wait for a human
                                      decision before failing open
                                      (default 120)
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE_URL = os.environ.get("RMT_CODING_AGENT_URL", "http://127.0.0.1:8000")
TOKEN = os.environ.get("RMT_CODING_AGENT_TOKEN")
POLL_TIMEOUT_S = float(os.environ.get("RMT_CODING_AGENT_POLL_TIMEOUT_S", "120"))
POLL_INTERVAL_S = 2.0
REQUEST_TIMEOUT_S = 5.0


def _allow(message: str | None = None) -> None:
    if message:
        print(f"[coding-agent-guard] {message}", file=sys.stderr)
    sys.exit(0)


def _block(reason: str) -> None:
    print(f"[coding-agent-guard] BLOCKED: {reason}", file=sys.stderr)
    sys.exit(2)


def _request(method: str, path: str, body: dict | None = None) -> dict | None:
    """Return the parsed JSON response, or None on any failure (network,
    timeout, non-2xx, bad JSON) -- every failure mode here means "fail open",
    never "block"."""
    url = f"{BASE_URL.rstrip('/')}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        _allow("could not parse hook input; allowing")
        return

    if payload.get("tool_name") != "Bash":
        _allow()
        return

    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command")
    if not command:
        _allow()
        return

    cwd = payload.get("cwd") or os.getcwd()
    session_id = payload.get("session_id")

    result = _request(
        "POST",
        "/coding-agent/propose",
        {"command": command, "cwd": cwd, "session_id": session_id},
    )
    if result is None:
        _allow("backend unreachable -- failing open")
        return

    decision = result.get("decision")
    if decision == "auto_allow":
        _allow()
        return
    if decision != "hold":
        _allow(f"unexpected decision '{decision}' -- failing open")
        return

    hold_id = result.get("hold_id")
    review = result.get("review") or {}
    print(
        f"[coding-agent-guard] held for review: rule={review.get('risk_rule')} "
        f"risk={review.get('risk_level')} verdict={review.get('verdict')} "
        f"hold_id={hold_id} -- approve or reject via "
        f"POST {BASE_URL}/coding-agent/decide",
        file=sys.stderr,
    )

    deadline = time.monotonic() + POLL_TIMEOUT_S
    while time.monotonic() < deadline:
        hold = _request("GET", f"/coding-agent/holds/{hold_id}")
        if hold is None:
            _allow("backend unreachable while polling -- failing open")
            return
        status = hold.get("status")
        if status == "approved":
            _allow(f"approved by {hold.get('decided_by')}")
            return
        if status == "rejected":
            _block(f"rejected by {hold.get('decided_by')}")
            return
        time.sleep(POLL_INTERVAL_S)

    _allow("no decision within timeout -- failing open")


if __name__ == "__main__":
    main()
