# Team Responsibilities — 3-Person Development Model

## Purpose

This document defines the current three-person division of responsibilities for the Construction PM Platform. It is the working ownership model for implementation, review, integration, and testing.

## 1. Jalal — Lead Developer / Architect / Integration

**Primary ownership**
- Overall software architecture and technical direction.
- Shared Domain / Calculation Core.
- Scheduling and calculation engine.
- Primavera P6-compatible scheduling logic and parity.
- Calendar Arithmetic and WorkingTimeResolver.
- Relationships: FS, SS, FF, SF; lag; constraints; forward/backward pass; float and critical path.
- Progress, EVM, Schedule Performance and related calculation semantics.
- Cross-module architecture and integration.
- Code review, regression strategy, acceptance criteria and final technical approval.
- Prevention of duplicate logic between backend and clients.
- Resolution of cross-team technical conflicts.

**Mandatory rule:** Shared calculation semantics are implemented in the Shared Domain/Calculation Core and are not independently reimplemented in Backend, Web, Desktop or Mobile.

## 2. Hasan — Backend / Database / API

**Primary ownership**
- PostgreSQL/database design and migrations.
- Backend Domain/Application/Repository implementation.
- API contracts and server-side application services.
- Authentication, authorization and permission enforcement.
- Project, WBS, Activity and master-data persistence.
- Resource, cost and project-control persistence/integration.
- Import/export services and server-side validation.
- Client Sync, revision handling, idempotency and conflict boundaries.
- Transaction boundaries, optimistic locking and concurrency controls.
- Backend integration tests and database-backed verification.
- Backend documentation and API contract maintenance.

**Boundary:** Hasan consumes the Shared Domain/Calculation Core rather than creating a competing scheduling/calculation implementation.

## 3. Javad — Frontend / Web / Desktop / Mobile / UX

**Primary ownership**
- Web, Desktop and Mobile client implementation.
- Main Workspace, WBS UI, Activity Grid and Gantt UI.
- Dashboards, forms, reports and user interaction flows.
- Responsive behavior and client-side UX.
- Persian/English UI, RTL/LTR behavior and localization integration.
- Offline client behavior and local mutation queue integration.
- Client-side API integration and synchronization UI.
- Client validation/presentation logic that does not duplicate authoritative business calculations.
- Accessibility, visual consistency and cross-client parity.

**Boundary:** Javad does not create a separate scheduling/calculation engine. Authoritative calculations come from the Shared Domain/Calculation Core and approved API contracts.


## 6. P6 26.4 No-Omission Parity Workstream

This workstream is a mandatory cross-team requirement under Product Principle 1A and Issue #389.

### Jalal — Shared Core / P6 semantics / calculation authority
**GitHub task:** #391
- P6 26.4 field and calculation-option inventory and disposition.
- Canonical Field Registry semantics.
- P6 Schedule Options and calculation behavior.
- Calendar parity: global/project/resource pools, inheritance, exceptions, detailed work time and hours-per-period.
- Formula/Calculated Column engine in Shared Core.
- Dependency graph, type checking, circular-dependency detection and deterministic rollups.
- P6 semantic conformance and non-regression tests.

### Javad — Columns / Layouts / Field UX
**GitHub task:** #392
- Web/Desktop/Mobile Field Chooser and complete shared field presentation.
- Add/remove/hide/show/reorder/rename/width/alignment/pin/freeze.
- Persistent user/project/global layouts and migration.
- Typed standard/UDF editors and display formatting.
- Formula editor UX and validation/dependency visualization.
- Grid sort/group/filter/report/print field selection.
- Cross-client presentation parity.

Javad consumes the Shared Core Formula Engine and Field Registry; he must not implement independent P6 calculations.

### Hasan — Persistence / API / Import-Export
**GitHub task:** #393
- Persistence/versioning/tenant-project scoping for Field Registry, UDF, Column/Layout and Formula definitions.
- Typed API contracts for field catalogs, layouts, formulas and schedule/calendar options.
- XER/XML/XLS/XLSX/Microsoft Project mapping work as approved by the parity registry.
- Explicit unsupported-field handling; no silent data loss.
- Financial-period, resource-spread, baseline and code persistence required by the registry.
- Database transaction, revision/concurrency and round-trip verification.

Hasan consumes Shared Core semantics and must not create a competing scheduling/calendar/formula engine.

### P6 parity sequence and ownership flow
1. **Jalal** freezes/dispositions semantics and contracts.
2. **Hasan** persists/exposes those contracts and builds interchange adapters.
3. **Javad** consumes those contracts for client grids, layouts and editors.
4. **Jalal** performs semantic integration/conformance acceptance.
5. **All three** participate in cross-client/import-export regression where their boundary is affected.

## 4. Shared Working Rules

1. GitHub/Codex is the canonical development, execution and test environment.
2. ChatGPT coordinates, reviews, analyzes and helps define implementation/test criteria.
3. Each person works only within the agreed ownership boundary unless an integration task explicitly crosses boundaries.
4. Shared contracts must be agreed before dependent implementation is finalized.
5. No duplicated business rules or calculations across Backend and clients.
6. Database-backed behavior must be verified in a real PostgreSQL-capable environment before being marked runtime-verified.
7. Every completed stage requires focused tests plus regression verification appropriate to its scope.
8. Existing completed work must be reviewed before adding duplicate implementations.
9. P6-shared behavior follows Primavera P6 logic as the baseline; deviations require explicit documentation.
10. Final integration and acceptance remain under Jalal's technical coordination.

## 5. Current Stage Ownership

**Current stage:** Stage 33.4.73 — PostgreSQL Atomic Idempotency Verification Hardening.

- **Primary:** Hasan — PostgreSQL/client-sync atomicity and database-backed verification.
- **Integration/acceptance:** Jalal.
- **Client impact review:** Javad, only where synchronization contracts or client behavior are affected.
- **Release gate:** Stage 33.4.73 remains pending until actual PostgreSQL-backed runtime verification succeeds.

