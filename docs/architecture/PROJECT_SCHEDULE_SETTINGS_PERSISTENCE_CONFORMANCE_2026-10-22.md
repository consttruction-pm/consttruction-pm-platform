# Project Schedule Settings Persistence — Contract to Code/Test Map

**Date:** 2026-10-22  
**Status:** persistence sub-slice; production Activity Master → immutable schedule snapshot composition remains OPEN under Issue #1462. Resource-leveling input → authoritative Schedule Query remains OPEN under Issue #1468.

## Scope and invariants

This change adds persistence only. It does not implement or change CPM, relationship logic, calendar working-time logic, float calculation, resource leveling, or the Schedule Query evaluation algorithm.

The repository must preserve authoritative context needed by a later production composer and reject incomplete or stale inputs rather than synthesizing a current value.

## Input → validation → stored output

| Input | Type/semantics | Validation and failure behavior | Persisted / round-trip evidence |
|---|---|---|---|
| Tenant, project, project revision | BackendScope; identifies one exact revision | Scope validation; revision mismatch raises REVISION_CONFLICT; reads cannot silently use a different revision | test_project_schedule_settings_fails_closed_on_missing_or_stale_project_revision |
| Calculation mode | DATE_BASED or TIME_AWARE | Must be typed; must match project calendar kind; mismatch rejected | test_project_schedule_settings_rejects_calendar_mode_mismatch_and_naive_datetime |
| Project calendar | Explicit CalendarReference: ID, version, calendar kind, calendar-system identifier | Exact ID/version and kind are retained; no ID-only “latest” substitution | test_project_schedule_settings_round_trip_preserves_all_options_and_calendar_identity |
| Project start/finish | Date-only values for date-based mode; timezone-aware datetimes for time-aware mode | Missing start, mixed type, naive datetime, or finish before start rejected; microseconds and UTC offset retained | test_time_aware_project_schedule_settings_preserve_timezone_precision |
| Schedule options | Full typed ScheduleOptions, including enums, data date, resource selection, ordered priority list and leveling toggles | Every current dataclass field must be present in stored schema; malformed enums/options or missing fields rejected; no silent field default on read | test_project_schedule_settings_round_trip_preserves_all_options_and_calendar_identity |
| Project leveling priority | Explicit integer in documented model range 1–100 | Booleans, non-integers and out-of-range values rejected; this range validation is not a claim that a particular default is externally certified | Round-trip and invalid settings tests |
| Expected record revision | Optional 0 for create; exact current revision for update | Stale/absent expectation on update raises REVISION_CONFLICT; compare-and-update rowcount must be exactly one | test_project_schedule_settings_update_requires_exact_record_revision |

## Persistence and integrity contract

- Canonical payload contains schema version, exact scope, mode, project calendar, start/finish, all ScheduleOptions, and project-level leveling priority.
- The stored SHA-256 is over the exact canonical UTF-8 payload. Tampering raises SETTINGS_HASH_MISMATCH.
- SQLite and PostgreSQL repositories expose the same save/get semantics.
- SQLite commits only when it owns the transaction; an outer caller transaction can roll back the settings write.
- PostgreSQL transaction ownership remains with the caller. The live integration tests prove create/read/update/scope isolation and rollback on a separate connection.
- A new setting record has an explicit record revision. Update is optimistic; no hidden merge or last-writer-wins behavior is intended.

## Source boundary

The typed options reflect the repository's existing shared scheduling contract (src/construction_pm/scheduling/schedule_options.py) and calendar-reference contract (src/construction_pm/scheduling/calendar_context.py). P6-overlap semantics must remain tied to the specific supported documentation version and be independently reviewed before being claimed conformant. This persistence change does not certify those calculation semantics.

Reference entry points used by adjacent scheduling contracts:
- P6 Professional v26 Schedule Options: https://docs.oracle.com/cd/G48902_01/client_help/en_US/general_tab_-_schedule_options_dialog_box.htm
- P6 Professional v26 relationship type/lag fields: https://docs.oracle.com/cd/G48902_01/client_help/en_US/relationships_tab_-_activity_details.htm
- P6 Professional v26 resource-leveling priority definitions: https://docs.oracle.com/cd/G48902_01/client_help/en_US/leveling_priority_definitions.htm

## Explicit remaining blockers

1. No current production composition yet performs persisted Activity Master + relationships + constraints + activity-calendar assignments + project schedule settings → fresh revision-consistent read → canonical AuthoritativeScheduleInput → immutable ScheduleInputSnapshot. The current query test that hand-builds an AuthoritativeScheduleInput does not prove this path. Keep #1462 OPEN.
2. No immutable raw resource-assignment/period/capacity/options envelope is bound to the snapshot/calculation identity and composed with intermediate CPM output for SchedulerLevelingInput. The provider still needs the leveling_input seam and real query-path tests. Keep #1468 OPEN.
3. Existing Activity Master persistence still does not authoritatively persist every Activity field, and duration/date/progress mappings cannot be guessed or silently coerced. Unsupported mappings remain a blocker until an explicit contract is established.

## Acceptance evidence expected for this sub-slice

- tests/test_project_schedule_settings_repository.py: SQLite round-trip, exact enum/field retention, revision conflicts, stale scope, date/time validation, timezone precision, hash tampering and caller-owned rollback.
- tests/integration/test_postgres_project_schedule_settings_live.py: live PostgreSQL round-trip, update revision, tenant/project isolation and caller-owned rollback.
- ConstructionPM CI, Client Typecheck, and PostgreSQL Integration must pass on the same exact final commit before this repository slice is merged.
