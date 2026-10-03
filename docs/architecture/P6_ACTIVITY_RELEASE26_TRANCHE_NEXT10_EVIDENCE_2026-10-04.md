# P6 Activity Release 26 — next 10 exact registry fields

Date: 2026-10-04
Scope: Shared-Core typed P6 field registry only.
Authority: Oracle P6 EPPM Release 26 REST Activity GET/PUT contracts plus Oracle P6 Pro Integration API FieldSummary.

| P6 field | Native type | Read-only | Shared-Core metadata |
|---|---|---:|---|
| EstimateToCompleteLaborUnits | Unit / REST number(double) | Yes | UNIT, non-writable, computed |
| EstimatedWeight | double | No | DOUBLE, writable, stored |
| IsNewFeedback | boolean | No | BOOLEAN, writable, stored |
| IsStarred | boolean | No | BOOLEAN, writable, stored |
| IsTemplate | boolean | Yes | BOOLEAN, non-writable, stored |
| IsWorkPackage | boolean | Yes | BOOLEAN, non-writable, stored |
| NonLaborCost1Variance | Cost / REST number(double) | Yes | COST, non-writable, computed |
| NonLaborCost2Variance | Cost / REST number(double) | Yes | COST, non-writable, computed |
| NonLaborCost3Variance | Cost / REST number(double) | Yes | COST, non-writable, computed |
| OwnerNamesArray | String / REST string | No | STRING, writable, stored |

Semantic boundary: registry metadata only. No Activity dataclass expansion, CPM/EVM formula changes, API/persistence schema changes, or client-side scheduling calculations.
