# P6 Activity Release 26 — Semantic Certification Tranche NEXT5L

Date: 2026-10-05
Owner: Jalal
Baseline: main@e18c003ffcb48f8ece5fd2e8b05d862a49cf4164
Issue: #1155

## Certified fields

| P6 field | Oracle type | Read-only / computed | Registry metadata |
|---|---|---|---|
| AtCompletionLaborCost | Cost / double | computed, read-only | DOUBLE, non-writable, computed, currency |
| AtCompletionLaborUnits | Unit / double | computed, read-only | DOUBLE, non-writable, computed, units |
| AtCompletionMaterialCost | Cost / double | computed, read-only | DOUBLE, non-writable, computed, currency |
| AtCompletionNonLaborCost | Cost / double | computed, read-only | DOUBLE, non-writable, computed, currency |
| AtCompletionNonLaborUnits | Unit / double | computed, read-only | DOUBLE, non-writable, computed, units |

## Published semantics

AtCompletionLaborCost = actual labor cost + remaining labor cost.
AtCompletionLaborUnits = actual labor units + remaining labor units.
AtCompletionMaterialCost = actual material cost + remaining material cost.
AtCompletionNonLaborCost = actual nonlabor cost + remaining nonlabor cost.
AtCompletionNonLaborUnits = actual nonlabor units + remaining nonlabor units.

## Certification boundary

These identities already exist in the canonical registry. This tranche adds current semantic evidence and deterministic regression coverage only. Historical typed-evidence artifacts remain unchanged.

No Activity dataclass expansion, CPM/EVM/calendar/formula engine change, persistence/API schema change, import/export mapping change, or client-side calculation is introduced.

## Oracle sources

- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html
- https://docs.oracle.com/cd/F51303_01/English/Integration/p6_pro_api_reference/FieldSummary.html
