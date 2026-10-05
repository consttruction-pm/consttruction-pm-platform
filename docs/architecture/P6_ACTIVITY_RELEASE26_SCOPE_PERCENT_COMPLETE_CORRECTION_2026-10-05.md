# P6 Activity Release 26 — ScopePercentComplete Semantic Correction

Date: 2026-10-05  
Owner: Jalal  
Baseline: `main@9c309ea8498aa2382a0ceb19f3acd0695b73b5f1`  
Issue: #1186

## Verified correction

The current canonical registry previously recorded:

- P6 field: `ScopePercentComplete`
- internal field: `activity.scope_percent_complete`
- type: `double`
- writable: false
- computed: true
- unit: percent

Oracle Release 26 / 26.4 evidence establishes:

- Integration API Field Summary: `Activity | ScopePercentComplete | Percent | Read Only blank`
- Oracle describes it as: “The scope percent complete is imported from Prime via integration.”
- Release 26 Activity GET and PUT expose `ScopePercentComplete` as a numeric/double field.

Therefore the canonical metadata is corrected to:

- type: DOUBLE
- writable: true
- computed: false
- unit: percent

## Boundary

This is a field-registry semantic correction only. No Activity identity is added. No Activity dataclass, scheduling/CPM, calendar, formula, progress/EVM, persistence, API, import/export, or client calculation behavior is changed.

## Oracle sources

- Oracle P6 Pro Integration API Field Summary (Release 26.4): https://docs.oracle.com/cd/F51303_01/English/Integration/p6_pro_api_reference/FieldSummary.html
- Oracle P6 EPPM Release 26 Read Activities: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- Oracle P6 EPPM Release 26 Update Activities: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html
