# P6 Activity Release 26 — Semantic Certification Tranche NEXT4K

Date: 2026-10-05
Owner: Jalal
Baseline: main@2845623e33f6dcb7847e6f8931079eec112212bf
Issue: #1153
Scope: current-main certification of four existing Activity fields whose historical artifacts provided typed read evidence but left writable/computed classification explicitly open.

## Oracle authority

Oracle Primavera P6 EPPM Release 26 Activity GET/PUT documentation is the authoritative source for current REST type/description. Oracle's Integration API Field Summary is used for field mutability classification.

## Exact certified fields

| P6 field | Oracle type | Oracle writable/read-only | Registry type | Writable | Computed | Unit |
|---|---|---|---|---:|---:|---|
| AutoComputeActuals | boolean | writable | BOOLEAN | Yes | No | — |
| ActualTotalUnits | double | computed/read-only | DOUBLE | No | Yes | — |
| AtCompletionTotalCost | double | computed/read-only | DOUBLE | No | Yes | — |
| AtCompletionTotalUnits | double | computed/read-only | DOUBLE | No | Yes | — |

## Semantic evidence

- **AutoComputeActuals** controls whether actual/remaining units, actual dates, and percent complete are automatically computed from planned values and schedule percent complete; when selected, project-actual application updates actual/remaining units and dates automatically. Oracle exposes this as an Activity option rather than a calculated result.
- **ActualTotalUnits** is the sum of Actual Labor Units and Actual Nonlabor Units.
- **AtCompletionTotalCost** is the total cost at completion, equal to at-completion labor cost + at-completion nonlabor cost + at-completion expense cost.
- **AtCompletionTotalUnits** is the sum of actual plus remaining units for resource assignments on the activity.

## Certification boundary

The canonical registry identities already exist and already match the certified writable/computed disposition. This tranche adds only current-main evidence and deterministic regression coverage.

No new Activity identity, Activity model expansion, CPM/EVM/calendar/formula implementation, persistence/API schema, import/export mapping, or client-side scheduling semantics are introduced.

Historical typed-read evidence artifacts from earlier tranches remain unchanged and are not rewritten.
 
## Oracle sources

- Oracle P6 EPPM Release 26 Activity GET:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- Oracle P6 EPPM Release 26 Activity PUT:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html
- Oracle P6 Integration API / Activity Field Summary:
  https://docs.oracle.com/cd/F51303_01/English/Integration/p6_pro_api_reference/FieldSummary.html
