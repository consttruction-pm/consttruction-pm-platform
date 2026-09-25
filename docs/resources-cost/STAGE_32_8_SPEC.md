# Stage 32.8 — Resource & Cost Control Center

## Baseline
For functionality overlapping Primavera P6, resource and cost behavior follows the P6 model as the compatibility baseline.

## Scope
- Resource categories and resources: labor, machinery, materials.
- Units, calendars, rates and rate-effective dates.
- Resource assignments to activities.
- Budgeted/planned units and cost.
- Actual units and actual cost.
- Remaining units and remaining cost.
- Resource loading and time-phased values.
- Resource curves and histograms.
- Cost curves and time-phased cost.
- Resource/cost variance against baseline.
- Integration with activity progress, schedule, EVM and reporting.
- Resource calendars and non-working time.
- Multi-rate and rate-version handling.
- Typed Excel import/export.
- Audit trail, revisions and project portability.
- Web/API readiness and deterministic cross-device calculations.

## Domain separation
Resource and cost calculations belong to the Shared Domain/Calculation Core. UI, database and API adapters must not contain calculation rules.

## Implementation status
**100% — complete at the documented development workflow level.** Implemented foundations include resource/rate/assignment models, effective-date rates, planned/actual/remaining values, time-phased loading, overload detection, capacity analysis, curves/histograms, EVM bridge, typed XLSX I/O, integration snapshots and regression coverage.

## Important boundary
Leveling is a scheduling decision, not a cost-calculation side effect. The resource domain reports capacity conflicts; the scheduling/application layer decides whether to move activities, split work, change assignments or accept overload according to project rules.

## Completeness expansion
The next market-completeness layer is not a rewrite of resource calculations. It extends Resource/Cost through Procurement commitments, purchase orders, delivery status, commercial forecasting and ERP/accounting interfaces via Application/API contracts.

## Validation
Negative/ambiguous prohibited values are rejected; rate/unit types remain explicit; time-phased values use effective calendar context; actual/baseline/current/forecast remain distinct; recalculation is deterministic and idempotent; XLSX numeric/date fields remain typed.