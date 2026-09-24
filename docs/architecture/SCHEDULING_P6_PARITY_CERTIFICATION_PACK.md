# Scheduling P6 Parity & Edge-Case Certification Pack — Stage 33.4.26

Date: 2026-09-24

## Purpose
This pack defines the regression contract for the Shared Scheduling Core before this scheduling section is considered stable. It is a compatibility test pack, not a claim of Oracle certification.

## Coverage
1. Calendar arithmetic
   - working-day duration
   - weekends and explicit holidays
   - custom working-week calendars
   - zero-duration activities
   - deterministic normalization
2. Relationship semantics
   - FS, SS, FF, SF
   - positive and negative working-day lag
   - relationship feasibility in both early and late schedules
   - mixed relationship networks
3. Constraint scope
   - Start/Finish No Earlier Than affect early dates
   - Start/Finish No Later Than affect late-date limits
   - Mandatory Start/Finish affect both early and late schedules
   - contradictory local constraint windows are rejected
4. Float and criticality
   - total float and free float
   - zero-float critical activities
   - negative total float remains reportable
   - negative float is critical under the current zero threshold
5. Schedule modes
   - EARLIEST selects early schedule
   - ALAP selects late schedule
   - both modes preserve the same Early/Late/Float analysis
6. Determinism
   - activity input order does not alter results
   - relationship input order does not alter results
   - same calendar/settings produce reproducible dates

## Oracle P6 reference alignment
Oracle documents the four relationship types and positive/negative lag semantics. Negative lag can create overlap and can distort float, so the product preserves the requested capability while exposing it for schedule-quality checking.

Oracle also documents negative float as a schedule-check condition rather than an impossible numeric state.

The current implementation intentionally remains a date-granularity Shared Core. P6's time-based lag/calendar behavior is richer than this slice and remains a pending parity area.

## Test file
tests/scheduling/test_schedule_parity.py provides the Stage 33.4.26 regression coverage for relationship/lag combinations, deterministic ordering, calendar boundaries, constraint scope, EARLIEST/ALAP separation, zero duration, and custom calendars.

## Certification gate
The gate is passed only after:
- the committed regression suite executes successfully in CI;
- no client-specific scheduling implementation exists;
- the same Shared Core behavior is consumed by Web, Desktop, and Mobile;
- remaining time-of-day/calendar differences are explicitly documented rather than silently approximated.

CI execution is intentionally not represented as passed until GitHub Actions reports a successful run.