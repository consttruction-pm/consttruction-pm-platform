# P6 Activity Release 26 — Secondary Baseline Semantic Certification

Date: 2026-10-08  
Owner: Jalal  
Issue: #1322  
Base: current `main`  
Scope: existing canonical Activity registry metadata and authoritative Release 26 evidence only.

## Oracle authority

Oracle P6 EPPM Release 26 Activity GET/PUT documentation and the Oracle Integration API Activity Field Summary are the authoritative sources for external field type, Read Only classification, and published semantics.

The Integration API Field Summary marks the secondary-baseline fields below Read Only. The internal `writable` and `computed` flags remain implementation metadata and are preserved from the canonical registry unless independently evidenced.

## Certified fields

| P6 field | Registry type | Read Only | Writable | Computed | Unit |
|---|---|---:|---:|---:|---|
| Baseline2Duration | DOUBLE | Yes | No | Yes | working-time |
| Baseline2FinishDate | DATE | Yes | No | Yes | — |
| Baseline2PlannedDuration | DOUBLE | Yes | No | Yes | working-time |
| Baseline2PlannedExpenseCost | DOUBLE | Yes | No | Yes | currency |
| Baseline2PlannedLaborCost | DOUBLE | Yes | No | Yes | currency |
| Baseline2PlannedLaborUnits | DOUBLE | Yes | No | Yes | units |
| Baseline2PlannedMaterialCost | DOUBLE | Yes | No | Yes | currency |
| Baseline2PlannedNonLaborCost | DOUBLE | Yes | No | Yes | currency |
| Baseline2PlannedNonLaborUnits | DOUBLE | Yes | No | Yes | units |
| Baseline2PlannedTotalCost | DOUBLE | Yes | No | Yes | currency |
| Baseline2StartDate | DATE | Yes | No | Yes | — |

## Semantic disposition

- All eleven identities already existed in the canonical Activity registry; this tranche adds no duplicate identity.
- The Release 26 evidence certifies the secondary-baseline fields as Read Only at the external P6 field contract.
- Registry data types and internal `computed` classifications are preserved from the canonical registry on current `main`; this tranche does not reinterpret those flags as newly proven Oracle formulas.
- No Activity dataclass, CPM/P6/calendar/Progress/EVM formula, client calculation logic, persistence/API redesign, second registry, or new field identity is introduced.

## Certification boundary

The global P6 certification state remains unchanged: these fields stay `seeded_not_certified` until this tranche is independently verified after merge.

## Evidence

Existing typed evidence:
`docs/architecture/P6_ACTIVITY_SECONDARY_BASELINE_TYPED_EVIDENCE_2026-10-02.json`

Oracle sources:
- Oracle P6 EPPM Release 26 Activity GET
- Oracle P6 EPPM Release 26 Update Activity
- Oracle Integration API Activity Field Summary
