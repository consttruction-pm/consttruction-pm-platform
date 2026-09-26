# Stage 34.2.4 — P0 Boundary Consolidation & Resource Envelope

Status: implementation in progress.

## Objective

Connect the concrete Stage 34.2 Backend P0 records to the already-published P0 generic resource envelopes without duplicating domain semantics.

## Rules

- Existing Stage 34.2.1 concrete contracts remain authoritative for record payload structure.
- P0 resource contracts are transport/resource envelopes only.
- Tenant, project and revision remain explicit at the envelope boundary.
- Shared revision bounds use the existing MAX_SAFE_PROJECT_REVISION source.
- Existing BackendP0API save/read behavior remains backward-compatible; envelope methods are additive.
- No Scheduling/P6, Calendar, Progress/EVM, Resource/Cost or financial calculations are reimplemented.

## Implemented mapping

- FieldDailyLog → field / daily_log
- FieldIssue → field / issue
- ChangeNotice → change / notice, variation, or claim
- ProcurementRFQ → procurement / rfq
