# P6 Activity Release 26 — exact registry tranche next 10 fields

Date: 2026-10-04
Scope: Shared-Core typed P6 field registry only.
Authority: Oracle P6 EPPM Release 26 REST Activity GET/PUT contracts plus Oracle P6 Pro Integration API FieldSummary.

## External field evidence

| P6 field | Oracle native type | Read-only in FieldSummary | Shared-Core metadata | Semantic evidence |
|---|---|---:|---|---|
| PerformancePercentCompleteByLaborUnits | Percent / REST number(double) | Yes | PERCENTAGE, non-writable, computed | Earned Value Labor Units / Budget at Completion Labor Units × 100. |
| PlannedExpenseCost | Cost / REST number(double) | Yes | COST, non-writable, computed | Planned costs for project expenses associated with the activity. |
| PlannedTotalCost | Cost / REST number(double) | Yes | COST, non-writable, computed | Planned Labor + Planned Nonlabor + Planned Material + Planned Expense Cost. |
| PlannedTotalUnits | Unit / REST number(double) | Yes | UNIT, non-writable, computed | Planned Labor Units + Planned Nonlabor Units. |
| PostRespCriticalityIndex | Percent / REST number(double) | Yes | PERCENTAGE, non-writable, computed | Post Response Criticality Index. |
| PostResponsePessimisticFinish | EndDate / REST date-time | Yes | DATE, non-writable, computed | Post-response activity pessimistic finish. |
| PostResponsePessimisticStart | BeginDate / REST date-time | Yes | DATE, non-writable, computed | Post-response activity pessimistic start. |
| PreRespCriticalityIndex | Percent / REST number(double) | Yes | PERCENTAGE, non-writable, computed | Pre Response Criticality Index. |
| PreResponsePessimisticFinish | EndDate / REST date-time | Yes | DATE, non-writable, computed | Pre-response activity pessimistic finish. |
| PreResponsePessimisticStart | BeginDate / REST date-time | Yes | DATE, non-writable, computed | Pre-response activity pessimistic start. |

## Semantic boundary

Registry metadata only. No Activity dataclass expansion, CPM/EVM calculation changes, API/persistence schema changes, or client-side scheduling formulas.

## Certification note

Oracle evidence establishes field identity, external type, and Read Only status. Internal implementation certification remains separate; entries keep disposition `seeded_not_certified`.
