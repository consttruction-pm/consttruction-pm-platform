# Stage 33.4.27 — Time-Aware Calendar Extension

Date: 2026-09-24

## Decision

The existing date-based WorkingCalendar / WorkingTimeResolver remains the compatibility path for the current scheduling slice.

A separate WorkingTimeCalendar / TimeAwareWorkingTimeResolver is now the Shared Core extension point for time-of-day scheduling.

This prevents Web, Desktop and Mobile from implementing different hour/shift/holiday calculations.

## Supported model

- working weekdays
- explicit holidays
- multiple non-overlapping intervals per day
- interval start/end validation
- normalization to the next working interval
- deterministic working-hour addition
- deterministic working-hour calculation
- Decimal-based duration quantities
- lunch/break intervals without treating the break as working time

Intervals use the half-open convention [start, end).

## Compatibility boundary

The current Activity, Relationship, Forward Pass and Backward Pass models remain date-granularity and whole-working-day based.

The new time-aware resolver must not be silently substituted into those APIs until:
1. activity duration units can explicitly represent working hours;
2. relationship lag units can explicitly represent working hours;
3. project/activity calendar assignment is versioned and portable;
4. Forward/Backward/Float semantics are tested against the same time-aware resolver;
5. Web/Desktop/Mobile consume the same contract.

## P6 parity implications

The extension is required because a date-only resolver cannot faithfully represent intraday working periods, breaks, shifts, or hour-based lag.

Until the full time-aware scheduling path is integrated and certified by tests, the product must not claim complete P6 time-of-day parity.

## Regression gate

tests/scheduling/test_time_calendar.py covers holiday exclusion, break handling, normalization, multi-interval working-hour addition, cross-holiday working-hour addition, Decimal working-hour calculation, and negative-duration rejection.

Runtime CI execution remains unverified.
