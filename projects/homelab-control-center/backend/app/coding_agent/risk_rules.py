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
        re.compile(r"\bgit\b[^\n;&|]*?\bpush\b[^\n;&|]*(--force(-with-lease)?\b|\s-[a-zA-Z]*f[a-zA-Z]*\b)"),
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
        re.compile(r"\brm\b[^\n;&|]*?(\s-[a-zA-Z]*[rR][a-zA-Z]*\b|\s--recursive\b)"),
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

@dataclass(frozen=True)
class RiskMatch:
    rule: RiskRule


def classify(command: str) -> RiskMatch | None:
    """Return the first matching rule, or None if the command matches nothing.

    Recursive deletion is reviewed even under /tmp: textual prefixes cannot
    prove confinement in the presence of traversal, symlinks or shell syntax.
    These patterns recognize common commands; they are not a shell sandbox.
    """
    for rule in RULES:
        if not rule.pattern.search(command):
            continue
        return RiskMatch(rule=rule)
    return None
