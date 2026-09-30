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

## 5. Current Stage Ownership — AUTHORITATIVE RULE (2026-09-30)

The old Stage 33.4.73 statement is stale and must not be used to choose the next task. The authoritative baseline is the latest `main` branch plus the merged PR history and current roadmap/status evidence.

### Current operating rule
1. **Main is the source of truth.** No task may start from an old branch, old PR, screenshot, memory, or previous chat state.
2. Before implementation, the owner must reconcile the target area against current `main`.
3. If the requested capability already exists on `main), the task is **not reimplemented**. The owner instead adds missing verification, integration, UI exposure, persistence, documentation, or a clearly identified gap.
4. A stale branch is never "continued" by default. Rebuild only the still-valid intent on current `main`.
5. Every task must declare: current-main base SHA, exact scope, ownership boundary, prerequisite PRs, files/modules expected to change, and explicit non-goals.
6. A task is complete only after focused tests, relevant regression tests, required CI gates, and merge into `main`.
7. After merge, the old working branch is no longer an implementation source. It becomes historical evidence only.
8. No team member may create a second implementation of an authoritative calculation, API contract, persistence model, or client-sync rule owned by another team member.
9. If a reviewer discovers overlap with existing work, the task stops immediately and is converted to a reconciliation/verification task.
10. ChatGPT/Jalal maintains the dependency order and final technical acceptance; team members do not independently redefine the roadmap.

### Release priority
The team is now operating under a **Finish Product / Finish Website priority**:
- P0: keep `main` green and eliminate regressions/duplication.
- P1: complete the end-to-end Web product path: authentication/authorization, project creation, WBS/activity entry, scheduling, calendars, resources/costs, progress/control, documents, reports, import/export, settings and bilingual UX.
- P2: complete Desktop/Mobile parity only where required by an already-defined product contract.
- P3: AI, advanced automation and non-blocking enhancements after the core Web product path is commercially usable.
- No new side feature may displace an unfinished P1 release path unless it is required to unblock P1.

## 6. Javad — mandatory anti-duplication client rule

Javad owns the client experience, but **does not own a second business/calculation implementation**.

Before starting any client task, Javad must:
- inspect current `main` and the authoritative Shared Core/API contract;
- search for existing Web/Desktop/Mobile implementation before creating a new component;
- reuse the existing contract, DTO, calculation result and sync boundary;
- create UI adapters/view-models only where presentation requires them;
- never recreate scheduling, calendar arithmetic, P6 formulas, float, EVM, resource/cost or authoritative validation logic in the client;
- stop and report an overlap instead of copying or forking an existing implementation.

### Javad delivery order
1. Web Main Workspace and navigation shell.
2. Project/WBS/Activity entry and editing.
3. Gantt and schedule-result presentation using Shared Core/API results.
4. Calendar/resource/cost/progress/document/report screens using existing contracts.
5. Import/export and print/report UX.
6. Persian/English + RTL/LTR + Jalali/Gregorian presentation.
7. Desktop/Mobile parity and offline behavior.
8. AI assistant/guide UI after the core Web workflow is complete.

## 7. Hasan — mandatory anti-duplication backend rule

Hasan must not restart a previously merged persistence/API implementation. For every new backend task:
- start from current `main`;
- inspect the authoritative Shared Core contract first;
- search existing repositories/application/API adapters before adding a new one;
- if a capability exists in SQLite but PostgreSQL/API exposure is missing, implement only that missing boundary;
- preserve tenant/project/revision/idempotency/transaction semantics;
- use real PostgreSQL verification where the task is database-backed;
- if Codex review quota is unavailable, mark the task blocked rather than creating a duplicate branch or asking another person to reimplement it.

## 8. Jalal — integration and completion control

Jalal owns:
- the authoritative task sequence;
- Shared Core/P6/scheduling/calculation semantics;
- cross-team dependency resolution;
- duplicate-work detection;
- acceptance criteria;
- final regression review;
- release readiness.

Jalal must not repeatedly rewrite already merged work merely because an old branch or conversation state appears incomplete. The current `main` state always wins.

## 9. Mandatory task record

Every new implementation PR must contain these fields:

- **Base:** current `main` SHA.
- **Owner:** exactly one primary owner.
- **Scope:** one bounded capability.
- **Existing implementation checked:** yes/no + paths/PRs checked.
- **Dependencies:** prerequisite PRs/contracts.
- **Production behavior changed:** yes/no.
- **Tests added/updated:** exact test scope.
- **CI gates:** required checks.
- **Non-goals:** explicit exclusions.
- **Next point after merge:** one concrete next task.

A PR without this information is not eligible for merge.

## 10. Merge and branch hygiene

`main` is the only integration baseline. Required reviews/status checks should protect it; GitHub supports enforcing pull requests, approvals and status checks on protected branches. citeturn0search0turn0search2

When a PR is merged:
- record its merge SHA and evidence;
- update the continuation/status record;
- close or archive stale successor branches;
- never revive the old branch as the next implementation baseline.

When a PR is rejected or superseded:
- record the reason;
- preserve only useful evidence;
- do not copy its implementation blindly into a new branch.

## 11. Definition of Done for the product

A feature is not "done" because its Python/domain code exists.

For release completion it must have:
1. Shared/domain authority where applicable.
2. Backend/API boundary where applicable.
3. Web UI integration.
4. Persistence where required.
5. Tests and regression coverage.
6. Error/permission handling.
7. Persian/English and RTL/LTR treatment where user-visible.
8. Import/export compatibility where applicable.
9. Documentation/traceability.
10. CI/runtime verification.
11. No known duplicate implementation.
12. A usable end-to-end Web workflow.

The immediate objective is therefore **not to increase the Stage number**. It is to convert the already-developed capabilities into a coherent, tested, usable Web product and close only the real remaining gaps.
