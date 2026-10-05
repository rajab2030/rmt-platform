# Security policy

## Reporting a vulnerability

Please **don't** open a public issue, discussion or pull request for a
security problem.

Report it privately through GitHub:
[**Report a vulnerability**](https://github.com/rajab2030/rmt-platform/security/advisories/new)
(Security tab → Advisories). Include what you found, how to reproduce it, and
what you think the impact is. Never include real credentials or tokens.

This is a single-maintainer project. You should get an acknowledgement within
7 days. Please allow reasonable time for a fix before public disclosure.

## Supported versions

Only the latest release and the `master` branch receive fixes.

## What counts as a vulnerability

RMT is designed for **trusted-operator environments**. Its security claims are
bounded by the [threat model](docs/RMT_THREAT_MODEL.md) and
[guarantees](docs/RMT_GUARANTEES.md). In scope, for example:

- a way for an action to reach an execution adapter without passing policy,
  risk and authorization;
- a way to approve, or to forge governance evidence, without an operator
  credential;
- a way for an agent grant to be reused beyond its operation, target, or
  single use;
- credential or evidence exposure through the API or logs.

Out of scope (documented limits, not vulnerabilities):

- anything requiring control of the host RMT runs on;
- actions performed outside the gateway;
- the Claude Code guard (RMT-CAP-10) failing open when the backend is
  unreachable;
- the [quickstart](quickstart/README.md)'s disabled authentication, which is
  for local demos only.

If you're unsure, report it privately anyway.

Current findings and fixes:
[security remediation status](docs/RMT_SECURITY_REMEDIATION.md).
