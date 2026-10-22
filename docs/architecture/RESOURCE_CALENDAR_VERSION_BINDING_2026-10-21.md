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

A first production-boundary resolver now exists in `src/construction_pm/p6_versioned_resource_calendar_resolver.py`. It reads the exact `CalendarMaster` ID/version, immutable canonical calendar snapshot, stored version-pinned exception rows, and work-hour rule records; resolves local/inherited exception precedence through `CalendarResolverRegistry`; and derives a deterministic SHA-256 identity over scope/revision, the versioned ancestry, canonical snapshots, work-hour records and exceptions. The calendar-definition hash is independent of the queried period range; date-specific capacity slices belong to the separately versioned raw-capacity envelope. It returns a `ResourceCalendar` with the exact version, hash, and date-specific `capacity_slices`. It never chooses a “latest” version.

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


## Production resource-leveling input bridge — docs-first contract proposal (2026-10-22)

**State: BLOCKED pending independent semantic review. No calculation code may change for this bridge until the reviewer confirms the contract and capacity-horizon rule.** Rule ID: CUBI-RES-005 in the Calculation Conformance Matrix.

### Proposed immutable companion contract

A resource-leveling input must not be reconstructed from live resource repositories during evaluation. The proposed companion snapshot is keyed to and cryptographically bound to the exact schedule snapshot using:

- schema_version, tenant_id, project_id, project_revision;
- schedule_snapshot_id, schedule_snapshot_hash, calculation_identity, and calculation_identity_version;
- canonical, deterministic resource assignment and period-demand records, including assignment ID, activity ID, resource ID, period start, Decimal units/cost where relevant, selected-resource scope, and assignment calendar ID+version;
- resolved capacity slices (resource ID, period, Decimal capacity, exact calendar ID+version, and canonical calendar-definition SHA-256);
- canonical JSON and its own SHA-256 resource_facts_hash, verified on every fresh read.

The main schedule snapshot remains the owner of the typed schedule options, project calendar, activities, relationships and constraints. The companion must bind to the same snapshot hash/calculation identity rather than copying mutable settings into a second authority. Tenant/project/revision or hash mismatch, a missing companion for leveling-enabled options, stale calendar version/hash, uncovered capacity dates or unsupported fields must fail closed.

### Execution contract

1. The publication path reads committed resource assignment/period rows and exact versioned resource calendar source records within the same project scope/revision. It resolves calendars only via the existing exact-ID+version resolver; no “latest” lookup or ID-only fallback is allowed on this path.
2. The publisher persists the schedule snapshot and resource companion atomically, then fresh-reads both and verifies scope, snapshot ID/hash, calculation identity and the resource facts hash before returning success.
3. The query provider fresh-reads immutable snapshot/context/companion records and checks all bindings before evaluation. It must not query mutable assignment/calendar repositories inside the evaluator.
4. Resource demand remains distinct from capacity. Early/late dates and Total/Free Float are generated by the base/intermediate Shared Core CPM pass and supplied to the existing leveling boundary; a request, stale activity field or resource repository must never provide those calculated floats.
5. The same authoritative Shared Core performs forward/backward leveling and final CPM, constraint, relationship and resource-capacity validation. No separate adapter calculation or second scheduler is permitted.
6. Capacity date coverage is not allowed to be silently truncated. The accepted policy must cover every date considered by the proposal routine and final-load validation for the selected leveling mode; if a finite boundary cannot be proved from the contract, that combination stays BLOCKED and fails closed.

### Source-backed behavioral baseline

- P6 Professional v26 **Level resources** says that resource curves are not used by the leveler, and resource Max Units/Time defines the maximum work available per time period: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_resources.htm
- P6 Professional v26 **Specify leveling priorities** says priority rows take precedence in listed order and each row specifies sort order: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/specify_leveling_priorities.htm
- P6 Professional v26 **Leveling priority definitions** documents ascending/descending behavior and Activity ID as the fallback when no prioritization codes are specified: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_priority_definitions.htm
- P6 Professional v26 **Level resources** distinguishes preserving current early/late dates (forward leveling) from clearing that option (backward leveling from late finish): https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/level_resources.htm
- P6 EPPM v26 **Working with Future Period Planning** confirms that manual future-period values can distribute planned assignment demand unevenly across periods: https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/89612.htm

### Required independent-review questions

- Does the immutable-envelope boundary preserve the intended source facts while leaving CPM-derived dates/floats to the Shared Core intermediate pass?
- What exact resource-period demand meaning and interval/calendar conversion applies to the imported period values for each supported time-period granularity?
- What provable date horizon covers all candidate shifts and final validation for forward-only, float-limited, and backward-leveling modes? Which combinations must remain unsupported until a bounded contract exists?
- Are any PriorityList/ResourceList fields or P6 priority semantics still unsupported, and if so are they explicitly rejected rather than dropped?

No implementation claim or closure of #1468 is allowed before this review, the actual provider-path regression matrix, exact-head CI, and PostgreSQL verification.
