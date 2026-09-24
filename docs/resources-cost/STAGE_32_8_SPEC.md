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
