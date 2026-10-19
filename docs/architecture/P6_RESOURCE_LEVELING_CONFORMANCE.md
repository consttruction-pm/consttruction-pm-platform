# Primavera P6 Resource-Leveling Calculation Conformance

Status: required calculation contract; implementation and release certification must be verified against the referenced Oracle P6 Professional Version 26 behavior.

## Authority and scope

Resource leveling is a calculation capability, not a UI resemblance. For overlapping behavior, Oracle Primavera P6 Professional Help Version 26 is the compatibility baseline. The Shared Domain/Calculation Core remains the single calculation authority; adapters and clients must not implement alternative scheduling semantics.

Primary Oracle references:
- [Leveling resources](https://docs.oracle.com/cd/G48902_01/client_help/en_US/leveling_resources.htm)
- [Level resources](https://docs.oracle.com/cd/G48902_01/client_help/en_US/level_resources.htm)
- [Leveling priority definitions](https://docs.oracle.com/cd/G48902_01/client_help/en_US/leveling_priority_definitions.htm)
- [Specify leveling priorities](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/specify_leveling_priorities.htm)
- [Scheduling projects (CPM)](https://docs.oracle.com/cd/G48902_01/client_help/en_US/scheduling_projects.htm)
- [Scheduling nondriving resource assignments](https://docs.oracle.com/cd/G48902_01/client_help/en_US/scheduling__nondriving__resource_assignments.htm)

## Required semantics

1. **Resource feasibility is a hard invariant.** An activity must not be placed in a period where the selected resource demand cannot be met by effective resource availability, including the configured maximum over-allocation percentage and applicable resource/project scope. Final CPM recalculation must not reintroduce an overload. A detected final overload is a calculation failure, not a warning to suppress.
2. **Forward leveling.** Resolve resource conflicts by delaying eligible activities to the earliest feasible dates under the configured priority order, working calendars, activity relationships, constraints, and leveling options.
3. **Preserve Scheduled Early and Late Dates.** When enabled, preserve the previously calculated early/late date context and perform forward leveling only. Do not silently run backward leveling in this mode.
4. **Backward leveling.** When preservation is disabled, P6 performs backward leveling from the project's late finish toward the beginning. If resources are unavailable at late dates, eligible activities are advanced earlier. Recalculate early/late dates and floats using CPM after the accepted moves. A proposed move is not accepted if CPM relationships or explicit activity constraints make it infeasible.
5. **Relationship authority.** FS, SS, FF and SF relationships, lag interpretation, activity/resource calendars, project finish boundaries and explicit constraints remain authoritative during and after leveling. A resource-leveling heuristic cannot override them. Candidate moves must be checked against the same CPM engine used for the final schedule.
6. **Priorities are ordered, not decorative.** Priority rows are evaluated in configured order; the first row has precedence over later rows. Match P6's supported fields and sort directions. Where applicable, P6's documented fallback ordering (numeric values, alphabetic values, blanks; Activity ID when no priority codes are specified) must be represented by tests rather than approximated silently.
7. **Resource scope and multi-project runs.** Honor the configured selected-resource set and the applicable project-level leveling settings. Shared resources across projects must be leveled against one shared activity graph and one aggregate demand ledger, not project-by-project independently.
8. **Calendar-aware dates.** Move demand periods using the authoritative working-time/calendar resolver. Do not substitute calendar-day arithmetic for working-day arithmetic, or silently change calendars when evaluating a candidate.
9. **No false success.** If constraints, relationships, resource capacity, or unsupported semantics prevent a feasible result, return a specific error or explicit unsupported result. Never disable final overload checks, drop dependencies, weaken constraints, or return a schedule that violates the requested calculation contract just to make a test pass.

## Implementation and verification gate

Every change to resource leveling must:
- identify the matching P6 option/behavior and the Oracle reference above;
- use the authoritative CPM scheduler for candidate feasibility and final recalculation;
- add regression tests for the behavior and its counterexamples;
- verify the final activity dates, early/late dates, floats, relationship constraints, resource demand by period, and selected-resource scope;
- cover both preservation modes, priority order/tie-breaks, calendars/non-working days, explicit constraints, SS/FS/FF/SF and lag where applicable, and shared resources across projects;
- run the repository CI and report its actual result. Source inspection alone is not evidence of a passing calculation.

A test that expects a feasible leveled schedule must assert both dependency/constraint validity and aggregate resource feasibility. If P6's documented behavior does not fully specify an edge case, document the uncertainty and do not claim parity until it is resolved by authoritative reference behavior and a reproducible comparison.

## Current verification and remaining release gates — 2026-10-19

The previous two release-blocking regressions are addressed in the focused scheduler candidate on code/test head `b350156fa8d1ffbe651478feb97a24f2f6658f2a`:

- Shared-graph aggregate resource capacity is asserted in the batch regression; the final validator stays enabled.
- Backward leveling candidates are recalculated through authoritative CPM and infeasible candidates are rejected rather than overriding user constraints.
- The candidate validation path now receives the same activity-calendar resolver map as the intermediate/final CPM paths (commit `10dbb1b96e9f40829568f626c1ceffcce5f80f7b`; regression commit `c0a29da3e9d4b38ab3a6a986fa48cc036afd65ef`).
- Equal-advance candidate alternatives preserve the priority order generated by the proposal routine instead of being re-sorted alphabetically (commit `0e5b656b109df6849d22377850b662b3e7188e48`; regression/test head `b350156fa8d1ffbe651478feb97a24f2f6658f2a`).

Exact-head CI evidence for `b350156fa8d1ffbe651478feb97a24f2f6658f2a`:
- ConstructionPM CI passed for Python 3.11, 3.12 and 3.13: https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/39189550470
- Client Typecheck passed for client-sync, mobile, web and desktop: https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/39189550298
- PostgreSQL Integration passed: https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/39189550280

This evidence covers the current source/test branch SHA, not the merged `main` branch. It does not certify full P6 parity.

## Remaining P6 compatibility gaps

This focused branch's `leveling_boundary.py` maps only activity ID/priority, early/late dates, Free Float and Total Float. It does not itself provide the full priority-value/provenance contract for Project Leveling Priority, Activity Leveling Priority, Remaining/Planned/Original Duration and Original-or-Planned Duration, Project Planned Start, and Planned Finish. The broader field/persistence work is present in the separate open PR #1457; the two branches must be reconciled before release rather than merged independently with duplicate scheduler logic.

The required independent acceptance matrix remains: FS/SS/FF/SF crossed with negative/zero/positive lag; activity, resource and relationship-lag calendar interactions; selected-resource scope and cross-project project-level priority; priority-row precedence, value types, blank/tie ordering and hierarchy where eligible; infeasible-window behavior; authoritative early/late dates and float; final period-by-period resource demand/capacity; and preserved assignment-cost / audit semantics where configured.

Do not weaken final resource-load validation, delete dependency constraints, or accept a candidate that the authoritative CPM scheduler rejects. Full P6 parity stays **OPEN / NOT CERTIFIED** until the broader priority contract is integrated, independent human review is recorded, and final exact-head checks/behavior evidence pass on the integrated candidate.

## Continuation audit — exact-head verification and object-plane boundary (2026-10-19)

The current scheduler candidate SHA is `15a4ec5d4f0bcea049997830fed5c7ed091d715c`. GitHub reports all three checks successful on this exact SHA:
- ConstructionPM CI: success (Python 3.11, 3.12 and 3.13).
- Client Typecheck: success.
- PostgreSQL Integration: success.

This is exact-head test evidence for the current candidate, not evidence that the candidate is merged into `main`, and not certification of complete Primavera P6 parity.

### Source-backed Project vs ScheduleOptions distinction

Oracle P6 EPPM Release 26 Project REST documentation defines `LevelPriorityList` and `LevelResourceList` as Project fields. The Project-level priority list describes fields and sort direction used to prioritize resource leveling; Project also exposes distinct controls such as `LevelAllResources`, `LevelWithinFloat`, `LevelingPriority`, and `RelationshipLagCalendar`. See the official [Project PUT schema](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-project-put.html).

The separately documented ScheduleOptions REST object has `PriorityList` and `ResourceList` fields, but its scalar-string schema does not establish the internal string encoding or prove that it is interchangeable with Project's `LevelPriorityList` / `LevelResourceList`. Do not map these object planes interchangeably without an authoritative wire fixture or an authorized Release 26 GET → PUT → GET round trip. Preserve null, explicit-empty, single-item, multi-item, ordering, and escaping semantics; do not guess a delimiter.

### Integration gate

The scheduler correction and broader priority/persistence work in PR #1457 remain complementary. The application path must be demonstrated end-to-end: persisted Activity Master and project settings → canonical typed authoritative input → immutable/version-bound snapshot → Shared Scheduling Core and resource-leveling comparator. Tests that manually construct the authoritative input or snapshot do not prove this production bridge. Verify tenant/project scope, revision freshness, field provenance and calendar resolution on the real composition path.

Keep full P6 parity **OPEN / NOT CERTIFIED** until the two change sets are reconciled on one candidate, production composition is integration-tested, remaining source-backed matrix rows are closed or explicitly unsupported, independent review is recorded, and all required checks pass on the same final SHA.
