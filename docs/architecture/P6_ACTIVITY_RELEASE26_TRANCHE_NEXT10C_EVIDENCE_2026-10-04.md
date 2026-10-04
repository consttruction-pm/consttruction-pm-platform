# P6 Activity Release 26 — exact registry tranche next 10 fields (next tranche)

Date: 2026-10-04
Scope: Shared-Core typed P6 field registry only.
Authority: Oracle P6 Pro Integration API FieldSummary plus Oracle P6 EPPM Web Services Activity Fields / Release 26 REST Activity contract.

## External field evidence

| P6 field | Oracle native type | Read-only | Shared-Core metadata | Semantic evidence |
|---|---|---:|---|---|
| PrimaryResourceId | String | Yes | STRING, non-writable, computed | Name/identifier of the primary resource. |
| PrimaryResourceObjectId | ObjectId | No | OBJECT_ID, writable | Unique ID of the primary resource responsible for the activity. |
| ProjectFlag | string | Yes | STRING, non-writable, computed | Indicates whether the associated WBS node is a Project/EPS node. |
| ProjectObjectId | ObjectId | No | OBJECT_ID, writable | Unique ID of the associated project. |
| ProjectProjectFlag | string | Yes | STRING, non-writable, computed | Indicates whether the associated Project/EPS node is a Project or EPS. |
| RemainingEarlyFinishDate | EndDate / REST date-time | No | DATE, non-writable, computed | Remaining early/early finish date calculated by the scheduler. |
| RemainingExpenseCost | Cost / REST number(double) | Yes | COST, non-writable, computed | Remaining costs for project expenses associated with the activity. |
| RemainingFloat | Duration / REST number(double) | Yes | DURATION, non-writable, computed | Remaining float; computed from late finish minus remaining finish. |
| RemainingLateFinishDate | EndDate / REST date-time | No | DATE, non-writable, computed | Remaining late finish date calculated by the scheduler. |
| RemainingLateStartDate | BeginDate / REST date-time | No | DATE, non-writable, computed | Remaining late start date calculated by the scheduler. |

## Semantic boundary

Registry metadata only. No Activity dataclass expansion, CPM/EVM calculation changes, API/persistence schema changes, or client-side scheduling formulas.

## Certification note

Oracle FieldSummary establishes field identity, native type, and Read Only status for the core API representation. The Oracle Activity Fields reference supplies the Activity-field descriptions and confirms REST/Web Services representations. These entries remain `seeded_not_certified`; implementation certification is separate.
