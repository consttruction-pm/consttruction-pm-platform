# Shared Contracts

Versioned, cross-client contracts live in this directory.

## Control Intelligence — Stage 34.1

| Contract | Version | Purpose |
| --- | --- | --- |
| `dependency-graph.v1.schema.json` | v1 | Cross-domain dependency/impact graph |
| `control-intelligence-result.v1.schema.json` | v1 | Auditable control-intelligence findings and proposed actions |
| `control-scenario.v1.schema.json` | v1 | Revision-scoped non-authoritative scenarios |
| `control-impact.v1.schema.json` | v1 | Cross-domain impact links |
| `schedule-query.v1.schema.json` | v1 | Natural-language schedule query request |
| `schedule-query-result.v1.schema.json` | v1 | Traceable schedule-query result |
| `predictive-schedule-risk.v1.schema.json` | v1 | Evidence-backed predictive schedule-risk boundary |
| `change-claim-impact.v1.schema.json` | v1 | Change/Claim links to schedule/cost references and evidence |

## Rules

- Contracts are versioned and machine-readable.
- Tenant, project and authoritative project revision are explicit wherever project-scoped state is represented.
- Source/evidence references are mandatory for control-intelligence outputs.
- Consequential proposed actions default to application-layer approval.
- Clients consume contracts; they do not become authoritative calculation engines.
- Primavera P6 scheduling, calendar, duration, Progress/EVM, Resource/Cost and financial semantics remain governed by their existing Shared Core contracts.
