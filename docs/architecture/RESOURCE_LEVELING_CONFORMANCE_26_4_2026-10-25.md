# Resource-leveling conformance matrix — 2026-10-25

## Purpose and release status

This matrix records source-derived resource-leveling behavior before changing calculation semantics. It is an engineering evidence map, not a certification of parity.

**Status: BLOCKED / NOT PARITY-CERTIFIED.** Current main has a fail-closed production boundary: the authoritative evaluator requires `SchedulerLevelingInput` when resource-leveling options are enabled, but the production snapshot/query path does not yet provide a hash-bound input. Do not count resource leveling as implemented because the shared scheduler or the Web options form exists.

## Official, versioned source set

Source set reviewed: P6 Professional User Guide / online help, Version 26, published 2026-07-16.

- Leveling resources index: https://docs.oracle.com/cd/G48902_01/client_help/en_US/levelingresources.htm
- Leveling priority definitions: https://docs.oracle.com/cd/G48902_01/client_help/en_US/leveling_priority_definitions.htm
- Specify leveling priorities: https://docs.oracle.com/cd/G48902_01/client_help/en_US/specify_leveling_priorities.htm
- Level resources: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/level_resources.htm
- Level selected resources: https://docs.oracle.com/cd/G48902_01/client_help/en_US/level_selected_resources.htm
- Limit resource leveling: https://docs.oracle.com/cd/G48902_01/client_help/en_US/limit_resource_leveling.htm
- Level resources automatically: https://docs.oracle.com/cd/G48902_01/client_help/en_US/level_resources_automatically.htm
- Leveling on Task, Resource Dependent, and WBS summary activities: https://docs.oracle.com/cd/G48902_01/client_help/en_US/leveling_resources_on_task_resource_dependent_wbs_activities.htm

The reference must remain internal technical metadata. User-facing site labels, help text and reference explorer must not render vendor names, URLs, logos or source-document branding.

## Source-to-code conformance matrix

| ID | Source-derived rule / edge case | Current code path | Evidence status | Required code and acceptance evidence |
|---|---|---|---|---|
| RL26-01 | Leveling priority rows are ordered: a field higher in the list takes precedence over all fields beneath it. | `scheduling/leveling_boundary.py::_map_priority_list`; `ScheduleOptions.priority_list` | **Partial / unverified** | Preserve ordered entries end-to-end without sorting/deduplication. Test two conflicting activities where reversing row order reverses the chosen activity; persist→fresh-read→snapshot must preserve the exact list and order. |
| RL26-02 | Priority sort directions exist for Activity ID, Activity Priority, Early Finish/Start, Free Float, Late Finish/Start, Original or Planned Duration, Planned Finish, Project Planned Start, Project Priority, Remaining Duration and Total Float. Numeric values sort before alphabetic, then blanks; no priority list falls back to Activity ID. | `_map_priority_list` currently accepts only `activity_id`, `activity_priority`, `early_start`, `early_finish`, `late_start`, `late_finish`, `free_float`, `total_float`. | **Known gap** | Enumerate and type every in-scope priority field and sort order with stable field-specific semantics. Add ascending/descending fixtures for each field, mixed numeric/alphabetic/blank activity IDs, and the no-priority Activity-ID fallback. Do not silently accept unsupported fields. |
| RL26-03 | `Level All Resources` applies to all project resources even if a selected-resource list exists; clearing it permits the selected subset to control leveling. | `ScheduleOptions.level_all_resources`, `resource_list`, `ResourceLevelingOptions.resource_ids` | **Mapped / not production-wired** | Map the canonical selection once, preserve empty-vs-absent-vs-populated lists, and test all-resource precedence and subset exclusion through persisted project data. |
| RL26-04 | Preserve Scheduled Early and Late Dates retains previously calculated early/late dates during resource leveling. | `ScheduleOptions.preserve_scheduled_early_and_late_dates`; `schedule_with_resource_leveling` | **Mapped / behavior not production-proven** | Prove early/late preservation and final resource-load validation on the authoritative snapshot path. Never report success if final resource over-allocation remains. |
| RL26-05 | Level Resources Only Within Activity Total Float limits resource-conflict delays to late dates; the controlling late boundary depends on start-float versus finish-float behavior. | `ScheduleOptions.level_within_float`; shared leveling scheduler; total-float option mapping | **Mapped / edge behavior needs independent review** | Link the float mode to the exact controlling boundary, preserve constraints and relationship logic, and test LS/LF boundaries, zero/negative/minimum float, and impossible demands. No new boundary rule until reviewed against this source. |
| RL26-06 | Preserve Minimum Float When Leveling retains the configured minimum float; Max Percent to Overallocate Resources can increase availability by the specified percentage after the float limit has been exhausted. | `min_float_to_preserve`, `over_allocation_percentage`, `ResourceLevelingOptions` | **Mapped / production wiring absent** | Confirm units, decimal precision and boundary conditions against the typed domain. Test zero and nonzero values, exact capacity threshold, permitted over-allocation, and final capacity validation; test the final ledger rather than only the proposed shift. |
| RL26-07 | Task Dependent activities with driving and nondriving assignments require all resources to be available to place the activity. Resource Dependent activities are driven by driving resources; nondriving resources are placed on/after activity dates and can be delayed separately. WBS Summary activities are ignored by leveling. | `Activity` and resource assignment persistence; adapter `build_scheduler_leveling_input`; resource leveling core | **Not demonstrated end-to-end** | Persist and snapshot activity type plus driving/nondriving assignment semantics. Add separate forward/backward tests for each combination, nondriving-only activity, unavailable nondriving resource, and WBS summary. Do not flatten these cases into one generic assignment rule. |
| RL26-08 | Resource curves are not used by leveling; a resource assigned to a suspended activity is treated as available to others until the resume date. Failed assignments must be represented in leveling output/reporting. | Resource-assignment period data and shared resource-leveling output | **Inventory / contract gap** | Define how suspension/resume and failed-assignment details enter the immutable snapshot and output contract. Test resource availability before/at/after resume dates and ensure failures are visible to the caller. |
| RL26-09 | When two activities from different chains are ready for leveling, priorities determine which is considered; if no priorities are set, Activity ID order is used. | `scheduling/leveling_scheduler.py`; `scheduling/leveling_boundary.py` | **Shared Core tests exist; production path unproven** | Test deterministic tie-breaking and exact selected order on a repository-backed authoritative query, with repeatable output identity. |
| RL26-10 | Resource assignments, time-phased demand and capacity data must be from the same tenant/project/revision and immutable snapshot used by the calculation. This is a platform safety invariant, not a substitute for source semantics. | `authoritative_schedule_input_composer.py`; `schedule_input_snapshot_repository.py`; `p6_resource_leveling_read_adapter.py`; `backend_p0/authoritative_schedule_query.py` | **Known production blocker** | Create a versioned/hash-bound resource-leveling payload or companion snapshot bound to the exact schedule snapshot, including assignment IDs, period-demand values, selected resource set, resource-calendar IDs/versions/canonical hashes, capacity slices, options and provenance. Provider must pass only this bound payload to the evaluator; no mutable repository reads inside evaluation. |
| RL26-11 | A fresh authoritative run must consume persisted data after commit, not caller-created in-memory scheduler rows. Stale project/calendar/resource revisions must fail closed. | `AuthoritativeScheduleInputComposer`; `ScheduleInputSnapshotRepository`; `AuthoritativeScheduleQueryProvider.execute` | **Not accepted** | Integration test must persist Activity Master, relationships, resource assignments, period values and versioned resource calendars; commit; create a fresh request/read path; publish; query; verify snapshot payload/hash and result. Include tenant, project, project revision and resource-calendar revision mismatch negatives. |
| RL26-12 | Schedule Options REST/interchange values are not interchangeable with resource-leveling project settings simply because names are similar; source contract and wire shape govern the mapping. | `scheduling/leveling_boundary.py::_map_priority_list`; resource-leveling settings and REST adapters | **Open mapping gap** | Reconcile typed `PriorityList`/`ResourceList` vs project `LevelPriorityList`/`LevelResourceList` with exact source/version evidence, preserving ordering and distinguishing missing, empty, malformed and populated values. Track with #1379 and #1447. |

## Implementation facts verified on main at the time of writing

- `AuthoritativeScheduleQueryProvider.execute` calls `evaluate_schedule_snapshot(snapshot, calculation_context, registry)` without a leveling input.
- `schedule_evaluator.py` rejects resource-leveling settings without `SchedulerLevelingInput` using `SCHEDULE_LEVELING_INPUT_REQUIRED`.
- `p6_resource_leveling_read_adapter.py::build_scheduler_leveling_input` maps persisted assignment/period DTOs into the shared boundary, but is not composed into the authoritative query path.
- `AuthoritativeScheduleInputComposer.compose` currently rejects resource-leveling settings and nonempty persisted resource assignments/periods because they are not bound to the snapshot.
- `SchedulerLevelingInput` holds forward and backward candidate rows, capacities and options, but these rows/capacities are not currently persisted as part of the schedule snapshot's canonical hash.
- The Website now exposes the reference inventory and a Run Schedule flow. This does not close the engine/input-snapshot gap or establish calculation parity.

## Mandatory implementation gate

Before changing resource-leveling calculation semantics:

1. An independent reviewer must confirm the source interpretation and the listed edge cases.
2. The resource demand/capacity source contract and calendar version binding must be accepted before an adapter can be considered production-ready.
3. The implementation must include a documented trace from persisted writes through commit, fresh read, immutable snapshot/hash, query provider, Shared Core evaluation and response.
4. Tests must include nonempty real persistence data, both forward/backward leveling, priority precedence/order, final resource-load validation, invalid/stale/unauthorized inputs and PostgreSQL-backed execution where supported.
5. A green aggregate CI without the above path coverage does not close #1462, #1468, #1347, #1379 or #1447.

Until those checks pass, keep the feature status as a known gap and keep the evaluator's fail-closed behavior. Do not silently ignore resource assignments or tell the user leveling completed.
