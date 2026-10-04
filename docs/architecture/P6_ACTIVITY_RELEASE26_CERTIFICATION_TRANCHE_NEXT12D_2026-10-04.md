# P6 Activity Release 26 — Semantic Certification Tranche NEXT12D

Date: 2026-10-04
Owner: Jalal
Baseline: main `d17e900ddc951154e90ff24fa51daa2cbc63244b`
Issue: #1085

## Scope

This tranche certifies the existing canonical typed Activity registry metadata for twelve exact Oracle P6 Release 26 Activity fields. No new registry identity is introduced.

## Fields and current-main certification

| P6 field | Oracle Release 26 REST type | Internal registry type | Writable | Computed | Unit |
|---|---|---|---:|---:|---|
| TotalCostVariance | number (double) | COST | No | Yes | currency |
| TotalPastPeriodEarnedValueCostBCWP | number (double) | COST | Yes | No | currency |
| TotalPastPeriodEarnedValueLaborUnits | number (double) | UNIT | Yes | No | units |
| TotalPastPeriodExpenseCost | number (double) | COST | Yes | No | currency |
| TotalPastPeriodPlannedValueCost | number (double) | COST | Yes | No | currency |
| TotalPastPeriodPlannedValueLaborUnits | number (double) | UNIT | Yes | No | units |
| UnreadCommentCount | integer (int32) | INTEGER | No | Yes | — |
| WBSCode | string | STRING | No | Yes | — |
| WBSName | string | STRING | No | Yes | — |
| WBSNamePath | string | STRING | No | Yes | — |
| WBSObjectId | integer (int32) | OBJECT_ID | Yes | No | — |
| WorkPackageId | string | STRING | Yes | No | — |

Oracle Release 26 Activity Read/Update contracts expose all twelve exact names. Oracle documents TotalCostVariance as a calculated difference between project baseline total cost and at-completion total cost; the five TotalPastPeriod* fields are stored period values; UnreadCommentCount is an integer count; WBSCode/WBSName/WBSNamePath are strings; WBSObjectId is the WBS identifier; and WorkPackageId is a string. The same names are present in the current-main typed registry with the internal writable/computed boundary shown above.

## Boundary and non-goals

- No Activity dataclass expansion.
- No new P6 Field Registry identity.
- No persistence schema or API contract changes.
- No CPM/EVM/calendar/formula/scheduling changes.
- No client-side calculation semantics.
- Oracle REST schema evidence is kept separate from internal implementation metadata.

## Acceptance evidence

- 12/12 exact P6 names present in the Activity registry.
- 12/12 internal type/writable/computed/unit metadata asserted by deterministic regression coverage.
- No duplicate Activity identities introduced.
- Focused regression: `tests/p6/test_activity_release26_certification_next12d.py`.
- Required CI must pass on the exact PR HEAD before merge.

## Oracle sources

- Read Activities (Release 26): https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- Update Activities (Release 26): https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html
- P6 Pro FieldSummary reference used by the registry implementation: https://docs.oracle.com/cd/F51303_01/English/Integration/p6_pro_api_reference/FieldSummary.html
