# P6 Activity Release 26 — exact registry tranche next11E

Date: 2026-10-04  
Owner: Jalal  
Scope: Shared-Core typed P6 Activity field registry only.

## Exact fields

| P6 field | Oracle FieldSummary | Shared-Core metadata |
|---|---|---|
| StartDate | BeginDate; not Read Only | DATETIME, writable, stored/scheduler-bound |
| StartDate1Variance | Duration; Read Only | DURATION, computed |
| StartDate2Variance | Duration; Read Only | DURATION, computed |
| StartDate3Variance | Duration; Read Only | DURATION, computed |
| TaskStatusCompletion | TaskStatusCompletion; not Read Only | COMPLEX, writable, stored |
| TaskStatusDates | TaskStatusDates; not Read Only | COMPLEX, writable, stored |
| TaskStatusIndicator | boolean; not Read Only | BOOLEAN, writable, stored |
| ToCompletePerformanceIndex | double; Read Only | DOUBLE, computed |
| TotalCost1Variance | Cost; Read Only | COST, computed |
| TotalCost2Variance | Cost; Read Only | COST, computed |
| TotalCost3Variance | Cost; Read Only | COST, computed |

Oracle Release 26 REST defines StartDate as a date-time field and documents the three numbered StartDate variances as baseline-duration differences. Oracle P6 FieldSummary identifies the three TaskStatus fields as writable typed fields and identifies ToCompletePerformanceIndex plus TotalCost1Variance/2Variance/3Variance as read-only calculated values.

Sources:
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- https://docs.oracle.com/cd/G18294_01/English/Integration_Documentation/p6_eppm_api_reference/FieldSummary.html
- https://docs.oracle.com/cd/F25600_01/English/Integration/p6_pro_api_reference/FieldSummary.html

Oracle Release 26 defines TCPI as (BAC - EV) / (EAC - ACWP) and the three numbered total-cost variances as baseline total cost minus at-completion total cost.

## Boundary

Registry metadata and focused regression coverage only. No Activity dataclass, persistence schema, scheduler/CPM engine, EVM formula engine, calendar logic, API schema, or client-side scheduling changes.

## Cumulative parity target

Before this tranche on the current-main branch: 261 Activity registry records / 252 exact inventory matches / 23 inventory-only / 9 registry-only. After adding the 11 exact fields: 272 registry records / 263 exact / 12 inventory-only / 9 registry-only.
