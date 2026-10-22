# Resource-Leveling Regression Correction — Source-to-Code-to-Test Record

Date: 2026-10-21  
Scope: close the two known backward/resource-leveling regressions in Issue #1476. This note describes the acceptance contract; it does not certify full P6 parity.

## Authoritative, versioned references

- [P6 Professional Version 26 — Level resources](https://docs.oracle.com/cd/G48902_01/client_help/en_US/level_resources.htm): resource-leveling behavior and preservation/leveling controls.
- [P6 Professional Version 26 — General tab, Schedule Options](https://docs.oracle.com/cd/G48902_01/client_help/en_US/general_tab_-_schedule_options_dialog_box.htm): “Level resources during scheduling”, “Calculate start-to-start lag from”, and “Calendar for scheduling Relationship Lag”.
- [P6 Professional Version 26 — Relationships tab, Activity Details](https://docs.oracle.com/cd/G48902_01/client_help/en_US/relationships_tab_-_activity_details.htm): supported FS, FF, SS and SF relationships and relationship Lag field.
- [P6 Professional Version 26 — Leveling priority definitions](https://docs.oracle.com/cd/G48902_01/client_help/en_US/leveling_priority_definitions.htm): supported priority values and ordering.
- [P6 EPPM Release 26 — Relationship GET schema](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-relationship-get.html): authoritative relationship Type/Lag data contract.
- [P6 EPPM Release 26 — ScheduleOptions GET schema](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-get.html): RelationshipLagCalendar and StartToStartLagCalculationType configuration.

## Source-derived rules and observable contract

| Rule | Inputs that must be honored | Expected output / invariant | Implementation and regression evidence |
|---|---|---|---|
| A proposed backward move is a candidate, not permission to violate the CPM network. | Early/late dates, predecessor/successor relationships, project finish, explicit constraints, configured preservation mode. | A candidate is accepted only when the authoritative CPM scheduler can produce a feasible schedule; infeasible candidates are rejected without suppressing unrelated errors. | `src/construction_pm/scheduling/leveling_scheduler.py`; `test_public_backward_leveling_moves_linked_activities_without_breaking_ss`; targeted CI on the exact final SHA required. |
| Final resource feasibility is a hard invariant. | Selected resources, demand by resource/period, capacity by resource/period, over-allocation percentage, priority order, project scope. | Aggregate batch demand must not exceed effective capacity for any occupied period after final CPM propagation; no “success” may be returned with a final overload. | `_validate_final_resource_load`; `test_shared_resource_leveling_runs_once_for_the_batch_graph`; final output assertions must confirm both date placement and aggregate capacity. |
| Every CPM pass and every demand translation must use the effective calendar for that activity. | Project resolver plus the resolved per-activity calendar map; activity/resource period demand. | Initial/intermediate/final dates, backward candidates, forward demand shifts, and final load validation use consistent working-time semantics. | `schedule_with_resource_leveling`, `propose_forward_leveling`, backward proposal, `apply_leveling_shifts`, and final-load validation receive the activity resolver map; regression tests assert that the actual output path preserves the calendars. |
| Backward alternatives preserve configured proposal precedence. | Ordered priority rows, sort direction, tie-break fields, candidate advance size. | Retry order may reject infeasible alternatives but must not alphabetically reorder candidates in a way that changes an already-established configured priority sequence. | `_order_backward_leveling_candidates`; `test_backward_candidate_order_preserves_proposal_priority_for_equal_advances`. |
| Priority values must be authoritative, not estimated. | CPM-derived early/late dates and Total/Free Float; supported typed priority fields. | Missing authoritative values fail explicitly; no substitution of Total Float for Free Float or unrelated dates. | `_forward_activities_with_authoritative_floats`; forward/backward priority regression tests. |
| Leveling rows and time-phased demands must be rebased to the fresh CPM early schedule before priority ordering. | Fresh CPM early start/finish, Total/Free Float, late dates, original LevelingActivity dates, activity-calendar resolver and demand periods. | Early dates and Total Float must not remain stale; assignment demand periods shift by the same working-day displacement under the activity calendar; no raw demand is silently dropped. | `_forward_activities_with_authoritative_floats`; `test_forward_activity_builder_rebases_all_values_from_fresh_cpm`; `test_public_leveling_rebases_resource_periods_to_fresh_cpm_dates`. |
| Unrestricted forward leveling must not replace real priority inputs with synthetic float/date values. | User-selected PriorityList fields including Total Float, Free Float, Late Start, Late Finish, plus the configured maximum shift. | The unconstrained path removes only the float movement limit; it preserves true priority values and late-date fields and has an explicit maximum-shift bound. | `propose_forward_leveling`; `test_unrestricted_forward_leveling_preserves_authoritative_priority_values`. |
| Backward leveling must retain already accepted forward demand at the intermediate CPM period. | Forward-shifted/protected activity IDs, the initial CPM dates/demand periods, intermediate early dates, late-date candidate windows and per-activity calendars. | Protected demand remains at its already accepted intermediate date in the backward capacity ledger; non-protected candidates use their candidate late windows. This prevents falsely freeing a shared-resource period before the final CPM check. | `_backward_activities_from_intermediate`; `test_backward_builder_keeps_protected_forward_demand_at_intermediate_cpm_period`; final batch capacity regression. |

## Known defects under correction

1. `test_shared_resource_leveling_runs_once_for_the_batch_graph`: current main previously failed with `FINAL_RESOURCE_OVERALLOCATION:R1:2026-10-02:demand=2:capacity=1.0`.
2. `test_public_backward_leveling_moves_linked_activities_without_breaking_ss`: current main previously failed with `ConstraintViolation: start no later than constraint violated for B`.

These failures are release blockers until the actual schedule and aggregate demand outputs are feasible on the integrated final commit. Do not update expected results to conceal an overload or weaken the authoritative CPM/constraint/resource validator.

## Required verification

- Focused tests for the two defect reproductions plus the added fresh-CPM rebasing, signed lag × relationship types, backward candidate-order, activity-calendar, authoritative Total/Free Float, late-date and unrestricted priority tests.
- Full ConstructionPM CI for Python 3.11, 3.12 and 3.13, Client Typecheck, and applicable PostgreSQL Integration on the *same final SHA*.
- Independent semantic review on that final SHA.
- Exact commit SHA, CI links, reviewer disposition, final activity dates/relationships/constraints and per-resource/per-period demand/capacity must be recorded in Issue #1476 before closure.

## Status

**OPEN — verification pending for the reconciled current-main-based branch.** No full P6 certification, production Schedule Query integration, or issue closure is claimed here. The separate persisted Activity Master → authoritative snapshot and version-bound resource-leveling input → Schedule Query gates remain tracked in Issues #1462 and #1468.
