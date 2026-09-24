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

## Required validation
- No negative or ambiguous unit/cost values where prohibited by the domain rule.
- Rate and unit types must be explicit.
- Time-phased calculations must use the activity/resource calendar context.
- Actual, baseline, current and forecast values remain distinct.
- Recalculation must be deterministic and idempotent.

## Delivery sequence
1. Resource domain model.
2. Resource calendar and availability.
3. Rates and cost model.
4. Activity resource assignments.
5. Time-phased resource loading.
6. Actual/remaining reconciliation.
7. Resource and cost variance.
8. EVM integration.
9. Reporting datasets.
10. Pytest regression/conformance suite.


## Implementation Progress — 32.8

Implemented in Shared Domain/Calculation Core:
- Resource, ResourceRate, ResourceAssignment domain models.
- Effective-date/versioned rates and typed cost calculation.
- Planned/Actual/Remaining units and costs.
- Deterministic time-phased loading and aggregation.
- Resource and assignment validation.
- Portfolio resource/cost control aggregation.
- Resource performance bridge for schedule/progress/EVM integration.
- Resource calendar and capacity calculations.
- Pytest coverage for the above behaviors.

Next implementation sequence:
1. Capacity-aware resource leveling and overload detection.
2. Resource/cost curves and histogram datasets.
3. EVM integration using the existing EV/PV/AC engines.
4. Typed Excel import/export contracts.
5. Audit/revision/portability and cross-device determinism tests.


### Latest implementation
- Capacity-aware overload detection with utilization percentage and excess units.
- Available-capacity calculation for leveling workflows.
- Deterministic resource curve dataset generation ordered by period.
- Pytest coverage for overload and curve behavior.

### Architectural rule
Leveling is a scheduling decision, not a cost-calculation side effect. The resource domain reports capacity conflicts; the scheduling/application layer must decide whether to move activities, split work, change assignments, or accept the overload according to project rules.
