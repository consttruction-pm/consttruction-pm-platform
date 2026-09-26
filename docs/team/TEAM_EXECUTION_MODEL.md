# Team Execution Model — 2026-09-25

## Release objective
At release, the product must pass the evidence-based completeness/leadership gate defined in PRODUCT_PRINCIPLES.md. Team execution therefore includes continuous market monitoring, gap discovery and re-prioritization in addition to implementation.

## Authority order
1. Principle 1: Primavera P6 + PMBOK alignment.
2. Principle 2: complete modern construction-management/project-controls coverage.
3. Shared Core and domain integrity.
4. Cross-client contracts and portability.
5. UX and implementation convenience.

## Jalal — Shared Core, Project Controls Intelligence, Integration QA
Jalal is an implementation developer, not only coordinator.

Primary ownership:
- Shared Domain/Calculation Core.
- Scheduling/P6, calendar, duration, constraints, relationships, float, schedule options and parity.
- Progress/EVM/Earned Schedule calculation extensions.
- Resource/Cost calculation semantics when cross-cutting control logic is involved.
- Cross-domain dependency graph semantics and project-control query model.
- AI decision-engine contracts where they depend on authoritative calculations.
- Regression/parity/validation, including Primavera conformance and controlled OSS oracles.
- Architecture decisions that cross more than one ownership boundary.

Jalal must not implement client UI and must not create a second calculation engine in Web/Desktop/Mobile.

## Hasan — Backend, Database, Application, API, Security and Enterprise Integration
Primary ownership:
- Application/use-case layer, repositories and database schemas.
- Versioned API contracts and transport.
- ProjectContext, tenant isolation, revisions, optimistic locking, idempotency, conflicts and transactions.
- Authentication/authorization, enterprise identity integration and audit persistence.
- Document storage/search/OCR service boundaries.
- Procurement/commercial persistence and workflow APIs.
- ERP/accounting/BI integration adapters and external APIs.
- Server-side AI orchestration, tool permissions, action audit and policy enforcement.
- PostgreSQL production hardening and deployment contracts.

Hasan must not implement P6/Progress/EVM/Resource-Cost formulas in Application/API/DB or in client code. Application orchestrates; Shared Core calculates.

## Javad — Web, Desktop, Mobile, UX and Field Experience
Primary ownership:
- Web/Site beta first.
- Desktop/Windows product second.
- Mobile/field product third.
- WBS/activity/Gantt editing UX using versioned contracts.
- Dashboard, reporting, print-preview and control-room presentation.
- Field modules UI: daily log, attendance/timecard, equipment, issue/observation, inspection, quality, safety, punch list, photo/location capture.
- Procurement/contract/document workflow UX.
- Offline UX, sync/conflict presentation and client adapters.
- Persian/English UI, RTL/LTR presentation and Jalali/Gregorian display.
- AI assistant UI, voice entry, Smart Guide and action-approval UX.

Javad must not implement authoritative scheduling, Progress/EVM, Resource/Cost or financial formulas in clients.

## Shared P0 workstream ownership
| Capability | Jalal | Hasan | Javad |
|---|---|---|---|
| AI Project Controls Copilot | Core contracts/analysis | orchestration/security/audit | UX/interaction |
| Cross-domain dependency graph | domain model/rules | persistence/API | visualization/navigation |
| Field operations | shared data semantics where needed | storage/workflow/API | complete client workflows |
| Change/Claim/Contract | schedule/cost impact semantics | workflow/persistence/API | UX |
| Portfolio Control Room | control metrics | aggregation/API | dashboards |
| Procurement | commitment/control semantics | DB/workflow/integration | screens |
| ERP/Accounting | financial contract semantics | connectors/API/security | presentation/status |

## Mandatory coordination rules
1. One feature = one primary owner.
2. Before changing a shared contract, check active PRs and current main.
3. Architecture-impacting changes are recorded in GitHub before dependent parallel implementation.
4. Every PR states ownership boundary, dependencies and whether shared semantics changed.
5. Open PRs are not baseline until reconciled and runtime-validated.
6. Client releases proceed Web -> Desktop -> Mobile, but independent contract/client work may run in parallel.
7. New product domains are implemented against versioned contracts; they do not bypass Shared Core authority.

## First execution wave
- Jalal: P0 Shared Core/control-intelligence contracts + regression architecture.
- Hasan: P0 backend/API/persistence contracts for dependency graph, field, change/claims and procurement.
- Javad: Web beta control-room and field workflow shells, then Desktop/Mobile parity.
- All three: daily overlap/merge-base/contract/CI review.