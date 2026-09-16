# RMT Master Definition

## Authority

This document is the authoritative source for the identity, purpose, architectural principles, direction, and Core-versus-domain boundaries of the RMT Platform.

Conflicting historical descriptions of RMT are obsolete as definitions. They may remain as historical records, but they must not override this document.

## RMT Identity and Purpose

**RMT stands for Risk-Mitigated Transactions** — defined 2026-09-11 to match
what the platform actually is, superseding any earlier or informal meaning of
the initials. Every consequential action the platform touches, in any domain,
is treated as a transaction that must be risk-mitigated — policy-checked,
risk-assessed, authorized, and verified — before and after it happens, never
assumed safe by default.

RMT is a general-purpose intelligent control, execution, and governance platform. It is not a specialized application.

RMT enables services, applications, systems, and AI agents to operate under a common control layer:

**Understand → Decide → Govern → Authorize → Execute → Verify → Learn**

This common layer provides the foundation for controlled operation across different environments and domains.

## RMT Core

The RMT Core is domain-agnostic. Its responsibilities are the general control, intelligence, governance, authorization, execution, verification, learning, audit, and platform-management concerns required to operate governed capabilities.

The Core must remain reusable across domains. Domain concepts, domain rules, domain workflows, and domain-specific products must not be embedded into the Core merely because a particular domain is an early or important use case.

## Core and Domain Boundaries

Banking Risk Management, Budget Control, AI Agent Governance, IT/Cloud Operations, and future domains are capabilities or products built on top of RMT. They are not reasons to make the RMT Core domain-specific.

These capabilities may be implemented as products, domain modules, integrations, adapters, or applications that consume the RMT Core’s common layer and contracts.

## Controlled Self-Management and Evolution

RMT is designed for controlled self-management and controlled evolution.

Self-evolution means controlled change through:

**Governance → Risk Assessment → Authorization → Execution → Verification → Audit**

It does not mean uncontrolled self-modification. Changes to RMT, its operation, or its capabilities must remain subject to explicit control, evidence, authorization, and verification.

## Finite Core Target State

The RMT Core must have a finite Target State. The Core must not become an indefinitely expanding architecture.

Remaining Core development must be derived from the Target State and expressed as finite milestones. Each milestone must have an explicit Definition of Done and must be validated against the intended Core responsibility.

New ideas must be classified before they are treated as Core work:

- required for Target State;
- above-Core/domain capability;
- future backlog; or
- unnecessary.

Only ideas required for the finite Target State belong in remaining Core development. Ideas in the other categories must not expand the Core by default.

## Target Direction

RMT Core development continues until the finite Target State is reached and the platform passes platform validation. At that point, the Core enters **Platform Freeze**.

After Platform Freeze, future growth occurs through products, domain modules,
integrations, adapters, and applications built on top of RMT. Following the sole
final domain-compatibility amendment accepted on 2026-09-15, the owner closed the
amendment procedure permanently: no future Core amendment, freeze deviation, Core
milestone, or C08 is admissible. A capability or domain that cannot comply with
the frozen contracts does not belong to RMT and must be kept outside RMT, deferred,
or rejected.

## Governing Rule

This document governs RMT identity, purpose, architectural principles, direction, and Core-versus-domain boundaries. It is the reference against which RMT proposals, implementation decisions, milestone classification, and future descriptions must be evaluated.
