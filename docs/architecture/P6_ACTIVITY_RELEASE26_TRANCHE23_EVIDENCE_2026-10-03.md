## Release 26 Activity tranche 23 evidence — 2026-10-03

Authority: Oracle P6 EPPM REST API Release 26 Activity contract and Update Activities endpoint.
Source:
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html

Certification boundary: Oracle GET/PUT schema evidence establishes field existence, documented type, and documented calculation/meaning. It does NOT by itself certify application-level writability, persistence, import/export mapping, or equivalence to the product's internal model. Computed fields remain outputs of the Shared Scheduling/EVM Core.

| P6 field | Oracle type | Documented semantic | Update-surface evidence | Internal certification |
|---|---|---|---|---|
| AtCompletionExpenseCost | double | total expense cost at completion | Activity PUT contract exposes Activity schema; semantic is computed/output | pending |
| AtCompletionLaborUnitsVariance | double | baseline planned total labor units minus EAC labor units | Activity PUT contract exposes Activity schema; semantic is computed/output | pending |
| Baseline1PlannedLaborUnits | double | baseline-1 planned labor units | Activity PUT contract exposes Activity schema | pending |
| BaselinePlannedDuration | double | baseline planned duration | Activity PUT contract exposes Activity schema | pending |
| BaselinePlannedExpenseCost | double | baseline planned expense cost | Activity PUT contract exposes Activity schema | pending |
| BaselinePlannedLaborCost | double | baseline planned labor cost | Activity PUT contract exposes Activity schema | pending |
| BaselinePlannedLaborUnits | double | baseline planned labor units | Activity PUT contract exposes Activity schema | pending |
| BaselinePlannedMaterialCost | double | baseline planned material cost | Activity PUT contract exposes Activity schema | pending |
| BaselinePlannedNonLaborCost | double | baseline planned nonlabor cost | Activity PUT contract exposes Activity schema | pending |
| BaselinePlannedNonLaborUnits | double | baseline planned nonlabor units | Activity PUT contract exposes Activity schema | pending |
| BaselinePlannedTotalCost | double | baseline planned total cost = labor + nonlabor + expense | Activity PUT contract exposes Activity schema | pending |
| CBSId | int32 | unique ID of CBS Code | Activity PUT contract exposes Activity schema | pending |
| CalendarName | string | name of activity calendar | Activity PUT contract exposes Activity schema | pending |
| CalendarObjectId | int32 | unique ID of calendar assigned to activity | Activity PUT contract exposes Activity schema | pending |
| CostPerformanceIndexLaborUnits | double | labor-unit earned-value performance ratio | Activity PUT contract exposes Activity schema; semantic is computed | pending |
| CostVarianceIndex | double | cost variance index | Activity PUT contract exposes Activity schema; semantic is computed | pending |
| CostVarianceIndexLaborUnits | double | labor-unit cost variance index | Activity PUT contract exposes Activity schema; semantic is computed | pending |
| CostVarianceLaborUnits | double | labor-unit cost variance | Activity PUT contract exposes Activity schema; semantic is computed | pending |
| EstimateAtCompletionLaborUnits | double | actual labor units + estimate-to-complete labor units; EVM dependent | Activity PUT contract exposes Activity schema; semantic is computed | pending |
| EstimateToComplete | double | estimated cost to complete; EVM dependent | Activity PUT contract exposes Activity schema; semantic is computed | pending |

### Registry mapping rule
Each field must receive exactly one canonical typed registry identity. No Activity dataclass expansion is authorized by this tranche. No client-side calculation is introduced. Computed fields must remain outputs of the Shared Scheduling/EVM Core.

### Next gate
Validate exact canonical field names against the inventory, add deterministic registry metadata, update gap/inventory regression expectations, then run focused tests and the required CI/typecheck/PostgreSQL gates on the resulting PR HEAD.
