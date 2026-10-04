# P6 Activity Release 26 — exact registry tranche next11E

Date: 2026-10-04  
Owner: Jalal  
Scope: Shared-Core typed P6 Activity field registry only.

## Exact fields

| P6 field | Oracle type | Read Only | Shared-Core metadata |
|---|---|---:|---|
| StartDate | date-time | No | DATETIME, writable, stored |
| StartDate1Variance | double / Duration | Yes | DURATION, non-writable, computed |
| StartDate2Variance | double / Duration | Yes | DURATION, non-writable, computed |
| StartDate3Variance | double / Duration | Yes | DURATION, non-writable, computed |
| TaskStatusCompletion | string | No | STRING, writable, stored |
| TaskStatusDates | string | No | STRING, writable, stored |
| TaskStatusIndicator | boolean | No | BOOLEAN, writable, stored |
| ToCompletePerformanceIndex | double | Yes | DOUBLE, non-writable, computed |
| TotalCost1Variance | double / Cost | Yes | COST, non-writable, computed |
| TotalCost2Variance | double / Cost | Yes | COST, non-writable, computed |
| TotalCost3Variance | double / Cost | Yes | COST, non-writable, computed |

Oracle Release 26 defines StartDate as the activity start boundary (remaining start until actual start), the three numbered start variances as baseline differences, TaskStatus fields as activity status information, TCPI as (BAC-EV)/(EAC-ACWP), and the numbered TotalCost variances as primary/secondary/tertiary baseline total cost minus at-completion total cost. citeturn474811search0turn474811search1turn474811search2

## Boundary

Registry metadata and focused regression coverage only. No Activity dataclass, persistence schema, scheduler/CPM, EVM calculation engine, calendar logic, API contract, or client-side scheduling changes.

The tranche deliberately does not include fields already covered by the open #1045 tranche: RemainingTotalCost, RemainingTotalUnits, SchedulePercentComplete, SchedulePerformanceIndexLaborUnits, ScheduleVariance, ScheduleVarianceIndex, ScheduleVarianceIndexLaborUnits, ScheduleVarianceLaborUnits, SecondaryConstraintDate, SecondaryConstraintType.
