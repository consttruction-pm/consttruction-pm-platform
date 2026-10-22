# Resource Max Units/Time — Immutable Schedule Snapshot Contract

Date: 2026-10-22  
Status: **Partial implementation: immutable capacity inputs, SQLite/PostgreSQL repositories, authenticated HTTP read/write routes, and production composition are implemented; exact-head verification and P6 edge-case parity remain gated.**

## Authoritative references

- [P6 Professional v26 — Units & Prices tab / Resource Details](https://docs.oracle.com/cd/G48902_01/client_help/en_US/20417.htm)
- [P6 Professional v26 — Leveling resources](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_resources.htm)
- [P6 Professional v26 — Level resources](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/level_resources.htm)
- [P6 Professional v26 — Suspend/resume an activity](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/suspend_or_resume_an_activity_s_progress.htm)
- [P6 Professional v26 — Calendar dialog and time-period factors](https://docs.oracle.com/cd/G48902_01/client_help/en_US/calendar_dialog_box.htm)
- [P6 Professional v26 — Leveling priority definitions](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_priority_definitions.htm)

## Required calculation inputs

The maximum work available from a resource is not derived from the resource calendar alone. The P6-compatible input contract therefore binds these values to the same immutable schedule snapshot:

- Resource ID and assignment ID, activity ID, assignment unit of measure, assigned units and remaining units.
- Resource calendar ID, exact calendar version and canonical calendar snapshot hash.
- Effective-dated Max Units/Time value, time-period unit, unit of measure and explicit hours-per-period conversion.
- Whether the conversion comes from the resource calendar or global time-period settings.
- For percentage-based limits, an explicit full-time units-per-period basis; the calculation must not invent a percentage base.
- Capacity horizon start/end, calculation timezone, per-period calendar work hours, derived capacity, and the exact resource-rate hash/effective date used to derive each capacity slice.

The canonical resource facts are schema version 2. Rate and capacity facts are validated again when an immutable snapshot is materialized; the evaluator must not query mutable repositories to fill gaps.

## Capacity calculation and fail-closed rules

For an absolute Max Units/Time limit, capacity is derived from the persisted limit and the explicit period conversion, scaled by the resource calendar's work hours for the date. Percentage-based limits additionally require the persisted full-time base. Decimal arithmetic is used throughout.

Publication/materialization rejects missing or ambiguous rate data, an ineffective rate, unit mismatches, a missing calendar-period conversion, mismatched rate/calendar hashes, duplicate period records, missing capacity slices, and a capacity horizon longer than 36,500 days. The horizon bound is a safety guard, not a scheduling limit in the product specification.

P6 documentation states that resource curves are not used by resource leveling, while manually entered future-period assignment values are considered. The snapshot therefore uses persisted period-demand values for the leveling input and does not treat a distribution curve as a capacity limit.

## Implemented path and current limitations

The authenticated HTTP boundary now exposes `GET /api/projects/{project_id}/p6/resource-rates` and `POST /api/projects/{project_id}/p6/resource-rates`. It derives tenant, project, revision, and actor roles from the authenticated project session rather than trusting the request body. The production composition uses the same rate repository as the snapshot composer; an explicitly different repository is rejected as `RESOURCE_RATE_REPOSITORY_WIRING_MISMATCH`. WSGI integration tests cover read-after-write, revision scope, reader-versus-writer authorization, split-repository wiring, and immutable profile conflicts reported as HTTP `409 Conflict`. The end-to-end snapshot test also covers a rate effective-date boundary and a non-working Saturday where both calendar work-hours and capacity must be zero.

SQLite and PostgreSQL immutable inserts now use conflict-safe insert/read-back comparison, so concurrent writes to the same effective-date key converge on one identical record or return `IMMUTABLE_RESOURCE_RATE_CONFLICT` instead of exposing a raw unique-key exception. A SQLite concurrency regression test and a PostgreSQL live integration test cover this behavior; the PostgreSQL test only runs when `CONSTRUCTION_PM_POSTGRES_DSN` is configured.

1. **Multiple resource shifts:** the current date-based capacity contract rejects multiple shift identities with `RESOURCE_RATE_SHIFT_LEVELING_UNSUPPORTED`. This is intentionally fail-closed behavior, not full parity for installations where resource shift schedules affect leveling.
2. **Suspended activities:** P6 states resource assignments on a suspended activity can be treated as available to other activities until the resume date. `ActivityMaster` persistence and snapshot semantics do not yet carry a complete suspend/resume interval into resource leveling. The HTTP activity write route now rejects populated `suspend_date` or `resume_date` with `ACTIVITY_SUSPEND_RESUME_NOT_PERSISTED`, rather than silently discarding those schedule-critical values. This is a protective fail-closed guard, not feature parity; proper persisted date semantics and demand suppression remain open.
3. **Cross-project resources:** P6 supports leveling decisions that can consider assignments from other open projects according to project leveling priority. The present rate/assignment snapshot is revision-scoped to one project and does not yet bind a multi-project leveling pool and its project-priority ordering.
4. **Post-level critical paths:** the code must prove that CPM dates/float and resource-driven critical-path outputs are recalculated/represented according to the selected P6 leveling options after changes. This behavior is not yet accepted by an independent semantic test in this work item.
5. **Percentage rates:** percentages require an authoritative full-time units-per-period base. The contract never infers a percentage base from job title, resource type, calendar, or unit.
6. **Time-period settings:** calendar-sourced conversion factors must be present in the versioned calendar snapshot. Missing factors are rejected rather than replaced with a default.

## Acceptance gate

Do not mark resource leveling complete until all of the following are evidenced on the same commit:

- Production composition binds the authenticated rate API to the exact same version-scoped repository used by the authoritative snapshot composer; the WSGI test proves read/write wiring at the app boundary.
- The authenticated write/read surface persists effective dates, Max Units/Time, unit, time-period source/conversion and percentage base without lossy defaults; tests reject invalid percentage rates and unauthorized writes.
- The snapshot publication route reads assignments, demand periods, rates and calendar versions in one transaction and commits their complete immutable payload/hash.
- The schedule query materializer reproduces the same facts from the saved snapshot and performs no mutable repository reads.
- Regression tests cover rate changes at an effective-date boundary, absolute and percentage limits, calendar/global time-period settings, zero/nonwork capacity, missing data, cross-tenant/revision isolation, concurrent conflicting writes, and the explicitly unsupported shift case. Suspended-activity intervals, cross-project leveling, and post-level resource-driven critical paths must receive dedicated tests before claiming parity.
- CI and PostgreSQL integration pass on the exact candidate commit, followed by independent review.

Until these gates are satisfied, this work remains a tested partial integration rather than a claim of complete P6 resource-leveling parity.
