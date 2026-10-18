# CUBI Scheduling, Resource, Cost and Project-Control Calculation Contract

**Document ID:** CUBI-CALC-CONTRACT-001  
**Status:** Mandatory engineering baseline; living, version-controlled scope registry  
**Initial issue date:** 2026-10-18  
**Reference edition checked:** Oracle Primavera P6 Professional User Guide / Help, Version 26  
**Audience:** all engineers, reviewers, testers, product owners and AI coding agents working on scheduling, dates, resources, cost/EVM, reports, visualizations, imports/exports or the CUBI assistant.

## 1. Purpose and authority

This is the project-wide calculation contract for all CUBI behavior overlapping with the documented behavior of the reference scheduling and project-controls product. It is not an overview. It is the mandatory starting point before calculation code is created, changed, reviewed, imported, wrapped by an API, displayed in a grid/chart/Gantt, or used by the AI assistant.

**Non-negotiable rule:** never implement or “fix” a calculation from intuition, a generic CPM/EVM textbook, an existing test expectation alone, or a copied formula from another product. First locate the applicable section here and official reference evidence; record any missing/ambiguous rule; add a regression fixture; implement in the shared calculation core; and demonstrate the expected result on the exact commit SHA.

Public guides describe supported fields, controls, options and observable behavior. They do not publish every internal detail of the reference scheduler. Where no public source settles a detail, this contract marks it **PARITY TEST REQUIRED** or **OPEN**. Do not assert complete compatibility until a reproducible reference case or authoritative documentation closes it.

### 1.1 Precedence

1. Applicable official reference-document rule and reproducible reference behavior for the supported edition.
2. This contract and its explicit test requirements.
3. Approved CUBI requirements for additive construction workflows.
4. Existing implementation and tests (evidence to inspect, not unquestionable truth).
5. Generic industry practice or engineer assumptions.

If two sources conflict, record the conflict and obtain a decision. CUBI-specific claims, payment, contract, ISO/PMBOK, cash-flow or AI additions must not silently change base CPM/date/resource behavior.

### 1.2 Evidence labels

- **DOCUMENTED** — official guide/API explicitly describes the option or formula.
- **FORMULA CONTRACT** — mathematically stated behavior to implement with explicit time/calendar semantics.
- **PARITY TEST REQUIRED** — public documentation does not fully define ordering, edge cases or internal algorithm behavior.
- **CUBI EXTENSION** — added capability requiring a separate specification and tests.
- **OPEN** — unresolved until sources, decision and tests are recorded.

### 1.3 Mandatory calculation-change record

Every PR affecting calculations must state: (1) this contract section IDs; (2) official source URL/title/edition and exact rule; (3) test inputs, expected outputs, units, dates, options, calendar/baseline versions; (4) happy-path, boundary, multi-calendar, progress/relationship/resource and regression tests as applicable; (5) focused and full CI results on exact final SHA plus independent review; and (6) unresolved ambiguity and fail-safe behavior. A source edit, comment, proposal-only test or red CI is not completion credit. Never weaken a validator to obtain a green test.

## 2. Calculation core and shared input contract

### 2.1 One authoritative engine

Web, desktop, later mobile, import/export, reports, Gantt, grid, chart, offline and AI paths must call one versioned shared domain/calculation core. No duplicate CPM, EVM, resource/cost or calendar arithmetic in UI components, API adapters, report renderers, exporters or AI prompts.

Each immutable calculation input/snapshot must include:

- tenant, project, project revision and calculation ID;
- activities, types, duration type, percent-complete type, status and actuals;
- typed predecessor/successor edges and signed lag;
- primary/secondary constraints and expected-finish inputs;
- data date, project dates and all selected schedule options;
- calendar identity **and version**, hours-per-period settings and exceptions;
- resources, roles, assignments, rates/effective dates, resource calendars;
- leveling options, priority order, selected resource list and capacity slices;
- selected baseline identity/version and WBS earned-value techniques;
- currency, units, precision/rounding policy, engine version and options/schema version.

Persist resolved inputs and provenance so the result can be replayed and audited. Never silently use a mutable “latest calendar” where an assignment is version-pinned. Never guess a missing rate, capacity, baseline, calendar or relationship.

### 2.2 Numeric and temporal rules

- Use exact decimal arithmetic for currency, units and capacity where appropriate; avoid binary floating-point accumulation for currency/resource totals.
- Calculate in canonical internal units. Locale, Persian/Latin digits, Jalali/Gregorian date display, language packs, RTL/LTR, color and icon selection must not change result values or order.
- Round only at documented boundaries. Separate stored precision from display precision.
- Division by zero, missing baseline/rate, unknown calendar, invalid graph, absent capacity and inconsistent dates must yield typed “not calculable/invalid” status or domain errors, never Infinity/NaN, an invented zero, swallowed errors or “success.”
- Sorting and tie-breaking must be deterministic and independent of database iteration order, process timing and locale.
- Keep date/time precision needed by shifts and calendars; do not silently truncate sub-day work periods to midnight.
- Display calendar and internal calendar arithmetic are separate. Changing Jalali/Gregorian presentation cannot change event ordering.

### 2.3 Shared calendar service

A “day” is not always 24 elapsed hours. Calendars define work intervals, holidays, exceptions and default hours-per-period. Scheduling, tracking and leveling use calendar assignments. Task-dependent activities use their activity calendar; resource-dependent activities use resource-calendar behavior. Relationship lag has a separate selectable calendar rule.

All date logic must use one named calendar service—not plain calendar-day integer addition. It must provide working-time add/subtract; next/previous work-period boundaries; duration between dates; normalization; lag/lead conversion/application; overlap enumeration for period demand; date-only versus timestamp normalization; holidays, exceptions, shifts and timezone handling where supported.

Calendar changes affecting durations, lag, availability, spread or rates invalidate dependent results. Cache keys include calendar version and option identity.

**Sources:** [Calendars](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/calendars.htm); [Default hours per time period](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/define_default_hours_per_time_period_in_calendars.htm); [Schedule Options / lag calendar](https://docs.oracle.com/cd/G48902_01/client_help/en_US/general_tab_-_schedule_options_dialog_box.htm).

## 3. Activity types: every supported type has different semantics

Every activity must have a type. A type change must revalidate fields, assignments and calculated values; invalid fields cannot remain active because they were entered under a previous type.

| ID | Type | Mandatory behavior/restriction |
|---|---|---|
| ACT-TD | Task Dependent | Schedule duration according to the activity calendar. Spread resources under the selected duration type, assignment and calendar rules. |
| ACT-RD | Resource Dependent | Each assigned resource's own calendar affects its work/time and activity-date behavior. Never flatten multiple resource calendars into a guessed calendar. |
| ACT-LOE | Level of Effort | Dates/duration depend on related activities; do not treat as independent executable work. The guide says constraints cannot be applied to LOE. |
| ACT-SM | Start Milestone | Event at start; zero duration. No time-based costs, ordinary duration or resource assignments per guide. |
| ACT-FM | Finish Milestone | Event at finish; zero duration. No time-based costs, ordinary duration or resource assignments per guide. |
| ACT-WBS | WBS Summary | Dates/duration derived from activities under the WBS. Constraints cannot be applied; resources that drive dates cannot be assigned to WBS summary activities. Do not treat as a normal work activity. |

Test every type with no/one/multiple predecessors and successors, constraints, actuals, resources, multiple calendars, WBS moves and baseline/summary outputs.

**Sources:** [Activity types](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/activity_types.htm); [Activities](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/activities.htm).

## 4. Duration types and units/rate synchronization

### 4.1 Governing identity

**DOCUMENTED:** maintain this relation under the supported units/time model:

**Duration = Units ÷ (Resource Units per Time)**

Conversions must honor resource type, hours per period, calendars and unit scale. Do not mix days, work hours, material quantities or currency without explicit conversion.

### 4.2 Duration-type matrix

| ID | Duration type | Quantity held fixed | Units changed | Duration changed | Units/time changed |
|---|---|---|---|---|---|
| DUR-FUT | Fixed Units/Time | Resource units per time | Duration changes | Units change | Duration changes |
| DUR-FDUT | Fixed Duration & Units/Time | Duration | Units/time changes | Units change | Units change |
| DUR-FU | Fixed Units | Total units | Duration changes | Units/time changes | Duration changes |
| DUR-FDU | Fixed Duration & Units | Duration and total units | Units/time changes | Units/time changes | Units change |

The official synchronization table also defines behavior when adding the first resource to an assignment with no budgeted/planned units and when adding additional resources. Implement and test those columns too; they cannot be omitted. Start/Finish Milestones disable the duration-type setting.

### 4.3 Mandatory tests

For each duration type, independently edit duration, units and units/time; test all pairwise edits, adding first and additional resources, removal, zero duration, zero units, invalid rate, labor/nonlabor/material, fractional shifts, different calendars, changed display units, actual/remaining data and save/load. Assert which variable remains fixed and which changes.

**Sources:** [Synchronization equation/table](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/synchronizing_activity_duration_units_and_resource_units_time.htm); [Duration types](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/define_activity_duration_types.htm).

## 5. Activity percent complete and dates/status

### 5.1 Percent-complete types

| ID | Type | Formula/meaning |
|---|---|---|
| PC-PHYS | Physical | Activity % Complete = user-entered Physical % Complete. Do not recalculate from duration unless type changes. |
| PC-DUR | Duration | (Original or Planned Duration − Remaining Duration) ÷ Original or Planned Duration. Zero denominator must be handled explicitly. |
| PC-UNITS | Units | (Actual Labor Units + Actual Nonlabor Units) ÷ (Actual Labor Units + Actual Nonlabor Units + Remaining Labor Units + Remaining Nonlabor Units). Zero denominator must be handled explicitly. |

Do not conflate Activity % Complete with Performance % Complete used for Earned Value. The WBS can select a different performance-percent technique.

### 5.2 Separate date fields

Retain distinct Actual Start/Finish, Early Start/Finish, Late Start/Finish, Project Planned Start, Planned Finish, Remaining Start/Finish, Remaining Late Start/Finish, Expected Finish, Constraint Date, Suspend Date and Resume Date. Displayed “Start”/“Finish” may represent actual dates for started/completed activities and remaining/planned dates for other states. The UI/help must make the field meaning clear; never substitute one date type silently.

- Before schedule calculation, planned dates can be planning values. Scheduled Early/Late/Remaining dates are engine outputs.
- For in-progress activities, Remaining Start is the Data Date according to the guide; after completion it is blank.
- Expected Finish is a distinct input and only affects calculated dates when selected.
- Suspension requires an actual start and is permitted by the guide only for Task Dependent and Resource Dependent activities. Suspension is nonworktime according to activity/resource calendars; units/costs are not spread during suspension.

**Sources:** [Percent-complete types](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/define_activity_percent_complete_types.htm); [Activity dates](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/activity_dates.htm); [Suspend/resume progress](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/suspend_or_resume_an_activity_s_progress.htm).

## 6. Relationship network: FS, SS, FF, SF, lag/lead

Each relationship is a directed event-date constraint. Persist relationship type, signed lag, lag unit and lag-calendar semantics. Never silently rewrite SS/FF/SF as FS or drop an edge to make scheduling pass.

Let P be predecessor, S successor, start(X)/finish(X) normalized event boundaries, and L signed lag applied by the configured calendar operation. The following are event-boundary inequalities; actual calculation must use selected calendar/date semantics.

| ID | Relationship | Forward lower bound | Reverse/backward bound |
|---|---|---|---|
| REL-FS | Finish-to-Start | start(S) ≥ addLag(finish(P), L) | finish(P) ≤ subtractLag(start(S), L) |
| REL-SS | Start-to-Start | start(S) ≥ addLag(start(P), L) | start(P) ≤ subtractLag(start(S), L) |
| REL-FF | Finish-to-Finish | finish(S) ≥ addLag(finish(P), L) | finish(P) ≤ subtractLag(finish(S), L) |
| REL-SF | Start-to-Finish | finish(S) ≥ addLag(start(P), L) | start(P) ≤ subtractLag(finish(S), L) |

These are not permission for naive calendar-date arithmetic. Activity duration connects start and finish through the applicable calendar.

- Positive lag delays; negative lag is lead and remains signed.
- The reference UI supports all four types and lag.
- If no lag calendar is selected, the successor activity calendar is the documented default. Options include predecessor calendar, successor calendar, 24-hour calendar and project default calendar.
- Lag entered in units other than hours is converted to hours based on the predecessor calendar; the configured lag calendar controls lag calculation. Test conversion separately from advancement.
- Start-to-start lag in out-of-sequence cases supports calculation from Actual Start or the predecessor internal Early Start. Actual Start uses elapsed time from actual start; Early Start uses work periods elapsed and remaining lag.
- External relationships preserve project identity, project-specific data dates and the explicit “ignore external relationships” option.

### 6.1 Validation

Test all relationship types × positive/zero/negative lag × same/mixed calendars × activity types × actual/in-progress/completed states × constraints × external links. Contradictory hard dates or cycles must yield traceable failures. Never delete edges, guess dates or “fix” input without an approved rule.

**Sources:** [Predecessor relationship types](https://docs.oracle.com/cd/G48902_01/client_help/en_US/predecessors_tab_-_activity_details.htm); [Schedule Options / lag calendar](https://docs.oracle.com/cd/G48902_01/client_help/en_US/general_tab_-_schedule_options_dialog_box.htm); [Release 26 Schedule Options API](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-get.html).

## 7. CPM forward pass, backward pass and float

### 7.1 Pass contract

Run one authoritative graph calculation over activities, calendars, relationships, constraints, progress and selected options. Never compute dates separately in a Gantt or a leveling proposer.

Conceptual forward pass:
- ES(i) is the earliest feasible start after project/data-date rules, remaining work, all predecessor event bounds and start constraints.
- EF(i) = calendarFinish(ES(i), remaining/planned duration, applicable calendar and progress state).
- Incoming edges impose Section 6 event inequalities.
- Expected finish, external relationships and out-of-sequence logic apply at the correct phase.

Conceptual backward pass:
- Establish the applicable finish anchor from the selected project/opened-project policy, expected-finish treatment, constraints and external-link policy.
- Propagate each successor relationship backwards using inverse lag/calendar operations to derive latest permissible events.
- Apply the appropriate constraints and recompute affected graph values consistently.
- Report typed conflicts with activity, edge, constraint, date boundary and selected settings. Never drop relations or return early/late dates that contradict accepted inputs.

These are conceptual pass contracts, not a claim that every progress/constraint/multi-calendar case reduces to one static max/min over timestamps. The interactions require independent fixtures.

### 7.2 Total and Free Float

Support these documented total-float methods:
- Start Float = Late Start − Early Start.
- Finish Float = Late Finish − Early Finish.
- Smallest of Start Float and Finish Float = the more critical of the two measures.

Measure date differences in the applicable work-time/calendar unit, not raw calendar-day integers. Preserve both component values so the selected method can change. Free Float is time an activity can be delayed without delaying its immediate successors; it is scheduler-derived and not a direct editable input. Do not clamp negative float to zero.

Test same/mixed calendars, start/finish constraints, post-data-date actuals, retained logic, open ends, finish-anchor alternatives, negative float, completed activities, milestones and all total-float methods.

### 7.3 Critical activities and multiple float paths

Support both:
- Maximum Total Float threshold: all activities satisfying the chosen threshold can be flagged, even if not on the single longest path.
- Longest Path: trace driving relationships from activities setting the latest calculated project early finish back toward project start, including multi-calendar networks.

Multiple float paths are calculated after base scheduling. Support Total Float- or Free Float-based path calculations, path count, optional endpoint activity, stable path IDs and path order. Critical-by-threshold and path membership are different concepts. Test resource-driven backward paths and multi-project leveled logic separately.

**Sources:** [Scheduling projects](https://docs.oracle.com/cd/G48902_01/client_help/en_US/scheduling_projects.htm); [General Schedule Options](https://docs.oracle.com/cd/G48902_01/client_help/en_US/general_tab_-_schedule_options_dialog_box.htm); [Multiple critical float paths](https://docs.oracle.com/cd/G48902_01/client_help/en_US/analyzing_the_schedule_using_multiple_critical_float_paths.htm); [Float values](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/view_activity_float_values.htm).

## 8. Constraints

Model primary/secondary constraints independently where supported. Validate against correct start/finish event.

| ID | Constraint | Semantic requirement |
|---|---|---|
| CON-START-ON | Start On | Soft date constraint; may affect float/feasibility. |
| CON-START-BEFORE | Start On or Before | Soft upper bound on start. |
| CON-START-AFTER | Start On or After | Soft lower bound on start. |
| CON-FINISH-ON | Finish On | Soft date constraint; may affect float/feasibility. |
| CON-FINISH-BEFORE | Finish On or Before | Soft upper bound on finish. |
| CON-FINISH-AFTER | Finish On or After | Soft lower bound on finish. |
| CON-MAND-START | Mandatory Start | Hard start constraint. |
| CON-MAND-FINISH | Mandatory Finish | Hard finish constraint. |
| CON-ALAP | As Late As Possible | Schedule as late as possible based on available free float and the relevant scheduling model. |

The guide describes Mandatory Start/Finish as hard constraints; the six on/before/after constraints are soft and can distort float. ALAP needs its own parity fixture. Expected Finish remains a separate input, included only when its schedule option is active.

When constraints and relations conflict, return a diagnostic with implicated activities, constraints, edge(s), event/date and settings. Do not accept a proposed exact-date pair that the actual CPM pass cannot satisfy.

**Sources:** [Constraint types](https://docs.oracle.com/cd/G48902_01/client_help/en_US/types_of_constraints.htm); [General Schedule Options](https://docs.oracle.com/cd/G48902_01/client_help/en_US/general_tab_-_schedule_options_dialog_box.htm).

## 9. Scheduling options: every user selection changes the calculation contract

Save these options in the calculation snapshot; reports, logs and assistant explanations must identify the selected values.

| ID | Selection | Required handling |
|---|---|---|
| SCH-DATA-DATE | Per-project Data Date vs selected date applied to all open projects | Preserve each project's chosen data date and project scope. |
| SCH-EXPECTED-FINISH | Use Expected Finish Dates | Include only when selected. |
| SCH-AUTO | Automatic scheduling on significant changes | Recalculate dependencies or explicitly mark cached values stale. |
| SCH-LEVEL-AUTO | Level resources during scheduling | Invoke shared leveling + authoritative CPM + final validation. |
| SCH-EXTERNAL | Ignore/respect external-project relationships | Apply the explicit policy to external links. |
| SCH-OPEN-END-CRITICAL | Make open-ended activities critical | Apply selected flag behavior; never invent missing edges. |
| SCH-FINISH-ANCHOR | Opened projects vs each project | Preserve backward-pass anchor scope. |
| SCH-TOTAL-FLOAT | Start, Finish, or Smallest | Use Section 7.2. |
| SCH-LAG-CALENDAR | Successor, predecessor, 24-hour, project default | Use Section 6 semantics. |
| SCH-PROGRESS-LOGIC | Retained Logic, Progress Override, Actual Dates | Apply different rules in Section 10. |
| SCH-SS-LAG | SS lag from Actual Start or internal Early Start | Apply selected out-of-sequence mode. |
| SCH-MULTI-PATH | Enabled; Total Float/Free Float; endpoint; count | Calculate paths after base schedule; do not conflate with critical flags. |
| SCH-RECALC-RATES | Recalculate assignment cost after schedule for multiple rates | Use selected behavior and effective dates. |
| SCH-PRESERVE-EARLY-LATE | Preserve scheduled early/late dates when leveling | If selected preserve; otherwise recalculate late dates as documented. |
| SCH-LEVEL-FLOAT | Level within float; minimum float; allowed overload % | Respect selected bounds; always validate final demand. |
| SCH-LEVEL-PRIORITY | Ordered priority fields and sort direction | Full lexicographic ordering and deterministic tie-breaks. |
| SCH-RESOURCE-LIST | All resources or selected subset | Never level a resource outside the chosen set. |

**Sources:** [General Schedule Options](https://docs.oracle.com/cd/G48902_01/client_help/en_US/general_tab_-_schedule_options_dialog_box.htm); [Advanced Schedule Options](https://docs.oracle.com/cd/G48902_01/client_help/en_US/advanced_tab_-_schedule_options_dialog_box.htm); [Schedule a project](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/schedule_a_project.htm); [Release 26 options API](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-get.html).

## 10. In-progress activities and out-of-sequence modes

Actual Start/Finish, Data Date, remaining duration/units, suspend/resume intervals and actual costs remain separate facts. Never infer actual data from forecast dates.

| ID | Option | Required documented behavior |
|---|---|---|
| OOS-RETAINED | Retained Logic | Remaining duration of a progressed activity is not scheduled until all predecessors are complete. |
| OOS-OVERRIDE | Progress Override | Network logic is ignored for the progressed activity so it can progress without delay from unfinished predecessor logic; retain original relationships. |
| OOS-ACTUAL | Actual Dates | Forward/backward passes are scheduled using actual dates. This can yield negative Total Float when actuals are after Data Date. |

Test unfinished predecessor with actual successor start, progress on both sides of Data Date, actuals after Data Date, actual finish entry/removal, changed Remaining Duration, negative lag and SS-lag mode. Never use one generic out-of-sequence branch for all three.

**Sources:** [General Schedule Options](https://docs.oracle.com/cd/G18296_01/client_help/en_US/general_tab_-_schedule_options_dialog_box.htm); [Release 26 Schedule Options API](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-get.html).

## 11. Resource leveling

Leveling is a constrained scheduling stage, not just a set of proposed date shifts. Accept no proposal until authoritative CPM has produced feasible dates and aggregate resource demand has been reconciled against capacity for every affected period.

### 11.1 Inputs

Use resource/role assignment identity; planned/actual/remaining units; units/time; effective rates; resource calendar identity/version; capacity per period; complete activity/relationship graph; calendars, Data Date, constraints and progress mode; all selected leveling options; priorities/resource subset; cross-project rules and project leveling priority; manually entered future-period assignment buckets.

The guide says resource curves are not used during leveling, but manual future-period values are considered. Do not treat a curve as a capacity limit.

### 11.2 Capacity invariants

For each selected resource r and period t:

- Demand(r,t) = sum of assignment demand overlapping that period under the applicable calendar/spread and leveling semantics.
- BaseCapacity(r,t) is resolved from the versioned canonical resource calendar/capacity source.
- EffectiveCapacity(r,t) = BaseCapacity(r,t) × (1 + OverAllocationPercentage / 100) only where the selected option applies.
- Overload(r,t) = max(0, Demand(r,t) − EffectiveCapacity(r,t)).
- A result claiming capacity-constrained success must satisfy Overload(r,t) = 0 in every period. Any permitted overload must be explicitly selected and reported.

Final demand validation is mandatory. Never disable, bypass, swallow or weaken it.

### 11.3 Mandatory candidate-feasibility loop

1. Propose a candidate using selected resources, capacities, calendars and configured priority order.
2. Apply it to a trial snapshot without mutating the accepted schedule.
3. Run authoritative CPM using all relationships, calendars, progress rules and constraints.
4. Recompute period demand from actual trial dates, not proposal dates.
5. Aggregate demand by resource/period across the combined multi-project graph.
6. Reject a trial that violates relationship feasibility, hard constraints, prohibited float bounds or unallowed final capacity.
7. Try the next deterministic feasible candidate within a documented bound. If none works, return typed infeasibility with bottleneck resource/period and involved activities.

Never transform a failed proposal into an exact start lower/upper bound that makes CPM impossible. Batch leveling must make a coordinated decision over the shared graph, not independently level projects and only discover overload at the end.

### 11.4 Priorities and test coverage

Support full ordered priorities and sort direction, project leveling priority (guide: 1 highest, 100 lowest), cross-project assignment threshold, preservation of Early/Late dates, minimum float and selected resource scope. Equal priorities must use deterministic documented ties. Level-within-float restrictions and over-allocation percentage must not be treated as universal permission to overload.

Required tests: linked SS/FS/FF/SF; lead/lag; mixed calendars; resource-dependent activities; shared resources across projects; priority ties; exact constraints; forward then backward leveling; zero/nonzero float and minimum float; preserve Early/Late dates on/off; selected resources; permitted overload setting; manual future buckets; calendar versions; final demand recomputed after CPM; infeasible capacity; determinism/replay.

**Sources:** [Leveling resources](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_resources.htm); [Level resources](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/level_resources.htm); [Leveling priority definitions](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_priority_definitions.htm); [Specify leveling priorities](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/specify_leveling_priorities.htm); [Project leveling priority](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/change_the_project_leveling_priority.htm).

## 12. Resource assignments, rates, spread and expenses

### 12.1 Assignment identity

Preserve resource/role ID, assignment ID, unit type, planned/budgeted units, actual units, remaining units, units/time, calendar ID/version, cost account, rate type/effective dates, actual/remaining cost, curve/future bucket and supported metadata through persistence, DTO, API, adapter and schedule snapshot. Roles represent skill/capability and are not interchangeable with concrete resource capacity unless a documented staffing resolver makes that conversion.

### 12.2 Cost formulas

For each applicable assignment/rate segment:
- Planned/Budgeted cost = planned/budgeted units × applicable price per unit.
- Actual cost comes from actual units/cost inputs according to selected resource/rate semantics, or explicit actual-cost entry when supported.
- Remaining cost comes from remaining quantity/cost using the selected method.
- At-completion cost = actual cost + remaining cost.

Use effective-date price rates and selected assignment rate type/source. When rates change during work, partition calculations by their effective periods where the reference requires. Honor the selected “recalculate assignment costs after scheduling” option for multi-rate assignments. Do not invent a default rate; use one only where reference behavior documents it.

Keep labor, nonlabor, material and expenses separately auditable before rollups.

### 12.3 Time-phasing and curves

- Without a curve/manual future-period override, budgeted units may be spread evenly across selected duration/timescale according to documented behavior.
- Curves affect planned time-phasing and reports; exact normalization and bucket boundaries require parity tests.
- Manual future-period buckets must persist and affect their documented values.
- Leveling ignores resource curves but considers manual future-period values; spread and capacity logic must not be conflated.
- Spread units/cost must reconcile to assignment totals with explicit precision/rounding policy.

### 12.4 Expenses and cost accounts

- Planned expense cost = planned units × price/unit.
- Start of Activity: accrue entire expense at activity start.
- End of Activity: accrue entire expense at activity finish.
- Uniform Over Activity: distribute uniformly over duration according to calendar/period spread semantics.
- Auto Compute Actuals, if selected, uses the documented planned completion percentage; otherwise preserve entered actuals.
- Cost-account hierarchy associations must trace to source activity/assignment/expense; do not double-count on rollup.

**Sources:** [Assign resources/roles](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/assigningresourcesandrolestoactivities.htm); [Resources](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/resources.htm); [Future period buckets](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/future_period_bucket_planning.htm); [Resource assignments window](https://docs.oracle.com/cd/G48902_01/client_help/en_US/resource_assignments_window.htm); [General Schedule Options](https://docs.oracle.com/cd/G48902_01/client_help/en_US/general_tab_-_schedule_options_dialog_box.htm); [Official guide contents: expenses/cost accounts](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm).

## 13. Earned Value Management (EVM) and forecast techniques

Earned Value is a family of selected calculation methods. Preserve baseline, baseline/date basis, WBS earning method, activity completion type, resource-curve/future-bucket option, ETC method and performance factor as explicit inputs.

### 13.1 Base metrics

- BAC = Budget at Completion from the selected baseline.
- EV = Earned Value cost, calculated from baseline BAC and Performance % Complete.
- PV = Planned Value cost, derived from selected baseline/time-phased plan and date basis.
- AC = Actual Cost from relevant actual labor/nonlabor/material/expense data.
- ETC = Estimate to Complete under selected WBS technique.
- EAC = Estimate at Completion = AC + ETC.
- CV = Cost Variance = EV − AC.
- SV = Schedule Variance = EV − PV.
- CPI = Cost Performance Index = EV ÷ AC.
- SPI = Schedule Performance Index = EV ÷ PV.
- TCPI against BAC = (BAC − EV) ÷ (BAC − AC).
- TCPI against EAC = (BAC − EV) ÷ (EAC − AC).

If a denominator is zero, return an explicit undefined/not-applicable state with reason; never divide by zero or fabricate zero. Standard cost-based SV is a cost-valued variance, not a time duration. CUBI Earned Schedule/time-based metrics are separate extensions with their own contract and tests.

### 13.2 WBS performance-percent techniques

Documented choices:
- **Activity % Complete:** use the current activity completion percentage according to the activity's selected Percent Complete Type.
- **WBS Milestones:** sum the weights of completed WBS milestones ÷ total possible weights of all milestones.
- **0/100 % Complete:** performance percentage is 0 until activity ends, then 100%.
- **50/50 % Complete:** after start and before finish, 50%; after finish, 100%.
- **Custom % Complete:** use configured percentage after start and before finish; after finish, 100%.
- **Use resource curves/future period buckets:** where selected and applicable, use documented resource-spread override rather than blindly using ordinary activity percent complete.

Weighted milestone formula:

**Performance % Complete = Actual Weight of Completed Milestones ÷ Total Possible Weight of All Milestones.**

**EV Cost = BAC Cost × Performance % Complete.**

**EV Labor Units = Baseline Labor Units × Performance % Complete.**

The baseline source and technique must appear in provenance. Do not treat Activity % Complete as performance percentage if a different WBS technique is selected.

### 13.3 ETC choices

Support the documented methods:

1. **ETC = remaining cost for activity.** Reference describes it as remaining activity duration × applicable resource rates; test how all supported resource/rate/expense categories participate.
2. **PF = 1:** ETC = 1 × (BAC − EV).
3. **PF = 1/CPI:** ETC = (1/CPI) × (BAC − EV).
4. **PF = 1/(CPI × SPI):** ETC = (1/(CPI × SPI)) × (BAC − EV).
5. **PF = user-defined:** ETC = user PF × (BAC − EV).

Then EAC = AC + ETC. Apply labor-unit variants only with corresponding baseline labor units and the selected documented method; never substitute cost and units.

### 13.4 Baseline and time basis

Documented selections include baseline At Completion values with current dates, Budgeted/Planned values with planned dates, or Budgeted/Planned values with current dates. Live calculations can be configured to use the project baseline or the user's primary baseline; published/summarized values may use a different baseline policy. Every report must state baseline and date policy. Changing baseline/date policy invalidates PV, EV, CV, SV, CPI, SPI, ETC, EAC, TCPI and derived trends.

### 13.5 EVM regression suite

Test all performance methods, activity Physical/Duration/Units, 0/partial/100 progress, started/completed/not-started, unequal milestone weights, curves/buckets, every ETC mode, zero CPI/SPI denominator, baseline switching, planned/current dates, multiple rates, expenses, all resource categories, WBS rollup, historical period edits, repeat posting and precision reconciliation. Same snapshot must reproduce identical values.

**Sources:** [Earned Value admin settings](https://docs.oracle.com/cd/G48902_01/client_help/en_US/earned_value_tab_-_admin_preferences_dialog_box.htm); [WBS-specific EVM settings](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/define_earned_value_settings_for_a_specific_work_breakdown_structure_element.htm); [WBS milestones](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/assign_wbs_weighted_milestones.htm); [EAC definition](https://docs.oracle.com/cd/F88968_01/client_help/en_US/estimate_at_completion.htm); [TCPI](https://docs.oracle.com/cd/F88966_01/p6help/en/43948.htm); [Release 26 activity API](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html).

## 14. Baselines, actuals, period performance and history

- A baseline is an identified/versioned comparison snapshot; changing it must not overwrite current actual facts.
- Keep current schedule, baseline, target, planned-value, actual-value and forecast series separate.
- Actual This Period and Actual To Date are distinct. With the “Link actual to date and actual this period units and costs” option, maintain the documented relationship. Period posting saves selected-period values then resets Actual This Period for the next update cycle.
- Period posting must record financial-period ID, source snapshot, unit/cost/EV/PV series, timestamp, actor and idempotency behavior. Reposting follows documented overwrite behavior; do not add the same values twice.
- Past-period edits require audit history and downstream recalculation.
- Data Date, baseline, calendar/version or WBS earned-value changes invalidate dependent values via an explicit dependency graph.

**Sources:** [Version 26 User Guide table of contents—period performance](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm); [Post period amounts](https://docs.oracle.com/cd/F51303_01/English/User_Guides/p6_pro_user/post_actual_amounts_for_a_period.htm); [EVM admin settings](https://docs.oracle.com/cd/G48902_01/client_help/en_US/earned_value_tab_-_admin_preferences_dialog_box.htm).

## 15. WBS, summary activity and rollup rules

- WBS Summary is derived data, not an independently schedulable work item.
- Preserve documented rollup basis for planned/actual dates, planned/actual/remaining duration, early/late dates, float, units, costs and activity counts.
- Never average completion percentages without their defined weighting. Weighted milestones use Section 13.2.
- Summary cost must reconcile to descendant assignment/expense amounts, counting each in-scope source exactly once.
- Each rollup formula must state contributing population and weighting. If a specific summary field definition is not verified, mark OPEN and add parity tests before claiming compatibility.

**Sources:** [How data is summarized](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/how_data_is_summarized.htm); [WBS weighted milestones](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/assign_wbs_weighted_milestones.htm); [Release 26 WBS API](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-wbs-get.html).

## 16. Grids, Gantt, charts, KPIs, reports and exports

Any calculated cell, formula column, Gantt bar, network diagram, KPI, chart, printout, export or AI answer must consume the authoritative engine output and expose calculation context where relevant.

- Gantt bars use scheduled dates/progress intervals; baseline bars use selected baseline dates.
- Critical coloring uses configured critical-activity definition; float-path grouping uses multiple-path mode. Different highlights can be correct.
- Resource histograms/usage spreadsheets show time-phased demand using selected calendar and buckets; total and spread must reconcile.
- Cost/EVM visuals use selected baseline, Data Date, period, currency and earning-value technique. Never recalculate a separate formula in chart/UI code.
- Status icons/colors are presentation of a typed state; they never replace the underlying warning/error record.
- Exported numbers must retain units, date/time basis, baseline, calculation timestamp/version and stale/not-calculated state where required.
- User-editable formula columns are a separate extension: declare inputs, output unit, order, precision/null/divide-by-zero behavior and tests.

**Sources:** [User Guide contents—Activity Table and Gantt Chart](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm); [Resource assignments window](https://docs.oracle.com/cd/G48902_01/client_help/en_US/resource_assignments_window.htm); [Multiple float paths](https://docs.oracle.com/cd/G48902_01/client_help/en_US/analyzing_the_schedule_using_multiple_critical_float_paths.htm).

## 17. CUBI-specific extensions must stay separate

| Extension | Separate approved formula/behavior contract |
|---|---|
| Contract/BOQ/quantities/cost control | Measurement rules, source quantities, units conversion, valuation date, rates, escalation/tax/retention, rounding and audit trail. |
| Payment applications/certificates | Gross value, approved change orders, retention, advance recovery, taxes/deductions, prior certificates, payable net, period cut-off and approval state. |
| Claims/extension of time | Baseline/snapshot, event chronology, contract clause, notice/evidence, impacted activities, critical/near-critical path, concurrency/causation assumptions, calendars and windowed analyses. CPM alone cannot determine legal entitlement. |
| Cash flow/spending plan | Planned/actual/forecast time-phased values, accrual basis, period/calendar, baseline and reconciliation to cost totals. |
| Risk/scenarios | Probability/impact model, distributions, correlation assumptions, deterministic seed/replay and clear separation from deterministic CPM. |
| ISO/PMBOK/PMI overlays | Workflow/form overlays may organize evidence, but must not change CPM/float/resource rules without a separately approved engineering contract. |
| AI project initialization | AI may propose WBS, activities, relationships, durations, resources/import mappings. Domain validation and the authoritative engine validate every committed value. |
| AI assistant/reporting | Use the same authorized APIs and calculation snapshot; explain settings and assumptions. No shadow formulas in prompts. |
| Languages/Jalali/Gregorian/RTL | Presentation only; calculations remain invariant across locale. |

Use separate identifiers/namespaces and tests. Never label a CUBI extension as a reference-documented formula.

## 18. Mandatory UI action/icon registry

“Every icon” is an engineering coverage requirement, not just a visual review. Every interactive menu item, toolbar icon, context command, keyboard shortcut, chart action, Gantt handle, grid editor, dialog selector, formula column, import/export action, report control and AI tool that creates/changes/displays calculated values must map to contract sections and tests.

Every registry row must include:
1. Stable action ID and visible/accessibility label.
2. Web/desktop/mobile-later surface, route/screen/dialog.
3. Menu path, icon asset/name, tooltip and keyboard shortcut.
4. Input fields/options changed and domain API invoked.
5. Calculation Contract IDs and invalidation behavior.
6. Mutation/calculation/display/visualization-only classification.
7. Authorization and AI-permission class (read, calculate, propose, write, approve/export).
8. Expected errors, resource/constraint validation and audit record.
9. Unit/integration/UI/regression test IDs.
10. Owner, evidence link, status, independent reviewer and final SHA.

Invariants:
- A visual control never contains separate calculation logic.
- Icon replacement/placement cannot alter business logic.
- Every new calculation-affecting control needs a registry row and acceptance test before merge.
- Every discovered existing control must be inventoried; absence from the registry is an audit gap, not proof it has no calculation.
- Tooltip/help/accessibility label must be clear in all supported languages. User-facing help/branding must not show internal source URLs/provider branding; these belong in engineering evidence.
- Menus, grids, charts, reports and AI tools expose consistent field definitions, units and stale/invalid/result states.

**Initial inventory state:** the control-by-control inventory is NOT complete merely because this specification exists. Scan the actual web/desktop routes, commands, grid columns, icons, dialogs, charts, Gantt controls, imports/exports and AI tools, map every discovered control and report unmapped items. Do not claim “icon-by-icon complete” until populated and independently reviewed.

## 19. Required test design

Every rule needs more than a happy-path test:
- hand-calculated formula example with units and expected output;
- zero/one-period, shift boundary, holiday, date crossing, negative float, exact capacity/constraint;
- calendar matrix: activity/project/resource/lag, exceptions, links, versions and multi-calendar networks;
- relation matrix: all four types × lag sign × out-of-sequence state × actual/remaining status;
- selected-option matrix, including option interactions;
- baseline/Data Date/financial-period matrix for EVM and reporting;
- write/commit/fresh-read/immutable-input/calculate/export round trip including scope and version IDs;
- invalid-input tests for typed fail-closed behavior;
- properties: deterministic replay; all accepted relations hold; no hard constraint is violated; quantities/costs reconcile; final leveled demand respects capacity; same inputs/options/engine return identical outputs;
- reference differential fixtures with edition, full inputs/output, settings and provenance;
- focused tests, full CI on exact SHA, independent review.

“Green” does not mean merely that no exception was thrown. A schedule that emits dates but violates a relationship or allowed capacity is a failed calculation.

## 20. OPEN/parity backlog and source maintenance

Keep unresolved items live. Initial items:
- Exact CPM normalization/boundaries for all activity types on intraday and mixed calendars.
- All primary/secondary constraint interactions, especially conflicts and ALAP with out-of-sequence actuals.
- Every combination of Retained Logic / Progress Override / Actual Dates, SS lag, completed activities and negative lag.
- Exact float and driving-relationship tie breaks for multiple paths.
- Full leveling candidate ordering, shared cross-project demand and infeasible diagnostics; public guides specify visible behavior but not every internal tie-break.
- Calendar inheritance/exception precedence/version pinning and availability/time-phase reconstruction.
- Resource curve normalization and cost handling across every rate effective-date boundary.
- Every summary/earned-value field with specific rollup semantics.
- Construction extensions lacking an independently approved formula contract.
- Full menu/icon/toolbar/grid/chart/dialog/AI-tool inventory.

Each OPEN item requires owner, source search, decision, test ID, reviewer and resolution date. Never delete an open item merely to make a report look complete. Review current official links before major calculation changes; historical editions may supplement but must not silently replace the selected current guide. Documentation changes require a diff review and regression tests.

## 21. Official source index

This is the initial index of calculation-relevant official sources reviewed for this contract; it is not a claim that every historical release, every UI-only help page or every possible field has been exhaustively transcribed. Expand it as the control inventory and OPEN backlog are closed.

### Core guide/navigation
- [P6 Professional User Guide Version 26 — complete table of contents](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm)
- [Scheduling projects / CPM](https://docs.oracle.com/cd/G48902_01/client_help/en_US/scheduling_projects.htm)
- [Schedule a project](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/schedule_a_project.htm)
- [General Schedule Options](https://docs.oracle.com/cd/G48902_01/client_help/en_US/general_tab_-_schedule_options_dialog_box.htm)
- [Advanced Schedule Options](https://docs.oracle.com/cd/G48902_01/client_help/en_US/advanced_tab_-_schedule_options_dialog_box.htm)
- [Release 26 Schedule Options API](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-get.html)

### Activity/relationship/calendar
- [Activities](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/activities.htm)
- [Activity types](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/activity_types.htm)
- [Activity dates](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/activity_dates.htm)
- [Duration synchronization](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/synchronizing_activity_duration_units_and_resource_units_time.htm)
- [Duration types](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/define_activity_duration_types.htm)
- [Percent-complete types](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/define_activity_percent_complete_types.htm)
- [Predecessor relationship types](https://docs.oracle.com/cd/G48902_01/client_help/en_US/predecessors_tab_-_activity_details.htm)
- [Calendars](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/calendars.htm)
- [Constraint types](https://docs.oracle.com/cd/G48902_01/client_help/en_US/types_of_constraints.htm)
- [Float values](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/view_activity_float_values.htm)
- [Multiple critical float paths](https://docs.oracle.com/cd/G48902_01/client_help/en_US/analyzing_the_schedule_using_multiple_critical_float_paths.htm)
- [Suspend/resume](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/suspend_or_resume_an_activity_s_progress.htm)

### Resources, leveling and cost
- [Resources](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/resources.htm)
- [Assign resources and roles](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/assigningresourcesandrolestoactivities.htm)
- [Leveling resources](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_resources.htm)
- [Level resources](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/level_resources.htm)
- [Leveling priority definitions](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_priority_definitions.htm)
- [Specify leveling priorities](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/specify_leveling_priorities.htm)
- [Project leveling priority](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/change_the_project_leveling_priority.htm)
- [Future period buckets](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/future_period_bucket_planning.htm)
- [Resource Assignments window](https://docs.oracle.com/cd/G48902_01/client_help/en_US/resource_assignments_window.htm)
- [Resource/assignment API field definitions](https://docs.oracle.com/cd/F51303_01/English/Integration/p6_pro_api_reference/FieldSummary.html)

### Earned value/WBS/financial periods
- [Earned Value admin settings](https://docs.oracle.com/cd/G48902_01/client_help/en_US/earned_value_tab_-_admin_preferences_dialog_box.htm)
- [WBS earned-value settings](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/define_earned_value_settings_for_a_specific_work_breakdown_structure_element.htm)
- [WBS weighted milestones](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/assign_wbs_weighted_milestones.htm)
- [Estimate at Completion](https://docs.oracle.com/cd/F88968_01/client_help/en_US/estimate_at_completion.htm)
- [To-Complete Performance Index](https://docs.oracle.com/cd/F88966_01/p6help/en/43948.htm)
- [Release 26 WBS API](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-wbs-get.html)
- [Release 26 activity API](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html)
- [How data is summarized](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/how_data_is_summarized.htm)
- [Post period actuals](https://docs.oracle.com/cd/F51303_01/English/User_Guides/p6_pro_user/post_actual_amounts_for_a_period.htm)

## 22. Definition of done

Adoption is complete only when:
1. This contract is merged to the authoritative repository branch.
2. Root agent instructions and contributor rules link to it.
3. The PR checklist requires section/source/test evidence.
4. Existing calculation modules and tests are mapped to section IDs.
5. The UI action/icon registry has been populated from actual product surfaces.
6. OPEN items have owners and are not mislabeled completed.
7. Named scheduler/resource regressions and applicable required tests are green on exact final SHA.
8. An independent reviewer confirms evidence.

Until those gates pass, this is the mandatory baseline and coverage plan—not a claim that the whole product already fully conforms.


## 23. Activity steps and step-weighted physical progress

When the project option “Activity Percent Complete Based on Activity Steps” is selected and an activity uses Physical as its percent-complete type, the activity's Physical % Complete is derived from its weighted steps. A step can hold a Step % Complete or be marked Completed; completed means 100%.

Required formula contract for weighted progress:

Physical % Complete = 100 × Σ(step weight × step percent complete / 100) ÷ Σ(all step weights).

This is mathematically equivalent to the weighted average of step percentages. Example: step weights 3, 2 and 1; the weight-3 step completed and the other two at 0 gives 3/6 = 50%. Adding, removing or editing a step, its weight or percentage must recalculate the activity when the project/activity settings call for this method. The guide documents the example and weighted behavior; partial-step, zero-total-weight and rounding edge cases still require reference parity fixtures. Do not divide by zero or make every new step weight 1 when the documented default rule requires 0 because prior steps are already complete.

Test: project option on/off; Physical vs Duration/Units type; every step 0/partial/100; Completed checkbox toggling; unequal/zero weights; add/remove/reweight; templates; saved/reloaded activity; and earned-value behavior when the WBS method uses activity percent complete.

**Sources:** [Activity steps (Version 26)](https://docs.oracle.com/cd/F51303_01/English/User_Guides/p6_pro_user/activity_steps.htm); [Add weights to steps (Version 26)](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/add_weights_to_steps.htm); [ActivityStep API](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/api-activitystep.html).

## 24. Schedule percent complete and other date-derived indicators

Do not treat every percentage field as the Activity % Complete from Section 5. At minimum distinguish:
- Activity % Complete (according to Physical/Duration/Units type);
- Performance % Complete (WBS Earned Value technique);
- Schedule % Complete (progress that the selected baseline schedule implies should have been achieved by Data Date);
- percent of duration/units/cost completed and any report-specific variants.

For Schedule % Complete, the official activity-field description defines the value relative to the selected baseline: 0% when Data Date is before baseline Start, 100% when Data Date is after baseline Finish, and a date/calendar-derived proportion between those boundaries. The exact inclusive work-period boundary and chosen baseline variant must be proven with a reference fixture before implementation claims parity. This value must not be substituted for Physical, Duration, Units or Performance % Complete.

**Source:** [Oracle activity subject-area field definitions](https://docs.oracle.com/en/industries/construction-engineering/intelligence/subject-area-reference-guide/p6-activity-primaveraactivity.html).

## 25. Leveling priority list: complete documented field vocabulary and tie rules

The supported priority list is ordered and lexicographic: a priority earlier in the list takes precedence over all priorities beneath it. Support all documented field choices and ascending/descending direction:

- Activity ID;
- Activity Priority;
- Early Finish;
- Early Start;
- Free Float;
- Late Finish;
- Late Start;
- Original or Planned Duration;
- Planned Finish;
- Project Planned Start;
- Project Priority;
- Remaining Duration;
- Total Float.

The documented per-field direction must be preserved: Activity ID uses low IDs first ascending/high IDs first descending; Activity Priority follows its configured numerical order; early/late/plan dates use earlier/later first; Free Float and Total Float can place more-critical activities first in ascending order; duration fields order shorter/longer first; Project Priority follows project priority ordering. Numbers sort before alphabetic characters, then blanks; with no priority codes the reference sorts by Activity ID.

For multiple open projects, the selected project's leveling settings must be explicit; do not mix priorities from different projects accidentally. Add same-date, equal-float, equal-duration and blank-code tests, including project-level priority tie-breaking.

**Sources:** [Leveling priority definitions, Version 26](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_priority_definitions.htm); [Specify leveling priorities, Version 26](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/specify_leveling_priorities.htm); [Project leveling priority, Version 26](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/change_the_project_leveling_priority.htm).

## 26. Global Change and user-defined arithmetic

Global Change is an explicit user-selected calculation/editing feature and must not be confused with the scheduler. Implement a typed and auditable expression model with the documented distinction between condition tests and assignments:

- If statements use comparisons/conditions; arithmetic expressions are not used as If expressions.
- Then/Else statements can calculate numeric data using addition, subtraction, multiplication and division.
- Ampersand is the documented text-concatenation operator.
- Integer + integer = integer.
- Date + integer = date, where integer adds working periods.
- Date − date = integer work-period difference.
- Date − integer = date.
- Integer division in this reference Global Change context returns decimal to two-digit accuracy.

Date arithmetic uses the applicable activity/resource calendar work-period numbering, not plain Gregorian/Jalali calendar-day subtraction. Preserve typed operands: invalid date/text/numeric combinations must be rejected with a clear error. Preview the affected records and calculated values before applying a multi-row change; record before/after values, user, scope, expression version and affected entity IDs. Changes to durations/dates/units/relationships must invalidate and recalculate dependent schedule/cost values after application.

CUBI may retain additional precision internally for core cost/resource calculations, but its **reference-compatible Global Change mode** must reproduce the reference expression operators, allowed operand types, date/work-period behavior and documented division display/rounding behavior. Do not allow raw arbitrary code evaluation.

**Sources:** [Global Change Version 26 help index](https://docs.oracle.com/cd/G48902_01/client_help/en_US/globalchange.htm); [Operators and valid calculations](https://docs.oracle.com/cd/G48902_01/client_help/en_US/operators_and_valid_calculations.htm); [Use arithmetic with Global Change](https://docs.oracle.com/cd/G48902_01/client_help/en_US/use_arithmetic_with_global_change.htm); [Use date arithmetic](https://docs.oracle.com/cd/G48902_01/client_help/en_US/use_date_arithmetic.htm).

## 27. Command-to-calculation mapping: reference control inventory for the actual CUBI UI audit

The rows below are the initial reference-command inventory derived from calculation-relevant guide navigation. Each must be mapped to the concrete CUBI screen/control/icon/tooltip/API/test using Section 18. This is a coverage seed, **not evidence that the current CUBI UI has already been completely inventoried**.

| Reference command/screen/control | Fields or selections that affect calculation | Contract IDs / expected test family |
|---|---|---|
| Tools → Schedule | Data Date, general/advanced options, project set | SCH-*, CPM, date/float regression |
| Schedule Options → General | external links, open ends, expected finish, auto scheduling, float method, lag calendar, OOS mode, SS lag | SCH-*, REL-*, OOS-*, CPM matrix |
| Schedule Options → Advanced | multiple paths, path method, endpoint and count | CPM float-path tests |
| Activity Details → General | activity type, duration type, percent-complete type, activity calendar | ACT-*, DUR-*, PC-*, CAL-* |
| Activity Details → Status | actuals, remaining duration, suspend/resume, float display | PC-*, OOS-*, dates, progress tests |
| Activity Details → Predecessors/Successors | relation type, lag, external/project identity | REL-*, graph integrity and mixed-calendar tests |
| Gantt relationship connector/editor | relation type, direction, lag | REL-*; UI edit must equal domain edit |
| Activity-table Start/Finish edit or Gantt drag handle | planned dates, constraints/edits created and resulting recalculation | CPM, CON-*, audit before/after |
| Activity Details → Resources/Assignments | resource/role, assignment units, units/time, rate type, cost, calendar | RES-*, COST-*, DUR-* |
| Enterprise → Calendars / project/resource calendar editor | work week, shifts, holiday exceptions, hours per time period, calendar version | CAL-*; all-dependent-value invalidation |
| Resource/Role → Units & Prices / rate effective dates | max units/time, price/unit, rate type and effective date | RES-*, COST-*, leveling capacity tests |
| Tools → Level Resources | selected resources, priorities/order, within float, minimum float, allowed overload, preserve Early/Late dates and cross-project policy | SCH-LEVEL-*, complete final-demand tests |
| Enterprise → Projects → General → Project Leveling Priority | project priority 1–100 | cross-project resource contention/tie tests |
| Project Details → Calculations | Activity Percent Complete Based on Activity Steps; link actual-to-date/actual-this-period settings | STEP-*, PERIOD-*, calculation toggles |
| Activity Details → Steps | step weight, Step % Complete, Completed flag, add/remove/reorder | STEP-*; partial/zero/unequal-weight tests |
| Project/WBS Details → Earned Value | performance-percent technique, ETC method, PF, baseline and date basis | EVM-* full method matrix |
| WBS → WBS Milestones | milestone weight/completion | EVM-MILESTONE weighted tests |
| Project → Baselines / Assign Baselines | create/assign/selected baseline identity | BASELINE-* and EV recomputation |
| Tools → Store Period Performance | selected financial period, actuals and period posting | PERIOD-* idempotency/reposting/history tests |
| Project → Expenses | budgeted units, price/unit, actual cost, accrual type, Auto Compute Actuals | EXP-*, COST-* |
| Activity Table/Grid → calculated columns | selected field, unit, formula/format and filter context | field provenance, parity and locale invariance |
| Activity Table → critical indicators/colors | critical definition/float threshold only | critical-flag tests; color must not alter result |
| Gantt → baseline/current bars and data-date line | current/baseline series selection, date scale, progress bars | GANTT-*; rendering uses authoritative results |
| Resource Usage/Assignments spreadsheet | timescale, resource filter, future-period buckets, resource/cost/EV series | SPREAD-*, demand/cost reconciliation |
| Global Change dialog | If/Then/Else, operator, fields, numeric/date/text operands | GC-* typed expression and preview tests |
| Import/Export / Excel/MS Project-like mappings | date/units/cost fields, relationships, calendar/baseline mapping | IMPORT-*, roundtrip and no-loss tests |
| Report/A4/print/export builder | field selections, date/baseline/data-date, grouping/rollup options | REPORT-*, field source and rollup parity |
| AI assistant action/tool controls | project create/read/write permission, scheduling action, calculation API, output/report action | AI-*, permission boundary and shared-engine test |

### Icon-by-icon completion checklist

For every concrete control discovered in web and desktop source:
- [ ] stable control/action ID;
- [ ] route/screen/menu path and icon asset name;
- [ ] accessible label/tooltip in all supported languages;
- [ ] exact domain/API action and user-selectable options;
- [ ] contract IDs and input invalidation list;
- [ ] authorization and AI-assistant permission behavior;
- [ ] focused UI/domain/regression test IDs;
- [ ] owner, review evidence and final commit SHA.

No checkbox may be marked complete from inference or screenshots alone. Confirm the actual source component, behavior, API invocation and test. The registry owner must report total controls discovered, controls mapped, controls tested and unmapped count.

## 28. Expanded official source index

- [Version 26 Global Change index](https://docs.oracle.com/cd/G48902_01/client_help/en_US/globalchange.htm)
- [Operators and valid calculations](https://docs.oracle.com/cd/G48902_01/client_help/en_US/operators_and_valid_calculations.htm)
- [Use arithmetic with Global Change](https://docs.oracle.com/cd/G48902_01/client_help/en_US/use_arithmetic_with_global_change.htm)
- [Use date arithmetic](https://docs.oracle.com/cd/G48902_01/client_help/en_US/use_date_arithmetic.htm)
- [Activity steps](https://docs.oracle.com/cd/F51303_01/English/User_Guides/p6_pro_user/activity_steps.htm)
- [Add weights to steps](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/add_weights_to_steps.htm)
- [ActivityStep API endpoints, Release 26](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/api-activitystep.html)
- [Leveling priority definitions, Version 26](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_priority_definitions.htm)
- [Specify leveling priorities, Version 26](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/specify_leveling_priorities.htm)
