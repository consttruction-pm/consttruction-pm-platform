# P6 Activity Release 26 — exact registry tranche next12

Date: 2026-10-04  
Owner: Jalal  
Scope: Shared-Core typed P6 Activity field registry only.

## Exact fields

| P6 field | Oracle P6 Pro type / mutability | Shared-Core metadata |
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

Oracle P6 Pro FieldSummary is the mutability authority. Release 26 Activity REST documents the six stored past-period fields plus WBS/work-package identity. TotalCostVariance is a calculated cost variance. citeturn813888view0turn813888view3

## Boundary

Registry metadata, deterministic typed-metadata regression coverage, cumulative parity coverage, and evidence only. No Activity dataclass, persistence schema, scheduler/CPM engine, EVM formula engine, calendar logic, API schema, or client-side scheduling changes.

## Cumulative parity

Base current main before this tranche: 263 exact Activity inventory matches / 12 inventory-only / 9 registry-only.

Expected after this tranche: 275 exact Activity inventory matches / 0 inventory-only / 9 registry-only.

## Oracle semantic notes

Release 26 REST identifies TotalPastPeriodEarnedValueCostBCWP and TotalPastPeriodEarnedValueLaborUnits as total stored period earned-value values, TotalPastPeriodExpenseCost as stored period expense cost, and TotalPastPeriodPlannedValueCost / TotalPastPeriodPlannedValueLaborUnits as stored period planned values. WBSObjectId is the WBS identifier for the activity; WBSCode, WBSName, WBSNamePath and WorkPackageId are activity-level identity/linkage fields. citeturn735558search0turn735558search1

## Guardrail

Registry parity is not schedule-weighted progress. The approved «جلال 2» schedule changes only after verified merge and explicit evidence-to-activity mapping.
