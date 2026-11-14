# P6 EPPM V26 vs P6 Professional V26 — Scheduling Options & Calculation Semantics Matrix

**Status:** Evidence-backed comparative audit; reference documentation only  
**Scope:** Scheduling dialogs, scheduling inputs, calculation switches, float/critical-path semantics, multi-project behavior, and documented API surface.  
**Out of scope:** Implementing or changing a scheduler, CUBI workspace, product menus, data flows, or any agent-owned work.  
**Evidence rule:** CONFIRMED means the exact behavior/control is documented in the cited V26 product source. PARTIALLY VERIFIED means the concept is documented but version/UI/API parity or an edge case is not. NOT VERIFIED means the available sources do not establish the claim. A missing Help topic is not proof that an underlying engine capability is absent.

## 1. Executive result

The core scheduling semantics documented for both V26 products are substantially aligned: data-date control, out-of-sequence progress modes, start-to-start lag interpretation, critical-activity selection (total-float threshold or longest path), float basis, total-float formula, relationship-lag calendar, expected-finish-date use, resource leveling, assignment-cost recalculation, and multiple float paths.

The meaningful differences found in the V26 Help comparison are primarily **workflow/UI and operating-context differences**, not evidence of a different scheduling algorithm:

1. Professional exposes **Schedule automatically when a change affects dates** in its Schedule Options General tab. The EPPM V26 Settings-tab topic does not list this checkbox. This supports a documented UI-surface difference; it does **not** prove the EPPM server has no automatic scheduling behavior through other mechanisms.
2. Professional's Schedule a project workflow documents a conditional **Set Data Date and Project Planned Start to Project Forecast Start during scheduling** option. The EPPM Schedule Project tab topic documents per-project data dates versus applying one selected date, but does not list that forecast-start checkbox. Treat as a Professional-documented workflow difference; exact EPPM equivalent is NOT VERIFIED.
3. EPPM explicitly documents permission-dependent availability and user-level persistence for the resource-leveling and assignment-cost recalculation controls. The Professional V26 Help describes the controls but does not state the same permission/persistence rule on the cited General-tab page.
4. Both products document multiple float paths with the same Total Float / Free Float choices, ending activity, path count, Float Path rank, and Float Path Order concepts. This is **not** an EPPM-only feature.

No claim is made that every hidden scheduler parameter, default, database column, API operation, or scheduler-engine edge case has been exhaustively compared.

## 2. V26 control and behavior matrix

| # | Topic / control | P6 EPPM V26 | P6 Professional V26 | Finding / evidence status |
|---:|---|---|---|---|
| 1 | Scheduling entry point | Activities page > Schedule; Schedule Project, Settings, Advanced tabs | Tools > Schedule; Schedule Options > General, Advanced | Same scheduling task, different navigation/dialog organization. CONFIRMED |
| 2 | Scheduling-options source for multiple projects | "Use scheduling options from" selects the project whose options are used | "Use scheduling options from" selects the project whose options are used | Same documented control. CONFIRMED |
| 3 | Per-project data date | "All projects use their own data date" | "All projects use their own data date" | Same documented option. CONFIRMED |
| 4 | Common data date | "Apply selected data date to all open projects" | "Apply selected data date to all open projects" | Same documented option. CONFIRMED |
| 5 | Data-date meaning | As-of/progress point for project status | Current Data Date drives the schedule; project-specific data dates can be set in Project Details | Same scheduling input. CONFIRMED |
| 6 | Schedule log | Display scheduling log upon completion | Log to File and view/log workflow | Both provide schedule-result logging; UI and destination handling differ. CONFIRMED |
| 7 | Ignore inter-project relationships | Setting to ignore relationships to/from other projects | Same named option | Same intent; do not ignore if dates depend on external relationships. CONFIRMED |
| 8 | Open-ended activities critical | Make open-ended activities critical | Same named option | Same control. CONFIRMED |
| 9 | Expected Finish Dates | Use expected finish dates; EPPM Settings topic describes scheduler use of Expected Finish Date constraint | Use Expected Finish Dates; Professional Help explicitly says checked by default | Semantics align; default is explicitly documented for Professional only in cited V26 topic. CONFIRMED / default PARTIALLY VERIFIED |
| 10 | Automatic schedule after date-affecting edits | Not listed in EPPM V26 Settings-tab screen-element inventory | Professional General tab exposes "Schedule automatically when a change affects dates" | Documented Professional UI control; EPPM equivalent not established. PARTIALLY VERIFIED (surface difference only) |
| 11 | Resource leveling during scheduling | Available only with leveling permission; selection is stored at user level and reused for later projects | Level resources during scheduling checkbox | Control exists in both; EPPM documents permission and persistence details not stated on cited Professional page. CONFIRMED |
| 12 | Recalculate assignment costs | EPPM checkbox recalculates multiple-rate resource/role costs; selection stored at user level | Professional checkbox recalculates multiple-rate resource/role costs after scheduling | Same purpose. EPPM user-level persistence is explicit. CONFIRMED |
| 13 | Out-of-sequence progress: Retained Logic | Remaining duration waits until predecessors finish | Same | Same documented behavior. CONFIRMED |
| 14 | Out-of-sequence progress: Progress Override | Scheduler ignores network logic for progressed activity and allows progress | Same | Same documented behavior. CONFIRMED |
| 15 | Out-of-sequence progress: Actual Dates | Backward/forward passes use actual dates | Same; Professional warns actuals after Data Date can cause negative total float | Same method; Professional warning explicitly documented. CONFIRMED |
| 16 | Start-to-Start lag basis: Early Start | Expired lag based on work periods between actual start and data date; successor uses predecessor remaining early start plus remaining lag | Same; Professional says option disabled under Actual Dates | Same method; Professional UI constraint explicitly documented. CONFIRMED |
| 17 | Start-to-Start lag basis: Actual Start | Successor start = data date + remaining lag; elapsed time from predecessor actual start governs | Same | Same method. CONFIRMED |
| 18 | Critical activities: total-float threshold | Total float less than or equal to entered duration | Same | Same classification method; threshold conversion depends on hours-per-period configuration. CONFIRMED |
| 19 | Critical activities: Longest Path | Driving sequence determining project end date | Same | Same classification method. CONFIRMED |
| 20 | Multiple projects and critical-setting source | Scheduling-options source project selected in dialog | Professional states when multiple projects are open, critical activities use the default project's setting | UI/source-selection nuances need careful handling; not evidence of different path mathematics. PARTIALLY VERIFIED |
| 21 | Float based on project finish date | Each Project vs Opened Projects | Each project vs Opened projects | Same concept and descriptions; Opened Projects uses latest finish across open projects and can yield more float. CONFIRMED |
| 22 | Total Float calculation: Start Float | Late Start − Early Start | Same | Same formula. CONFIRMED |
| 23 | Total Float calculation: Finish Float | Late Finish − Early Finish | Same | Same formula. CONFIRMED |
| 24 | Total Float calculation: Smallest | Smaller/more critical of start and finish float | Same | Same method. CONFIRMED |
| 25 | Relationship-lag calendar: Predecessor | Supported | Supported | Same option. CONFIRMED |
| 26 | Relationship-lag calendar: Successor | Supported and default if none selected | Supported and default if none selected | Same option/default. CONFIRMED |
| 27 | Relationship-lag calendar: 24-hour | 7 days/week, 24 hours/day | 24-hour continuous work periods | Same semantic option. CONFIRMED |
| 28 | Relationship-lag calendar: Project Default | Uses default calendar for new activities | Same | Same option. CONFIRMED |
| 29 | Lag conversion | EPPM notes non-hour lag is converted using predecessor calendar | Professional notes non-hour lag is converted to hours using predecessor activity calendar | Same documented conversion rule. CONFIRMED |
| 30 | Multiple Float Paths toggle | Advanced tab: Calculate Multiple Float Paths | Advanced tab: Calculate multiple float paths | Available in both; not product-exclusive. CONFIRMED |
| 31 | Multiple-path method: Total Float | Relationship Total Float drives backward/forward path tracing | Same | Same documented path method. CONFIRMED |
| 32 | Multiple-path method: Free Float | Defines paths based on longest path; most critical path matches Longest Path setting | Same | Same documented path method. CONFIRMED |
| 33 | Multiple-path ending activity | User may select activity; otherwise EPPM REST describes method-specific auto-selection | User may select activity; Professional Help documents same auto-selection behavior | Same semantics. CONFIRMED |
| 34 | Number of paths | User-specified number; Oracle tip recommends 10 or fewer for performance | User-specified number; Oracle tip recommends 10 or fewer for performance | Same control and performance guidance. CONFIRMED |
| 35 | Float Path and Float Path Order | Float Path 1 is most critical; grouping/sorting reveals paths and processing order | Same | Same output interpretation. CONFIRMED |
| 36 | Critical flag vs float-path membership | Critical classification and multiple paths are separate; critical activities may not all belong to a selected path | Professional guide likewise says multiple-path calculation does not change the critical-activity definition | Important shared semantic: do not conflate the two. CONFIRMED |
| 37 | Forecast Start scheduling option | EPPM Schedule Project V26 topic documents data-date choices, not this forecast-start checkbox | Professional schedule workflow documents conditional option to set Data Date and Planned Start to Forecast Start | Professional-documented workflow difference; EPPM equivalent NOT VERIFIED |
| 38 | WBS Summary relationships | Not established by cited EPPM Schedule Project topic | Professional Help says relationships to/from WBS Summary activities are ignored even when inter-project relationships are maintained | Professional-specific documented caveat; EPPM parity NOT VERIFIED |
| 39 | Schedule-options persistence granularity | EPPM Settings help explicitly says leveling/cost recalculation selections are stored at user level | Professional page describes defaults and option controls; exact persistence scope not established there | Do not assume same persistence model without further evidence. PARTIALLY VERIFIED |
| 40 | Schedule-options API | EPPM V26 REST exposes ScheduleOptions GET/PUT and a broad field schema | Professional V26 Help establishes UI behavior; V26 Professional API field-by-field counterpart was not established by the sources reviewed here | API parity must not be inferred from matching UI labels. PARTIALLY VERIFIED |

## 3. Calculation semantics — important distinctions

### 3.1 Critical activities are not the same as multiple float paths

The General/Settings choice (Total Float threshold or Longest Path) labels activities as critical. The Advanced multiple-float-path calculation is a separate analysis that identifies one principal path and additional sub-critical paths. Oracle's Professional documentation explicitly states that multiple-path calculation does not redefine which activities are marked critical. The EPPM documentation describes the same separation in its critical-activity and multiple-path topics.

**Audit consequence:** A feature checklist that reports "critical path / multiple float paths" as one binary feature is too coarse. Compare the classification rule and path-analysis rule separately.

### 3.2 Total Float versus Free Float path method

- **Total Float path method:** relationship-level total float drives the backward and forward tracing process from the selected ending activity.
- **Free Float path method:** the principal path is based on longest path; in multi-calendar projects, Oracle traces driving relationships from activities with the latest calculated early finish back toward project start.
- The selected ending activity and path count materially affect which sub-critical paths are returned.
- A Float Path value of 1 means most critical path; Float Path Order is processing order, not a duration or priority score.

### 3.3 Out-of-sequence progress is a calculation-policy choice

Retained Logic, Progress Override and Actual Dates are all documented in both products. They are not interchangeable:
- Retained Logic preserves remaining predecessor logic for remaining duration.
- Progress Override allows progressed work to proceed despite network logic.
- Actual Dates uses actual dates in forward/backward passes and can produce negative total float where actuals extend beyond Data Date.

A comparison that says Professional lacks these choices, or EPPM alone supports them, would be incorrect.

### 3.4 Float values depend on more than the displayed unit

The float threshold is converted to hours. In EPPM, Oracle explicitly connects the conversion to Application Settings > Time Periods and whether assigned calendars define hours per time period. Professional Help describes conversion to hours and references Admin Preferences / default project calendar when connected to a Professional database, versus Application Settings when connected to an EPPM database.

**Audit consequence:** Do not compare a displayed threshold such as "1 day" without recording the connected database context and hours-per-period configuration.

### 3.5 Relationship lag calendar is a scheduler input

Both products document predecessor, successor, 24-hour and project-default calendars. The selected calendar changes how relationship lag is interpreted; non-hour lag conversion also references the predecessor calendar. This should be tested with mixed calendars and non-hour lag values before claiming numerical equivalence for all edge cases.

## 4. EPPM V26 ScheduleOptions REST field evidence

Oracle's EPPM V26 REST API documents a `ScheduleOptions` entity and GET/PUT operations. The V26 GET schema includes, among others:

- `CalculateFloatBasedOnFinishDate`
- `ComputeTotalFloatType`
- `CriticalActivityFloatThreshold`
- `CriticalActivityPathType`
- `IgnoreOtherProjectRelationships`
- `LevelAllResources`, `LevelWithinFloat`
- `MakeOpenEndedActivitiesCritical`
- `MaximumMultipleFloatPaths`, `MultipleFloatPathsEnabled`
- `MultipleFloatPathsEndingActivityObjectId`, `MultipleFloatPathsUseTotalFloat`
- `OutOfSequenceScheduleType`
- `RelationshipLagCalendar`
- `StartToStartLagCalculationType`
- `UseExpectedFinishDates`

The same schema includes project/user identifiers and audit timestamps. It describes the multiple-path auto-ending-activity behavior and the multi-project float basis. This proves an EPPM V26 REST data contract exists for these schedule options; it does **not** prove every UI setting is independently writable, that every scheduler option is exposed through the same API surface, or that the Professional V26 API schema is identical.

Professional's V26 Help is the primary evidence used here for desktop scheduling UI. A separate Professional API field-by-field mapping remains open because a directly version-matched V26 Professional API schema was not established in the reviewed sources. Do not use older API FieldSummary pages as proof of exact V26 API parity.

## 5. Source register — Oracle primary sources

### P6 EPPM V26
1. Settings Tab of the Schedule Dialog Box (V26): https://docs.oracle.com/cd/G48897_01/p6help/en/90519.htm
2. Schedule Project Tab of the Schedule Dialog Box (V26): https://docs.oracle.com/cd/G48897_01/p6help/en/90520.htm
3. Advanced Tab of the Schedule Dialog Box (V26): https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/92768.html
4. Scheduling Settings Section of the Schedule Project Log (V26): https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/99348.html
5. Working with Critical Activities (V26): https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/workingwithcriticalactivities-6679a.html
6. Configuring Advanced Scheduling Options (V26): https://docs.oracle.com/cd/G48897_01/p6help/en/37940.htm
7. P6 EPPM REST API V26 — Read ScheduleOptions: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-get.html
8. P6 EPPM REST API V26 — Update ScheduleOptions: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-put.html
9. P6 EPPM Integration API V26.4 — ScheduleOptions business object: https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/com/primavera/integration/client/bo/object/ScheduleOptions.html

### P6 Professional V26
10. Schedule Options dialog box (V26): https://docs.oracle.com/cd/G48902_01/client_help/en_US/schedule_options_dialog_box.htm
11. General tab — Schedule Options (V26): https://docs.oracle.com/cd/G48902_01/client_help/en_US/general_tab_-_schedule_options_dialog_box.htm
12. Advanced tab — Schedule Options (V26): https://docs.oracle.com/cd/G48902_01/client_help/en_US/advanced_tab_-_schedule_options_dialog_box.htm
13. Scheduling Projects (V26): https://docs.oracle.com/cd/G48902_01/client_help/en_US/schedulingprojects.htm
14. Schedule a project (V26): https://docs.oracle.com/cd/G48902_01/client_help/en_US/schedule_a_project.htm

## 6. Remaining gaps — explicitly not closed

The following are not represented as fully verified:
- Every scheduler default value and its source (user, project, database/application preference) for both products.
- Full V26 Professional API ScheduleOptions schema and exact field-to-field comparison against EPPM REST V26.
- Every REST endpoint / Integration API operation for invoking a schedule, retrieving logs, and handling asynchronous scheduling.
- Full leveling algorithm settings, priority rules, resource availability semantics, external resource assignment behavior and leveling report fields.
- Every constraint type, constraint conflict, mandatory date, expected finish and project Must Finish By interaction under each out-of-sequence mode.
- Numerical equivalence under calendars with different work weeks, shifts, exceptions, holidays, time zones and non-hour lag units.
- WBS Summary relationship handling parity in EPPM.
- Forecast-start scheduling equivalent in EPPM.
- Whether the Professional automatic-scheduling checkbox has an EPPM web/server equivalent outside the cited Schedule dialog.
- Defaults and behavior when scheduling mixed database contexts, external projects, multiple open projects, and projects with different data dates.
- Independent execution of controlled test schedules in both V26 products. This audit is documentary; it does not claim runtime test parity.

## 7. Boundary and conclusion

This is a **documentation-only reference comparison**. It changes no product, repository application code, CUBI workspace, menu, schema, scheduler, API, project data or agent-owned task. It is not an implementation request.

**Conclusion:** The evidence supports broad parity in the core documented schedule calculation controls and multiple-float-path semantics, with specific documented differences in Professional's scheduling workflow/UI and some EPPM-specific permission/persistence detail. It does not support a blanket claim that one product has the scheduling engine capability and the other does not. The remaining gaps above must stay open until the exact V26 API schemas and controlled calculation cases are compared.
