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
| Strict adapter must not resolve by calendar ID alone if a version is required. | `build_resource_capacity_slices(..., require_calendar_versions=True)` requires a version and looks up only the exact `(calendar_id, calendar_version)` map key. | `test_strict_adapter_fails_closed_for_legacy_assignment_without_calendar_version`; `test_strict_adapter_never_falls_back_to_same_calendar_id_with_wrong_version`; positive exact-pair mapping test. |

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
