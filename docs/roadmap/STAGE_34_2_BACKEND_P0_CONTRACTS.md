# Stage 34.2.1 — Backend P0 Versioned Contracts

Status: **contract layer implemented — runtime verification pending**

## Included
- `field-daily-log.v1`: revision-scoped daily field record with auditable entries.
- `field-issue.v1`: field issue/observation boundary with severity, lifecycle and evidence.
- `change-notice.v1`: controlled change/variation/delay/claim notice boundary with schedule/cost/dependency references.
- `procurement-rfq.v1`: RFQ boundary with typed line items and supplier scope.

## Cross-cutting rules
- Every project-scoped resource carries tenant, project and authoritative revision.
- Audit metadata is part of the resource contract.
- Evidence-bearing workflows require traceable evidence references.
- Schedule/cost references are links to authoritative domain records; formulas remain in Shared Core.
- Application/API layers own authorization, idempotency, transactions and persistence.

## Verification
JSON schema parsing and structural review are required before runtime certification. GitHub Actions runtime verification remains infrastructure-dependent while Hosted Runner jobs terminate before executable steps.
