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

| ID | Duration type | When Units change | When Duration changes | When Units/Time changes | Add first resource with no budgeted/planned units | Add additional resource(s) |
|---|---|---|---|---|---|---|
| DUR-FUT | Fixed Units/Time | Duration changes | Units change | Duration changes | Units change | Duration changes |
| DUR-FDUT | Fixed Duration & Units/Time | Units/Time changes | Units change | Units change | Units change | Units change |
| DUR-FU | Fixed Units | Duration changes | Units/Time changes | Duration changes | Units change | Duration changes |
| DUR-FDU | Fixed Duration & Units | Units/Time changes | Units/Time changes | Units change | Units change | Units/Time of each resource changes |

This is the full Version 26 synchronization table, including resource-addition behavior—not an optional test note. Apply the rule at the supported activity/assignment calculation boundary and preserve resource-type/calendar unit conversions. Start/Finish Milestones disable the duration-type setting.

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
| SCH-EXPECTED-FINISH | Use Expected Finish Dates | The Version 26 General Schedule Options help documents this option as checked by default. Use Expected Finish as the scheduled finish only when this option is active. |
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
- Overload(r,t) = max(0, Demand(r,t) − CapacityAllowedBySelectedLevelingMode(r,t)).
- IMPORTANT REFERENCE SEMANTICS: “Max Percent to Overallocate Resources” is not a blanket capacity multiplier for every resource and period. The documented leveling option increases resource availability only if resource assignments cannot be leveled after the activity-float limit has been used. Model that conditional fallback explicitly, log where it was invoked, and preserve the original base capacity as a separate value.
- CUBI must separately expose (a) base-calendar capacity, (b) the selected leveling mode’s permitted capacity allowance/fallback, and (c) actual final demand. Where a CUBI safety policy requires zero overload, it must say whether that means zero against base capacity or zero against the explicitly selected effective allowance. Never silently change between those meanings.
- If a user-selected overload allowance is applied, report the exact resource, period, base capacity, added allowance, final demand and remaining/excess margin. A schedule that still violates its selected allowed-capacity rule is not successful.

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

- BAC Cost = Budgeted/Planned Labor Cost + Budgeted/Planned Nonlabor Cost + Budgeted/Planned Material Cost + Budgeted/Planned Expense Cost from the selected baseline.
- EV Cost = BAC Cost × Performance % Complete, where Performance % Complete is selected by the WBS earned-value technique. Represent percentages as a fraction in the calculation core (for example, 50% = 0.5), not as 50. Apply the resource-curve/manual-future-period override conditions in Section 13.2 and Section 36 before assuming a straight-line activity percentage controls assignment-level EV.
- PV Cost for an individual resource assignment = assignment BAC × (Current Project Data Date − Baseline Assignment Start Date) ÷ (Baseline Assignment Finish Date − Baseline Assignment Start Date), under the selected reference date/calendar semantics. Sum assignment-level PV Cost to the activity. If an assignment has manually defined future-period buckets, use those manual values to calculate PV.
- PV Cost for an activity without resources = activity BAC × Schedule % Complete. The documented Schedule % Complete form is 0% when Data Date is before baseline start, 100% after baseline finish, and between those dates uses (Data Date − Baseline Start) ÷ (Planned Finish − Baseline Start). Treat equal/zero date span and calendar-boundary behavior as parity fixtures; never divide by zero.
- AC Cost = Actual Labor Cost + Actual Nonlabor Cost + Actual Material Cost + Actual Expense Cost for the selected scope and date basis; the activity/assignment source fields remain separately auditable.
- ETC Cost = Remaining Total Cost for the activity, or PF × (BAC Cost − EV Cost), according to the WBS ETC method.
- EAC Cost = AC Cost + ETC Cost.
- CV Cost = EV Cost − AC Cost.
- SV Cost = EV Cost − PV Cost. This is cost-valued schedule variance, not time duration.
- CPI Cost = EV Cost ÷ AC Cost.
- SPI Cost = EV Cost ÷ PV Cost.
- TCPI against BAC Cost = (BAC Cost − EV Cost) ÷ (BAC Cost − AC Cost).
- TCPI against EAC Cost = (BAC Cost − EV Cost) ÷ (EAC Cost − AC Cost).
- VAC Cost = BAC Cost − EAC Cost.
- Unit-based EVM is a separate field family: EV Labor Units = Baseline Planned Labor Units × Performance % Complete where the selected method applies; ETC Labor Units is Remaining Total Units or the selected PF × (Baseline Planned Labor Units − EV Labor Units); EAC Labor Units = Actual Labor Units + ETC Labor Units; VAC Labor Units = Baseline Planned Labor Units − EAC Labor Units; TCPI Units uses the same BAC/EAC formulas with the unit-valued BAC, EV, AC and EAC fields. Never substitute cost values for units or vice versa.

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


## 29. Exhaustive source-coverage rule: calculation-related official guide scope

This section was added after a full pass over the current Version 26 User Guide table of contents and the official Help navigation for the areas that can affect schedule dates, calendar arithmetic, progress, resource units/cost, earned value, budget/time-phased outputs and calculated reporting. The guide contains many pages about access, layout appearance and administration that do not define calculation semantics; they are not silently treated as formulas. The engineering team must still map actual CUBI controls to this domain.

The source topics below are in scope and must not be skipped simply because a feature is exposed through a menu rather than a formula field:

1. **Administration and user calculation preferences:** global/per-calendar hours per time period; time units and display precision; currency/view currency; default rate types; default price/unit; EVM defaults; overtime factor synchronization; assignment staffing price source; resource calculation options; fiscal-year start month where period reporting is used.
2. **Project definition and defaults:** project planned start, forecast start, planned finish, Must Finish By/finish anchor where supported, Data Date, default calendar, default activity type, duration type, percent complete type, default cost account/rate type, project leveling priority, baseline for current schedule comparison, summarization and earned-value roles.
3. **Activity fields and user selections:** Activity Type; Duration Type; Percent Complete Type; activity calendar; Original/Planned/Remaining/Actual duration; Start/Finish vs Early/Late/Remaining dates; actual start/finish/status; expected finish; suspend/resume; constraints; primary/secondary resource; WBS/cost account; all four relationship types; signed lag and lag calendar; assignment rate type/rate source/cost-unit links; steps and step weights; time-phased buckets; baseline-associated values.
4. **Calendar definition and assignment:** global/project/shared resource/personal resource calendars; default global calendar; calendar Used By assignments; work/nonwork days; weekly working hours and daily segments; exceptions; default Hours per Time Period; activity/resource calendar assignment; calendar replacement when deleting an in-use calendar; calendar edits that affect manual future-period assignment values.
5. **Schedule command and options:** chosen options source project for multi-project scheduling; current Data Date; whether all open projects use own Data Date or the selected date; optional “set Data Date and Project Planned Start to Project Forecast Start” behavior; output log; multiple-project warnings; General and Advanced tabs; every selection enumerated in Sections 9, 30 and 31.
6. **Progress/update commands:** Update Progress for selected/spotlighted activities; Apply Actuals; new Data Date; own project dates vs shared date; schedule forecast/progress; Started/Finished flags; remaining duration; actual duration and units; automatic actual computation; progress removal; suspend/resume; timesheet-derived actuals; manual future bucket side effects; rescheduling after update.
7. **Level Resources:** level selected/all resources; automatically level during scheduling; project-resource priority filter; activity-priority sequence and sort order; only within Total Float; preserve minimum float; Max Percent to Overallocate fallback; driving vs non-driving assignments; WBS summary treatment; resource shifts behavior according to the supported deployment; recalculation of costs after leveling; leveling report.
8. **Cost and units:** Calculate Costs from Units; cost/units linked flags; assignment rate type and rate source Resource/Role/Override; multiple rates over time; default price/unit; cost/units synchronization under activity duration types; Add Actual to Remaining / Subtract Actual from At Completion; Reset Planned/Original duration and units to Remaining / Reset Remaining to Planned/Original; auto compute actuals; actuals and period values; expenses/accrual; cost-account rollup; labor/nonlabor/material/expense totals.
9. **Curves and manual period spread:** assign/remove curve; curve distribution; planned and actual time-phased spread; remaining distribution; manual future-period bucket planning; settings that change how actuals/remaining units derive from planned vs remaining spread; the effect of calendar edits, status changes, schedule changes, and EVM.
10. **Baseline/EVM:** create/copy/assign/update/modify baseline; separate baselines for earned value, summary and comparison; current/planned date basis; activity/WBS percent technique; WBS milestone weights; ETC/PF method; BAC/EV/PV/AC/CV/SV/CPI/SPI/EAC/TCPI; using curves/buckets for earned value; stored period data and historical-period corrections.
11. **Calculation-adjacent reports/diagnostics:** Check Schedule Report tests, thresholds for long lags/large float/large duration, open-ended and relationship diagnostics, closed/missing external project links, missing baseline activities, scheduling/leveling logs, critical path, multiple float paths, Gantt progress line/data-date line, resource/usage profile and spreadsheet units.
12. **Calculated views and persistence boundaries:** Activity Table calculated columns and formulas, Gantt bar labels/geometry, Activity Network and Trace Logic, Usage/Profile/Spreadsheet time-phased data, Tracking Project Tables/Bar Charts/Gantt/Profile, group/sort/filter/summarize, publish/export/import and any AI/desktop output. Presentation settings may change rendering only; they cannot independently calculate dates, float, units, cost or progress.

A page listed in this section may contain one or more explicit options, field definitions, note paragraphs or edge-case rules. Implementation owners must read the relevant page, not merely cite the navigation title.

## 30. Calendar arithmetic, hours/time-period conversion and display units

### 30.1 Canonical storage versus display

**DOCUMENTED:** the reference application stores time-unit values in hourly increments. Users may display/enter durations and units in hours, days, weeks, months or years. The Hours per Time Period conversion factors convert non-hour values to hours for storage, and stored hours back to display units.

Two different calculation settings must not be confused:
- **Global hours-per-period mode:** uses the administrative/application Hours per Time Period values even if the assigned calendar works a different number of hours per day.
- **Assigned-calendar mode:** uses the Hour per Time Period values from the activity/resource's assigned calendar.

Example explicitly described in the guide: with display unit = day, global factor = 8 h/day, calendar work = 10 h/day, and stored duration = 30 hours, the global conversion display is 3 days 6 hours, while calendar conversion is 3 days. This distinction is a conversion/display configuration, not permission to alter the actual 30 hours of work.

### 30.2 Conversion contract

For a defined display period q with conversion factor H(q) hours per period:

- Convert entered amount x periods to canonical hours: Hours = x × H(q).
- Convert canonical hours h to display amount: DisplayUnits = h ÷ H(q), subject to the selected formatting/precision rules.
- For calendar-aware duration and working-time advancement, separately calculate actual working intervals from the assigned calendar. Do not use hours-per-period display conversion as a substitute for iterating real work periods.
- If global Hours per Time Period differs from assigned calendar work hours, show the selected conversion source and avoid presenting the display count as actual working-day count without explanation.
- Per the guide, calendar work-hour decimals other than 0.0 or 0.5 round up/down to 0.0 or 0.5 in that calendar UI. The CUBI compatibility layer must parity-test this field-entry/normalization rule and not spread it silently to every internal decimal calculation.

### 30.3 Calendar operations and edit effects

The compatibility inventory must include calendar type (global/project/shared resource/personal resource), assignment, inherited/linked relationship, workday/nonworkday, day segments, exceptions, calendar used-by and deletion/replacement workflow. Deleting an in-use calendar cannot silently orphan references; the selected replacement/link-to-default behavior must be explicit and audited. Calendar changes can change working-time distribution, duration conversions and manual future-period bucket values; invalidate and recompute affected values with the calendar ID/version recorded.

### 30.4 Required calendar fixtures

Use a golden fixture for each of: calendar-specific 8/10/12-hour days; global versus per-calendar conversion; split day shifts; midnight-crossing shifts if supported by the model; Friday/Saturday or other nonstandard workweek; holiday/exception as work and as nonwork; fractional hour rounding; month/year display conversion; mixed activity/resource/lag calendars; calendar inheritance/change; deleting/replacing a used calendar; manually planned future bucket after calendar change; Jalali/Gregorian display invariance.

**Sources:** [Hours per Time Period — User Guide v26](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/defining_default_hours_per_time_period_in_calendars.htm); [Time Periods tab — Admin Preferences v26](https://docs.oracle.com/cd/G48902_01/client_help/en_US/time_periods_tab_-_admin_preferences_dialog_box.htm); [Edit a project calendar](https://docs.oracle.com/cd/F37128_01/English/User_Guides/p6_pro_user/edit_a_project_calendar.htm); [Edit a resource calendar](https://docs.oracle.com/cd/F51303_01/client_help/en_US/edit_a_resource_calendar.htm).

## 31. Full schedule command input/output contract

The Tools → Schedule action is itself a calculation contract. Before invoking the engine, collect and persist:

- selected project(s);
- source of schedule options when multiple projects are open;
- each project's current Data Date, or the explicit choice to apply one selected Data Date to all open projects;
- whether scheduling will first set Data Date and Project Planned Start to each project's Forecast Start;
- every General and Advanced option from Section 9;
- any selected default values restored from the Default action;
- whether to generate a scheduling log and its output target;
- acknowledgement/cancel state for warnings about different project Data Dates or “Opened projects” float/end-date mode.

Output must return an immutable calculation ID, the project/option snapshot, scheduled start/finish/early/late/remaining dates, total/free/start/finish float, critical flags, multiple path IDs/order, constraint/relationship diagnostics, project scheduled finish and summary resource/cost outputs. A log file is evidence output—not a substitute for typed machine-readable diagnostics.

### 31.1 Multi-project schedule semantics

- “All projects use their own Data Date” must use each project’s selected date.
- “Apply selected Data Date to all open projects” intentionally changes calculation input; record that choice and the resulting dates.
- Under “Calculate float based on end date of Each project,” backward pass/open-ended activities use each project finish date, including external relationships.
- Under “Opened projects,” the latest finish date across all opened projects governs backward dates for open-ended/external-linked activities and can yield more float; each project's Scheduled Finish field uses that latest finish date.
- “Use scheduling options from” determines which project settings to use when multiple projects are open. CUBI must not mix settings from different projects unintentionally.
- WBS Summary activity relationships are ignored during schedule calculation even where activity relationships between projects are otherwise maintained, as documented.
- Canceling a warning must not silently proceed with a different configuration.

**Sources:** [Schedule a project — v26](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/schedule_a_project.htm); [General Schedule Options](https://docs.oracle.com/cd/G48902_01/client_help/en_US/general_tab_-_schedule_options_dialog_box.htm); [Schedule Options dialog](https://docs.oracle.com/cd/G48902_01/client_help/en_US/schedule_options_dialog_box.htm).

## 32. Exact Project Details → Calculations tab behavior

These settings interact with units, costs, status changes, baselines, remaining work and time-phased values. They must be separate options, individually testable; do not collapse them into one generic “autocalculate” switch.

### 32.1 Activity settings

**Default Price/Unit for activities without resource/role prices**
- Used for activities with labor/nonlabor units but no assigned resources/roles, or assignments with no price, according to this project default.
- The entry has a price and a time unit. Changing the default is not an automatic recalculation of every existing assignment; the explicit recalculation action and project option rules apply.
- A resource assignment whose rate type is not defined can fall back to this value according to the guide; the UI should identify the fallback source.

**Activity percent complete based on activity steps**
- When enabled, an activity using Physical percent-complete type derives its Physical % Complete from weighted steps; see Section 23. It does not replace Duration/Units type behavior.

**Link Planned or Budget and At Completion for not-started activities**
- When enabled, for Not Started activities, Budgeted/Planned, Remaining and At Completion values are linked/equal according to the guide; future-period planned and Remaining (Early) units fields for the assignment stay equal in aggregate and paired period edits can mirror one another.
- When disabled, planned/budgeted values are retained as the original plan while Remaining or At Completion values can diverge; future-period budgeted/planned and Remaining (Early) bucket distributions may be entered and calculated independently.
- When a Not Started activity already has Actual Costs, Planned Cost and At Completion Cost remain unlinked regardless of this option.
- Changing a task from Started to Not Started or changing this option from unlinked to linked interacts with “Reset Planned or Original Duration and Units to Remaining.” Do not treat the checkbox as a simple equal-fields UI rule; recalculate as documented.

**Reset Planned or Original Duration and Units to Remaining**
- Recalculate Planned duration and dates from At Completion duration and Remaining dates, and Planned units from At Completion units for activity and assignments.
- If there are no actual costs, Planned Cost, At Completion Cost and ETC become equal.

**Reset Remaining Duration and Units to Planned or Original**
- Recalculate At Completion duration and Remaining dates from Planned duration and dates, and At Completion units from Planned units.
- If there are no actual costs, Planned Cost, At Completion Cost and ETC become equal.

These reset choices are discrete operations. Record prior inputs/outputs and the specific choice; do not run both or silently infer one from activity status.

### 32.2 Resource assignment settings

**When Updating Actual Units or Cost → Add Actual to Remaining**
- At Completion Units/Cost = Actual Units/Cost + Remaining Units/Cost.
- This is a common true-at-completion mode (for example, cost-plus work).

**When Updating Actual Units or Cost → Subtract Actual from At Completion**
- Remaining Units/Cost = At Completion Units/Cost − Actual Units/Cost.
- This tracks remaining budget under a fixed-price/fixed-budget model.
- Documented exception: Fixed Duration & Units/Time always uses Add Actual to Remaining regardless of this Add/Subtract setting, because subtract mode would require changing duration or units/time and contradict fixed-duration/fixed-units-time semantics.

**Recalculate Actual Units and Cost when Duration % Complete changes**
- When enabled and Duration % Complete is edited, Actual Units/Cost = Budgeted/Planned Units/Cost × Duration % Complete.
- Without resource assignment, activity budgeted/planned units/costs are used.
- An explicitly entered value overrides the auto-calculated value.
- Costs use this rule only when the resource detail option Calculate costs from units is enabled.
- This rule recalculates actuals only for Fixed Duration & Units/Time and Fixed Duration & Units duration types; it calculates actuals when Duration % Complete changes, but does not reverse-calculate Duration % Complete from actual unit/cost changes.
- With a resource curve, Actual Units/Cost = curve-area percentage at Duration % Complete × Budgeted/Planned Units/Cost, then roll up to the activity.
- Manual future period planning changes whether actuals are distributed from the manual Remaining or Planned/Budgeted distribution depending on which fields are edited; see Section 36.

**Update units when costs change on resource assignments**
- Enables recalculation of units when assignment cost changes, such as remaining cost. It depends on Calculate Costs from Units/assignment settings. Cost-to-unit conversions must use selected rate and units/time semantics; do not apply where the guide disables synchronization for Fixed Units/Fixed Units-Time.

**Link actual to date and actual this period units and costs**
- When enabled, edits to either value recalculate the other according to the linked period/actual model.
- This setting is required for Store Period Performance and editing past period actuals.
- Save period, activity/assignment and before/after values with an audit trail.

**Sources:** [Calculations tab — Project Details v26](https://docs.oracle.com/cd/G48902_01/client_help/en_US/calculations_tab_-_project_details.htm); [Recalculate resource and role assignment costs](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/recalculate_resource_and_role_assignment_costs.htm).

## 33. Progress commands, Progress Spotlight and Apply Actuals

Activity progress is an input workflow with explicit date and assignment updates; it is not equivalent to running CPM or editing one percentage field.

### 33.1 Tools → Update Progress / Progress Spotlight

- Progress Spotlight identifies activities expected to start/progress/finish between the previous Data Date and the new date, using the smallest interval of the displayed Gantt timescale unless the user adjusts the Data Date line.
- If multiple projects are open, the default project's Data Date is used as the start of the highlighted period.
- Spotlight selection is persistent independently of row selection.
- When the data-date line is dragged or Progress Spotlight is enabled, automatic scheduling is turned off. The user must complete the update and then schedule again; CUBI must make unscheduled/stale values explicit.
- Update Progress chooses whether to update all spotlighted activities or just selected activities and specifies the new Data Date. Do not silently update activities outside the selected set.

### 33.2 Documented Apply Actuals / Update Progress calculations

The official Update Progress dialog describes the following operations when estimating progress for activities that should have occurred by the new Data Date:

- If Project Planned Start is before the new Data Date, set Actual Start to Project Planned Start.
- Remaining Duration = Early Finish − New Data Date, under the scheduler’s appropriate time/calendar semantics.
- Actual Duration = Original Duration − Remaining Duration.
- Actual Units = Units % Complete × At Completion Units.
- If Planned Finish is before the new Data Date, set Actual Finish to Planned Finish.
- Update Current Data Date to the selected New Data Date after applying.

These formulas describe the auto-progress workflow; they do not overwrite timesheet/report actuals or manually controlled actual fields unless the selected application mode calls for it. Test exact boundaries when dates equal the Data Date, activities should not have started, activities progressed out of sequence, remaining duration below zero, calendar exceptions and activities with manually planned buckets.

### 33.3 Timesheets and remaining-duration policy

When actuals are applied from timesheets, a user can choose to recalculate remaining duration based on activity duration type or always recalculate it. “Always” treats activities as Fixed Units and Fixed Units/Time. This is a calculation mode and must be captured in snapshot/audit. Unapproved timesheet handling and permission to Apply Actuals are workflow preconditions; they must not be bypassed in the assistant.

### 33.4 Manual progress versus automatic estimate

Support the documented flows to update all activities, individually selected activities, spotlighted activities or an entire project; update/remove progress; suspend/resume; set Started/Finished status; change remaining duration/units or Expected Finish; and then recalculate. Show separately what the user entered, what was automatically estimated, what was applied from timesheets and what CPM recalculated afterward.

**Sources:** [Update Progress dialog box v26](https://docs.oracle.com/cd/G48902_01/client_help/en_US/update_progress_dialog_box.htm); [Apply Actuals dialog box v26](https://docs.oracle.com/cd/G48902_01/client_help/en_US/apply_actuals_dialog_box.htm); [Update progress for the project](https://docs.oracle.com/cd/G48902_01/client_help/en_US/update_progress_for_the_project.htm); [Highlight activities for updating](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/highlight_activities_for_updating.htm); [Updating progress](https://docs.oracle.com/cd/G48902_01/client_help/en_US/updating_progress.htm).

## 34. Resource/role rate source, price calculations and resource details

The assignment’s calculation is determined by multiple independent fields. Do not make Rate Type, Rate Source, Cost Units Linked, Calculate Costs from Units and project default price/unit into one setting.

### 34.1 Rate Type and Rate Source

- **Rate Type:** selects which named price/unit is used from rate table/assignment settings.
- **Rate Source = Resource:** use the resource’s selected rate type.
- **Rate Source = Role:** use the role’s selected rate type.
- **Rate Source = Override:** use custom price/unit entered for the assignment; the recalculation utility must not overwrite it.
- If resource and role share an assignment, follow the explicit rate source or the user-preference behavior (always resource, always role, or prompt on assignment). If only a resource exists, the rate source cannot be Role; if only a role exists, it cannot be Resource.
- A missing selected price/unit can invoke the documented project default price/unit for activities without resource/role prices. Record that fallback in the output.
- Recalculate Assignment Costs updates assignments across open projects under the documented permission and selection rules. It can synchronize the overtime factor if selected, ignores Rate Source = Override, and requires Link actual to date/Actual This Period according to the official guide.
- Schedule Options can request cost recalculation after scheduling. Level Resources can separately request cost recalculation after leveling. These trigger points are not interchangeable.
- When the rate type changes and units/costs are linked, the selected rate can recalculate cost. If Activity Duration Type is Fixed Units or Fixed Units/Time, units are not recalculated merely because cost changes.

### 34.2 Time-varying rates

For each work segment s where the chosen rate applies:
- Segment Cost(s) = Segment Units(s) × Price per Unit(s).
- Assignment Cost = Σ Segment Cost(s) across all applicable effective periods/rate changes under the chosen rate type and source.
- Example in the official guide: 16 hours at $10/hour = $160; subsequent 8 hours at $30/hour = $240; total = $400.
- When dates change, recalculate the rate segments if the relevant option/action is selected.
- The guide notes special handling for resource shifts that use timesheets and notes that multiple rates are not reflected in Activity Usage/Resource Usage Spreadsheets. If CUBI displays cost spreading in those views, document and test exactly which aggregate it represents rather than assuming it equals a segment-rate calculation.
- Price rate tables by effective date, currencies and rounding require separate fixtures.

### 34.3 Resource and role availability

Resource/role data includes max units/time, price/unit rates over time, effective dates, resource shifts, shared/personal calendar, primary resource designation and resource/role assignments. Role limits over time are not the same as calendar hours and not the same as current assignment demand. Availability must be checked over the correct work periods and selected project scope.

### 34.4 Resource shifts and environment-specific behavior

The Version 26 guide describes resource shifts as 24-hour definitions composed of segments with start times on the hour and a minimum segment duration of one hour. In the documented P6 Professional database context, leveling does not consider shifts in one mode, while another documented behavior uses shifts to calculate units/prices during leveling and uses calendar to determine workability; the exact product/database deployment matters. Therefore, CUBI must not make a universal claim about shift-based leveling without matching the selected reference deployment. Put deployment profile/version into compatibility fixtures, and make shift support/status explicit.

### 34.5 Non-driving resource assignment leveling

The reference guide distinguishes driving and non-driving assignments:
- For Task Dependent activities with driving and non-driving assignments, all assigned resources must be available to place the activity.
- For Resource Dependent activities with both, driving resources drive the activity dates; non-driving resources are leveled on/after those dates.
- For Resource Dependent activities with only non-driving assignments, those assignments may be placed any time after the earliest possible activity start.
- If driving resources can be placed but non-driving resources cannot, non-driving assignment dates may be delayed based on driving placement and a failure is recorded in leveling report.
- WBS Summary activities are ignored during leveling.
- A suspended-activity resource is considered available for other assignments until the resume date per the Level Resources guide.

These are mandatory activity-type/assignment-level parity cases. “No overload at activity dates” cannot be simplified to one boolean for the entire multi-resource assignment.

**Sources:** [Rate Type](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/assign_a_rate_type_to_a_resource_assignment.htm); [Rate Source](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/choose_the_rate_source_for_an_assignment.htm); [Multiple resource rates](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/calculating_cost_when_using_multiple_resource_rates.htm); [Resource shifts](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/define_resource_shifts.htm); [Leveling by activity type — Version 26 Help](https://docs.oracle.com/cd/G48902_01/client_help/en_US/leveling_resources_on_task_resource_dependent_wbs_activities.htm); [Recalculate assignment costs](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/recalculate_resource_and_role_assignment_costs.htm).

## 35. Complete Resource Leveling command options and edge cases

The Tools → Level Resources dialog must model these options independently:
- Consider assignments in other projects with priority equal/higher than threshold.
- Preserve Scheduled Early and Late Dates.
- Level All Resources or choose a subset via Select Resources.
- Ordered leveling priorities and sort direction.
- Level Resources Only Within Activity Total Float.
- Preserve Minimum Float When Leveling.
- Max Percent to Overallocate Resources.
- Automatically Level Resources When Scheduling.
- Recalculate Assignment Costs After Leveling where available.
- Log leveling results to file.
- Restore defaults.
- The selected project's leveling options when multiple projects are open.

### 35.1 Exact float-limit and over-allocation meaning

“Level Resources Only Within Activity Total Float” limits delayed activities to their late dates (Late Finish when the finish-float basis is used, or Late Start when the start-float basis is used). “Preserve Minimum Float When Leveling” defines the minimum retained total float. “Max Percent to Overallocate Resources” defines a maximum increase in resource availability and is used only if the assignments cannot be leveled after their activity float limit is used. This percentage cannot be blindly applied to every date or act as a normal allowance independent of float constraints.

### 35.2 Priority vocabulary and order

Support the complete orderable field vocabulary: Activity ID; Activity Priority; Early Finish; Early Start; Free Float; Late Finish; Late Start; Original/Planned Duration; Planned Finish; Project Planned Start; Project Priority; Remaining Duration; Total Float. Sort direction and the order of the priority list matter: a first-priority field wins before lower-priority fields. The guide documents number-before-alpha ordering for codes and Activity ID ordering when there are no priority codes. Keep tie-breaks deterministic and separately test blanks/values.

### 35.3 Special assignment behavior

The Level Resources report must identify each resource assignment that could not be leveled even if other driving assignments of that activity succeeded. Preserve distinct assignment dates when non-driving resource assignments can be placed later than activity dates. Do not force all resource assignment dates to equal the activity dates if resource-dependent reference behavior allows independent non-driving assignments.

### 35.4 Final validation

The final output validator must inspect the accepted scheduled graph, all assignment-level effective dates, all time-phased demands/capacity periods, the selected allowance policy, and any failed assignment record. It must not validate only the proposal ledger or only resource/date totals. An infeasible result must identify the resource, bucket, demand, base capacity, allowed capacity policy, activities/assignments and blocking constraints/relations.

**Sources:** [Level Resources v26 Help](https://docs.oracle.com/cd/G48902_01/client_help/en_US/levelingresources.htm); [Limit resource leveling](https://docs.oracle.com/cd/F25600_01/client_help/en_US/limit_resource_leveling.htm); [Level selected resources](https://docs.oracle.com/cd/G48902_01/client_help/en_US/level_selected_resources.htm); [Level resources automatically](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/level_resources_automatically_2.htm); [Leveling special activity types](https://docs.oracle.com/cd/F74771_01/client_help/en_US/leveling_resources_on_task_resource_dependent_wbs_activities.htm).

## 36. Resource curves, future-period buckets and Earned Value interaction

Curves and manually entered future-period buckets are independent inputs to the assignment time-phasing model and can change actual units/costs and Earned Value. Keep all of these distinctions:

- Without a curve or manually entered buckets, budgeted/planned assignment units are spread evenly over the activity duration in the selected timescale. A resource/cost distribution curve changes this to a nonlinear spread.
- Version 26 documents 21 points on a resource curve. The public page does not define every interpolation/bucket-boundary tie rule, so preserve reference fixtures instead of inventing an interpolation formula.
- Curves may be assigned only for Fixed Duration & Units/Time and Fixed Duration & Units activities. Resource lag is considered; the curve starts at the lagged start date.
- If timesheet data exists for actuals, curves are ignored for actual values and timesheet data is used; remaining units continue to use the curve.
- Curves do not support expenses; expense Accrual Type continues to control their spread. Curves are reflected in Resource Usage Profile and Resource Usage Spreadsheet.
- If Actual Units/Cost is computed from Duration % Complete and a curve applies, actuals are the corresponding curve-area percentage × planned/budgeted assignment units/cost, not a simple linear Duration % Complete × full budget.
- When applying actuals with manually planned buckets, the source of the distribution depends on what was edited: Duration % Complete/Remaining Duration, Remaining Units/Remaining Early Finish, or Actual Units. Different cases can use Remaining distribution, planned/budgeted distribution, or not modify planned/remaining bucket values.
- If the option Link Planned/Budget and At Completion is enabled for a Not Started assignment, planned/budgeted units and Remaining (Early) units bucket values remain linked/equal per the guide. If disabled, those totals can be independent. In-progress assignments may enter different planned versus remaining future-period values.
- Calendar edits can change values in manual future-period buckets. Recompute and preserve audit history.
- **EVM curve/bucket conditions:** the guide says curves/manual future-period buckets are used when Activity % Complete Type is Units and the WBS Performance % Complete technique is Activity % Complete; or when the WBS option “Use resource curves/future period buckets” is checked with Activity % Complete technique. For ETC to spread using a curve, ETC = Remaining Cost for Activity must be selected.
- The EVM user must be able to select the WBS method and see why curve/bucket behavior did or did not apply. Do not apply curves to every WBS technique automatically.

**Sources:** [EVM with resource curves/future buckets v26](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/calculating_earned_value_using_resource_curves_or_manual_future_period_buckets.htm); [Future period bucket planning](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/future_period_bucket_planning.htm); [Troubleshooting future buckets](https://docs.oracle.com/cd/G48902_01/client_help/en_US/48610.htm); [Project calculations settings](https://docs.oracle.com/cd/G48902_01/client_help/en_US/calculations_tab_-_project_details.htm).

## 37. Baseline selection, baseline values and historical period data

A “baseline” is not one generic record. Inventory and test these distinct decisions:
- create/copy/update/modify/delete baseline;
- choose the baseline used for current project comparison/display;
- choose the baseline used for summarization;
- choose the baseline used for earned value;
- choose user primary baseline vs project baseline policy;
- compare current schedule to baseline and select which baseline fields are shown;
- retain current actual and remaining values when creating/updating a baseline;
- handle an activity missing from the assigned baseline in reports;
- historical-period unit/cost actuals and corrections.

Baseline comparisons are calculated against a selected version and field mapping, not necessarily current schedule dates. Historical period values and current actual-to-date/actual-this-period are separate time series. Editing a past period must trigger the appropriate recalculation of EVM and reports and must leave an audit record.

Required test: same snapshot with two different baselines; planned-date versus current-date EV policy; project baseline versus primary baseline; baseline without one activity; update baseline on progressed activities; two fiscal calendars/period scopes; posting/reposting period; changing historic Actual This Period; restore/recalculate result replay.

**Sources:** [Baselines section in official User Guide v26](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm); [EVM baseline/date method](https://docs.oracle.com/cd/G48902_01/client_help/en_US/earned_value_tab_-_admin_preferences_dialog_box.htm); [Post period values](https://docs.oracle.com/cd/F51303_01/English/User_Guides/p6_pro_user/post_actual_amounts_for_a_period.htm); [Edit past period actuals](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/edit_past_period_actual_data.htm).

## 38. Activity/work-calendar defaults and project settings

Before scheduling a newly created/imported project or activity, resolve and persist all defaults that can affect calculations, including:
- project default activity type;
- project default activity duration type;
- project default percent-complete type;
- project default activity calendar;
- project default cost account and assignment rate type;
- global vs project vs resource calendar availability;
- project planned start, finish/date settings, Data Date, forecast start if present;
- project status and level priority;
- fiscal year starts and financial-period definitions when time-phased cost/EVM is in use;
- default price/unit and assignment cost/unit settings;
- chosen baseline roles and critical-activity definition.

Defaults apply at specific creation/import points; changing a default later must not silently rewrite existing activity fields unless the documented bulk-change action explicitly requests it. Test each default for: new activity, copy/paste, WBS template, import, duplicate project and changed default after existing activities already exist.

**Sources:** [Project Details/Defaults and settings in official P6 Help v26](https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm); [Project dates](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/enter_project_dates.htm); [Default activity/calendar/rate settings](https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm).

## 39. Check Schedule Report as a calculated diagnostic contract

Tools → Check Schedule Report is not a substitute for calculating the schedule, but its selected checks, thresholds and results are a required validation/reporting capability for the project scope. Support configurable thresholds for Long Lags, Large Float and Large Durations, select which checks run, and preserve the generated report's project IDs/names/Data Dates, total/completed activity counts, internal/external relationship counts, activities missing from the assigned baseline, and links to/from external projects that are closed when checked.

Every check result should expose the input threshold, activity/relationship identifiers, specific observed value, failed condition and source schedule calculation ID. The threshold/reporting filters must not alter the core scheduler's values or hide the diagnostic from the stored report. Include tests for mixed projects, external relationship endpoints closed, missing baseline activity, threshold boundaries exactly equal to target, and rerunning after a corrected schedule.

**Sources:** [Check a schedule v26](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/101251.htm); [Check Schedule threshold navigation](https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm).

## 40. Complete calculation menu/control coverage matrix — additions after TOC audit

This supplements Section 27. The engineering inventory must include these controls/options where present in CUBI, and explicitly mark a row “not implemented / planned” if a CUBI surface does not yet exist. Absence is not silently treated as “not calculation-relevant.”

| Official menu/window or control | Fields / options / calculations to inventory | Contract areas and required tests |
|---|---|---|
| Enterprise → Calendars; Global/Project/Resource tabs | create/edit/delete; calendar type; work week and exceptions; default global calendar; Used By; replacement/link-to-default on delete; Hours per Time Period | CAL-*; conversion and invalidation, roundtrip and reference fixture |
| Enterprise → Resource Shifts | shift segments; start-hour boundaries; 24-hour total; resource assignments; deployment-specific leveling effect | CAL-*, RES-*; exact version/deployment parity |
| Enterprise → Projects → Dates | Data Date; Project Planned Start; Planned Finish; Forecast Start; must-finish/finish anchor; project status | SCH-*, OOS-*; multi-project and forecast-start option |
| Enterprise → Projects → Defaults | default activity type, duration type, percent type, calendar, cost account, rate type, price/unit | ACT-*, DUR-*, PC-*, RES-*, COST-*; existing values not silently rewritten |
| Enterprise → Projects → Calculations | default price/unit; steps-based Physical%; link/unlink planned/at-completion; reset plan to remaining; reset remaining to plan; Add/Subtract actuals; automatic actuals; update units from costs; link actual period values | CALC-PROJECT-* and exact formula fixtures |
| Enterprise → Projects → Settings | baseline for EV; critical activity rule/threshold; other calculation defaults and fiscal start month | BASELINE-*, EVM-*, CRIT-*; baseline/threshold behavior |
| Admin Preferences → Time Periods | global conversion factors vs assigned-calendar hours; unit abbreviations; project/environment-specific behavior | CAL-HOURS-*; hours storage and display invariant |
| User Preferences → Time Units/Dates/Currency | display unit, date/time format, currency, rounding/display precision and decimal separators | FORMAT-*, locale invariance; no calculation differences from display |
| Admin Preferences → Earned Value | default performance-complete method, ETC technique/PF, baseline value/date basis | EVM-*; WBS override and denominator tests |
| Admin Preferences → Rate Types | rate type vocabulary and default names | RES-RATE-*; selected price/source |
| Project → Activities → General | activity type, duration type, percent complete type, calendar, WBS, responsible manager, primary resource, cost account | ACT-*, CAL-*, PC-*; defaults/calc invalidation |
| Activity Details → Status/Dates | Started/Finished state, actual dates, durations, Physical/Duration/Units %, expected finish, remaining dates, suspend/resume | PROGRESS-*, OOS-*, DATE-*; automatic/manual update matrix |
| Activity Details → Constraints | primary and secondary constraints, dates and allowed combinations | CON-*; conflicts/negative float |
| Activity Details → Predecessors/Successors/Relationships | project/WBS/activity IDs, relation type, lag/time unit, status and external endpoints; synchronization between tabs | REL-*; add/edit/remove and mixed calendars |
| Activity Details → Resources | resource/role assignment, primary resource, planned/actual/remaining units and cost, rate type/source, price/unit, cost units linked, calendar and manual bucket values | RES-*, RATE-*, DUR-*, COST-*; field-linked/unlinked tests |
| Activity Details → Steps / Step Templates | step %, completed checkbox, weight, templates copied/assigned | STEP-*; weighted sum and default weights |
| Tools → Schedule | selected projects/options source; own/shared Data Date; forecast-start mode; default/options; schedule log; warnings/cancel | SCH-*; reproducible input/output snapshot |
| Schedule Options → General | all fields from Section 9 plus explicit date/finish/critical float and lag calendar options | SCH-*; one-factor and interaction matrix |
| Schedule Options → Advanced | calculate multiple paths toggle, Total Float vs Free Float, endpoint default, number of paths, path/ordering fields | PATH-*; endpoint selection and path order |
| Tools → Level Resources | cross-project priority threshold; preserve Early/Late; all/selected resources; full priority list; within float; min float; max overallocate; automatic leveling; recalculate costs; log | LEVEL-*; assignment-level final validation |
| Tools → Recalculate Assignment Costs | scope of open projects; synchronize overtime factor; Rate Source Override behavior; security gating | COST-*, RATE-*; not overwriting Override |
| Tools → Apply Actuals / Update Progress | target projects; own/shared Data Date; timesheet remaining-duration policy; project planned start/finish auto-actuals; apply/cancel | PROGRESS-*; actual dates, duration, units and audit |
| View → Progress Spotlight / Gantt date line | timescale minimum increment; prior/new Data Date; highlighted set; schedule auto-toggle | PROGRESS-*; schedule stale/refresh state |
| Resource Usage Spreadsheet | period scale, budget/planned vs remaining/actual columns, manual future values, grouping/sort, project/resource scope | SPREAD-*, CURVE-*; total reconciliation and calendar change |
| Activity Usage Profile / Resource Usage Profile | regular/stacked histogram, series, filters, overtime/past periods, background lines | VIS-*; outputs derived from engine |
| Tools → Check Schedule Report | selected checks, targets, durations/thresholds, output location, baseline gaps and closed external links | CHECK-*; boundary values and report IDs |
| Project → Expenses | category, planned units/cost, actual cost, activity assignment, accrual (Start/End/Uniform), Auto Compute Actuals | EXP-*, COST-*; time spread/summary |
| WBS Details → Earned Value | local overrides to admin default, performance %, ETC/PF, curves/buckets, milestone weight | EVM-*; WBS-specific override |
| WBS Milestones | name, weight, complete status/date, total weight denominator | STEP-/EVM-MILESTONE-*; zero weight/unequal weights |
| Project → Baselines / Assign Baselines | project/primary/comparison/summarization/EVM baseline assignments, update/copy/modify | BASELINE-*; not changing source actuals |
| Tools → Store Period Performance | financial period selection; linking actual to date/this period; post/edit historical values | PERIOD-*; repeat/idempotent and audit |
| Activity Table / Gantt / Activity Network / Trace Logic | field columns, sort/group/filter, relationship connectors, drag-to-date/duration, critical indicators, progress line, collapse/summary bars | UI action registry; all edit paths use one domain engine |
| Global Change | condition, operator, typed arithmetic/date/text fields, Then/Else ordering, preview/report, multi-row mutation | GC-*; data type and work-period arithmetic |
| Import/export, copy/paste, dissolve, baseline import | date/duration units, relation types/lags, calendars, status/progress, rates/costs, bucket/baseline identity | IO-*; lossless roundtrip and invalid-import diagnostics |
| AI assistant tools | option selections, project scope, permissions, preview/apply, calculation API, reports, write-audit | AI-*; tool calls constrained to shared engine |

## 41. Activity field matrix: calculation dependencies and invalidation

For each activity and assignment field below, record type, unit, source-of-truth, editor, validation and dependency invalidation in the code inventory. Names may differ between CUBI and the reference UI, but semantics must not be merged.

| Field family | Examples | Required invalidation/recalculation |
|---|---|---|
| Identity/scope | project, activity ID, WBS ID, assignment ID, tenant/revision | references, graph indexes, rollups, cached snapshots |
| Activity type | task/resource dependent, LOE, start/finish milestone, WBS summary | date/duration behavior, valid fields, assignments, leveling eligibility |
| Duration model | original/planned/remaining/actual duration, duration type, units/time | dates, finish, floats, resource spread, cost when tied |
| Completion state | status, actual start/finish, physical/duration/units %, steps | actual/remaining fields, schedule progress mode, EV and time-phasing |
| Schedule dates | project planned start/finish, early/late, remaining dates, expected finish, suspend/resume, data date | CPM, constraints, float, status and period spreads |
| Relationship edge | endpoint, relationship type, lag amount/unit/calendar, external-project scope | connected graph forward/backward propagation and diagnostics |
| Constraint | type, date, primary/secondary status | CPM feasibility, late dates/float/critical status |
| Calendar | ID/version, time periods, exceptions, shifts | duration conversion, event dates, lag, demand, unit/cost spread |
| Assignment quantity | budgeted/planned/actual/remaining/at-completion units and unit type | units %, duration sync, cost, resource demand and EVM |
| Assignment cost | planned/actual/remaining/at-completion cost, price/unit, rate type/source, costs linked | cost totals, ETC/EAC, period series, reports |
| Capacity/availability | max units/time, calendar availability, period demand, project priority | leveling, overload, resource profile/report |
| Baseline/EVM | baseline ID/version, EV method/PF, BAC/PV/EV/AC/ETC/EAC/indices | all derived EVM and variance outputs |
| Financial period | period ID, Actual This Period/To Date, historical values and link setting | cumulative totals, EVM, cash flow and audit history |
| WBS summary | parent/child scope, milestone weights, local EVM override | summary dates/units/cost/progress/EVM |
| Presentation only | icon, color, label, language, date format, time unit label | never changes core calculation values |

## 42. Final source and coverage audit ledger

Use a tracked row per applicable official source topic from the current User Guide and Help. Minimum columns: guide edition, source page title and URL, feature/menu, option/field, exact documented rule, CUBI contract ID, current source file/function, current test file/ID, actual UI control/action ID, parity fixture/evidence, reviewer, status and SHA.

Permitted statuses: NOT REVIEWED; REVIEWED—DOCUMENTED; IMPLEMENTED—UNVERIFIED; TESTED—REFERENCE PARITY; OPEN—AMBIGUOUS; NOT IMPLEMENTED; NOT APPLICABLE WITH REASON. “Reviewed” does not mean implemented; “implemented” does not mean parity tested.

**No-omission acceptance gate:** compare the registry against every calculation-relevant node in the official Version 26 TOC/help tree and every actual web/desktop calculation-affecting control. Report counts of sources inspected, settings/fields enumerated, formulas captured, CUBI implementation sites mapped, test cases mapped, live controls found, controls mapped, controls tested and unresolved items. A zero missing count is permitted only after an independent source-tree and source-code scan. Until then, coverage remains OPEN even though this contract is mandatory.

## 43. Expanded source index for detailed option and formula pages

- [Version 26 full User Guide TOC](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm)
- [Version 26 full P6 Professional Help TOC](https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm)
- [Project Details Calculations tab](https://docs.oracle.com/cd/G48902_01/client_help/en_US/calculations_tab_-_project_details.htm)
- [Admin Preferences Time Periods tab](https://docs.oracle.com/cd/G48902_01/client_help/en_US/time_periods_tab_-_admin_preferences_dialog_box.htm)
- [Admin Preferences Earned Value tab](https://docs.oracle.com/cd/G48902_01/client_help/en_US/earned_value_tab_-_admin_preferences_dialog_box.htm)
- [Update Progress dialog](https://docs.oracle.com/cd/G48902_01/client_help/en_US/update_progress_dialog_box.htm)
- [Apply Actuals dialog](https://docs.oracle.com/cd/G48902_01/client_help/en_US/apply_actuals_dialog_box.htm)
- [Update progress for project](https://docs.oracle.com/cd/G48902_01/client_help/en_US/update_progress_for_the_project.htm)
- [Updating progress](https://docs.oracle.com/cd/G48902_01/client_help/en_US/updating_progress.htm)
- [Resource assignment cost synchronization](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/recalculate_resource_and_role_assignment_costs.htm)
- [Resource rate types](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/assign_a_rate_type_to_a_resource_assignment.htm)
- [Rate source](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/choose_the_rate_source_for_an_assignment.htm)
- [Resource cost across multiple time-varying rates](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/calculating_cost_when_using_multiple_resource_rates.htm)
- [Level Resources dialog and features](https://docs.oracle.com/cd/G48902_01/client_help/en_US/levelingresources.htm)
- [Limit resource leveling](https://docs.oracle.com/cd/F25600_01/client_help/en_US/limit_resource_leveling.htm)
- [Level selected resources](https://docs.oracle.com/cd/G48902_01/client_help/en_US/level_selected_resources.htm)
- [Level resources automatically](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/level_resources_automatically_2.htm)
- [Special leveling rules by activity type](https://docs.oracle.com/cd/F74771_01/client_help/en_US/leveling_resources_on_task_resource_dependent_wbs_activities.htm)
- [Check Schedule Report](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/101251.htm)
- [BAC definition](https://docs.oracle.com/cd/G48902_01/client_help/en_US/budget_at_completion.htm)
- [Earned Value Cost definition](https://docs.oracle.com/cd/G48902_01/client_help/en_US/earned_value_cost.htm)
- [Planned Value Cost definition and assignment/no-resource formulas](https://docs.oracle.com/cd/G48902_01/client_help/en_US/planned_value_cost.htm)
- [CPI definition](https://docs.oracle.com/cd/G48902_01/client_help/en_US/cost_performance_index.htm)
- [SPI definition](https://docs.oracle.com/cd/G48902_01/client_help/en_US/schedule_performance_index.htm)
- [ETC definition](https://docs.oracle.com/cd/G48902_01/client_help/en_US/estimate_to_complete.htm)
- [EAC definition](https://docs.oracle.com/cd/G48902_01/client_help/en_US/estimate_at_completion.htm)
- [PF definition](https://docs.oracle.com/cd/G48902_01/client_help/en_US/performance_factor_pf.htm)
- [TCPI formulas — official P6 guide](https://docs.oracle.com/cd/F88966_01/p6help/en/43948.htm)
- [Resource curves/future-bucket EVM](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/calculating_earned_value_using_resource_curves_or_manual_future_period_buckets.htm)



## 44. Budget log, spending plan, funding and variance formulas

These calculations are adjacent to schedule cost control and must be included when CUBI builds the project financial-control layer. Do not confuse project-budget variances with EVM Cost Variance or Schedule Variance.

| Field | Formula / source behavior |
|---|---|
| Original Budget | User-entered estimate of total project need, including funding contributions. |
| Approved Budget Changes | Sum of approved budget changes in the Budget Log. Keep pending/proposed changes distinct. |
| Current Budget | Original Budget + Approved Budget Changes. |
| Distributed Current Budget | Sum of current budget values distributed to the next level/control accounts as defined by the field. It is not a substitute for the total Current Budget. |
| Total Spending Plan | Sum of monthly/period spending plan values. |
| Total Spending Plan Tally | Sum of the period spending tally values. |
| Current Variance | Current Budget − Total Spending Plan. |
| Undistributed Current Variance | Total Spending Plan − Total Spending Plan Tally, at the corresponding project/period scope. |
| Benefit Variance | Benefit Plan Tally − Benefit Plan at the corresponding period scope. |
| Net Present Value (when the feature is supported) | Present Value of Total Benefit Plan − Present Value of Total Spending Plan; requires explicit discount rate, timescale and date basis. |

Budget changes, approval statuses, project/EPS scope and time-period/fiscal-calendar basis must be retained in the input snapshot. Current Budget is the approved baseline budget for this feature; it is not necessarily the same field as activity BAC or the selected earned-value baseline total cost. Spending plan values are manually time-phased financial projections and do not automatically equal EVM PV, cost ETC or cash actually spent.

Funding source assignments can be defined at different EPS/project levels, may include the same source multiple times with different amount/share contributions, and **do not automatically roll up** across EPS levels in the documented workflow. Total Funding is the sum of funding assigned to the selected project/EPS node. Do not calculate a parent’s fund by summing lower-level values unless the selected reference feature expressly does so.

Required tests: Original Budget only; approved and pending changes; current budget changes after approval; distributed versus undistributed values; monthly/period plan and tally totals; variance sign including negative variance; funding contribution amount/share and duplicate source entries; no implicit parent rollup; NPV zero discount/empty periods; and currency/date/fiscal-period settings.

**Sources:** [Compare budgets and variances](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/compare_budgets_and_variances.htm); [View budget and spending plan totals](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/view_budget_and_spending_plan_totals.htm); [Assign funding sources](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/assign_funding_sources.htm); [P6 Activity subject-area field definitions](https://docs.oracle.com/en/industries/construction-engineering/intelligence/subject-area-reference-guide/p6-activity-primaveraactivity.html).

## 45. Separate percent-complete, scheduled-percent, and remaining-float fields

The word “percent” does not identify one formula. Store field identity and computation type explicitly.

| Field | Formula / meaning | Guardrail |
|---|---|---|
| Physical % Complete | User-entered physical progress, or weighted activity-step value if the corresponding project option is enabled. | Not derived from duration or units unless the selected method specifies it. |
| Duration % Complete | (Original/Planned Duration − Remaining Duration) ÷ Original/Planned Duration. | Original duration is from the current plan under the documented field definition, not necessarily the baseline. Test zero duration, completed activity and precision/range. |
| Units % Complete | (Actual Labor Units + Actual Nonlabor Units) ÷ (Actual Labor Units + Actual Nonlabor Units + Remaining Labor Units + Remaining Nonlabor Units). | Does not silently add Material quantities to this particular Activity Units % Complete definition; material-unit/EVM metrics are separate. |
| Labor Units % Complete | Actual Labor Units ÷ At Completion Labor Units × 100, where the field is exposed. | Check denominator and link/actual settings. |
| Nonlabor Units % Complete | Actual Nonlabor Units ÷ At Completion Nonlabor Units × 100, where the field is exposed. | Check denominator and link/actual settings. |
| Schedule % Complete | Date-based progress implied by the selected plan/baseline at Data Date; the official activity subject-area formula provides (Data Date − Baseline Start) ÷ (Planned Finish − Baseline Start), with 0% before baseline start and 100% after baseline finish. | Not equivalent to Activity % Complete or Performance % Complete; precise calendar/date boundary behavior needs parity fixtures. |
| Performance % Complete | WBS-selected EVM method: activity percent, WBS milestone weights, 0/100, 50/50, custom percent or applicable curve/bucket method. | Only drives EV under the selected WBS method. |
| Remaining Float | Official subject-area definition: Late Finish − Remaining Finish. | Distinct from Total Float; use selected schedule dates/calendar semantics. |
| Total Float | The selected scheduler method: Late Start − Early Start; Late Finish − Early Finish; or the smaller of those values. | Retain component floats; do not clamp negative values. |

This matrix is a semantic separation contract. When a field appears with a different definition in a specific P6 interface/API/export schema, log the source and version as a compatibility case rather than silently mixing the two definitions.

**Sources:** [Activity percent-complete types v26](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/define_activity_percent_complete_types.htm); [Activity subject-area field definitions](https://docs.oracle.com/en/industries/construction-engineering/intelligence/subject-area-reference-guide/p6-activity-primaveraactivity.html); [P6 subject-area reference for resource assignments](https://docs.oracle.com/en/industries/construction-engineering/intelligence/subject-area-reference-guide/dimensions-resource-assignment.html); [Schedule Options v26](https://docs.oracle.com/cd/G48902_01/client_help/en_US/general_tab_-_schedule_options_dialog_box.htm).

## 46. Role limits, resource availability and resource-analysis outputs

Role limits over time and resource assignment leveling capacity are related but not identical concepts. Keep them separate in the model and user interface.

- Role limit entries use an effective date and Max Units/Time. Effective dates must be unique for each role; input values may be units or percentages depending on the user’s selected resource units/time preference and are converted to the user’s default display format.
- The reference guide says role limits help identify role overload in Resource/Role Usage Profiles and histograms. By default, calculated role limits can be based on the limits of each role’s primary resource. User preferences may instead consider only active resources or show custom role limits.
- Do not treat a role-limit histogram indicator as automatically equivalent to the resource-calendar capacity used by resource leveling. Identify the selected analysis mode and show which source supplies the capacity/limit.
- Resource limits, role limits, time-varying Max Units/Time, resource calendars, resource shifts, project priority and actual assignment demand must all be retained as separate facts. A chart color is only a visual overload indicator, not a recalculation.
- Resource Analysis dynamic leveling and “what-if” forecast outputs must be marked as scenarios/proposals until their selected schedule/leveling engine calculation is run and validated; they must not overwrite the authoritative baseline/current schedule without an explicit commit action.

**Sources:** [Define role limits over time v26](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/define_role_limits_over_time.htm); [Roles guide v26](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/roles.htm); [Level Resources v26](https://docs.oracle.com/cd/G48902_01/client_help/en_US/levelingresources.htm); [Project Gantt/Profile and Resource Analysis](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/profileandresourceanalysis.htm).

## 47. Cross-checks for the activity duration synchronization table

The duration-type table in Section 4 was rechecked against the full official Version 26 table, including both “add resource when no budgeted/planned units exist” and “add additional resources” columns. The required expected changes are:

| Duration Type | Edit Units | Edit Duration | Edit Units/Time | Add first resource when no planned units | Add additional resources |
|---|---|---|---|---|---|
| Fixed Units/Time | Duration | Units | Duration | Units | Duration |
| Fixed Duration & Units/Time | Units/Time | Units | Units | Units | Units |
| Fixed Units | Duration | Units/Time | Duration | Units | Duration |
| Fixed Duration & Units | Units/Time | Units/Time | Units | Units | Units/Time of each resource |

No caller may override this matrix ad hoc in a view, import/export path or AI tool. Every cell in the matrix needs a focused test, including multi-resource assignments, zero planned units, non-hour time periods, and the selected activity/resource calendar.

**Source:** [Synchronizing activity duration, units, and resource units/time — Version 26](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/synchronizing_activity_duration_units_and_resource_units_time.htm).

