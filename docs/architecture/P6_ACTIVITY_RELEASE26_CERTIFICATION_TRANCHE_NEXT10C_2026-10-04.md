# P6 Activity Release 26 — Semantic Certification Tranche NEXT10C

Date: 2026-10-04
Owner: Jalal
Baseline: main `3b8588bace177be760183883032aa0ae782f3209`

## Scope

This tranche certifies the existing canonical typed Activity registry metadata for ten exact Oracle P6 Release 26 Activity fields. No new registry identity is introduced.

## Fields and certification evidence

| P6 field | Oracle native type | Read-only | Internal registry type | Writable | Computed | Unit |
|---|---|---:|---|---:|---:|---|
| PrimaryResourceId | String | Yes | STRING | No | Yes | — |
| PrimaryResourceObjectId | ObjectId | No | OBJECT_ID | Yes | No | — |
| ProjectFlag | string | Yes | STRING | No | Yes | — |
| ProjectObjectId | ObjectId | No | OBJECT_ID | Yes | No | — |
| ProjectProjectFlag | string | Yes | STRING | No | Yes | — |
| RemainingEarlyFinishDate | EndDate / REST date-time | No | DATE | No | Yes | — |
| RemainingExpenseCost | Cost / REST number(double) | Yes | COST | No | Yes | currency |
| RemainingFloat | Duration / REST number(double) | Yes | DURATION | No | Yes | working-time |
| RemainingLateFinishDate | EndDate / REST date-time | No | DATE | No | Yes | — |
| RemainingLateStartDate | BeginDate / REST date-time | No | DATE | No | Yes | — |

External field evidence is recorded in:
`docs/architecture/P6_ACTIVITY_RELEASE26_TRANCHE_NEXT10C_EVIDENCE_2026-10-04.md`

## Internal certification

The current canonical Activity registry contains all ten exact P6 names in the Activity subject area. The focused regression test verifies the expected internal type, mutability, computed/stored boundary, unit, and Oracle source for every field.

No Activity dataclass expansion is required by this tranche. No scheduler, CPM, EVM, calendar, formula, persistence, API, or client-side calculation semantics are changed.

## Disposition

These fields remain represented as canonical typed registry entries. This certification records deterministic semantic evidence without promoting unrelated registry entries or changing the global registry disposition.

## Acceptance

- 10/10 exact P6 names verified against Oracle evidence.
- 10/10 internal registry definitions verified.
- No duplicate Activity registry identities.
- Focused regression test passes.
- Required project CI passes on the exact PR HEAD.