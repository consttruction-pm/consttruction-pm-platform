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

## Known release-blocking regression cases

The regression cases observed during this work—shared-graph resource over-allocation after final CPM recalculation and a backward-leveling move that violates a `START_NO_LATER_THAN` constraint—must be covered at the candidate-selection/orchestration boundary. The shared-graph regression now asserts the final scheduled dates and aggregate demand against each period's capacity. CI passed on commit `921bd0ac4bf20800d0eb7e3b5b80269ee88eb574`; broader release certification remains pending independent review and additional coverage of relationship/calendar/priority edge cases. The final resource-load validator and the authoritative CPM constraints must remain enabled. The correct fix is to accept only P6-compatible, CPM-feasible moves and to re-evaluate aggregate shared-resource demand—not to weaken validation.
