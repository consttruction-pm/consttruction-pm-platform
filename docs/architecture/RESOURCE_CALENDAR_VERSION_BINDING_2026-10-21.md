# Resource Assignment Calendar Version Binding — Source-to-Code-to-Test Record

Date: 2026-10-21  
Related blocker: [Issue #1468](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1468)  
Related persisted-input blocker: [Issue #1462](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1462)

## Problem and required behavior

The current resource-assignment contract stored `calendar_id` but not `calendar_version`. Two immutable versions of the same calendar ID could therefore not be distinguished at the assignment/transport boundary. In a version-sensitive calculation this creates a risk of silently using a newer or otherwise mismatched calendar definition.

The rule is now explicit: a calendar version, when present, must be paired with a calendar ID. Legacy persisted assignments are migrated with a nullable `calendar_version`; the migration must **not** infer a version or bind old rows to the latest calendar. Any production-leveling path requiring authoritative calendar identity must opt into strict version resolution and reject missing or mismatched versions.

## Input → code → output traceability

| Requirement / input | Implementation | Evidence |
|---|---|---|
| Assignment carries a nullable, typed calendar version in addition to ID; existing positional constructor contract remains stable. | `P6ResourceAssignment.calendar_version` appended after `note`; validation rejects blank versions and a version without an ID. | `tests/test_p6_resource_assignment_repository.py` — validation and immutability tests. |
| SQLite schema evolves additively and does not invent a version for old rows. | SQLite repository adds `calendar_version TEXT` when absent; explicit SELECT/INSERT projections persist the field. | `test_legacy_sqlite_schema_migrates_without_guessing_calendar_version`; round-trip and changed-version immutability tests. |
| PostgreSQL schema and row mapping preserve the same version. | PostgreSQL repository has `ADD COLUMN IF NOT EXISTS` and explicit SELECT/INSERT/decoder mappings. | `tests/test_p6_postgres_resource_assignment.py`; PostgreSQL Integration workflow must pass on the exact final SHA. |
| Read API preserves the version without losing tenant/project/revision scope. | `P6ResourceReadAPI` assignment DTO includes `calendar_version`; adapter materializes that field into the typed assignment. | `tests/test_p6_resource_read_api.py` and adapter tests. |
| Strict adapter must not resolve by calendar ID alone if a version is required. | `build_resource_capacity_slices(..., require_calendar_versions=True)` requires a version, looks up only the exact `(calendar_id, calendar_version)` map key, and verifies the resolved `ResourceCalendar.id` and `ResourceCalendar.calendar_version` agree with that key; a tuple key cannot relabel a stale version object. | `test_strict_adapter_fails_closed_for_legacy_assignment_without_calendar_version`; `test_strict_adapter_never_falls_back_to_same_calendar_id_with_wrong_version`; `test_strict_adapter_rejects_exact_key_with_wrong_calendar_object_version`; positive exact-pair mapping test. |

## Exact persisted calendar resolver added — acceptance evidence required

A first production-boundary resolver now exists in `src/construction_pm/p6_versioned_resource_calendar_resolver.py`. It reads the exact `CalendarMaster` ID/version, immutable canonical calendar snapshot, stored version-pinned exception rows, and work-hour rule records; resolves local/inherited exception precedence through `CalendarResolverRegistry`; and derives a deterministic SHA-256 over scope/revision, the versioned ancestry, canonical snapshots, work-hour records, exceptions, requested periods and effective capacity slices. It returns a `ResourceCalendar` with the exact version, hash, and date-specific `capacity_slices`. It never chooses a “latest” version.

The current resolver deliberately fails closed on incomplete mapping instead of silently dropping values:
- missing master/version or snapshot;
- revision/scope mismatch, kind mismatch, inheritance cycle, or unresolved base reference;
- P6 dated `DetailedWorkHours` records represented by the current repository as weekday-only (the persisted identity is insufficient to determine dates);
- calendar-level `total_work_hours` whose source mapping is not the same contract as the separately typed Hours-per-Time-Period factors;
- conflicting standard total-hour and detailed interval declarations;
- malformed/unsupported effective exception modes, missing capacity periods, or wrong calendar version.

These are explicit blockers, not hidden defaults. Official source context for the resolver’s distinction between standard week, date-specific detailed work hours, total hours per day and time-period conversion factors:
- [P6 EPPM Release 26 — Update StandardDetailedWorkHours of Calendar](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-calendar-standarddetailedworkhours-put.html)
- [P6 EPPM Release 26 — Update DetailedWorkHours of Calendar](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-calendar-detailedworkhours-put.html)
- [P6 Professional v26 — Calendar/User Guide](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/p6_pro_user.pdf)

New regression suite: `tests/test_p6_versioned_resource_calendar_resolver.py` exercises deterministic hash/period capacity, weekly hour and nonwork overrides, inherited exceptions plus local reset precedence, detailed work-hours exceptions on time calendars, incorrect version rejection, and fail-closed ambiguous work-hour records. These tests and CI must pass on the same final SHA before acceptance.

## Important remaining gaps — not certified

This change is a **sub-slice**, not closure of Issue #1468 or full P6/calendar parity.

1. `SchedulerLevelingInput` currently exposes capacity as resource/date/units; it does not yet carry a hash-bound immutable identity for the raw resource facts, calendar definitions, or snapshot to which those facts belong.
2. The strict adapter currently accepts an explicit version-keyed `ResourceCalendar` map, but the production path must resolve each exact `CalendarMaster` ID+version to the canonical calendar snapshot, apply/version-pin relevant exceptions and working-hour rules, and prove the capacity meaning. Do not replace that production source with an ID-only legacy map or silently assume a default daily capacity.
3. `AuthoritativeScheduleQueryProvider` still does not pass a version-bound leveling input to `evaluate_schedule_snapshot`. Raw assignment/period/capacity/calendar/options facts must be authorized and read for the same tenant/project revision, snapshot ID/hash and calculation context; CPM-derived dates/floats must be combined only after the CPM intermediate pass.
4. No test in this slice proves the complete persisted write → commit → fresh scoped read → canonical immutable snapshot → leveling-enabled production Schedule Query → final dates/constraints/resource-capacity output.

Until those are implemented and tested on one exact final SHA, keep Issues #1462 and #1468 open, keep the calculation conformance status PARTIAL/UNVERIFIED as appropriate, and do not award end-to-end feature completion credit.

## Acceptance requirements for this slice

- SQLite legacy migration, round-trip, immutable version change, DTO preservation and strict wrong-version/missing-version rejection tests pass.
- PostgreSQL round-trip and immutability tests pass on a live CI database.
- ConstructionPM CI, Client Typecheck and PostgreSQL Integration are green on the same exact commit.
- Independent semantic review is recorded. Any failure or review finding must be fixed and re-tested on the resulting SHA.
