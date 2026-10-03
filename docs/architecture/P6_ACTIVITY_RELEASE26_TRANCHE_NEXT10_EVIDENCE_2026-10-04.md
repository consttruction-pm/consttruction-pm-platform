# P6 Activity Release 26 — next 10 exact registry fields

Date: 2026-10-04
Scope: Shared-Core typed P6 field registry only.
Authority: Oracle P6 EPPM Release 26 REST Activity GET/PUT contracts plus Oracle P6 Pro Integration API FieldSummary.

## Certified external field evidence

| P6 field | Native type | Read-only in FieldSummary | Shared-Core metadata | Oracle evidence |
|---|---|---:|---|---|
| EstimateToCompleteLaborUnits | Unit / REST number(double) | Yes | UNIT, non-writable, computed | Quantity remaining to complete; derived from remaining total units or PF × (baseline labor units − earned value). |
| EstimatedWeight | double | No | DOUBLE, writable, stored | Activity estimation weight used for top-down estimation. |
| IsNewFeedback | boolean | No | BOOLEAN, writable, stored | Indicates unreviewed resource feedback notes exist. |
| IsStarred | boolean | No | BOOLEAN, writable, stored | Indicates the activity is starred in P6 Team Member. |
| IsTemplate | boolean | Yes | BOOLEAN, non-writable, stored | Indicates relation to a template Project. |
| IsWorkPackage | boolean | Yes | BOOLEAN, non-writable, stored | Indicates the WBS is a workpackage in Prime. |
| NonLaborCost1Variance | Cost / REST number(double) | Yes | COST, non-writable, computed | Primary baseline nonlabor cost − at-completion nonlabor cost. |
| NonLaborCost2Variance | Cost / REST number(double) | Yes | COST, non-writable, computed | Secondary baseline nonlabor cost − at-completion nonlabor cost. |
| NonLaborCost3Variance | Cost / REST number(double) | Yes | COST, non-writable, computed | Tertiary baseline nonlabor cost − at-completion nonlabor cost. |
| OwnerNamesArray | String / REST string | No | STRING, writable, stored | Activity owner names represented as a comma-separated list by REST; the Integration API types the field as String. |

## Source details

Oracle Release 26 Read Activities documents the numeric/boolean fields and their meanings; the Update Activities contract exposes the writable Activity properties including EstimatedWeight, IsNewFeedback, IsStarred, and OwnerNamesArray. turn988473search1 turn176758search0 turn116056view0

Oracle's Integration API FieldSummary explicitly marks Read Only with an X. The requested tranche fields are listed at the Activity rows for EstimateToCompleteLaborUnits, EstimatedWeight, IsNewFeedback, IsStarred, IsTemplate, IsWorkPackage, NonLaborCost1Variance/2Variance/3Variance, and OwnerNamesArray. turn439835view0 turn232244view1 turn232244view2 turn232244view3 turn232244view4

## Semantic boundary

The implementation adds registry metadata only. It does not add Activity dataclass members, change CPM/EVM calculations, modify API/persistence schemas, or introduce client-side scheduling formulas. Scheduler-derived/computed values remain fields of the authoritative Shared Scheduling Core rather than a second calculation implementation.

## Regression contract

The focused test requires exactly one Activity registry identity for each P6 name, verifies the native typed metadata, and checks that each entry remains sourced from the Oracle P6 Version 26 / 26.4 registry authority.

## Certification note

Oracle documentation establishes field identity, native type, and read-only status. Internal implementation certification remains distinct from Oracle inventory evidence; this tranche therefore keeps the existing disposition seeded_not_certified rather than claiming full end-to-end implementation certification.
