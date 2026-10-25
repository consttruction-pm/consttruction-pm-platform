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

## Implementation update — 2026-10-25 (PR #1566 pending merge)

The earlier two blockers have implementation coverage in the current branch, but not yet in `main`:

1. `src/construction_pm/authoritative_schedule_input_composer.py` no longer rejects valid date-based leveling settings or every non-empty resource assignment set. It validates persisted assignment/period scope, unique identities, cross-record activity/resource references and date keys while the immutable schedule snapshot preserves the authoritative activity, relationships, constraints, calendar assignments and schedule options.
2. `src/construction_pm/p6_persisted_resource_leveling_resolver.py` reads the real authorized assignment/period repositories at the snapshot's exact tenant/project/revision, resolves each resource calendar by exact ID+version and hashes the source assignments, time-phased facts, calendar capacity manifest, snapshot and calculation identity. The production WSGI composition can construct this resolver from the real read API and calendar repositories.
3. `tests/test_authoritative_schedule_snapshot_composer.py::test_activity_snapshot_publication_and_query_use_persisted_resource_leveling` covers authenticated activity writes → persisted schedule settings/relationships/constraints/calendar assignment/resource assignments and periods → explicit commit → published immutable snapshot → production Schedule Query → final leveling dates. The test asserts the non-empty resource overload is separated by the Shared Scheduling Core and the snapshot preserved the non-default activity-calendar, priority and constraint values.

The exact head `12be1a8f2facaf527dc240b31e16bef8f9cfd0cc` passed ConstructionPM CI (Python 3.11/3.12/3.13), Client Typecheck (web/desktop/mobile/client-sync) and PostgreSQL Integration. This evidence applies to that SHA; any subsequent source change requires fresh checks. PR #1566 still must be merged before the implementation counts as current-main completion.

## Remaining certification gaps

- Keep #1468 open until the current PR is integrated and an independent semantic review confirms the unit meaning of resource-calendar capacity versus assignment demand, PriorityList/ResourceList options, movement horizon, constraints and exact-version calendar exception/work-hour precedence. Do not call this full resource-leveling conformance.
- Keep #1462 open until the integrated write→commit→fresh scoped read→snapshot→query coverage and optimistic-concurrency/scope-negative evidence are reviewed on current main; unsupported duration/date/progress/calendar mapping contracts must continue to fail explicitly rather than being coerced.
- This is only a date-based resource-leveling slice. It does not certify all calculations, time-aware resource leveling, every external scheduling option or complete product parity.

Keep overall conformance status PARTIAL/UNVERIFIED, and do not award full product-completion credit from this resource-leveling slice alone.

## Acceptance evidence expected for this sub-slice

- tests/test_project_schedule_settings_repository.py: SQLite round-trip, exact enum/field retention, revision conflicts, stale scope, date/time validation, timezone precision, hash tampering and caller-owned rollback.
- tests/integration/test_postgres_project_schedule_settings_live.py: live PostgreSQL round-trip, update revision, tenant/project isolation and caller-owned rollback.
- ConstructionPM CI, Client Typecheck, and PostgreSQL Integration must pass on the same exact final commit before this repository slice is merged.
