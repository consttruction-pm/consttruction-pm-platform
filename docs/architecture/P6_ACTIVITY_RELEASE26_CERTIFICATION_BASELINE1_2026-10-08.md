# P6 Activity Release 26 — Primary Baseline Semantic Certification

Date: 2026-10-08  
Owner: Jalal  
Issue: #1299  
Base: `main@344dcedf18a438f5be39f62194bc133c28995eb1`  
Scope: existing canonical Activity registry metadata and source evidence only.

## Oracle authority

Oracle P6 EPPM Release 26 Activity GET/PUT documentation and the Oracle Integration API Activity Field Summary are the authoritative sources for the external field type, Read Only classification, and published semantics.

The Integration API Field Summary marks the primary-baseline fields below Read Only with X. The internal `writable` and `computed` flags are kept separate from that external fact.

## Certified fields

| P6 field | Oracle type | Oracle Read Only | Registry type | Registry writable | Registry computed | Registry unit |
|---|---|---:|---|---:|---:|---|
| Baseline1Duration | Duration | Yes | DURATION | No | Yes | working-time |
| Baseline1FinishDate | EndDate | Yes | DATE | No | Yes | — |
| Baseline1PlannedDuration | Duration | Yes | DURATION | No | Yes | working-time |
| Baseline1PlannedExpenseCost | double / Cost | Yes | DOUBLE | No | No | currency |
| Baseline1PlannedLaborCost | double / Cost | Yes | DOUBLE | No | Yes | currency |
| Baseline1PlannedLaborUnits | double / Unit | Yes | DOUBLE | No | No | units |
| Baseline1PlannedMaterialCost | double / Cost | Yes | DOUBLE | No | No | currency |
| Baseline1PlannedNonLaborCost | double / Cost | Yes | DOUBLE | No | Yes | currency |
| Baseline1PlannedNonLaborUnits | double / Unit | Yes | DOUBLE | No | No | units |
| Baseline1PlannedTotalCost | double / Cost | Yes | DOUBLE | No | Yes | currency |
| Baseline1StartDate | BeginDate | Yes | DATE | No | Yes | — |

## Semantic disposition

- **Baseline1Duration**: total working time from the activity current start to current finish in the primary baseline; Oracle explicitly relates it to actual duration plus remaining duration and activity-calendar working time. It is therefore represented as computed working-time.
- **Baseline1FinishDate**: status-dependent current finish in the primary baseline: planned finish before start, remaining finish while in progress, actual finish after completion. This is an authoritative derived/selected value.
- **Baseline1PlannedDuration**: total working time in the primary baseline, explicitly tied to actual duration plus remaining duration and the activity calendar. It is computed working-time.
- **Baseline1PlannedExpenseCost**: planned project-expense cost in the primary baseline. Oracle does not publish a derivation formula for this Activity field in the reviewed Release 26 material, so the registry treats it as a read-only value rather than inventing a computation.
- **Baseline1PlannedLaborCost**: Oracle explicitly states that it is computed from primary-baseline at-completion labor units, with a default-price/time fallback when no resources are assigned. It is therefore computed currency.
- **Baseline1PlannedLaborUnits**: planned units for labor resources in the primary baseline. Oracle publishes the value semantics but no derivation formula on the reviewed Activity field documentation, so it remains a read-only value.
- **Baseline1PlannedMaterialCost**: planned material cost for the primary baseline activity. No explicit derivation formula is published in the reviewed Activity documentation, so it remains a read-only value.
- **Baseline1PlannedNonLaborCost**: Oracle explicitly gives the resource-based value and a computed fallback from planned nonlabor units × project default price/time when no resources are assigned. It is therefore computed currency.
- **Baseline1PlannedNonLaborUnits**: planned units for nonlabor resources in the primary baseline. No explicit derivation formula is published in the reviewed Activity field documentation, so it remains a read-only value.
- **Baseline1PlannedTotalCost**: explicitly equals planned labor cost + planned nonlabor cost + planned expense cost. It is therefore computed currency.
- **Baseline1StartDate**: current start in the primary baseline, selecting planned start until the activity starts and actual start thereafter. This is an authoritative derived/selected value.

## Certification boundary

All eleven identities already exist in the canonical Activity registry. This change:
- records authoritative Read Only metadata;
- corrects registry units for baseline duration/cost/unit fields;
- corrects four existing fields whose reviewed Oracle descriptions do not state a calculation formula, so they are no longer asserted as computed;
- leaves all P6 scheduling, CPM, calendar, Progress/EVM, formula, persistence, API, import/export, and client calculation semantics unchanged.

No new Activity identity, Activity dataclass, second registry, or calculation engine is introduced.

## Oracle sources

- Oracle P6 EPPM Release 26 Read Activities:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- Oracle P6 EPPM Release 26 Update Activities:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html
- Oracle Integration API Field Summary:
  https://docs.oracle.com/cd/F51303_01/English/Integration/p6_pro_api_reference/FieldSummary.html
- Existing repository typed evidence:
  docs/architecture/P6_ACTIVITY_PRIMARY_BASELINE_TYPED_EVIDENCE_2026-10-02.json
