"""RMT-CAP-10: evidence source 3 -- a cheap, read-only situational check.

Git-specific for v1: whether uncommitted changes are present
(``git status --porcelain``), and, for a force-push specifically, whether the
remote has commits the operation would discard
(``git rev-list --left-right --count``). Each check is present only when
determinable (a real git repo, a real upstream) -- never guessed, never a
filler claim when nothing can be checked.
"""
import re
import subprocess

from app.coding_agent.models import EvidenceItem

_UPSTREAM_COUNTS_RE = re.compile(r"^\s*(\d+)\s+(\d+)\s*$")


def _run(args: list[str], cwd: str) -> str | None:
    try:
        result = subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _uncommitted_changes(cwd: str) -> EvidenceItem | None:
    out = _run(["git", "status", "--porcelain"], cwd)
    if out is None:
        return None
    if out.strip():
        return EvidenceItem(
            source="situational",
            claim="uncommitted changes present in the working tree",
            leans="reject",
        )
    return EvidenceItem(
        source="situational",
        claim="working tree is clean (no uncommitted changes)",
        leans="neutral",
    )


def _force_push_would_discard(cwd: str) -> EvidenceItem | None:
    upstream = _run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd,
    )
    if upstream is None:
        return None
    upstream = upstream.strip()

    out = _run(
        ["git", "rev-list", "--left-right", "--count", f"HEAD...{upstream}"],
        cwd,
    )
    if out is None:
        return None
    m = _UPSTREAM_COUNTS_RE.match(out)
    if not m:
        return None
    remote_ahead = int(m.group(2))

    if remote_ahead > 0:
        return EvidenceItem(
            source="situational",
            claim=(
                f"remote '{upstream}' has {remote_ahead} commit(s) this "
                "force-push would discard"
            ),
            leans="reject",
        )
    return EvidenceItem(
        source="situational",
        claim=f"remote '{upstream}' has no commits this force-push would discard",
        leans="neutral",
    )


def situational_evidence(risk_rule: str, cwd: str) -> list[EvidenceItem]:
    """Return every determinable situational :class:`EvidenceItem` for this
    rule in this working directory. Zero items when nothing is
    determinable (not a real git repo, no upstream, etc.)."""
    items: list[EvidenceItem] = []

    uncommitted = _uncommitted_changes(cwd)
    if uncommitted is not None:
        items.append(uncommitted)

    if risk_rule == "git-force-push":
        force_push = _force_push_would_discard(cwd)
        if force_push is not None:
            items.append(force_push)

    return items
