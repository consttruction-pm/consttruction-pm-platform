# Stage 33.4.30 — Time-Aware Forward Pass Integration

Date: 2026-09-24

## Scope

The first real CPM integration slice for the time-aware contract is now available in Shared Core as `time_forward_pass`.

It uses:
- TimeActivity + TimeQuantity
- TimeRelationship + LagQuantity
- SchedulingCalendarContext
- CalendarResolverRegistry
- TimeAwareWorkingTimeResolver

## Semantics

The time-aware path uses exact datetime event boundaries with half-open working intervals `[start, end)`:

- FS: successor start is predecessor finish plus lag.
- SS: successor start is predecessor start plus lag.
- FF: successor finish is predecessor finish plus lag; successor start is derived by subtracting its working duration.
- SF: successor finish is predecessor start plus lag; successor start is derived by subtracting its working duration.

Unlike the date-only model, a zero-lag FS relationship can continue at the exact predecessor finish boundary. If that boundary is outside working time, the successor start is normalized to the next working interval.

## Explicit limitations

This stage intentionally does not perform hidden conversions:
- working-day duration is not converted to hours;
- working-day lag is not converted to hours;
- negative working-hour lag is not yet enabled because inverse working-time lag semantics need a dedicated tested contract.

These are explicit `NotImplementedError` gates, not silent approximations.

## Determinism

Calendar identity/version and lag-calendar selection come from Shared Core context. No client performs scheduling calculations.

## Regression coverage

`tests/scheduling/test_time_forward_pass.py` covers working-hour duration across breaks, FS/SS/FF, positive lag, holiday crossing, explicit rejection of implicit day/hour conversion, and the negative-lag integration gate.

Runtime CI execution remains unverified.
