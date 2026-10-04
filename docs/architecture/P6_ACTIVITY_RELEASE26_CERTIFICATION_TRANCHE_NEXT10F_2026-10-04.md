# P6 Activity Release 26 — Semantic Certification Tranche NEXT10F

Date: 2026-10-04
Owner: Jalal
Baseline: current main
Issue: #1105 / superseded #1107
Scope: Shared-Core typed P6 Activity field registry semantic/source evidence.

## Oracle authority

Oracle P6 Pro Integration API Field Summary (Activity) is the authority for native type and Read Only classification. Oracle P6 EPPM Release 26 Activity GET/PUT documentation is used for Release 26 field descriptions and REST representations.

## Exact fields

| P6 field | Oracle native type | Read Only | Current registry type | Writable | Computed | Unit |
|---|---|---:|---|---:|---:|---|
| AtCompletionLaborUnitsVariance | Unit | X | DOUBLE | No | Yes | units |
| AtCompletionMaterialCost | Cost | X | DOUBLE | No | Yes | currency |
| AtCompletionTotalCost | Cost | X | DOUBLE | No | Yes | currency |
| AtCompletionTotalUnits | Unit | X | DOUBLE | No | Yes | units |
| DurationVariance | Duration | X | DOUBLE | No | Yes | working-time |
| ExpenseCostPercentComplete | Percent | X | DOUBLE | No | Yes | percent |
| ExpenseCostVariance | Cost | X | DOUBLE | No | Yes | currency |
| LaborCost3Variance | Cost | X | DOUBLE | No | Yes | currency |
| LaborCostPercentComplete | Percent | X | DOUBLE | No | Yes | percent |
| LaborCostVariance | Cost | X | DOUBLE | No | Yes | currency |

## Semantic evidence

- AtCompletionLaborUnitsVariance: project-baseline planned total labor units minus estimate-at-completion labor units.
- AtCompletionMaterialCost: sum of actual and remaining material-resource costs.
- AtCompletionTotalCost: at-completion labor + nonlabor + expense costs.
- AtCompletionTotalUnits: actual plus remaining units for the resource assignment/activity.
- DurationVariance: project-baseline duration minus at-completion duration.
- ExpenseCostPercentComplete: actual expense cost / at-completion expense cost × 100.
- ExpenseCostVariance: project-baseline expense cost minus at-completion expense cost.
- LaborCost3Variance: tertiary-baseline labor cost minus at-completion labor cost.
- LaborCostPercentComplete: actual labor cost / at-completion labor cost × 100.
- LaborCostVariance: project-baseline labor cost minus at-completion labor cost.

## Certification boundary

All ten identities already exist in the canonical Activity registry. This tranche adds only external semantic/type/mutability evidence and deterministic registry regression coverage.

No Activity dataclass expansion, duplicate registry, CPM/EVM/calendar/formula implementation, persistence/API schema, import/export mapping, or client-side scheduling semantics are introduced.

Oracle sources:
- https://docs.oracle.com/cd/F51303_01/English/Integration/p6_pro_api_reference/FieldSummary.html
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html
