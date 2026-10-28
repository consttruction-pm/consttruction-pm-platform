# Quantity Takeoff and BOQ — First Executable Slice

**Owner requirement:** 2026-10-28  
**Implementation issue:** [#1617](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1617)  
**Branch PR:** [#1618](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1618)  
**Status:** First domain/persistence/action slice implemented on the feature branch. Not merged to `main`; not full takeoff/estimating V1.

## 1. What is executable now

Implemented in `src/construction_pm/quantity_takeoff.py`:

- Typed `QuantityTakeoffLine` and `QuantityTakeoffEstimate` contracts.
- Decimal-based billable quantity calculation: base measured quantity × (1 + waste percentage / 100).
- Optional source-backed unit rates and currency-specific minor-unit precision; financial line amounts use explicit Decimal `ROUND_HALF_UP` at the supplied currency precision.
- Separate totals by currency. Mixed currencies are never summed together; lines using the same currency cannot silently disagree about its minor-unit precision.
- An item without a unit rate has `extended_cost = null` and increases the unpriced-line count; it is never treated as zero cost.
- Strict limits and validation for line counts, IDs, units, finite/non-negative quantities and rates, waste, measurement status, currency, provenance text and duplicate item identifiers.
- Immutable, tenant/project/revision-scoped SQLite and PostgreSQL repository adapters, with exact-replay behavior, ID-conflict detection and stored-record revalidation.

The action tool `quantity.takeoff.create` is wired into the authenticated private preview runtime. It is listed as a typed tool that requires human approval, has an explicit planner/project-admin permission boundary, writes through the shared action idempotency/transaction boundary and performs a fresh repository read-back. No estimate is persisted when only the proposal is created.

## 2. Record and calculation rules

A line currently accepts:

- Stable line ID, optional classification code, description and explicit unit.
- Base quantity, waste/allowance percentage and derived billable quantity.
- Measurement status: `measured`, `calculated` or `provisional`; each record also stores a human-readable calculation/measurement basis.
- Optional source reference; measured and calculated lines require a reference.
- Optional unit rate, currency, explicit currency minor-unit precision and rate basis. A rate cannot be recorded without its currency precision and stated basis.
- Derived extended cost when priced.

An estimate records the current tenant, project and project revision, estimate ID/version, creator, approving proposal ID and timestamp. Reuse of an estimate ID with changed content fails rather than overwriting the old estimate. A new estimate should use a new ID until a version/supersession workflow is deliberately implemented.

## 3. Honest provenance boundary

This slice stores source and rate references as claims but does **not** yet connect them to an authoritative project document/source registry or approved rate-card repository. Accordingly each line emits:

- `source_verification_status: "unverified_reference"`
- `rate_verification_status: "unverified_rate_basis"` for priced lines
- Summary flags `source_verification_performed: false` and `rate_verification_performed: false`

These fields must not be reinterpreted as verified evidence. Human approval proves the user approved the exact proposal; it does not automatically prove the referenced drawing, measurement or price is authentic. Before production estimates can be labeled verified, connect references to persisted sources/rate cards and verify access scope, content hash/version, source date, currency, validity period and applicable rate rules.

The local language model may organize a proposal but is not the arithmetic authority and must not invent source facts, quantities, productivity rates or prices. Input/output figures are calculated in this deterministic module.

## 4. Verification evidence

The exact tested code head is `5dd00c6d2e469676d6c009b4a0d4d206442a1f43`:

- [ConstructionPM CI](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40608679751): Python 3.11, 3.12 and 3.13 passed.
- [PostgreSQL Integration](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40608679770): passed.
- [Client Typecheck](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40608679913): Web, Desktop, Mobile and Client-Sync passed.

Tests cover deterministic Decimal arithmetic, source/rate status disclosure, invalid/negative inputs, unpriced lines, per-line rounding, currency grouping/precision, tenant/project/revision isolation, immutable ID behavior, approval-before-write, the execution transaction/idempotency boundary and fresh read-back in a full private-preview HTTP workflow.

## 5. What is still missing before production BOQ acceptance

1. Register and wire the action in a production authenticated composition with actual current grants and a PostgreSQL integration/E2E test for the new repository.
2. Connect a trustworthy source-evidence resolver for drawing/document/page/row/cell or measured-object references, including source version/content hash and access checks.
3. Connect approved rate cards/effective dates/currency policy and validate rates rather than accepting an arbitrary text basis.
4. Implement supported drawing, document, spreadsheet and project-file intake into a normalized takeoff staging format, with visible source mapping and ambiguity reports. Do not claim 2D image or 3D/BIM measurement until tested parsers/runtimes exist.
5. Link accepted BOQ lines to supported WBS/work packages, activities, resource demand, procurement and cost records through typed application services.
6. Add reviewed version/supersession and variant comparison workflow with backup/export/import behavior.
7. Add localized Web UI for line review, quantity/rate evidence, unpriced rows, estimate ranges and approval; the current slice is a typed tool/repository contract and preview action path, not the finished BOQ user interface.

## 6. Remaining CUBI Engineering Intelligence work

This slice does not complete #1617 or assistant V1. Crew/labor/equipment planning and capacity checks, evidenced risk findings/corrective actions, persisted Form Builder definitions/submissions/approval routes, PMBOK-tailored report templates/data-grounded charts, full production tool registration, authorized research/publishing, durable interaction learning, retention/deletion, backup/restore/migration and golden-regression rollback remain separate open work packages. Every one must be implemented as real application behavior and tested end to end; a prompt or document alone is not completion.
