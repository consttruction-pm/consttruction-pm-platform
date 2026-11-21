# Calendar registry traceability — P0-N.2

Blocker under test: `_calendar_registry_not_wired` and
`SCHEDULE_QUERY_NOT_DEPLOYED`. Both were configuration guards that prevented the
production runtime from constructing a `CalendarResolverRegistry`; the schedule
query endpoint therefore could not be deployed against persisted calendars.

## 1. Before / after

| Point | Before (`ae6e72e4`) | After (`8fdb06a9`) |
| --- | --- | --- |
| Registry construction | `calendar_registry_factory=None`; `ProductionRuntime` raised `ProductionConfigurationError("SCHEDULE_QUERY_NOT_DEPLOYED")` | `build_calendar_registry_for_scope()` reads the four PostgreSQL calendar repositories for the snapshot scope |
| Scope | n/a | `BackendScope(tenant_id, project_id, project_revision)` of the snapshot; another tenant/project/revision can never resolve |
| Version pinning | n/a | key `calendar_id@calendar_version`; no “latest version” substitution |
| Blocker strings | present in `production_runtime.py` | absent from the production path; asserted by a source-level test |
| Provider wiring | zero-argument factory | `scoped_calendar_registry_factory(scope)` (`authoritative_schedule_query.py:50,62`) |
| Schema | calendar tables not initialized by production | `initialize_production_schema()` initializes all four calendar tables and the job schema (`deployment/schema.py`) |

## 2. Builder algorithm (`p6_versioned_resource_calendar_resolver.py:205`)

For every master row returned by `calendar_repository.list(scope)`:

1. Reject a kind outside `{working-day, working-time}` with
   `CALENDAR_KIND_UNSUPPORTED:<key>`.
2. Validate the master; a persistence-level defect becomes
   `CALENDAR_DEFINITION_INVALID:<key>:<reason>` instead of an untyped failure.
3. Reject scope or revision drift: `CALENDAR_SCOPE_OR_REVISION_MISMATCH`.
4. Reject duplicate keys: `CALENDAR_KEY_DUPLICATED:<key>`.
5. Require a snapshot: `CALENDAR_SNAPSHOT_NOT_FOUND:<key>`.
6. Require snapshot identity and kind agreement with the master:
   `CALENDAR_SNAPSHOT_IDENTITY_MISMATCH`, `CALENDAR_SNAPSHOT_KIND_MISMATCH`.
7. Parse the canonical snapshot into `WorkingCalendar` (working-day) or
   `WorkingTimeCalendar` (working-time); parse failure is `INVALID_CALENDAR_SNAPSHOT`.
8. Load persisted work-hour rules and apply `apply_weekly_work_hour_rules`; the
   closed-set rule errors (`DATED_DETAILED_WORK_HOURS_REQUIRE_DATE_KEY`,
   `CALENDAR_TOTAL_WORK_HOURS_MAPPING_UNVERIFIED`, `WEEKDAY_REQUIRED`,
   `WORK_HOUR_MODE_CONFLICT`, `OVERLAP_WORK_HOUR_INTERVAL`) propagate unchanged.
9. Register `WorkingTimeResolver` or `TimeAwareWorkingTimeResolver`; attach
   `CalendarExceptionLayers(local=...)` only when the scope actually has exceptions.
10. Resolve bases only inside the same scope. A parent that is not registered is
    `BASE_CALENDAR_NOT_REGISTERED:<child>-><parent>`; a working-day child with a
    working-time parent (or vice versa) is `CALENDAR_INHERITANCE_KIND_MISMATCH`.

`calendar_registry_hash()` (`:338`) canonicalises references, snapshots, bases and
local/inherited exceptions, then SHA-256s them. The hash is stable across two
independent builds from the same rows and changes when any of those inputs change.

## 3. Why it cannot silently invent a calendar

* No default calendar is registered. A `CalendarReference` that is not a persisted
  row fails at `CalendarResolverRegistry.resolve()` with `KeyError`.
* No “latest version” lookup. `CAL-1@2` never resolves to `CAL-1@1`.
* Base chains are validated after all rows are known, but only within the same
  scope; a cross-scope base is treated as unregistered.
* Work-hour rules are applied fail-closed; a total-hours/weekday conflict is an
  error, not an approximation.

## 4. Tests

| Test | What it proves | Runs |
| --- | --- | --- |
| `tests/test_calendar_registry_production_builder.py` (6 tests) | definition+snapshot build, stable hash, persisted 4-day week changes arithmetic, missing snapshot, unsupported kind, base-kind mismatch, scope isolation | every CI run (SQLite) |
| `tests/integration/test_p0n2_runtime_activation.py::test_calendar_registry_is_built_from_persisted_calendars` | real PostgreSQL rows → registry | PostgreSQL run |
| `...::test_calendar_registry_is_scoped_and_hash_is_stable` | scope bound and hash stable | PostgreSQL run |
| `...::test_missing_calendar_version_fails_closed_without_latest_fallback` | no latest-version fallback | PostgreSQL run |
| `...::test_unregistered_base_calendar_fails_closed` | base chain closed | PostgreSQL run |
| `...::test_production_runtime_source_no_longer_contains_the_wiring_blocker` | strings absent | PostgreSQL run |
| `...::test_http_submit_runs_on_real_worker_and_result_is_retrieved` | registry used by the real worker path | PostgreSQL run |

Observed results (2026-11-20, commit `8fdb06a9`):

```
tests/test_calendar_registry_production_builder.py                6 passed
tests/integration/test_p0n2_runtime_activation.py                11 passed
```

Logs: `logs/targeted.log`, `logs/full-suite.log`.

## 5. GitHub references

* Builder: `src/construction_pm/p6_versioned_resource_calendar_resolver.py`
* Scope wiring: `src/construction_pm/backend_p0/authoritative_schedule_query.py`
* Runtime composition: `src/construction_pm/deployment/production_runtime.py`
* Schema: `src/construction_pm/deployment/schema.py`
* Builder tests: `tests/test_calendar_registry_production_builder.py`
* Live proof: `tests/integration/test_p0n2_runtime_activation.py`

All paths are published on branch `feat/p0n2-runtime-activation` at commit
`8fdb06a9`.
