# CUBI Core Completion Execution Ledger

Branch: `codex/jalal/resource-dependent-core-20261102`
Baseline: `main` at `2577a56287f446fe0177458808e77952c12d4d7a`
Latest implementation/test head: `78d78414` (this ledger update follows it)
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
| CPM-01 | Forward pass | Early dates honor project start, Data Date, duration, calendars, relationships, lag, constraints and progress. | Event-time propagation; `ES = max(predicate bounds, constraint bounds, project start, data date)`; `EF = ES + duration - 1` in working days. | Activity durations, remaining durations, actual dates, constraints; days. | Activity calendar; project calendar; Data Date. | `src/construction_pm/scheduling/forward_pass.py`, `schedule.py` | `tests/scheduling/test_forward_pass.py`, `test_progress_data_date_anchor.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Reference fixture equivalence for every calendar/lag/constraint combination is not yet run. | Add Version 26 numeric fixtures for combined calendar/lag/constraint/progress cases. | ES/EF for FS/SS/FF/SF with positive, zero and negative lag across two calendars. | Full schedule composed from persisted snapshot; assert dates and floats. | PASS — full suite 3055 passed / 132 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Schedule calculations) | bf0424db |
| CPM-02 | Backward pass | Late dates honor project finish, relationships, lag, constraints, float options and leveling changes. | Backward event propagation; `LS`, `LF`, total float and free float from authoritative CPM outputs. | Late constraints, project finish, durations; days. | Activity calendar; project finish basis. | `src/construction_pm/scheduling/forward_pass.py`, `schedule.py` | `tests/scheduling/test_backward_constraints.py`, `test_schedule.py` | IMPLEMENTED_TESTED_PARITY_PENDING | No licensed reference fixture for project-finish and constraint combinations. | Add reference fixtures for backward pass with negative float and leveling constraints. | Late dates and floats for each relationship type and constraint kind. | Backward pass after resource-leveling constraints; assert float paths. | PASS — full suite 3055 passed / 132 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Schedule calculations) | bf0424db |
| CPM-03 | Relationships FS/SS/FF/SF and lag/lead | All four types apply the correct start/finish bound with calendar-aware lag. | FS: successor start ≥ predecessor finish + lag; SS: start ≥ start + lag; FF: finish ≥ finish + lag; SF: finish ≥ start + lag; inverse for backward. | Relationship type, lag, lag unit/calendar; days/hours. | Relationship lag calendar; activity calendars. | `src/construction_pm/scheduling/relationships.py`, `forward_pass.py`, `schedule_options.py` | `tests/scheduling/test_relationships.py`, `test_relationships` cases in `test_schedule.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Version 26 fixture equivalence and every lag-calendar interaction are not certified. | Build reference fixtures for each type × lag sign × lag calendar. | Hand-computed working dates for the 4×3 matrix. | Persisted relationship ingestion and schedule assertion. | PASS — full suite 3055 passed / 132 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Relationships and lag) | bf0424db |
| CPM-04 | Float and critical path | Total/Free Float selection and critical-path rules are configurable and explicit. | Start float = LS−ES; finish float = LF−EF; smallest float; critical when float ≤ threshold; open-ended critical option. | Float options, threshold; days. | Activity calendar. | `src/construction_pm/scheduling/schedule.py`, `schedule_options.py` | `tests/scheduling/test_schedule.py`, `test_public_forward_backward_leveling.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Reference threshold/path fixtures absent. | Add reference fixtures for each float mode and critical rule. | Float values and critical flag for each mode. | Schedule options persisted and replayed through API. | PASS — full suite 3055 passed / 132 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Float and critical activities) | bf0424db |
| CPM-05 | Multiple float paths | Path count, endpoint and Total/Free Float basis are honored. | Rank near-critical paths from the selected endpoint; emit path number per activity. | Path count 0–1000, endpoint ID/short name, float basis. | Activity calendar. | `src/construction_pm/scheduling/schedule.py` (`_multiple_float_paths`) | `tests/scheduling/test_multi_project_float.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Short-name endpoint is explicitly unsupported; reference path ordering is not certified. | Implement short-name endpoint or fail closed at persistence; add reference fixtures. | Path numbers for two near-critical chains. | Endpoint resolution from persisted activity identity. | PASS — full suite 3055 passed / 132 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Multiple float paths) | bf0424db |
| CPM-06 | Out-of-sequence and Data Date progress | Retained Logic, Progress Override and Actual Dates are distinct; progressed work anchors at the Data Date. | Remaining work starts at max(Data Date, actual/early bound); completed work retains actual finish; OOS policy controls remaining-logic propagation. | Actual start/finish, remaining duration, Data Date; days. | Activity calendar; Data Date. | `src/construction_pm/scheduling/progress_state.py`, `out_of_sequence.py`, `forward_pass.py` | `tests/scheduling/test_out_of_sequence.py`, `test_oos_policy.py`, `test_progress_data_date_anchor.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Reference fixtures for each OOS mode in combination with constraints are not run. | Add combined OOS × constraint × Data Date fixtures. | In-progress activity with stale early dates measured at Data Date. | Progress snapshot through authoritative composer. | PASS — full suite 3055 passed / 132 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Out-of-sequence scheduling) | bf0424db |
| CPM-07 | Data Date anchor and completed work | Data Date never moves completed actual dates; unstarted activities keep early dates; remaining work begins no earlier than Data Date. | Completed: keep actual end. In progress: `remaining_start = max(Data Date, actual/early bound)`. Not started: CPM early start. | Data Date, actual dates, remaining duration. | Activity calendar. | `src/construction_pm/scheduling/forward_pass.py`, `authoritative_schedule.py` | `tests/scheduling/test_progress_data_date_anchor.py` | IMPLEMENTED_TESTED_PARITY_PENDING | No licensed reference run for boundary weekends/holidays at Data Date. | Add reference fixtures for Data Date on nonworking days and completed-without-finish states. | Completed, in-progress and not-started rows around a weekend Data Date. | Persisted progress → composed schedule → date assertions. | PASS — full suite 3055 passed / 132 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Data Date and progress) | bf0424db |
| CPM-08 | Constraints | Primary and secondary constraints bind start/finish and are validated against relationships. | Start/Finish No Earlier/Later/Mandatory and secondary constraints map to event bounds; violations reported explicitly. | Constraint type and date; day. | Activity calendar. | `src/construction_pm/scheduling/constraints.py`, `forward_pass.py` | `tests/scheduling/test_constraints.py`, `test_time_constraints.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Full reference matrix of constraint × relationship × progress is not certified. | Add reference fixtures for every constraint kind combined with progress. | ES/LS under each constraint kind. | Constraints persisted and applied through the composer. | PASS — full suite 3055 passed / 132 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Activity constraints) | bf0424db |
| CPM-09 | Calendars and lag calendars | Work hours, exceptions, inherited calendars and per-relationship lag calendars are explicit and versioned. | Working-time resolver; duration addition/subtraction; previous/next working day; calendar snapshots hashed. | Calendar versions, work hours, exceptions; hours/days. | Calendar snapshot and version. | `src/construction_pm/scheduling/calendar.py`, `calendar_system.py`, `time_calendar.py` | `tests/scheduling/test_calendar.py`, `test_calendar_exceptions.py`, `test_time_calendar_boundaries.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Reference DST/time-zone and multi-shift fixtures are not run. | Add versioned reference fixtures for exceptional weeks and lag calendars. | Elapsed working days across holiday/exception and 24-hour calendar. | Calendar manifest through persisted snapshot. | PASS — full suite 3055 passed / 132 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Calendars) | bf0424db |
| CPM-10 | Infeasible/negative-float diagnostics | Impossible bound combinations are reported, not silently rewritten. | Detect negative float and contradictory constraint/relationship bounds; fail closed where an event cannot satisfy inputs. | Schedule graph, constraints, Data Date. | Activity calendar. | `src/construction_pm/scheduling/schedule.py`, `constraints.py`, `src/construction_pm/schedule_evaluator.py` | `tests/scheduling/test_constraints.py`, `test_leveling_scheduler.py` | IMPLEMENTED_BUT_INCOMPLETE | No single codified matrix enumerating all infeasible combinations and their diagnostics. | Add explicit infeasibility matrix and stable diagnostic codes. | Negative float for finish-before-start constraint chains. | Evaluator report on an infeasible persisted project. | PASS for existing cases (3055 passed / 132 skipped); matrix coverage incomplete. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Schedule diagnostics) | bf0424db |
| RES-01 | Resource Dependent driving | Driving assignment determines activity duration from resource quantities and calendar. | Duration derived from assigned units/rate and driving calendar; driving assignment marked. | Units, units/time, calendar, resource rates; units/days. | Resource calendar version. | `src/construction_pm/scheduling/resource_dependent.py`, `resource_dependent_placement.py` | `tests/scheduling/test_resource_dependent.py`, `test_resource_dependent_placement.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Version 26 reference comparison for driving selection is not run. | Add licensed reference fixtures for driving assignment selection. | Duration for daily and non-daily rates. | Persisted assignments and calendar -> derived duration. | PASS — full suite 3055 passed / 132 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Resource Dependent scheduling) | bf0424db |
| RES-02 | Resource Dependent nondriving, in-progress and completed | Nondriving assignments are placed within activity windows; in-progress remaining duration uses Remaining Units; completed work keeps actuals. | Nondriving placement consumes capacity; in-progress duration = remaining units / rate; completed rows use actual units. | Assignment demand, Remaining Units, actual dates. | Activity/resource calendars. | `src/construction_pm/scheduling/resource_dependent_placement.py`, `src/construction_pm/p6_persisted_resource_leveling_resolver.py` | `tests/scheduling/test_resource_dependent_assignment_windows.py`, `test_resource_dependent_placement.py`, `tests/test_persisted_resource_leveling_resolver.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Reference parity for nondriving-only projects and same-day capacity boundaries is not certified. | Add reference fixtures for nondriving-only and completed-only projects. | Placement windows and remaining duration for each status. | Persisted assignment/period rows -> placement result. | PASS — full suite 3055 passed / 132 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Resource Dependent scheduling) | bf0424db |
| RES-03 | Non-daily and fractional rates | Rates expressed per hour/day/week/month convert with the exact calendar hours-per-day factor. | `duration = units / (rate × hours_per_day)` for period rates; Decimal arithmetic; invalid calendar factors fail closed. | Fractional units, `units_per_time_period`, calendar hours/day. | Versioned resource calendar. | `src/construction_pm/scheduling/resource_dependent.py`, `src/construction_pm/p6_persisted_resource_leveling_resolver.py` | `tests/scheduling/test_resource_dependent.py`, `tests/test_persisted_resource_leveling_resolver.py` | IMPLEMENTED_TESTED_PARITY_PENDING | No reference run for every period unit and rounding convention. | Add reference fixtures for hour/day/week/month rates and rounding. | Fractional rate conversion across 8h/10h calendars. | Persisted rate + calendar -> derived duration. | PASS — full suite 3055 passed / 132 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Resource rates) | bf0424db |
| RES-04 | Resource leveling core | Forward/backward leveling, priorities, selected resources, over-allocation tolerance, within-float and final ledger validation. | Move overloaded activities by working days inside float/priority order; re-run CPM; reject remaining overloads. | Demand, capacity, priorities, over-allocation %, min float; units/days. | Resource calendar; activity calendars. | `src/construction_pm/scheduling/resource_leveling.py`, `leveling_scheduler.py`, `leveling_boundary.py` | `tests/scheduling/test_resource_leveling.py`, `test_resource_leveling_backward.py`, `test_leveling_final_resource_demand.py` | IMPLEMENTED_BUT_INCOMPLETE | Shift-aware leveling, cross-project threshold behavior and cost recalculation remain open (RES-002/RES-007). | Implement shift/time-window capacity and cross-project priority thresholds; then add reference fixtures. | Overload removal under each priority and within-float mode. | Persisted demand/capacity -> leveled schedule -> final ledger. | PASS — full suite 3055 passed / 132 skipped; open gaps above. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Resource leveling) | bf0424db |
| ACT-01 | Level of Effort | LOE spans linked neighbours and never drives successors. | Start = earliest start of start-linked neighbours; finish = latest finish of finish-linked neighbours; no successor propagation; constraints rejected. | LOE activity, neighbour dates. | Activity calendar. | `src/construction_pm/scheduling/activity.py`, `forward_pass.py`, `schedule.py` | `tests/scheduling/test_activity_type_scheduling.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Reference behavior for partially linked LOE and progress display is not certified. | Add reference fixtures for one-ended and unlinked LOE. | LOE span derived from neighbours. | Snapshot composer with LOE and successors. | PASS — full suite 3055 passed / 132 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Level of Effort) | bf0424db |
| ACT-02 | WBS Summary | Dates roll up earliest start/latest finish of WBS descendants; relationships and constraints are ignored. | `start = min(descendant early starts)`; `finish = max(descendant early finishes)` over snapshot-bound ancestry. | WBS identity/ancestry, descendant dates. | Descendant calendars. | `src/construction_pm/scheduling/activity.py`, `schedule.py`, `schedule_snapshot_materializer.py` | `tests/scheduling/test_activity_type_scheduling.py`, `tests/test_authoritative_schedule_snapshot_composer.py` | IMPLEMENTED_BUT_INCOMPLETE | Percent-complete/status aggregation and duration behavior are not implemented. | Add WBS percent-complete/status rollup semantics and reference fixtures. | Summary dates and percent for mixed descendants. | Snapshot with WBS ancestry -> summary output. | PASS for date rollup (3055 passed / 132 skipped); aggregation gap explicit. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (WBS Summary activities) | bf0424db |
| ACT-03 | Milestones | Start and Finish milestones are zero-duration events with distinct placement rules. | Zero duration; finish milestone binds successors from its finish; start milestone binds from its start. | Milestone type, date. | Activity calendar. | `src/construction_pm/scheduling/activity.py`, `schedule.py` | `tests/scheduling/test_activity_type_scheduling.py`, `tests/test_authoritative_schedule_snapshot_composer.py` | IMPLEMENTED_BUT_INCOMPLETE | Nonzero persisted milestone duration fails closed, but start-vs-finish relationship placement restrictions are not fully implemented. | Implement documented placement restrictions and reference fixtures. | Successor dates from Start vs Finish milestones. | Persisted milestone with relationships. | PASS for zero-duration validation (3055 passed / 132 skipped); placement gap explicit. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Milestones) | bf0424db |
| BAS-01 | Baseline identity and immutable values | Baseline roles/identity are separate from assignment; baseline activity values are immutable and auditable. | Immutable `(tenant, project, baseline, activity)` rows with FK to baseline; identical replay idempotent; divergent replay rejected. | Baseline type, activity planned window, budget, currency, technique. | Baseline planned dates. | `src/construction_pm/p6_baseline_repository.py`, `p6_baseline_activity_repository.py`, `p6_baseline_api.py` | `tests/test_p6_baseline_repository.py`, `tests/test_p6_baseline_activity_repository.py`, `tests/test_p6_postgres_baseline_activity.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Converting another project into a baseline and assigning roles to live summary fields remain open; PostgreSQL integration tests exist but have not yet run against the CI database from this workstation. | Implement conversion/assignment workflows and add reference fixtures. | Immutable set replay and revision conflict. | SQLite and PostgreSQL repository round trip, immutability, revision conflict and missing-parent FK. | PASS — 10 SQLite tests; 3 PostgreSQL tests skipped locally without DSN and executed by PostgreSQL CI; full suite 3055 passed / 132 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Maintain Baselines) | 481a1b0b |
| BAS-02 | Selective baseline update and comparison | Update only selected project/activity/resource data; compare baseline to current. | Scoped copy/update sets and variance fields. | Selection flags, fields. | Baseline/current dates. | No implementation | No test | KNOWN_GAP | Baseline update/compare is not implemented. | Implement scoped update and comparison APIs. | Variance for changed/unchanged activity fields. | Persisted update selection -> baseline diff. | Not run — capability absent. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Update Baselines) | bf0424db |
| EVM-01 | EV/PV/AC/BAC source selection | Values come from one selected baseline and one status date; all activity and WBS totals reconcile. | Per activity `PV = budget × planned% / 100`; `EV = budget × earned% / 100`; AC sums period actuals and activity/WBS/project expenses; `BAC = sum budget`; delegate CV/SV/CPI/SPI/ETC/EAC/VAC to the formula core. | Baseline budget/date, Data Date, progress, actual/remaining cost, currency. | Baseline working days; Data Date. | `src/construction_pm/scheduling/evm_source.py`, `p6_earned_value_read_model.py`, `p6_earned_value_read_model_api.py` | `tests/scheduling/test_evm_source.py`, `tests/test_p6_earned_value_read_model.py` | IMPLEMENTED_TESTED_PARITY_PENDING | PV uses the explicit linear working-day activity-budget distribution; reference curve/bucket parity is not run. | Add resource-curve/future-period reference fixtures. | PV/EV/AC/BAC for in-progress and completed rows, including WBS/project expenses. | Persisted baseline + current facts -> read model API. | PASS — 26 targeted tests including a persisted SQLite integration case; full suite 3055 passed / 132 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Earned Value) | 1b121f22 |
| EVM-02 | EV techniques and ETC formulas | 0/100, 50/50, custom and activity percent complete earn distinctly; ETC methods and PF are explicit. | Technique-specific earned percent; ETC remaining cost, PF=1, PF=1/CPI, PF=1/(CPI×SPI), user PF; zero denominators fail closed. | Technique, percent, actual start/finish, costs. | Status date working days. | `src/construction_pm/scheduling/evm_source.py`, `earned_value.py` | `tests/scheduling/test_evm_source.py`, `test_earned_value.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Reference fixtures for each technique and PF choice are not run. | Add reference fixtures for all technique × ETC combinations. | EV/ETC/EAC/VAC for each technique. | Persisted technique setting -> read model. | PASS — full suite 3055 passed / 132 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (WBS Earned Value) | bf0424db |
| EVM-03 | WBS aggregation, weighted milestones and future periods | WBS technique inheritance/overrides, weighted milestones and resource-curve/manual future-period PV are supported. | WBS-level technique resolution and weighted milestone earning; period-bucket PV. | WBS overrides, milestone weights, curves. | Financial/reporting periods. | `src/construction_pm/scheduling/evm_source.py` (WBS rollup only) | `tests/scheduling/test_evm_source.py` | IMPLEMENTED_BUT_INCOMPLETE | WBS technique inheritance/overrides and weighted milestones are absent; WBS milestone input fails closed; future-period curves are approximated by linear distribution. | Implement WBS-level technique resolution and curve/future-period PV. | WBS override and weighted milestone numeric cases. | Persisted WBS settings -> EVM result. | PASS for implemented subset (3055 passed / 132 skipped); explicit fail-closed gaps. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (WBS Earned Value) | bf0424db |
| EVM-04 | Earned Schedule | Time-based ES/SPI(t) is kept distinct from cost-based EVM. | Earned schedule from PV curve crossing; schedule variance/index in time units. | PV curve, status date. | Reporting periods. | `src/construction_pm/scheduling/earned_schedule.py` | `tests/scheduling/test_earned_schedule.py` | IMPLEMENTED_TESTED_PARITY_PENDING | Reference fixtures for ES boundaries and zero-PV behavior are not run. | Add reference fixtures for ES at project start/finish and flat PV. | ES/SPI(t) for three status dates. | Baseline PV -> earned schedule. | PASS — full suite 3055 passed / 132 skipped. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Earned Schedule) | bf0424db |
| INT-01 | XER/XML/XLSX interchange | Supported interchange formats preserve types, units, nulls and round-trip identity. | Versioned field maps with explicit unsupported reporting. | Import/export documents. | Imported calendars/time units. | No complete implementation | No test | KNOWN_GAP | Full interchange round-trip is absent. | Implement field maps and fixtures per format. | Round-trip equality for typed fields. | Import -> persist -> schedule -> export. | Not run — capability absent. | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (Import/Export) | bf0424db |

### Status summary at this head

| Status | Rows |
|---|---:|
| IMPLEMENTED_AND_PARITY_TESTED | 0 |
| IMPLEMENTED_TESTED_PARITY_PENDING | 17 |
| IMPLEMENTED_BUT_INCOMPLETE | 5 |
| KNOWN_GAP | 2 |
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

## Remaining acceptance criteria

1. All core capabilities inspected in real code — in progress; matrix rows
   identify remaining code gaps.
2. All in-scope capabilities implemented or repaired — **not yet**: BAS-02 and
   INT-01 are known gaps; RES-04, ACT-02, ACT-03, CPM-10 and EVM-03 are
   implemented but incomplete.
3. Important behavior aligned with valid reference documentation — behavioral
   mapping exists; licensed reference-run certification is pending.
4. All main formulas have numeric and boundary tests — formula core and EVM
   source rows pass; reference boundary fixtures remain.
5. CPM, relationships, calendars, actual dates, Data Date and resource
   scheduling integrated and tested — integrated composition tests pass; full
   cross-domain reference fixtures remain.
6. Known Resource Dependent gaps dispositioned — dispositioned in the registry
   and matrix; shift-aware leveling remains open.
7. Regression and integration tests pass — full Python suite passes.
8. No known fixable failure remains in required tests — none observed in the
   Python suite at this head; cross-language CI is verified separately.
9. CUBI code reference updated with real paths/tests — updated for EVM-001,
   EVM-003 and BAS-001; remaining rows reference current paths.
10. Final commits saved on GitHub — `78d78414` pushed; exact-head CI 9/9 green.
11. PR contains latest code, precise description and real CI results — pending
    PR body update and exact-head CI.
12. Unproven capabilities and external limits clearly identified — recorded
    above with zero falsely certified rows.

## Continuation rule

After any session restart: read this file, then compare its head SHA with
`git rev-parse HEAD` and the PR head. Continue from the first open row whose
code, tests or evidence is missing. Do not close the mission because a stage or
a test run ends.
