# Progress, EVM and Schedule Performance

Stage 32.3 established Physical Progress & Progress Rules.

## Pipeline
Progress Input -> Normalize -> Validate -> Apply Actuals -> Calculate Progress -> Remaining Work -> Remaining Duration -> Scheduling -> EVM -> Earned Schedule -> Reports.

## Controls
Baseline, Current, Actual and Forecast remain separate concepts. Effective progress changes create immutable revisions and append-only audit records. WBS roll-ups use appropriate weighted calculations rather than simple averaging.

## Current documented status
Stage 32.7 Reporting/Print Engine is complete at 100%. Next planned stage is Stage 32.8 Resource & Cost Control Center.

## 2026-10-01 Procurement integrity investigation
- Reviewed the P0 procurement commercial models, generic Backend P0 repository/application boundary, persistence behavior, contracts, roadmap acceptance criteria, and existing procurement tests.
- Confirmed a referential-integrity gap: Quote -> RFQ and Delivery -> PO are required domain references but are not currently resolved against stored records before save.
- Confirmed additional references that should be resolved when present: Bid Comparison -> RFQ and its Quote entries; Purchase Order -> RFQ/Quote/Commitment; Commitment -> PO.
- Confirmed scope consistency must be checked when resolving references so a reference cannot cross tenant/project boundaries.
- Confirmed the current generic repository can resolve procurement records by (tenant_id, project_id, record_type, record_id), so an application-level Procurement Reference Resolver fits the existing architecture without a storage-schema redesign.
- Confirmed reference validation should execute inside the existing application transaction/mutation path, before repository.save(), so a failed reference check cannot commit a partial mutation or idempotency result.
- Deliberately did not invent supplier-consistency or lifecycle-transition rules where the inspected contracts/roadmap do not explicitly define them.
- No production code or schema was changed in this section; this commit records the completed investigation and implementation boundary.
- Next implementation section: define the resolver contract and exact error semantics, then add focused tests before changing production code.

## Procurement reference test repair — 2026-10-01
- Fixed the missing RFQ test fixture and corrected the atomicity read assertion.
- Added coverage for a missing Purchase Order -> Commitment reference.
- Resolver inspection confirms the optional PO -> Commitment reference is already enforced; no production change was needed for that relation.
- Test commit: 979b732bd30f939fc8046424173a6bc8e092a824.
- Next: verify main-push CI, then continue with scope-isolation and transactional/idempotency coverage.
