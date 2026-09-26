# Stage 34.2.8 — Procurement / Commercial Commitments Core

Status: implementation in progress.

## Scope

Extend the existing RFQ boundary into Quote, Bid Comparison, Purchase Order, Commitment and Delivery records.

## Acceptance criteria

- Supplier quotes reference an authoritative RFQ and preserve exact quantity/unit-price values.
- Bid comparisons record supplier/quote compliance and auditable selection/approval without embedding ranking formulas.
- Purchase orders preserve supplier, RFQ/quote references, line items, delivery dates and approval reference.
- Procurement commitments preserve the committed amount as an exact Decimal value and link to cost/activity references.
- Deliveries record received quantities and optional inspection/punch links; received status requires a receipt reference.
- All resources carry tenant, project, authoritative revision, audit metadata and evidence references.
- Generic P0 procurement resource envelope is used for transport.
- Existing ProcurementRFQ behavior remains backward-compatible.
- No project cost, EVM, schedule-impact or financial calculation engine is reimplemented.
- Python and client runtime verification is required before merge.
