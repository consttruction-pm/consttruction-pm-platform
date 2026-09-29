# Authoritative Schedule Backend Materialization Boundary

Date: 2026-09-30

## Purpose

The Shared Core authoritative schedule contract now exists on main. The backend persistence layer also contains Activity Master, Relationship Master, Calendar Master and Activity Calendar Assignment records.

This boundary converts those persisted records into the immutable AuthoritativeScheduleInput consumed by Shared Core.

## Ownership

Hasan owns the backend materialization seam. Shared Core remains authoritative for scheduling, calendar arithmetic, duration conversion and all other calculation semantics.

## Current scope

The implementation currently materializes the date-based shape only:

- versioned project calendar reference;
- persisted activities and working-day durations;
- persisted activity calendar assignments;
- persisted relationships and working-day lag;
- tenant/project/project-revision provenance;
- explicit snapshot identity and canonical snapshot hashing.

The adapter performs validation and mapping only. It does not schedule, recalculate, convert working days to hours, or derive missing business values.

## Fail-closed rules

The adapter rejects:

- missing project calendar;
- non-working-day calendar for date-based materialization;
- fractional date-based durations or lags;
- working-hour duration/lag values in the date-based path;
- datetime actual starts in the date-based path;
- missing assigned activity calendars;
- relationships that reference unknown activities.

Time-aware materialization is not claimed until the persisted master contracts carry sufficient authoritative time-aware data.

## Verification

Focused tests cover successful materialization, deterministic snapshot identity, fractional-duration rejection and missing activity-calendar rejection.

GitHub Actions runtime verification is required before merge and completion.
