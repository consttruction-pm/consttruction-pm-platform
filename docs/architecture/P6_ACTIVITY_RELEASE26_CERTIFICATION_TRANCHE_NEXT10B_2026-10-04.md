# P6 Activity Release 26 — Semantic Certification Tranche NEXT10B

Date: 2026-10-04
Owner: Jalal
Baseline: main `d5445a3c0a55c01c27e539b75be9b19bdc4f6028`

## Scope

This tranche certifies the existing canonical typed Activity registry metadata for ten exact Oracle P6 Release 26 Activity fields. No new registry identity is introduced.

## Fields and certification evidence

| P6 field | Oracle native type | Read-only | Internal registry type | Writable | Computed | Unit |
|---|---|---:|---|---:|---:|---|
| PerformancePercentCompleteByLaborUnits | Percent / REST double | Yes | PERCENTAGE | No | Yes | percent |
| PlannedExpenseCost | Cost / REST double | Yes | COST | No | Yes | currency |
| PlannedTotalCost | Cost / REST double | Yes | COST | No | Yes | currency |
| PlannedTotalUnits | Unit / REST double | Yes | UNIT | No | Yes | units |
| PostRespCriticalityIndex | Percent / REST double | No | PERCENTAGE | Yes | No | percent |
| PostResponsePessimisticFinish | EndDate / REST date-time | No | DATE | Yes | No | — |
| PostResponsePessimisticStart | BeginDate / REST date-time | No | DATE | Yes | No | — |
| PreRespCriticalityIndex | Percent / REST double | No | PERCENTAGE | Yes | No | percent |
| PreResponsePessimisticFinish | EndDate / REST date-time | No | DATE | Yes | No | — |
| PreResponsePessimisticStart | BeginDate / REST date-time | No | DATE | Yes | No | — |

External source evidence is recorded in:
`docs/architecture/P6_ACTIVITY_RELEASE26_TRANCHE_NEXT10B_EVIDENCE_2026-10-04.md`

## Internal certification

The current canonical registry contains all ten exact P6 names exactly once. The focused regression test verifies the independently expected type, mutability, computed/stored boundary, and unit for every field.

No Activity dataclass expansion is required by this tranche. No scheduler, CPM, EVM, calendar, formula, persistence, API, or client-side calculation semantics are changed.

## Disposition

These fields remain represented as canonical typed registry entries. This tranche records deterministic semantic evidence separately from the registry's global disposition flag so the certification gate does not silently promote unrelated fields.

## Acceptance

- 10/10 exact P6 names verified against Oracle evidence.
- 10/10 internal registry definitions verified.
- No duplicate registry identities.
- Focused regression test passes.
- Required project CI passes on the exact PR HEAD.
