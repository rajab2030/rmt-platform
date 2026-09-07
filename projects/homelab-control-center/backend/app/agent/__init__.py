"""RMT-CAP-05 (5A) — Governed Agent Surface (above-Core).

Implements the MCR child-contract surface (Identity, Intent, Authority,
Proposed Action, Decision, Outcome) on top of the frozen Core's single governed
mutation boundary. An agent *proposes* a consequential homelab operation; the
proposal is translated into an ``ActionRequest`` and routed through
``execute_governed_action`` -- the same path a Homelab remediation takes. The
agent never executes, authorizes, approves, or continues a hold.

Scope 5A only: the governed surface + a deterministic reference agent + the
T13 dependency-cascade escalation rule. No LLM (that is 5B). Disabled by
default (``RMT_AGENT_ENABLED``). No ``app/core/**`` change; no new mutation
path.
"""
