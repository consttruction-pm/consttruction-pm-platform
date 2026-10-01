# P6 Activity Read-Model Boundary v1

This boundary exposes activity-linked persisted cost, period-actual and baseline metadata without extending the canonical Scheduling Activity model.

## Authoritative sources

- P6Expense supplies stored planned/actual/remaining cost entries linked to an activity.
- P6ActivityPeriodActual supplies stored period actual units/cost entries linked to an activity.
- P6Baseline supplies persisted baseline identity/type/source-revision metadata.
- EVM values are not calculated here. The existing resource EVM bridge is a calculation helper, not a persisted authoritative result contract, so the v1 read model reports EVM as explicitly unavailable until Shared Core exposes the authoritative computed-result boundary.

## Scope and determinism

The projection preserves tenant/project/project-revision scope and sorts expenses, period actuals and baselines deterministically. Decimal values remain canonical strings at the transport boundary.

## Deliberate non-goals

No scheduling, calendar, duration, baseline comparison, cost aggregation, EVM, Progress/EVM or financial formulas are implemented. The canonical scheduling Activity model and Field Registry are unchanged.
