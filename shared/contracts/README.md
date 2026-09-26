# Shared API Contracts v1

These schemas are authoritative for both Web and Desktop clients.

- Decimal-like financial and unit values cross the API as canonical decimal strings, never floating-point JSON numbers.
- Dates use ISO-8601 representation.
- IDs are strings.
- Nullable fields are explicitly nullable.
- Schema versions are part of the contract identity.
- API serialization must invoke Domain methods for calculated values; it must never serialize a bound method/reference.
- Web and Desktop consume the same contract.

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

### Concrete resource contracts

- `field-daily-log.v1.schema.json`
- `field-issue.v1.schema.json`
- `change-notice.v1.schema.json`
- `procurement-rfq.v1.schema.json`
- `field-timecard.v1.schema.json`
- `equipment-status-report.v1.schema.json`
- `field-inspection.v1.schema.json`
- `quality-record.v1.schema.json`
- `safety-observation.v1.schema.json`
- `punch-item.v1.schema.json`

### Change / Claim Core

- `change-case.v1.schema.json`
- `claim-record.v1.schema.json`

### Procurement / Commercial Core

- `procurement-rfq.v1.schema.json`
- `procurement-quote.v1.schema.json`
- `procurement-bid-comparison.v1.schema.json`
- `purchase-order.v1.schema.json`
- `procurement-commitment.v1.schema.json`
- `procurement-delivery.v1.schema.json`

### Portfolio Control Read Model

- `portfolio-control-snapshot.v1.schema.json`

### Generic resource envelopes

- `p0-field-resource.schema.json`
- `p0-change-resource.schema.json`
- `p0-procurement-resource.schema.json`
- `p0-dependency-resource.schema.json`

The concrete contracts define payload semantics; generic P0 resource contracts define the transport/resource envelope and do not replace Shared Core calculations.

Change and Claim records link to schedule/cost/dependency/impact references. Financial quantum, entitlement calculation and schedule impact calculations remain authoritative in their existing domain engines. Procurement monetary values are persisted and transported as exact Decimal strings; this layer does not calculate project cost or earned value.

Portfolio Control is a cross-project read model. It references authoritative project results and revisions; it does not duplicate scheduling, progress/EVM, resource/cost or financial calculations.

Stage 34.2.5 adds attendance/timecard and equipment-status field workflows. Stage 34.2.6 adds inspection, quality, safety and punch/closeout workflows. Field records remain revision-aware and carry explicit evidence/audit boundaries.

## Contract evolution rules

- Project-scoped resources carry tenant, project and authoritative revision.
- Audit metadata is explicit at the backend resource boundary.
- Evidence-bearing workflows use traceable evidence references.
- Clients consume contracts and must not become authoritative calculation engines.
- Scheduling/P6, calendar, duration, Progress/EVM, Resource/Cost and financial formulas remain governed by their Shared Core contracts.
- Breaking changes require a new contract version.
