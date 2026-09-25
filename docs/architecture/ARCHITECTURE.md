# System Architecture

## Architectural baseline
The platform uses a Shared Domain/Calculation Core with strict separation of Domain, Application, Infrastructure, API and Client layers.

## Governing order
1. Primavera P6 + PMBOK compatibility.
2. Complete modern construction lifecycle coverage.
3. Shared Core/domain integrity.
4. Cross-client contract/portability parity.
5. UX and implementation convenience.

## Web-readiness
- Domain and calculation logic are UI-independent.
- Windows, PostgreSQL, filesystem and authentication are infrastructure concerns.
- Document storage and background jobs use abstractions.
- API contracts expose application use cases rather than database internals.
- Multi-tenant boundaries, optimistic locking and transaction boundaries are first-class concerns.

## Authoritative calculation boundaries
Scheduling/P6, Calendar, Duration/Lag, Progress/EVM/Earned Schedule, Resource/Cost and financial calculation semantics belong to the Shared Domain/Calculation Core.

## Product architecture domains
Preconstruction/Estimating, Planning/Scheduling, Progress/EVM, Resources/Cost, Procurement/Commercial, Field Operations, Quality, Safety, Contracts/Changes/Claims, Documents/OCR/RFI/Submittal, Risk, BIM/CDE/4D/5D, Reality/Progress Intelligence, Portfolio/Control Room, Reporting/Print, AI/Agents, Commissioning/Closeout and Enterprise Integrations.

## Cross-domain project graph
All major records should carry stable tenant/project/revision identifiers and be linkable across Schedule, Progress, Cost, Resource, Document, Contract, Procurement, Field and Risk domains.

## AI boundary
AI may analyze authoritative data and propose actions, but consequential mutations require explicit application-layer authorization, auditability and human approval according to the action policy. AI does not own project truth.

## Client boundary
Web, Desktop and Mobile are first-class clients. Client code presents workflows and consumes versioned contracts; it must not duplicate authoritative business calculations.

## Open-source boundary
Commodity infrastructure or validation packages may sit behind explicit adapters and license/security review. Shared product intelligence remains project-owned.