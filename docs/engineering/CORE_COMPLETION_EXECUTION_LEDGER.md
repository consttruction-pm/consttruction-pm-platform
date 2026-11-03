# CUBI Core Completion Execution Ledger

Branch: `codex/jalal/resource-dependent-core-20261102`
Baseline: `main` at `2577a56287f446fe0177458808e77952c12d4d7a`
Latest implementation/test head: `1a9dbfea` (this ledger update follows it)
PR: #1668 (open; not yet Ready/merged)

This ledger is the durable continuation record for the core-calculation mission.
It records what is implemented in real code, which tests prove it, what remains
open, and which acceptance criteria are still unmet. A capability is never
promoted to parity-tested merely because code or a unit test exists. No licensed
Version 26 reference run is available in this environment, so no row is marked
`IMPLEMENTED_AND_PARITY_TESTED` on this branch.

## Compliance matrix

The matrix uses exactly the sixteen required columns. Column key:

1. ID — stable capability ID
2. Capability
3. Version 26 reference behavior
4. Formula / algorithm
5. Inputs and units
6. Calendar or time basis
7. Current CUBI code path
8. Current test path
9. Actual implementation status
10. Observed difference
11. Required change
12. Required numeric test
13. Required integration test
14. Test result at this head
15. Official reference URL
16. Implementation/test SHA

| 1 ID | 2 Capability | 3 Reference behavior | 4 Formula / algorithm | 5 Inputs and units | 6 Calendar / time basis | 7 Current CUBI code path | 8 Current test path | 9 Status | 10 Observed difference | 11 Required change | 12 Required numeric test | 13 Required integration test | 14 Test result | 15 Official URL | 16 SHA |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CPM-01 | Forward pass | Early dates honor project start, Data Date, duration, calendars, relationships, lag, constraints and progress. | Event-time propagation; `ES = max(predicate bounds, constraint bounds, project start, data date)`; `EF = ES + duration - 1` in working days. | Activity durations, remaining durations, actual dates, constraints; days. | Activity calendar; project calendar; Data Date. | `src/construction_pm/scheduling/forward_pass.py`, `schedule.py` | `tests/scheduling/test_forward_pass.py`, `test_progress_data_date_anchor.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Reference fixture equivalence for every calendar/lag/constraint combination is not yet run. | Add Version 26 numeric fixtures for combined calendar/lag/constraint/progress cases. | ES/EF for FS/SS/FF/SF with positive, zero and negative lag across two calendars. | Full schedule composed from persisted snapshot; assert dates and floats. | PASS — full suite 3280 passed / 139 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Schedule calculations) | bf0424db |
| CPM-02 | Backward pass | Late dates honor project finish, relationships, lag, constraints, float options and leveling changes. | Backward event propagation; `LS`, `LF`, total float and free float from authoritative CPM outputs. | Late constraints, project finish, durations; days. | Activity calendar; project finish basis. | `src/construction_pm/scheduling/forward_pass.py`, `schedule.py` | `tests/scheduling/test_backward_constraints.py`, `test_schedule.py` | IMPLEMENTED_TESTED_PARITY_PENDING | No licensed reference fixture for project-finish and constraint combinations. | Add reference fixtures for backward pass with negative float and leveling constraints. | Late dates and floats for each relationship type and constraint kind. | Backward pass after resource-leveling constraints; assert float paths. | PASS — full suite 3280 passed / 139 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Schedule calculations) | bf0424db |
| CPM-03 | Relationships FS/SS/FF/SF and lag/lead | All four types apply the correct start/finish bound with calendar-aware lag. | FS: successor start ≥ predecessor finish + lag; SS: start ≥ start + lag; FF: finish ≥ finish + lag; SF: finish ≥ start + lag; inverse for backward. | Relationship type, lag, lag unit/calendar; days/hours. | Relationship lag calendar; activity calendars. | `src/construction_pm/scheduling/relationships.py`, `forward_pass.py`, `schedule_options.py` | `tests/scheduling/test_relationships.py`, `test_relationships` cases in `test_schedule.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Version 26 fixture equivalence and every lag-calendar interaction are not certified. | Build reference fixtures for each type × lag sign × lag calendar. | Hand-computed working dates for the 4×3 matrix. | Persisted relationship ingestion and schedule assertion. | PASS — full suite 3280 passed / 139 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Relationships and lag) | bf0424db |
| CPM-04 | Float and critical path | Total/Free Float selection and critical-path rules are configurable and explicit. | Start float = LS−ES; finish float = LF−EF; smallest float; critical when float ≤ threshold; open-ended critical option. | Float options, threshold; days. | Activity calendar. | `src/construction_pm/scheduling/schedule.py`, `schedule_options.py` | `tests/scheduling/test_schedule.py`, `test_public_forward_backward_leveling.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Reference threshold/path fixtures absent. | Add reference fixtures for each float mode and critical rule. | Float values and critical flag for each mode. | Schedule options persisted and replayed through API. | PASS — full suite 3280 passed / 139 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Float and critical activities) | bf0424db |
| CPM-05 | Multiple float paths | Path count, endpoint and Total/Free Float basis are honored. | Rank near-critical paths from the selected endpoint; emit path number per activity. | Path count 0–1000, endpoint ID/short name, float basis. | Activity calendar. | `src/construction_pm/scheduling/schedule.py` (`_multiple_float_paths`, `_resolve_ending_activity_short_name`) | `tests/scheduling/test_schedule.py`, `tests/scheduling/test_schedule_options_capabilities.py`, `tests/scheduling/test_multi_project_float.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Persisted short-name endpoint resolution is implemented: a unique persisted short name selects the endpoint, while missing, ambiguous and non-driving matches fail closed, and an object-id/short-name disagreement is rejected. Reference path ordering and float-basis behavior are not certified. | Add Version 26 reference fixtures for path numbering and float basis. | Path numbers for two near-critical chains. | Endpoint resolution from persisted activity identity. | PASS — short-name selector and rejection matrix covered; full suite result recorded in Stage 10. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Multiple float paths) | 2609330e |
| CPM-06 | Out-of-sequence and Data Date progress | Retained Logic, Progress Override and Actual Dates are distinct; progressed work anchors at the Data Date. | Remaining work starts at max(Data Date, actual/early bound); completed work retains actual finish; OOS policy controls remaining-logic propagation. | Actual start/finish, remaining duration, Data Date; days. | Activity calendar; Data Date. | `src/construction_pm/scheduling/progress_state.py`, `out_of_sequence.py`, `forward_pass.py` | `tests/scheduling/test_out_of_sequence.py`, `test_oos_policy.py`, `test_progress_data_date_anchor.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Reference fixtures for each OOS mode in combination with constraints are not run. | Add combined OOS × constraint × Data Date fixtures. | In-progress activity with stale early dates measured at Data Date. | Progress snapshot through authoritative composer. | PASS — full suite 3280 passed / 139 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Out-of-sequence scheduling) | bf0424db |
| CPM-07 | Data Date anchor and completed work | Data Date never moves completed actual dates; unstarted activities keep early dates; remaining work begins no earlier than Data Date. | Completed: keep actual end. In progress: `remaining_start = max(Data Date, actual/early bound)`. Not started: CPM early start. | Data Date, actual dates, remaining duration. | Activity calendar. | `src/construction_pm/scheduling/forward_pass.py`, `authoritative_schedule.py` | `tests/scheduling/test_progress_data_date_anchor.py` | IMPLEMENTED_TESTED_PARITY_PENDING | No licensed reference run for boundary weekends/holidays at Data Date. | Add reference fixtures for Data Date on nonworking days and completed-without-finish states. | Completed, in-progress and not-started rows around a weekend Data Date. | Persisted progress → composed schedule → date assertions. | PASS — full suite 3280 passed / 139 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Data Date and progress) | bf0424db |
| CPM-08 | Constraints | Primary and secondary constraints bind start/finish and are validated against relationships. | Start/Finish No Earlier/Later/Mandatory and secondary constraints map to event bounds; violations reported explicitly. | Constraint type and date; day. | Activity calendar. | `src/construction_pm/scheduling/constraints.py`, `forward_pass.py` | `tests/scheduling/test_constraints.py`, `test_time_constraints.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Full reference matrix of constraint × relationship × progress is not certified. | Add reference fixtures for every constraint kind combined with progress. | ES/LS under each constraint kind. | Constraints persisted and applied through the composer. | PASS — full suite 3280 passed / 139 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Activity constraints) | bf0424db |
| CPM-09 | Calendars and lag calendars | Work hours, exceptions, inherited calendars and per-relationship lag calendars are explicit and versioned. | Working-time resolver; duration addition/subtraction; previous/next working day; calendar snapshots hashed. | Calendar versions, work hours, exceptions; hours/days. | Calendar snapshot and version. | `src/construction_pm/scheduling/calendar.py`, `calendar_system.py`, `time_calendar.py` | `tests/scheduling/test_calendar.py`, `test_calendar_exceptions.py`, `test_time_calendar_boundaries.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Reference DST/time-zone and multi-shift fixtures are not run. | Add versioned reference fixtures for exceptional weeks and lag calendars. | Elapsed working days across holiday/exception and 24-hour calendar. | Calendar manifest through persisted snapshot. | PASS — full suite 3280 passed / 139 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Calendars) | bf0424db |
| CPM-10 | Infeasible/negative-float diagnostics | Impossible bound combinations are reported, not silently rewritten. | Detect negative float and contradictory constraint/relationship bounds; fail closed where an event cannot satisfy inputs; defensive guards are marked so they never mask a reachable defect. | Schedule graph, constraints, Data Date. | Activity calendar. | `src/construction_pm/scheduling/diagnostics.py`, `schedule.py`, `constraints.py`, `src/construction_pm/schedule_evaluator.py`, `backend_p0/authoritative_schedule_query.py` | `tests/scheduling/test_schedule_diagnostics.py`, `tests/test_schedule_evaluator.py`, `tests/test_authoritative_schedule_query.py` | IMPLEMENTED_TESTED_PARITY_PENDING | The codified `INFEASIBILITY_MATRIX` assigns each case a stable code and severity; the evaluator wraps failures as `SCHEDULE_INFEASIBLE:<CODE>`; Schedule Query FACT/EXPLANATION/FILTER now expose diagnostics scoped to selected activities. Version 26 fixture equivalence for coupled conflicts is not run. | Add Version 26 reference fixtures for coupled constraint/relationship conflicts and certify severity mapping. | Negative float and each infeasibility code with severity and fail-closed flag. | Evaluator and query API on a persisted infeasible project. | PASS — full suite 3280 passed / 139 skipped; targeted diagnostics, evaluator and query tests pass. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Schedule diagnostics) | e210f5c1 |
| RES-01 | Resource Dependent driving | Driving assignment determines activity duration from resource quantities and calendar. | Duration derived from assigned units/rate and driving calendar; driving assignment marked. | Units, units/time, calendar, resource rates; units/days. | Resource calendar version. | `src/construction_pm/scheduling/resource_dependent.py`, `resource_dependent_placement.py` | `tests/scheduling/test_resource_dependent.py`, `test_resource_dependent_placement.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Version 26 reference comparison for driving selection is not run. | Add licensed reference fixtures for driving assignment selection. | Duration for daily and non-daily rates. | Persisted assignments and calendar -> derived duration. | PASS — full suite 3280 passed / 139 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Resource Dependent scheduling) | bf0424db |
| RES-02 | Resource Dependent nondriving, in-progress and completed | Nondriving assignments are placed within activity windows; in-progress remaining duration uses Remaining Units; completed work keeps actuals. | Nondriving placement consumes capacity; in-progress duration = remaining units / rate; completed rows use actual units. | Assignment demand, Remaining Units, actual dates. | Activity/resource calendars. | `src/construction_pm/scheduling/resource_dependent_placement.py`, `src/construction_pm/p6_persisted_resource_leveling_resolver.py` | `tests/scheduling/test_resource_dependent_assignment_windows.py`, `test_resource_dependent_placement.py`, `tests/test_persisted_resource_leveling_resolver.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Reference parity for nondriving-only projects and same-day capacity boundaries is not certified. | Add reference fixtures for nondriving-only and completed-only projects. | Placement windows and remaining duration for each status. | Persisted assignment/period rows -> placement result. | PASS — full suite 3280 passed / 139 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Resource Dependent scheduling) | bf0424db |
| RES-03 | Non-daily and fractional rates | Rates expressed per hour/day/week/month convert with the exact calendar hours-per-day factor. | `duration = units / (rate × hours_per_day)` for period rates; Decimal arithmetic; invalid calendar factors fail closed. | Fractional units, `units_per_time_period`, calendar hours/day. | Versioned resource calendar. | `src/construction_pm/scheduling/resource_dependent.py`, `src/construction_pm/p6_persisted_resource_leveling_resolver.py` | `tests/scheduling/test_resource_dependent.py`, `tests/test_persisted_resource_leveling_resolver.py` | IMPLEMENTED_TESTED_PARITY_PENDING | No reference run for every period unit and rounding convention. | Add reference fixtures for hour/day/week/month rates and rounding. | Fractional rate conversion across 8h/10h calendars. | Persisted rate + calendar -> derived duration. | PASS — full suite 3280 passed / 139 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Resource rates) | bf0424db |
| RES-04 | Resource leveling core | Forward/backward leveling, priorities, selected resources, over-allocation tolerance, within-float and final ledger validation. | Move overloaded activities by working days inside float/priority order; re-run CPM; reject remaining overloads; capacity is the sum of non-overlapping shift windows, and overlapping windows fail closed. | Demand, capacity, priorities, over-allocation %, min float, resource rates; units/days. | Resource calendar; shift/time-window calendars; activity calendars. | `src/construction_pm/scheduling/resource_leveling.py`, `leveling_scheduler.py`, `leveling_boundary.py`, `leveling_cost_recalculation.py`, `p6_versioned_resource_calendar_resolver.py`, `src/construction_pm/resources/rate_facts.py`, `p6_resource_rate_repository.py`, `p6_resource_leveling_cost_service.py`, `p6_resource_rate_read_api.py`, `p6_resource_rate_write_api.py` | `tests/scheduling/test_resource_leveling.py`, `test_resource_leveling_backward.py`, `test_leveling_final_resource_demand.py`, `test_leveling_cost_recalculation.py`, `test_leveling_cross_project_priority.py`, `tests/test_p6_versioned_resource_calendar_resolver.py`, `tests/test_p6_resource_rate_repository.py`, `tests/test_p6_resource_leveling_cost_service.py`, `tests/test_p6_postgres_resource_rate.py`, `tests/test_schedule_evaluator.py`, `tests/test_authoritative_schedule_query.py`, `tests/test_preview_runtime.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Shift/time-window capacity, cross-project priority thresholds, persisted effective-dated rate facts with append-only supersession, and exact post-leveling assignment-cost recomputation are implemented. A content-addressed SQLite/PostgreSQL rate-fact repository, application service, versioned read/write APIs and HTTP routes now provide the rate inputs through the application-bound `cost_inputs_resolver` seam; the evaluator never reads a repository. PostgreSQL rate tests skip locally without a DSN and run in the PostgreSQL CI job. Version 26 leveling fixtures are not run. | Add Version 26 reference fixtures for priority/within-float/over-allocation combinations at the final head. | Overload removal under each priority and float mode; capacity across overlapping/non-overlapping shift windows; cost spreading after leveling. | Persisted demand/capacity -> leveled schedule -> final ledger and recalculated assignment cost; persisted rate facts -> cost inputs -> HTTP read/write and cost service. | PASS — persisted rate repository, cost service, evaluator/query binding and preview rate HTTP tests pass; 2 PostgreSQL rate tests skip locally without a DSN and execute in PostgreSQL CI. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Resource leveling) | ddff9af7 |
| ACT-01 | Level of Effort | LOE spans linked neighbours and never drives successors. | Start = earliest start of start-linked neighbours; finish = latest finish of finish-linked neighbours; no successor propagation; constraints rejected. | LOE activity, neighbour dates. | Activity calendar. | `src/construction_pm/scheduling/activity.py`, `forward_pass.py`, `schedule.py` | `tests/scheduling/test_activity_type_scheduling.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Reference behavior for partially linked LOE and progress display is not certified. | Add reference fixtures for one-ended and unlinked LOE. | LOE span derived from neighbours. | Snapshot composer with LOE and successors. | PASS — full suite 3280 passed / 139 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Level of Effort) | bf0424db |
| ACT-02 | WBS Summary | Dates roll up earliest start/latest finish of WBS descendants; percent complete and status aggregate from the same descendants; relationships and constraints are ignored. | `start = min(descendant early starts)`; `finish = max(descendant early finishes)`; duration-weighted percent complete and derived status over snapshot-bound ancestry. | WBS identity/ancestry, descendant dates, percent and status. | Descendant calendars. | `src/construction_pm/scheduling/activity.py`, `schedule.py`, `schedule_snapshot_materializer.py`, `backend_p0/authoritative_schedule_query.py` | `tests/scheduling/test_activity_type_scheduling.py`, `tests/test_authoritative_schedule_snapshot_composer.py`, `tests/test_authoritative_schedule_query.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Date rollup plus duration-weighted percent-complete and status aggregation are implemented and exposed through the Schedule Query FACT projection; task rows intentionally report `None` because the persisted Activity row owns those facts. Version 26 summary fixtures are not run. | Add Version 26 reference fixtures for mixed-descendant summaries, including completed-only and zero-duration descendants. | Summary dates, percent and status for mixed descendants. | Persisted WBS ancestry -> composed schedule -> query fact. | PASS — full suite 3280 passed / 139 skipped; targeted persisted mixed-descendant query test passes. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (WBS Summary activities) | b7483eca |
| ACT-03 | Milestones | Start and Finish milestones are zero-duration events; since Release 24.12 any relationship type may attach to either milestone, and the declared relationship end places the successor. | Zero duration; FS/SS/FF/SF bind from the milestone's start or finish exactly as for a zero-duration activity; nonzero persisted duration fails closed. | Milestone type, date, relationship type. | Activity calendar. | `src/construction_pm/scheduling/activity.py`, `schedule.py`, `backend_p0/authoritative_schedule_query.py` | `tests/scheduling/test_activity_type_scheduling.py`, `tests/test_authoritative_schedule_snapshot_composer.py`, `tests/test_authoritative_schedule_query.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Release 26 target semantics permit all four relationship types on both milestone types, so the obsolete pre-24.12 start/finish restriction is intentionally not enforced. All four combinations are verified as predecessor and as successor, including a persisted snapshot placement. Version 26 fixtures are not run. | Add Version 26 reference fixtures covering all four relationship types on both milestone types. | Successor dates from Start vs Finish milestones for FS/SS/FF/SF. | Persisted milestone with relationships through the composer and query. | PASS — full suite 3280 passed / 139 skipped; targeted milestone relationship matrix and persisted placement tests pass. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Milestones) | b7483eca |
| BAS-01 | Baseline identity and immutable values | Baseline roles/identity are separate from assignment; baseline activity values are immutable and auditable. | Immutable `(tenant, project, baseline, activity)` rows with FK to baseline; identical replay idempotent; divergent replay rejected; summary roles assigned through a separate revision-guarded slot with append-only audit. | Baseline type, activity planned window, budget, currency, technique; summary role and assignment provenance. | Baseline planned dates. | `src/construction_pm/p6_baseline_repository.py`, `p6_baseline_activity_repository.py`, `p6_baseline_api.py`, `p6_baseline_assignment.py`, `p6_baseline_assignment_api.py`, `p6_baseline_conversion.py`, `p6_baseline_conversion_api.py`, `shared/contracts/p6-baseline-assignment-api.v1.schema.json`, `shared/contracts/p6-baseline-conversion-api.v1.schema.json` | `tests/test_p6_baseline_repository.py`, `tests/test_p6_baseline_activity_repository.py`, `tests/test_p6_baseline_assignment_and_conversion.py`, `tests/test_p6_baseline_role_http.py`, `tests/test_p6_postgres_baseline_activity.py`, `tests/test_p6_postgres_baseline_assignment.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Role assignment to PROJECT/PRIMARY/SECONDARY/TERTIARY summary slots, explicit reassignment with audit history, and atomic cross-project conversion from source current values or a source baseline are implemented over SQLite/PostgreSQL repositories and versioned APIs/HTTP. PostgreSQL assignment/conversion tests skip locally without a DSN; Version 26 assign/convert reference fixtures have not been run. | Add Version 26 reference fixtures for assign/convert and execute the PostgreSQL CI job. | Immutable set replay; role-slot conflict; conversion target conflict; same-project and cross-tenant refusal; metadata rollback on row-write failure. | SQLite and PostgreSQL repository round trip, immutability, revision conflict, missing-parent FK, assignment audit, conversion atomicity and HTTP scope/permission contract. | PASS — 15 new tests passed (13 SQLite/HTTP, 2 PostgreSQL skipped locally without DSN); existing baseline suites green. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Maintain Baselines) | 08d7524d / b4bd4430 |
| BAS-02 | Selective baseline update and comparison | Update only selected project/activity/resource data; compare baseline to current. | Scoped field/activity selection with preview/apply; the target baseline is new and immutable; variance rows report changed and one-sided fields explicitly. | Selection flags, field set, activity subset, add/remove switches, currency. | Baseline/current planned dates. | `src/construction_pm/p6_baseline_update.py`, `p6_baseline_activity_repository.py`, `p6_baseline_repository.py` | `tests/test_p6_baseline_update.py` (10), `tests/test_p6_postgres_baseline_activity.py` (4) | IMPLEMENTED_TESTED_PARITY_PENDING | Scoped update, deterministic plan payload, apply-to-new-immutable-baseline and comparison/variance are implemented; invalid scopes and currency mismatches fail closed. PostgreSQL coverage is wired into the live CI job. Version 26 update/compare fixtures are not run. | Add Version 26 reference fixtures for selective update and variance output. | Variance for changed, unchanged and one-sided activity fields. | Persisted update selection -> baseline diff under SQLite and PostgreSQL. | PASS — 10 SQLite tests pass; 4 PostgreSQL tests skip locally without a DSN and execute in the PostgreSQL CI job; full suite 3280 passed / 139 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Update Baselines) | 54eabd13 / 3c29300a |
| EVM-01 | EV/PV/AC/BAC source selection | Values come from one selected baseline and one status date; all activity and WBS totals reconcile. | Per activity `PV = budget × planned% / 100`; `EV = budget × earned% / 100`; AC sums period actuals and activity/WBS/project expenses; `BAC = sum budget`; delegate CV/SV/CPI/SPI/ETC/EAC/VAC to the formula core. | Baseline budget/date, Data Date, progress, actual/remaining cost, currency. | Baseline working days; Data Date. | `src/construction_pm/scheduling/evm_source.py`, `p6_earned_value_read_model.py`, `p6_earned_value_read_model_api.py`, `http/project_lifecycle_routes.py`, `shared/contracts/p6-earned-value-read-model.v1.schema.json` | `tests/scheduling/test_evm_source.py`, `tests/test_p6_earned_value_read_model.py`, `tests/test_p6_earned_value_http.py`, `tests/test_evm_persisted_integration.py` | IMPLEMENTED_TESTED_PARITY_PENDING | PV uses the explicit linear working-day activity-budget distribution; reference curve/bucket parity is not run. | Add resource-curve/future-period reference fixtures. | PV/EV/AC/BAC for in-progress and completed rows, including WBS/project expenses. | Persisted baseline + current facts -> versioned read model API -> HTTP route and contract schema. | PASS — EVM source, read model, versioned HTTP (5) and persisted integration tests pass; full suite re-verified at the final head. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Earned Value) | 1b121f22 / 1a9dbfea |
| EVM-02 | EV techniques and ETC formulas | 0/100, 50/50, custom and activity percent complete earn distinctly; ETC methods and PF are explicit. | Technique-specific earned percent; ETC remaining cost, PF=1, PF=1/CPI, PF=1/(CPI×SPI), user PF; zero denominators fail closed. | Technique, percent, actual start/finish, costs. | Status date working days. | `src/construction_pm/scheduling/evm_source.py`, `earned_value.py`, `p6_earned_value_read_model_api.py`, `http/project_lifecycle_routes.py` | `tests/scheduling/test_evm_source.py`, `test_earned_value.py`, `tests/test_p6_earned_value_http.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Reference fixtures for each technique and PF choice are not run. | Add reference fixtures for all technique × ETC combinations. | EV/ETC/EAC/VAC for each technique. | Persisted technique setting -> read model -> versioned HTTP with typed validation. | PASS — targeted technique/ETC and HTTP validation tests pass; full suite re-verified at the final head. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (WBS Earned Value) | bf0424db / 1a9dbfea |
| EVM-03 | WBS aggregation, weighted milestones and future periods | WBS technique inheritance/overrides, weighted milestones and resource-curve/manual future-period PV are supported. | WBS-level technique resolution and weighted milestone earning; explicit `PERIOD_BUCKET_PV` buckets, a `RESOURCE_CURVE_PV` cumulative distribution over the activity working window, or linear activity-budget PV; `RESOURCE_CURVE` Units % Complete earning. | WBS overrides, milestone weights, future-period buckets, curve points, curve technique. | Financial/reporting periods; activity working days. | `src/construction_pm/scheduling/evm_source.py`, `p6_earned_value_read_model.py`, `p6_baseline_activity_repository.py`, `http/project_lifecycle_routes.py`, `shared/contracts/p6-earned-value-read-model.v1.schema.json` | `tests/scheduling/test_evm_source.py`, `tests/test_p6_earned_value_read_model.py`, `tests/test_evm_persisted_integration.py`, `tests/test_p6_earned_value_http.py` | IMPLEMENTED_TESTED_PARITY_PENDING | WBS technique inheritance/overrides, weighted milestones, explicit future-period buckets, resource-curve PV, `RESOURCE_CURVE` Units % Complete and assignment-level cost decomposition are implemented with persisted SQLite integration and a versioned HTTP boundary that accepts only selection plus typed settings. Assignment planned costs must reconcile exactly to the immutable activity budget; each assignment reports its own PV/EV and currency, and a RESOURCE_CURVE activity earns from per-assignment Units Percent Complete (derived from persisted budgeted/actual units) with the weighted result reported on the activity. Curve and bucket inputs are mutually exclusive and no distribution is silently approximated. Version 26 fixtures are not run. | Add Version 26 reference fixtures for WBS overrides, weighted milestones and curve/bucket PV. | WBS override and weighted milestone numeric cases; interpolated curve PV at start, mid-window, weekend and finish. | Persisted WBS settings and curve/bucket inputs -> EVM read model -> versioned HTTP and contract schema. | PASS — targeted EVM, read-model curve, persisted integration and HTTP settings tests pass; full suite re-verified at the final head. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (WBS Earned Value) | f69503ee / 3a780106 / 1a9dbfea |
| EVM-04 | Earned Schedule | Time-based ES/SPI(t) is kept distinct from cost-based EVM. | Earned schedule from PV curve crossing; schedule variance/index in time units. | PV curve, status date. | Reporting periods. | `src/construction_pm/scheduling/earned_schedule.py` | `tests/scheduling/test_earned_schedule.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Reference fixtures for ES boundaries and zero-PV behavior are not run. | Add reference fixtures for ES at project start/finish and flat PV. | ES/SPI(t) for three status dates. | Baseline PV -> earned schedule. | PASS — full suite 3280 passed / 139 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Earned Schedule) | bf0424db |
| INT-01 | XER/XML/XLSX interchange | Supported interchange formats preserve types, units, nulls and round-trip identity. | Versioned field maps, typed canonical values and a round-trip verifier; unsupported mappings are reported explicitly. | Import/export documents. | Imported calendars/time units. | `src/construction_pm/p6_interchange_adapter.py`, `p6_interchange_mapping.py`, `p6_interchange_typed_conversion.py`, `p6_interchange_values.py`, `p6_interchange_verification.py`, `p6_xer_codec.py`, `p6_primavera_xml_codec.py`, `p6_msproject_xml_codec.py`, `p6_xls_codec.py`, `p6_xlsx_codec.py`, `p6_mpx_codec.py` | `tests/test_p6_interchange_roundtrip.py`, `tests/test_p6_interchange_schedule_integration.py`, `tests/test_p6_xer_typed_roundtrip_certification.py`, per-codec tests | IMPLEMENTED_TESTED_PARITY_PENDING | Six codecs (XER, Primavera XML, MS Project XML, XLS, XLSX, MPX) share typed value conversion; the round-trip verifier checks typed equality; the new cross-module test imports XLSX dates, persists an activity, runs the shared scheduler and re-exports the scheduled dates. Licensed provider files for byte-level parity are not available. | Certify byte/semantic parity against authorized XER/XML/XLSX fixtures per format. | Round-trip equality for typed date, Decimal and null fields. | Import -> persist -> shared schedule -> export with real SQLite persistence. | PASS — full suite 3280 passed / 139 skipped; round-trip verifier, per-codec and schedule-integration tests pass. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Import/Export) | 55fe65f2 / 3c29300a |

### Status summary at this head

| Status | Rows |
|---|---:|
| IMPLEMENTED_AND_PARITY_TESTED | 0 |
| IMPLEMENTED_TESTED_PARITY_PENDING | 24 |
| IMPLEMENTED_BUT_INCOMPLETE | 0 |
| KNOWN_GAP | 0 |
| BLOCKED_BY_EXTERNAL_DEPENDENCY | 0 |

`IMPLEMENTED_AND_PARITY_TESTED` is intentionally zero: no licensed Version 26
project run is available to establish reference equivalence. `BLOCKED_BY_EXTERNAL_DEPENDENCY`
is currently zero because the open items above are implementable in this
repository; they are not waiting on external input.

## Execution ledger

### Stage 1 — Repository, branch and PR inspection

- What was done: fetched `origin/main`, confirmed `main` is contained in the
  branch, reviewed PR #1668 and Issues #1517/#1483/#1468, preserved prior
  commits.
- Commit: none (inspection only).
- Files: none changed.
- Tests: none.
- Open: none for this stage.
- Next: close the documented core gaps without opening a parallel PR.
- Acceptance criterion: real code on the existing branch and PR.

### Stage 2 — Data Date and remaining-start anchoring

- What was done: completed activities keep actual dates; remaining work starts
  at the Data Date; unstarted activities keep CPM early dates; persisted
  milestone duration and contradictory status fail closed.
- Commit: `dba5000b`, `68f9fc92`, `235aed7f`.
- Files: `scheduling/forward_pass.py`, `progress_state.py`,
  `authoritative_schedule.py`, composer/materializer paths, tests.
- Tests: `tests/scheduling/test_progress_data_date_anchor.py` and full suite.
- Open: licensed reference fixtures for Data Date boundaries.
- Next: Resource Dependent status coverage.
- Acceptance criterion: integrated CPM + Data Date tests.

### Stage 3 — Resource Dependent coverage

- What was done: in-progress remaining duration from Remaining Units, each
  driving resource on its own calendar, non-daily/fractional rates, completed
  and nondriving placement, immutable assignment placement ledger.
- Commits: `6c62f5d8`, `139d08dd`, `cbbca438`, `0752f9ee`.
- Files: `scheduling/resource_dependent.py`,
  `scheduling/resource_dependent_placement.py`,
  `p6_persisted_resource_leveling_resolver.py`, tests.
- Tests: resource-dependent and resolver suites.
- Open: shift-aware leveling; reference fixtures.
- Next: LOE and WBS Summary.
- Acceptance criterion: driving/nondriving/in-progress/completed tested.

### Stage 4 — LOE and WBS Summary

- What was done: LOE spans linked neighbours and never drives successors; WBS
  Summary rolls up snapshot-bound descendants; both excluded from leveling and
  float/critical analysis; immutable WBS ancestry.
- Commit: `f813f07f`.
- Files: `scheduling/activity.py`, `forward_pass.py`, `schedule.py`,
  `authoritative_schedule_input_composer.py`,
  `schedule_snapshot_materializer.py`,
  `p6_persisted_resource_leveling_resolver.py`, registry and generated web
  catalog, tests.
- Tests: `tests/scheduling/test_activity_type_scheduling.py`, composer and
  resolver tests, full suite 3019 passed / 129 skipped at the time.
- Open: WBS percent/status aggregation; milestone placement restrictions.
- Next: baseline/EVM source selection.
- Acceptance criterion: real algorithms, not status relabeling.

### Stage 5 — Baseline-based EVM source selection

- What was done: immutable baseline activity budgets/dates/currencies/techniques;
  persisted current-progress composition; PV/EV/AC/BAC selection; WBS rollups;
  formula-core delegation; scoped read-model API; explicit fail-closed cases.
- Commit: `bf0424db`.
- Files: `scheduling/evm_source.py`,
  `p6_baseline_activity_repository.py`, `p6_earned_value_read_model.py`,
  `p6_earned_value_read_model_api.py`, registry, generated catalog, three test
  files.
- Tests: `tests/scheduling/test_evm_source.py` (14),
  `tests/test_p6_baseline_activity_repository.py` (10),
  `tests/test_p6_earned_value_read_model.py` (6); full suite 3049 passed /
  129 skipped in 94.89s at that commit.
- Open: WBS technique inheritance/overrides, weighted milestones, resource-curve
  and manual future-period PV, multi-currency conversion, reference fixtures.
- Next: shift-aware leveling and infeasible matrix, then CI/PR.
- Acceptance criterion: EV/PV/AC/BAC are traceable to one baseline and status
  date; no invented data.

### Stage 6 — This ledger

- What was done: created the sixteen-column matrix and durable execution record.
- Commit: see the commit that adds this file (follows `bf0424db`).
- Files: `docs/engineering/CORE_COMPLETION_EXECUTION_LEDGER.md`.
- Tests: documentation-only change; test suite unchanged.
- Open: row-level parity fixtures; remaining implementation rows.
- Next: run full CI-equivalent checks, update PR #1668, and continue with the
  highest-impact open row (RES-04 shift-aware leveling / CPM-10 infeasible
  matrix).
- Acceptance criterion: every stage and unmet criterion is recorded.

### Stage 7 — Cost attribution, persistence evidence and persisted EVM path

- What was done: PostgreSQL baseline-activity persistence tests and FK error
  mapping; activity expense actuals now enter AC; WBS/project expenses become
  explicit `EarnedValueCostAdjustment` rows included in project totals and only
  in their own WBS rollup; unknown-baseline actual/expense rows fail closed;
  unfinished work without remaining cost fails closed while completed work
  defaults to zero; a SQLite persisted end-to-end EVM integration test runs
  baseline -> progress -> actuals/expenses -> read model.
- Commits: `481a1b0b`, `1b121f22`.
- Files: `scheduling/evm_source.py`, `p6_earned_value_read_model.py`,
  `p6_baseline_activity_repository.py`, registry and generated catalog,
  `tests/scheduling/test_evm_source.py`,
  `tests/test_p6_earned_value_read_model.py`,
  `tests/test_p6_postgres_baseline_activity.py`,
  `tests/test_evm_persisted_integration.py`.
- Tests: EVM source (16), read model (9), persisted integration (1), PostgreSQL
  baseline activity (3, skipped locally without DSN); full suite 3054 passed /
  132 skipped.
- Open: WBS technique inheritance/overrides, weighted milestones, curve/future
  period PV, multi-currency; those remain recorded on EVM-03.
- Next: highest-impact remaining rows (RES-04 shift-aware leveling, CPM-10
  infeasible matrix, ACT-02/ACT-03 aggregation and milestone placement).
- Acceptance criterion: cost facts are never silently dropped or spread, and
  the full persisted path is exercised.

### Stage 8 — Exact-head verification and PostgreSQL CI repair

- What was done: fixed the PostgreSQL baseline-activity fixture to pass calendar
  dates instead of strings, and wired that test file into the dedicated
  PostgreSQL Integration workflow paths and command. Confirmed the PR
  description now reflects the implemented scope and the remaining gaps.
- Commits: `750d721f`, `4d569a1c`, `78d78414`.
- Tests: local full suite 3055 passed / 132 skipped; exact-head CI 9/9 on
  `78d78414` (Python 3.11/3.12/3.13, Web, PostgreSQL, four client typechecks).
- Open: PR remains Draft because the acceptance criteria below are not all
  met; marking Ready or merging now would present incomplete rows as complete.
- Next: implement the remaining matrix rows or obtain a licensed reference run
  before claiming parity.
- Acceptance criterion: CI is green on the exact pushed head with no weakened
  tests.

### Stage 9 — Closure of the seven mandatory implementation rows

- What was done:
  - CPM-10: codified the infeasibility matrix with stable codes and severity,
    marked the unreachable backward-bound guard as defensive and fail-closed,
    wrapped evaluator failures as `SCHEDULE_INFEASIBLE:<CODE>`, and exposed
    diagnostics in the Schedule Query FACT/EXPLANATION/FILTER projections with
    selection scoping.
  - ACT-02: rolled up duration-weighted percent complete and derived status over
    snapshot-bound WBS ancestry and exposed them in the Schedule Query fact;
    task rows return `None` so persisted facts are not duplicated.
  - ACT-03: enforced zero-duration milestone invariants and verified all four
    relationship types on both milestone types, because the Release 26 target
    removed the obsolete pre-24.12 restriction. Updated the provider reference
    metadata and regenerated the web catalog.
  - RES-04: added shift/time-window capacity with fail-closed overlapping
    windows, cross-project priority thresholds and exact post-leveling
    assignment-cost recomputation.
  - BAS-02: implemented scoped field/activity selection, preview/apply, a new
    immutable target baseline, and explicit variance comparison; wired the
    PostgreSQL test file into the live CI job and command.
  - EVM-03: implemented WBS technique inheritance/overrides, weighted
    milestones, explicit future-period buckets, `RESOURCE_CURVE` Units %
    Complete and interpolated resource-curve PV over the activity working
    window, with persisted SQLite integration and fail-closed curve validation.
  - INT-01: added the round-trip verifier, lossless typed values and a real
    cross-module import -> persist (SQLite) -> shared schedule -> export test.
- Commits: `ed26aef7`, `72a18596`, `2bd88bf4`, `4c851b75`, `f69503ee`,
  `54eabd13`, `55fe65f2`, `ddff9af7`, `e210f5c1`, `b7483eca`, `3c29300a`,
  `3a780106`; ledger commits `12771e14` and `66072977` follow, then this
  final evidence update.
- Files: scheduling diagnostics, evaluator, Schedule Query projection,
  activity/schedule WBS and milestone paths, resource leveling and cost
  recalculation, baseline update, EVM source and read model, interchange
  adapter/values/verification/codecs, PostgreSQL workflow, tests, provider
  metadata and generated web catalog, this ledger.
- Tests at the final implementation head: full suite 3193 passed / 133 skipped
  / 2 warnings in 58.95s with `PYTHONPATH=src py -3 -m pytest -q`. The skipped tests are the
  live PostgreSQL suite without a local DSN; that suite executes in the
  dedicated CI job. Targeted coverage added: infeasibility matrix, evaluator
  wrapping, scoped query diagnostics, persisted WBS summary progress, milestone
  relationship matrix and persisted placement, shift capacity and overlap
  rejection, cross-project priority, cost recalculation, baseline update (10
  SQLite + 4 PostgreSQL), EVM WBS/milestone/bucket/curve integration,
  interchange round-trip and import/persist/schedule/export.
- Exact-head CI on the final code head `66072977`: 9/9 green. ConstructionPM CI
  run `41392001760` (jobs 125105219025 `test (3.11)`, 125105219148
  `test (3.12)`, 125105219176 `test (3.13)`); PostgreSQL Integration run
  `41392001753` (job 125105218931 `postgres`); Client Typecheck run
  `41392001902` (jobs 125105219370 `apps/desktop`, 125105219580
  `apps/client-sync`, 125105219618 `apps/mobile`, 125105219736 `apps/web`);
  ConstructionPM Web CI run `41392001782` (job 125105219108 `web`). All
  concluded `success`. The prior code head `3c29300a` was also 9/9 green
  (runs `41390618837`, `41390618603`, `41390618649`, `41390618561`). This
  ledger-only commit does not change code.
- Open: no matrix row is `IMPLEMENTED_BUT_INCOMPLETE` or `KNOWN_GAP`. No
  licensed Version 26 reference run exists, so no row is
  `IMPLEMENTED_AND_PARITY_TESTED`; external parity fixtures remain the only
  outstanding evidence.
- Next: exact-head CI verification, PR description update, and external parity
  fixtures when an authorized reference environment is available.
- Acceptance criterion: the seven mandated rows have real code and regression
  coverage; remaining limitations are recorded rather than relabeled.

### Stage 10 — HTTP exposure of baseline roles, conversion and earned value

- What was done:
  - CPM-05: the activity short-name endpoint now resolves a unique
    project-scoped short name to the full activity identifier and fails closed
    on ambiguity or a non-driving match; the ledger row now reflects the real
    implementation instead of the earlier "not exposed" note.
  - BAS-01: summary baseline roles (PROJECT/PRIMARY/SECONDARY/TERTIARY) are
    assigned through a revision-guarded, append-only audited slot, and a
    cross-project conversion copies either source current values or a source
    baseline into an immutable target; both are exposed through versioned APIs,
    HTTP routes and JSON schemas.
  - EVM-01/02/03: `P6EarnedValueReadModelAPI` accepts an optional contract
    version and typed settings; the read-model service resolves the project
    working calendar per scope through `resolver_provider`; the new
    `POST /api/projects/{project_id}/p6/earned-value` route validates unknown
    keys, dates, guarded decimals, technique overrides, milestones, buckets and
    curves, and maps fail-closed errors to 400/403/404/409. Preview composition
    binds persisted baseline activities, current activities, period actuals,
    expenses, WBS hierarchy, assignments and the persisted calendar registry.
  - The versioned payload contract is published as
    `shared/contracts/p6-earned-value-read-model.v1.schema.json`; a contract
    test asserts the required key sets and version constants.
- Commits: `2609330e` (CPM-05), `08d7524d` + `b4bd4430` (BAS-01), `1a9dbfea`
  (EVM HTTP exposure, typed API, schema and preview wiring).
- Files: `http/project_lifecycle_routes.py`, `http/production_composition.py`,
  `preview/runtime.py`, `p6_earned_value_read_model.py`,
  `p6_earned_value_read_model_api.py`, baseline assignment/conversion modules,
  `shared/contracts/p6-earned-value-read-model.v1.schema.json`,
  `src/construction_pm/p6_code_reference.py`, tests, this ledger.
- Tests: full suite at code head `1a9dbfea` reported 3280 passed / 139 skipped
  / 2 warnings in 49.16s with `PYTHONPATH=src py -3 -m pytest -q`; the
  skipped tests are the live PostgreSQL suites without a local DSN and execute
  in the dedicated PostgreSQL CI job. Targeted coverage added:
  `tests/test_p6_earned_value_http.py` (5 route/contract tests) and a persisted
  preview EVM round trip in `tests/test_preview_runtime.py`.
- Open: multi-currency/financial-period conversion and licensed Version 26
  reference fixtures remain unproven. `gh` is not installed on this
  workstation, so exact-head CI status and the PR body cannot be updated from
  here without forbidden credential extraction; the PR stays Draft.
- Next: exact-head CI query from an environment that has `gh`, then external
  parity fixtures when an authorized reference environment is available.
- Acceptance criterion: every claimed core capability is reachable through a
  versioned server-side boundary and exercised by executable tests, with
  unproven parity recorded honestly.

## Remaining acceptance criteria

1. All core capabilities inspected in real code — in progress; matrix rows
   identify remaining code gaps.
2. All in-scope capabilities implemented or repaired — **yes for the shared
   core**: all 24 matrix rows have a real implementation and regression
   coverage, including BAS-02, INT-01, RES-04, ACT-02, ACT-03, CPM-10 and
   EVM-03. External reference equivalence remains unproven.
3. Important behavior aligned with valid reference documentation — behavioral
   mapping exists; licensed reference-run certification is pending.
4. All main formulas have numeric and boundary tests — formula core and EVM
   source rows pass; reference boundary fixtures remain.
5. CPM, relationships, calendars, actual dates, Data Date and resource
   scheduling integrated and tested — integrated composition tests pass; full
   cross-domain reference fixtures remain.
6. Known Resource Dependent gaps dispositioned — dispositioned in the registry
   and matrix; shift-aware leveling, cross-project thresholds and
   post-leveling cost recalculation are implemented. A persisted P6 rate-fact
   repository remains outside the resolver boundary.
7. Regression and integration tests pass — full Python suite passes.
8. No known fixable failure remains in required tests — none observed in the
   Python suite at this head; cross-language CI is verified separately.
9. CUBI code reference updated with real paths/tests — updated for EVM-001,
   EVM-003, BAS-001, ACT-001 and FRM-ACT-TYPES-001; the generated web catalog
   was regenerated and checked.
10. Final commits saved on GitHub — implementation/test head `1a9dbfea` is
    pushed to the same branch; prior head `66072977` was exact-head CI 9/9
    green. The current head's CI cannot be queried from this workstation
    because `gh` is unavailable.
11. PR contains latest code, precise description and real CI results — the PR
    body update and exact-head CI query are blocked by the missing `gh`
    client/credentials; no credential extraction is permitted, so the PR stays
    Draft with this limitation stated rather than guessed.
12. Unproven capabilities and external limits clearly identified — recorded
    above with zero falsely certified rows.

## Continuation rule

After any session restart: read this file, then compare its head SHA with
`git rev-parse HEAD` and the PR head. Continue from the first open row whose
code, tests or evidence is missing. Do not close the mission because a stage or
a test run ends.
