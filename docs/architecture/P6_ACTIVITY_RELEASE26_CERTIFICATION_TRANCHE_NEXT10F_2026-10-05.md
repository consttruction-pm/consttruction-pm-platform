# P6 Activity Release 26 — Semantic Certification Tranche NEXT10F

Date: 2026-10-05
Owner: Jalal
Baseline: main `8b558327a59f538fa39db4316fa7070952e1918f`
Issue: #1172
Scope: Shared-Core typed P6 Activity field registry semantic/source evidence.

## Oracle authority

Oracle P6 Pro Integration API Field Summary, Activity class:
https://docs.oracle.com/cd/F51303_01/English/Integration/p6_pro_api_reference/FieldSummary.html

Oracle P6 EPPM REST API Release 26 Activity GET:
https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html

The Field Summary is the authority for native type and Read Only classification. The REST Activity GET documentation is used for the semantic description and calculation boundary. Oracle evidence is kept separate from the internal implementation representation.

## Exact fields

| P6 field | Oracle type | Oracle Read Only | Current registry type | Current writable | Current computed | Registry unit | Semantic boundary |
|---|---|---:|---|---:|---:|---|---|
| AtCompletionDuration | Duration | no | double | false | true | working-time | total working time from current start to current finish using the activity calendar |
| CostPercentComplete | Percent | X | double | false | true | percent | actual total cost / at completion total cost × 100; bounded 0–100 |
| CostPercentOfPlanned | Percent | X | double | false | true | percent | actual total cost / baseline planned total cost × 100; may exceed 100 |
| CostPerformanceIndex | double | X | double | false | true | none | earned value / actual cost |
| Duration1Variance | Duration | X | double | false | true | working-time | primary baseline duration − at completion duration |
| DurationVariance | Duration | X | double | false | true | working-time | project baseline duration − at completion duration |
| ExpenseCostPercentComplete | Percent | X | double | false | true | percent | actual expense cost / at completion expense cost × 100; bounded 0–100 |
| ExpenseCostVariance | Cost | X | double | false | true | currency | project baseline expense cost − at completion expense cost |
| ActualExpenseCost | Cost | X | double | false | true | none | actual costs for all project expenses associated with the activity |
| ActualMaterialCost | Cost | X | double | false | true | none | sum of regular and overtime material-resource costs |

## Certification result

- All ten identities already exist in the canonical Activity registry on current main.
- Oracle native types and Read Only classifications are consistent with the current Shared-Core non-writable/computed boundary for the nine computed fields except AtCompletionDuration, which is also computed but is documented as not Read Only in the Oracle Field Summary.
- No Activity dataclass expansion is required.
- No new scheduling, CPM, EVM, calendar, persistence, or API calculation logic is introduced.
- This artifact certifies source/type/mutability/semantic evidence only; persistence and interchange round-trip certification remain separate backend responsibilities.

## Focused regression

The companion test verifies deterministic canonical registry identity, internal type, writable/computed flags, unit, and seeded disposition for all ten fields. It also guards the important AtCompletionDuration distinction: Oracle exposes it as writable/non-read-only, while the current internal representation remains a computed scheduling value; this discrepancy is evidence for a future domain decision, not a license to silently change the scheduler.

## Notes

AtCompletionDuration was included in Issue #1098 but was not present in the merged #1099 ten-field scope. It is therefore explicitly included here rather than treated as already certified.

The certification work does not change the Jalal 3 weighted percentage until this PR is merged and the corresponding baseline row is re-evaluated.
