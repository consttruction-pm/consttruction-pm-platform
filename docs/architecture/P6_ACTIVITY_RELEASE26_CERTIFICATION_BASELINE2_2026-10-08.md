# P6 Activity Release 26 — Secondary Baseline Semantic Certification

Date: 2026-10-08  
Owner: Jalal  
Issue: #1322  
Base: `main@ee2c6e42047d7cc6c4baf5b60427ab1117a9250e`  
Scope: existing canonical Activity registry metadata and source evidence only.

## Oracle authority

Oracle P6 EPPM Release 26 Activity GET/PUT documentation and the Oracle Integration API Activity Field Summary are the authoritative sources for external field type, Read Only classification, and published semantics.

The Integration API Field Summary marks the secondary-baseline fields below Read Only. The internal `writable` and `computed` flags remain separate from that external fact.

## Certified fields

| P6 field | Registry type | Read Only | Writable | Computed | Unit |
|---|---|---:|---:|---:|---|
| Baseline2Duration | DURATION | Yes | No | Yes | working-time |
| Baseline2FinishDate | DATE | Yes | No | Yes | — |
| Baseline2PlannedDuration | DURATION | Yes | No | Yes | working-time |
| Baseline2PlannedExpenseCost | DOUBLE | Yes | No | No | currency |
| Baseline2PlannedLaborCost | DOUBLE | Yes | No | No | currency |
| Baseline2PlannedLaborUnits | DOUBLE | Yes | No | No | units |
| Baseline2PlannedMaterialCost | DOUBLE | Yes | No | No | currency |
| Baseline2PlannedNonLaborCost | DOUBLE | Yes | No | Yes | currency |
| Baseline2PlannedNonLaborUnits | DOUBLE | Yes | No | No | units |
| Baseline2PlannedTotalCost | DOUBLE | Yes | No | Yes | currency |
| Baseline2StartDate | DATE | Yes | No | Yes | — |

## Semantic disposition

- **Baseline2Duration** and **Baseline2PlannedDuration** are computed working-time values using the activity calendar.
- **Baseline2FinishDate** is the status-dependent current finish selected from planned, remaining, or actual finish; the registry therefore treats it as derived.
- **Baseline2PlannedExpenseCost**, **Baseline2PlannedLaborUnits**, **Baseline2PlannedMaterialCost**, and **Baseline2PlannedNonLaborUnits** are retained as read-only values because the reviewed Release 26 Activity material does not publish a derivation formula for them.
- **Baseline2PlannedLaborCost** is retained as a read-only value because the reviewed secondary-baseline description does not publish a derivation formula in the evidence available to this tranche.
- **Baseline2PlannedNonLaborCost** is computed where Oracle documents the nonlabor-units × default-price/time fallback.
- **Baseline2PlannedTotalCost** is computed because Oracle explicitly defines it as planned labor cost + planned nonlabor cost + planned expense cost.
- **Baseline2StartDate** is the status-dependent current start (planned until started, then actual), so it is treated as derived.

## Certification boundary

All eleven identities already existed in the canonical Activity registry. This tranche:
- certifies their Release 26 Read Only status;
- aligns registry duration/date/cost/unit semantics with the existing typed evidence and the stronger Release 26 semantic reading;
- changes only the existing `Baseline2PlannedLaborCost` computed flag where no calculation formula is evidenced;
- preserves all canonical field identities;
- adds deterministic registry regression coverage.

No Activity dataclass, CPM/P6/calendar/Progress/EVM formula, client calculation logic, persistence/API redesign, second registry, or new field identity is introduced.

The global P6 certification state remains unchanged: these fields stay `seeded_not_certified` until the tranche is independently verified after merge.

## Evidence

Existing typed evidence:
`docs/architecture/P6_ACTIVITY_SECONDARY_BASELINE_TYPED_EVIDENCE_2026-10-02.json`

Oracle sources:
- Oracle P6 EPPM Release 26 Activity GET
- Oracle P6 EPPM Release 26 Update Activity
- Oracle Integration API Activity Field Summary
