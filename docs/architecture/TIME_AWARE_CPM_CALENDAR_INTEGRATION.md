# Stage 33.4.30 — Time-Aware CPM Calendar Integration

Date: 2026-09-24

## P6 compatibility direction

For schedule calculations, activity calendars determine working-time duration behavior, while relationship-lag calendar behavior must remain explicit and deterministic. The Shared Core owns the effective calendar used by each calculation; clients must not independently convert or reinterpret lag/calendar semantics.

## Implementation status

Stage 33.4.30 integrates the existing versioned calendar-resolution contract into the time-aware CPM path:

- Forward Pass resolves the activity calendar for activity duration.
- Relationship lag resolves from the successor activity's relationship-lag calendar.
- Backward Pass resolves the activity calendar for predecessor duration and the relationship-lag calendar for relationship event inversion.
- Terminal backward scheduling uses the authoritative project calendar for project-finish normalization.
- time_schedule normalizes an explicit/effective project finish through the project calendar before the Backward Pass.
- FS/SS/FF/SF and signed working-hour lag remain supported.
- Working-time arithmetic remains interval-aware and preserves split daily intervals, holidays and cross-day boundaries.

## Determinism and portability

CalendarReference remains the stable (calendar_id, calendar_version, kind) contract. Missing calendar versions remain hard errors; no client may silently substitute another version.

## Regression coverage

Added tests verify that:
1. an explicit project finish is interpreted using the project calendar;
2. Backward Pass does not accidentally use the last activity's calendar as the project calendar.

Existing time-scheduling tests continue to cover split intervals, holidays, FS/SS/FF/SF, signed lag, constraints and float behavior.

## Verification

Repository writes are complete on main. CI/runtime execution must be verified from the GitHub Actions status before Stage 33.4.30 is marked complete.
