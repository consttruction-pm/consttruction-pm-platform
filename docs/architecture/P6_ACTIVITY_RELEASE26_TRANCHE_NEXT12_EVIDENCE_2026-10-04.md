# P6 Activity Release 26 — exact registry tranche next12

Date: 2026-10-04  
Owner: Jalal  
Scope: Shared-Core typed P6 Activity field registry only.

## Exact fields

| P6 field | Oracle P6 Pro FieldSummary | Shared-Core metadata |
|---|---|---|
| TotalCostVariance | Cost; Read Only | COST, computed |
| TotalPastPeriodEarnedValueCostBCWP | Cost; writable | COST, writable, stored |
| TotalPastPeriodEarnedValueLaborUnits | Unit; writable | UNIT, writable, stored |
| TotalPastPeriodExpenseCost | Cost; writable | COST, writable, stored |
| TotalPastPeriodPlannedValueCost | Cost; writable | COST, writable, stored |
| TotalPastPeriodPlannedValueLaborUnits | Unit; writable | UNIT, writable, stored |
| UnreadCommentCount | int; Read Only | INTEGER, computed |
| WBSCode | String; Read Only | STRING, computed |
| WBSName | String; Read Only | STRING, computed |
| WBSNamePath | String; Read Only | STRING, computed |
| WBSObjectId | ObjectId; writable | OBJECT_ID, writable, stored |
| WorkPackageId | String; writable | STRING, writable, stored |

Oracle P6 Pro FieldSummary is the mutability authority. Release 26 Activity REST documents the stored period-value fields, WBS fields, and work-package identity on Activity.

## Boundary

Registry metadata, deterministic typed-metadata regression coverage, and evidence only. No Activity dataclass, persistence schema, scheduler/CPM engine, EVM formula engine, calendar logic, API schema, or client-side scheduling changes.

## Cumulative parity

Before tranche next12 on the prepared current-main line: 272 registry records / 263 exact inventory matches / 12 inventory-only / 9 registry-only.

Expected after tranche next12: 284 registry records / 275 exact inventory matches / 0 inventory-only / 9 registry-only.

## Oracle sources

- https://docs.oracle.com/cd/F25600_01/English/Integration/p6_pro_api_reference/FieldSummary.html
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html

## Guardrail

Do not claim project schedule-weighted progress from registry parity alone. Schedule progress changes only after verified merge/evidence mapping into the approved «جلال 2» schedule baseline.
