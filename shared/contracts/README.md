# Shared Contracts

Versioned, machine-readable cross-client contracts live in this directory.

## Core / Sync

- `client-parity.schema.json`
- `project-portability.schema.json`
- `resource.schema.json`
- `resource-assignment.schema.json`
- `sync-conflict.schema.json`
- `sync-mutation.schema.json`
- `sync-outcome.schema.json`
- `time-scheduling.schema.json`

## Stage 34.1 — Shared Control Intelligence

- `dependency-graph.v1.schema.json`
- `control-intelligence-result.v1.schema.json`
- `control-scenario.v1.schema.json`
- `control-impact.v1.schema.json`
- `schedule-query.v1.schema.json`
- `schedule-query-result.v1.schema.json`
- `predictive-schedule-risk.v1.schema.json`
- `change-claim-impact.v1.schema.json`

## Stage 34.2 — Backend P0

- `field-daily-log.v1.schema.json`
- `field-issue.v1.schema.json`
- `change-notice.v1.schema.json`
- `procurement-rfq.v1.schema.json`

## Contract rules

- Project-scoped resources carry tenant, project and authoritative revision.
- Audit metadata is explicit at the backend resource boundary.
- Evidence-bearing workflows use traceable evidence references.
- Clients consume contracts and must not become authoritative calculation engines.
- Scheduling/P6, calendar, duration, Progress/EVM, Resource/Cost and financial formulas remain governed by their Shared Core contracts.
- Contract evolution is versioned; breaking changes require a new contract version.
