# P6 Activity Release 26 — Semantic Certification Tranche NEXT10G

Date: 2026-10-05  
Owner: Jalal  
Baseline: `main@5a621b70a14b3e3a7405df1312f09f58091ddcab`  
Issue: #1119  
Scope: Shared-Core typed P6 Activity field registry semantic/source evidence only.

## Oracle authority

Oracle P6 Integration API Field Summary is used as the authority for Activity native field type and Read Only classification. Oracle P6 EPPM Release 26 Activity GET/PUT documentation is used for the current REST representation and descriptions.

## Exact fields

| P6 field | Oracle native type | Oracle Read Only | Registry type | Writable | Computed | Unit |
|---|---|---:|---|---:|---:|---|
| PlannedStartDate | BeginDate | No | DATE | Yes | No | — |
| PlannedFinishDate | EndDate | No | DATE | Yes | No | — |
| ActualStartDate | BeginDate | No | DATE | Yes | No | — |
| ActualFinishDate | EndDate | No | DATE | Yes | No | — |
| RemainingDuration | Duration | No | DURATION | No | Yes | working-time |
| ActualDuration | Duration | No | DURATION | No | Yes | working-time |
| DurationPercentComplete | Percent | No | PERCENTAGE | No | Yes | percent |
| PhysicalPercentComplete | Percent | No | PERCENTAGE | Yes | No | percent |
| PercentCompleteType | PercentCompleteType | No | ENUM | Yes | No | — |
| TotalFloat | Duration | Yes | DURATION | No | Yes | working-time |

The Oracle column is deliberately kept separate from the internal registry writable/computed disposition. A blank Read Only cell in the Oracle Field Summary is recorded as “No” and does not, by itself, assert that the field is scheduler-derived in every internal execution path.

## Semantic evidence

- PlannedStartDate: scheduled activity begin date; Oracle says the scheduler computes it and the project manager can update it manually.
- PlannedFinishDate: scheduled activity finish date; Oracle says the scheduler computes it and the project manager can update it manually.
- ActualStartDate: date on which the activity is actually started.
- ActualFinishDate: date on which the activity is actually finished.
- RemainingDuration: remaining working time from remaining start to remaining finish, using the activity calendar; before start it equals planned duration, after completion it is zero.
- ActualDuration: working time from actual start to actual finish for completed activities, or actual start to the current data date for in-progress activities, using the activity calendar.
- DurationPercentComplete: (planned duration - remaining duration) / planned duration × 100, using the current plan rather than the baseline.
- PhysicalPercentComplete: physical progress, either user-entered or calculated from activity weighted steps.
- PercentCompleteType: activity percent-complete basis; Oracle values are Physical, Duration, or Units.
- TotalFloat: amount of time an activity can be delayed before delaying project finish; Oracle describes calculation from late/early dates and says the calculation option is chosen when scheduling.

## Certification boundary

All ten identities already exist in the canonical Activity registry. This tranche does not add identities or change scheduler calculations. It adds only source/evidence documentation and deterministic regression coverage for the existing registry metadata.

No Activity dataclass expansion, duplicate Field Registry, persistence/API schema, CPM/EVM engine, calendar engine, formula engine, import/export mapping, or client-side scheduling semantics are introduced.

## Oracle sources

- Integration API Field Summary:
  https://docs.oracle.com/cd/F51303_01/English/Integration/p6_pro_api_reference/FieldSummary.html
- P6 EPPM Release 26 Activity GET:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- P6 EPPM Release 26 Activity PUT:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html
