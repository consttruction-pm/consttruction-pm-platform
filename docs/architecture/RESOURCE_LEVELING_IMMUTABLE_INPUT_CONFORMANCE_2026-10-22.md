# Immutable Resource-Leveling Input Contract — Source-to-Code-to-Test Plan

Date: 2026-10-22  
Related blockers: [#1462](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1462), [#1468](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1468), [#1347](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1347), [#1447](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1447)

## Source-derived behavior

The implementation must remain inside the existing Shared Scheduling Core. Resource-leveling inputs are not inferred from cost fields; assignment-period units provide demand, while capacity is calculated from the assigned, exact-version resource calendar's working hours and the resource's effective-dated Max Units/Time profile. Rate and calendar facts are bound into the immutable snapshot. A schedule calculation must not query mutable repositories mid-evaluation.

The internal conformance references used for this work are:

- P6 Professional v26 — Level resources: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/level_resources.htm
- P6 Professional v26 — Leveling priority definitions: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_priority_definitions.htm
- P6 Professional v26 — Change the project leveling priority: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/change_the_project_leveling_priority.htm
- P6 EPPM Release 26 — Update detailed work hours: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-calendar-detailedworkhours-put.html

## Immutable input invariants

1. Resource assignments and assignment-period demands must be read under the exact `BackendScope` (tenant, project, revision). Each demand must resolve to one assignment and the assignment's activity/resource identity.
2. Resource capacity must combine the assigned `calendar_id + calendar_version` with the resource's effective-dated Max Units/Time rate profile and explicit time-period factors. No latest-version selection, ID-only fallback, guessed daily capacity, implicit percentage base, or client-side calendar calculation is permitted.
3. Every capacity slice carries the exact calendar version/hash plus the selected rate profile's effective date/hash; the complete raw fact set is canonicalized into the schedule snapshot hash. Replay therefore cannot silently adopt changed assignments, periods, calendar definitions, or rates.
4. Before the leveling pass, CPM-derived early/late dates and Total/Free Float remain authoritative outputs from the existing scheduler. Resource-leveling rows may be rebased from these results; they must not replace or approximate CPM formulas.
5. Resource periods must use an explicit finite capacity horizon. If the scheduler cannot find a legal period inside the materialized horizon, or any required capacity period is absent, the result must fail closed through existing final resource-load validation. Missing capacity must never be treated as known zero capacity in order to claim success.
6. The authenticated publisher's repository reads and immutable snapshot/context writes must share the existing transaction. The query/evaluator must consume only the persisted immutable snapshot and must not read mutable repositories during calculation.
7. Legacy snapshots that contain no resource-leveling data remain readable for non-leveling calculations. A snapshot that requests leveling but has no bound immutable resource input continues to fail with `SCHEDULE_LEVELING_INPUT_REQUIRED`.

## Implementation and verification gate

This is an implementation contract, not a claim of full P6 feature acceptance. The current implementation demonstrates the persisted → immutable snapshot → query path in `test_leveling_snapshot_binds_persisted_resource_inputs_and_executes_production_query`: it seeds activity/assignment/period/rate data, publishes and reads the hash-bound snapshot, verifies effective-date capacity changes and non-work-day zero capacity, then executes authenticated Schedule Query and verifies the leveling result. WSGI tests cover rate read/write authorization, HTTP 409 immutable conflicts, shared repository wiring, and fail-closed unsupported settings. The evaluator now resolves the exact activity-calendar map and the schedule-wide P6 relationship-lag calendar option for both CPM and leveling; regressions cover an activity calendar that differs from the project calendar and a predecessor-calendar lag holiday. Because P6 defines lag calendar as a schedule-wide option, legacy/nonstandard per-relationship lag overrides are rejected by the composer and materializer rather than silently changing results. Exact current checkpoint `7d567597b969a2910db3fede3a681c40039fe4fd` passed ConstructionPM CI (2,695 passed, 93 skipped), PostgreSQL Integration, and Client Typecheck. Remaining full-feature acceptance requires versioned resource-shift calendars, suspended activity semantics, Resource Dependent driving/nondriving behavior, cross-project leveling priorities, recalculated resource assignment costs, and independent tests for post-level resource-driven critical-path semantics. Scope/version mismatch, stale calendar identity, missing periods, and unsupported requests fail closed.

The capacity horizon is intentionally explicit and hash-bound. It must not silently expand after publication; horizon exhaustion remains a validation failure visible to the caller.

A legacy utility, `p6_resource_leveling_read_adapter.py`, still builds capacity from `ResourceCalendar.capacity_on()` and has no Max Units/Time rate binding. It must not replace the authoritative snapshot composer/evaluator for production P6 leveling. New production leveling requests must use the immutable snapshot path or fail closed.

Exact-head CI currently verifies the implemented slice, but full conformance remains **PARTIAL/UNVERIFIED**. Keep Issues #1462 and #1468 open until the explicit semantic gaps above are implemented and verified; do not mark this entire resource-leveling feature complete.
