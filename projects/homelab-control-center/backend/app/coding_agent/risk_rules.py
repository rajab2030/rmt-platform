"""RMT-CAP-10: deterministic risk classification for a proposed shell command.

A small, explicit, reviewable pattern list -- not an LLM. A command matching
none of these is never intercepted (auto-allow, zero cost). Adding a rule is
a one-line, reviewable diff, same spirit as ``REMEDIATION_POLICY``.
"""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RiskRule:
    name: str
    pattern: re.Pattern
    risk_level: str  # "high" | "medium"
    description: str


RULES: list[RiskRule] = [
    RiskRule(
        "git-force-push",
        re.compile(r"\bgit\s+push\b.*(--force(-with-lease)?\b|\s-f\b)"),
        "high",
        "irreversible remote history rewrite",
    ),
    RiskRule(
        "git-hard-reset",
        re.compile(r"\bgit\s+reset\s+--hard\b"),
        "high",
        "discards local work irreversibly",
    ),
    RiskRule(
        "git-clean-force",
        re.compile(r"\bgit\s+clean\s+(-[a-zA-Z]*f[a-zA-Z]*|--force)\b"),
        "medium",
        "irreversibly deletes untracked files",
    ),
    RiskRule(
        "recursive-delete",
        re.compile(r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*|-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*)\b"),
        "high",
        "unrecoverable recursive deletion",
    ),
    RiskRule(
        "sudo",
        re.compile(r"(^|[;&|]\s*)sudo\b"),
        "medium",
        "elevated privilege",
    ),
    RiskRule(
        "service-restart",
        re.compile(r"\bsystemctl\s+(stop|restart)\b"),
        "medium",
        "affects a running service",
    ),
]

# Paths where recursive delete is treated as ordinary scratch cleanup, not risky.
_SAFE_DELETE_PREFIXES = ("/tmp/", "/tmp",)


@dataclass(frozen=True)
class RiskMatch:
    rule: RiskRule


def classify(command: str) -> RiskMatch | None:
    """Return the first matching rule, or None if the command matches nothing.

    ``recursive-delete`` is suppressed for paths clearly confined to /tmp
    (scratch cleanup) -- a narrow, explicit carve-out, not a general escape
    hatch: any target outside /tmp still matches.
    """
    for rule in RULES:
        if not rule.pattern.search(command):
            continue
        if rule.name == "recursive-delete" and _targets_only_tmp(command):
            continue
        return RiskMatch(rule=rule)
    return None


def _targets_only_tmp(command: str) -> bool:
    tokens = [t for t in command.split() if not t.startswith("-")]
    # tokens[0] is the command name (e.g. "rm"); the rest are candidate paths.
    paths = tokens[1:]
    if not paths:
        return False
    return all(p.startswith(_SAFE_DELETE_PREFIXES) for p in paths)
