# P6 Activity Release 26 — exact registry tranche next 10D

Date: 2026-10-04
Scope: Shared-Core typed P6 field registry only.
Authority: Oracle P6 Pro Integration API FieldSummary and Oracle P6 Activity API / Activity field references.

## Field evidence

| P6 field | Oracle type | Read Only | Shared-Core metadata |
|---|---|---:|---|
| RemainingTotalCost | Cost | Yes | COST, non-writable, computed |
| RemainingTotalUnits | Unit | Yes | UNIT, non-writable, computed |
| SchedulePercentComplete | Percent | Yes | PERCENTAGE, non-writable, computed |
| SchedulePerformanceIndexLaborUnits | double | Yes | DOUBLE, non-writable, computed |
| ScheduleVariance | Cost | Yes | COST, non-writable, computed |
| ScheduleVarianceIndex | double | Yes | DOUBLE, non-writable, computed |
| ScheduleVarianceIndexLaborUnits | double | Yes | DOUBLE, non-writable, computed |
| ScheduleVarianceLaborUnits | Unit | Yes | UNIT, non-writable, computed |
| SecondaryConstraintDate | java.util.Date / date-time | No | DATE, writable, stored |
| SecondaryConstraintType | ConstraintType / string | No | ENUM, writable, stored |

## Semantic evidence

Oracle defines RemainingTotalCost as remaining labor + nonlabor + expense cost, RemainingTotalUnits as remaining labor + nonlabor units, SchedulePercentComplete from data date versus baseline dates, and the schedule variance/index fields from earned value/planned value relationships. Oracle also defines the two secondary constraint fields as the additional scheduler constraint date/type. 

## Boundary

Registry metadata only. No Activity dataclass expansion, CPM/EVM/calendar/formula implementation changes, backend/API schema, persistence schema, or client-side scheduling.

Entries remain `seeded_not_certified`; implementation certification is separate.
