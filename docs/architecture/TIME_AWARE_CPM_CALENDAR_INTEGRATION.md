# Stage 33.4.30 — Time-Aware CPM Calendar Integration

Date: 2026-09-24

## P6 compatibility direction

For schedule calculations, activity calendars determine working-time duration behavior, while relationship-lag calendar behavior must remain explicit and deterministic. The Shared Core owns the effective calendar used by each calculation; clients must not independently convert or reinterpret lag/calendar semantics.

## Implementation status

**Stage 33.4.30 — complete.** The time-aware CPM calendar integration is now verified in the repository CI path.

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
3. mixed activity project-calendar references are rejected instead of silently selecting the first activity's calendar.

Existing time-scheduling tests continue to cover split intervals, holidays, FS/SS/FF/SF, signed lag, constraints and float behavior.

## Verification

Repository writes are complete on main.

- ConstructionPM CI passed on commit `a78be1ca2d723d7a07ca199f0aba4f16c8174f6f`, covering Python 3.11, 3.12 and 3.13.
- PostgreSQL Sync State Integration passed on the same commit.
- The separate Client Typecheck workflow remains red because of existing TypeScript `TS7006` errors in client test callbacks; those failures are outside the time-aware CPM Python scheduling path and were also present on the preceding scheduling commits.
