# Immutable Resource-Leveling Input Contract — Source-to-Code-to-Test Plan

Date: 2026-10-22  
Related blockers: [#1462](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1462), [#1468](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1468), [#1347](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1347), [#1447](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1447)

## Source-derived behavior

The implementation must remain inside the existing Shared Scheduling Core. Resource-leveling inputs are not inferred from resource spreads or cost fields; assignment-period units provide demand, while the assigned, exact-version resource calendar provides capacity. A schedule calculation must not query mutable repositories mid-evaluation.

The internal conformance references used for this work are:

- P6 Professional v26 — Level resources: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/level_resources.htm
- P6 Professional v26 — Leveling priority definitions: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_priority_definitions.htm
- P6 Professional v26 — Change the project leveling priority: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/change_the_project_leveling_priority.htm
- P6 EPPM Release 26 — Update detailed work hours: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-calendar-detailedworkhours-put.html

## Immutable input invariants

1. Resource assignments and assignment-period demands must be read under the exact `BackendScope` (tenant, project, revision). Each demand must resolve to one assignment and the assignment's activity/resource identity.
2. Resource capacity must be resolved only from the assigned `calendar_id + calendar_version`, through the existing versioned calendar resolver. No latest-version selection, ID-only fallback, guessed daily capacity, or client-side calendar calculation is permitted.
3. Every capacity slice must carry the exact calendar version and canonical calendar hash. The resulting input must be canonicalized and included in the schedule snapshot hash, so replay cannot silently adopt changed assignments, periods, or calendar definitions.
4. Before the leveling pass, CPM-derived early/late dates and Total/Free Float remain authoritative outputs from the existing scheduler. Resource-leveling rows may be rebased from these results; they must not replace or approximate CPM formulas.
5. Resource periods must use an explicit finite capacity horizon. If the scheduler cannot find a legal period inside the materialized horizon, or any required capacity period is absent, the result must fail closed through existing final resource-load validation. Missing capacity must never be treated as known zero capacity in order to claim success.
6. The authenticated publisher's repository reads and immutable snapshot/context writes must share the existing transaction. The query/evaluator must consume only the persisted immutable snapshot and must not read mutable repositories during calculation.
7. Legacy snapshots that contain no resource-leveling data remain readable for non-leveling calculations. A snapshot that requests leveling but has no bound immutable resource input continues to fail with `SCHEDULE_LEVELING_INPUT_REQUIRED`.

## Implementation and verification gate

This is an implementation contract, not a claim of full feature acceptance. The production path is accepted only when tests demonstrate persisted assignment and period writes, commit, fresh scoped reads, exact-version calendar resolution, canonical snapshot hash/replay, a leveling-enabled production Schedule Query, and final CPM constraints plus resource-capacity validation on one exact commit. Scope/version mismatch, stale calendar identity, missing periods, and missing resource input must fail closed.

The capacity horizon is intentionally explicit and hash-bound. The initial implementation may choose a conservative finite window from the schedule's dates, constraints, time-phased demand dates, activity durations, and positive relationship lags; it must not silently expand the horizon after snapshot publication. A horizon exhaustion is a validation failure and remains visible to the caller.

Independent semantic review and exact-head CI are required before merge. Until then, Issues #1462 and #1468 remain open and conformance status remains PARTIAL/UNVERIFIED.
