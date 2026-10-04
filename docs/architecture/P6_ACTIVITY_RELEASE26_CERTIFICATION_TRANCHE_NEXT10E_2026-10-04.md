# P6 Activity Release 26 — Semantic Certification Tranche NEXT10E

Date: 2026-10-04
Owner: Jalal
Baseline: main `bb4bbd31cec3acbd5bc15f333b0d76d16553299f`
Issue: #1098
Scope: Shared-Core typed P6 Activity field registry semantic/source evidence.

## Oracle authority

Oracle P6 Pro Integration API Field Summary, Activity class:
https://docs.oracle.com/cd/F51303_01/English/Integration/p6_pro_api_reference/FieldSummary.html

Oracle P6 EPPM REST API Release 26 Activity GET/PUT:
https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html

The Field Summary is the source for native type and Read Only classification. The REST Activity GET/PUT documentation is used as the semantic description authority. Oracle evidence is kept separate from internal implementation disposition.

## Exact fields

| P6 field | Oracle type | Oracle Read Only | Current registry type | Current writable | Current computed | Registry unit | Semantic boundary |
|---|---|---:|---|---:|---:|---|---|
| AccountingVariance | Cost | X | double | false | true | none | planned value minus actual cost; computed |
| AccountingVarianceLaborUnits | Unit | X | double | false | true | none | planned value labor units minus actual units; computed |
| AtCompletionVariance | Cost | X | double | false | true | currency | BAC minus EAC; computed |
| Duration2Variance | Duration | X | double | false | true | working-time | secondary baseline duration minus at-completion duration; computed |
| Duration3Variance | Duration | X | double | false | true | working-time | tertiary baseline duration minus at-completion duration; computed |
| DurationPercentOfPlanned | Percent | X | double | false | true | percent | actual duration divided by baseline duration × 100; computed |
| EarnedValueCost | Cost | X | double | false | true | currency | BAC × performance percent complete; computed |
| ExpenseCost1Variance | Cost | X | double | false | true | currency | primary baseline expense cost minus at-completion expense cost; computed |
| ExpenseCost2Variance | Cost | X | double | false | true | currency | secondary baseline expense cost minus at-completion expense cost; computed |
| ExpenseCost3Variance | Cost | X | double | false | true | currency | tertiary baseline expense cost minus at-completion expense cost; computed |

## Certification result

- All ten identities already exist in the canonical Activity registry.
- Oracle native types and Read Only classifications are consistent with the intended Shared-Core non-writable/computed boundary for these ten fields.
- No Activity dataclass expansion is required.
- No new calculation logic is introduced. The existing Shared Scheduling/Progress/EVM semantics remain authoritative.
- This artifact certifies source/type/mutability evidence only; persistence/import-export certification remains a separate backend responsibility.

## Focused regression

The companion test verifies deterministic registry identity/type/writable/computed/unit metadata for all ten fields and guards against accidental promotion to writable fields.

## Oracle evidence references

Field Summary lines 39-40, 70, 134-137, 143, 151-153 document the corresponding Activity fields, native types, Read Only markers, and semantic descriptions.
