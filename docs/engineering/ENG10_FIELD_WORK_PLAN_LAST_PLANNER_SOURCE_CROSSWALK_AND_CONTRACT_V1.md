# ENG-10 Field Work Plan / Last Planner — Source Crosswalk & Domain Contract V1

**Date:** 2026-11-16  
**Capability:** ENG-10 (Engineering / project execution)  
**Status:** SOURCE_MAPPED / CONTRACTED — not implemented  
**Issue:** #2011  
**Navigation:** Project → Field Operations → Work Plan / Lookahead / Constraints / Daily Huddle / Commitments / PPC / Production & Productivity

## 1. Product boundary

ENG-10 is a project-execution commitment and field-planning capability. It is not:
- the Enterprise generic Task Center / enterprise task aggregate;
- a P6 CPM Activity or Activity Step;
- ENG-11 Team Member Activity Status Update;
- ENG-12 Timesheet;
- a second CPM scheduler or schedule-calculation engine.

Engineering owns Field Work Plan tasks, task plans, hand-offs, constraints, commitments/recommitments, reason codes and PPC facts. P6 Activity/WBS links are explicit references, not shared aggregate ownership. Workbench may project a user's commitments but is not the data owner. Enterprise owns cross-project portfolio/commercial governance; Shared may provide identity, authorization, file and notification primitives only.

Primavera Cloud is used as the additive source for lean construction planning behaviors not established by EPPM Help. P6 EPPM V26 remains normative for shared project/activity/security semantics and the EPPM integration boundary.

## 2. Source crosswalk — verified topics

| Capability behavior | Oracle source | Verified semantics | CUBI contract consequence |
|---|---|---|---|
| Tasks overview / relationship to CPM | [Tasks Overview](https://primavera.oraclecloud.com/help/en/user/101908.htm); [Understanding Tasks App Concepts](https://primavera.oraclecloud.com/help/en/user/207799.htm) | Tasks app provides lightweight field work management without CPM complexity; tasks may optionally link to activities; public/private visibility; task vs milestone; company/user responsibility | Separate Engineering Field Task aggregate; optional versioned Activity/WBS links; do not silently convert tasks to CPM activities |
| Planning board / window | [Work Plan](https://primavera.oraclecloud.com/help/en/user/102171.htm); [Manage Tasks on Work Plan](https://primavera.oraclecloud.com/help/en/user/102799.htm) | Planning board, daily/weekly views, configurable planning period up to six weeks; default period is one prior week, current week and four future weeks; task plans organize swimlanes | Configurable lookahead window; persisted task plan and swimlane configuration; don't hard-code a six-week view |
| Task plans / swimlanes | [Understanding Tasks App Concepts](https://primavera.oraclecloud.com/help/en/user/207799.htm) | Multiple task plans; swimlane categories include user, company, activity code, task code and WBS; Configure Task Plan project privilege | TaskPlan and TaskPlanLane configuration are distinct from tasks; enforce project-scoped configuration permission |
| Hand-offs | [Understanding Tasks App Concepts](https://primavera.oraclecloud.com/help/en/user/207799.htm); [Add a Hand-off](https://primavera.oraclecloud.com/help/en/user/146939.htm) | Finish-to-Start, Finish-to-Finish and Start-to-Start; multiple predecessor/successor edges; only one edge between a pair; no private-task hand-offs; multiple companies; milestones support finish connections; lag and slack; Keep/Break modes | Typed relationship enum, constraints and deterministic propagation; prohibit duplicate pair and invalid private-task links; implement lag/slack only if explicitly contracted; no ad hoc CPM engine |
| Cross-company proposed dates | [Propose and Accept a Task Due Date](https://primavera.oraclecloud.com/help/en/user/207822.htm) | Proposed date does not alter current due date until accepted; acceptance changes due date; committed task removes proposal; hand-off chains may move; workday setting can be cleared for accepted non-workday | Separate ProposedDueDate and acceptance event; actor/approver audit; don't mutate current schedule until accepted |
| Constraints | [Understanding Tasks App Concepts](https://primavera.oraclecloud.com/help/en/user/207799.htm); [Manage Task Constraints](https://primavera.oraclecloud.com/help/en/user/221632.htm); [Assign Constraint](https://primavera.oraclecloud.com/help/en/user/221630.htm) | Constraint types/status, responsible company/user, promised and needed dates, notes/files, one constraint can affect multiple public tasks, delivery action; removing association does not delete constraint | Constraint is independent aggregate; many-to-many task association; promised/needed/resolved dates; notes/files and deliver action; association removal is not deletion |
| Commitments | [Commit to a Task](https://primavera.oraclecloud.com/help/en/user/102082.htm); [Understanding Tasks App Concepts](https://primavera.oraclecloud.com/help/en/user/207799.htm) | Optional submitted agreement by assigned company/user for a public task and date; no milestone or completed-task commitment; history retained; commitment date updates task due date | Commitment is immutable history event plus current projection; reject milestone/private/completed tasks; keep actor/company attribution |
| Recommitment / reason codes | [Recommit to a Task](https://primavera.oraclecloud.com/help/en/user/139410.htm) | Recommit needs new due date and one or more missed reasons; optional comment; commitment history visible; chain may move; most recent commitment may be deleted under source UI rules | Reason dictionary and multi-reason selection; explicit policy for correction/deletion preserving audit; chain propagation tested |
| Completion | [Complete a Task](https://primavera.oraclecloud.com/help/en/user/102578.htm) | Completion date derived from due date if due today/past, otherwise today; completed tasks lock selected fields; non-workday restrictions; cannot complete Pending task with commitments; security needed to complete another user's task | Explicit completion transition; server validates state, calendar and privilege; completed field restrictions and reversibility rules; preserve source date logic |
| PPC / task performance | [Tasks Analysis Overview](https://primavera.oraclecloud.com/help/en/user/105747.htm); [View Tasks Analysis Metrics](https://primavera.oraclecloud.com/help/en/user/105748.htm) | PPC = completed tasks divided by task commitments; daily/weekly values only through previous day/week; total-project PPC since project start through previous week; selected time-frame PPC; company PPC; reasons missed; filters by company and current week/six-week/custom ranges | Implement PPC with exact commitment denominator and completed numerator; no mixing with CPM % complete/EVM; preserve time cutoffs, company filters and reason dimensions |
| Security / task ownership | [Tasks App TOC](https://primavera.oraclecloud.com/help/en/user/toc.htm); [Understanding Tasks App Concepts](https://primavera.oraclecloud.com/help/en/user/207799.htm) | Public/private semantics; task plan configuration privilege; task editing and cross-company visibility governed by app/project access | Need full topic-level security permissions crosswalk before implementation; enforce tenant/project/company/actor/object scope server-side |

## 3. Important source semantics

### 3.1 Task is not an activity
A Field Task describes physical work and may optionally be linked to a CPM Activity for more detailed alignment. The task remains separately owned. A milestone has no duration or assigned user; task milestones are public. Private tasks cannot participate in hand-offs or shared constraint/commitment flows.

### 3.2 Hand-off relationship rules
Supported hand-off types:
- FS: successor starts only after predecessor finishes.
- FF: successor cannot finish before predecessor finishes.
- SS: successor cannot start before predecessor starts.

Tasks may have multiple predecessor and successor links, but only one link per task pair. Task milestones only support finish-side connections. Lag can count workdays only or all days; lag cannot be consumed. Dependency slack and task slack are read-only values. Keep Hand-offs maintains relationship logic while allowing slack to grow/shrink; Break Hand-offs preserves surrounding due dates as much as possible and may break a link when slack reaches zero or date changes cross neighbors. Completed tasks cannot be moved.

These rules must be treated as the Field Work Plan relationship engine, not delegated to or duplicated inside the authoritative CPM scheduler. If CUBI elects not to support a source feature in the first release, that exact behavior must be labelled deferred rather than approximated.

### 3.3 PPC formula and reporting window
For a given period, `PPC = completed committed tasks / task commitments`. The denominator is commitments, not all planned tasks and not CPM activities. Daily PPC excludes the current day; weekly PPC excludes the current week. The Analysis view supports:
- project PPC over time;
- total-project PPC (project inception through previous week);
- selected-time-frame PPC;
- company PPC and company PPC over time;
- missed commitment reason distribution and trends;
- current week, six-week window or custom date range;
- company quick filter, with explicit configuration to honor or ignore that filter in PPC calculation.

The first implementation must explicitly define treatment of multiple commitments/recommitments for one task in the denominator based on source data semantics and validate against source examples. Do not assume a simple count of distinct tasks if the source counts commitment records; keep this as a required source/acceptance test before production.

### 3.4 Constraint lifecycle
A constraint is a prerequisite issue/material/deliverable. It can have responsible company/user, type, status, promised delivery date, needed-by date, actual delivery/resolution, notes and files. It may affect multiple public tasks. Removing a task association must not delete the constraint object. Delivery is an explicit action.

### 3.5 Commitments and completion
Commitments are optional agreements tied to public tasks and responsible company/user. A commitment/recommitment updates the task's current due date and clears any proposal. Recommitment requires at least one reason missed. A task milestone cannot be committed. A completed task cannot be recommitted/committed. Completion locks selected fields and applies project calendar/non-working-day rules.

## 4. Domain contract proposal (not implementation)

Proposed aggregates / records:
- `FieldTask`: project, visibility, company, assigned user, duration, start/due/proposed due/completed dates, calendar/workday mode, optional WBS/activity references, status, revision.
- `TaskPlan` and `TaskPlanLane`: saved planning board configuration and swimlane grouping.
- `TaskHandOff`: predecessor, successor, relationship type, lag, lag calendar mode, hand-off mode, revision.
- `TaskConstraint`: type, status, responsible company/user, promised/needed/resolved dates, notes/files, revision.
- `TaskConstraintLink`: task/constraint relation; independently removable.
- `TaskCommitment`: immutable commitment/recommit event with actor, company, due date, reason IDs, comments and timestamp.
- `TaskReasonCode`: project/workspace-owned reason dictionary with active state and audit.
- `TaskPpcSnapshot`: derived, reproducible period/company result, source commitment IDs and completed task IDs, cutoff and filter configuration.

Proposed versioned contracts (names are placeholders pending repository naming review):
- `engineering-field-operations-api.v1`
- `engineering-field-task-api.v1`
- `engineering-task-planning-api.v1`
- `engineering-task-commitment-api.v1`
- `engineering-task-constraint-api.v1`
- `engineering-task-analysis-api.v1`

The contract owner must choose whether these are separate endpoints or one versioned bounded-context API; do not create redundant APIs solely to mirror the proposed names.

## 5. Lifecycle and permissions

Minimum transitions:
- Task: draft/unplanned → planned → committed → overdue/recommit → completed; cancellation/deletion rules require separate source review.
- Proposed due date: proposed → accepted or replaced; never silently mutate current due date on proposal.
- Constraint: identified → assigned → linked → delivered/resolved; reopening policy needs source verification.
- Commitment: committed → missed → recommitted; keep immutable history and source-compatible latest-entry correction semantics.
- Hand-off: created → modified/removed, with deterministic validation and propagation.
- Task Plan: draft/configured/shared; project-level Configure Task Plan permission.

Permission distinctions must include: view public/private; create; edit own; edit other users; configure task plan; manage task plan; create/modify hand-offs; propose due date; accept proposed date; assign/manage constraints; commit; recommit; complete own; complete others; manage reason dictionary; view analysis; export/print. Derive tenant/project/company/user scope server-side; client-provided scope is never authoritative.

## 6. Acceptance matrix

- Public/private visibility and cross-company reads/writes.
- Task vs milestone field constraints.
- Optional Activity/WBS linking without aggregate mutation.
- All three hand-off types, invalid edge combinations, pair uniqueness, multiple predecessor/successor, private-task prohibition.
- Lag with workdays-only vs all-days, slack read-only and deterministic, Keep/Break modes, completed task immobility.
- Proposed date visible without current-date mutation; acceptance and committed-date replacement; cross-company authorization.
- Constraint multi-task links, responsible party, dates, notes/files, delivery, association removal without aggregate deletion.
- Commitment rejects milestone/completed/private tasks; recommit requires >=1 reason; history and actor attribution.
- Completion date and calendar/non-workday behavior; pending commitment restriction; completion-other-user permission.
- PPC exact numerator/denominator, daily/weekly cutoff, total-project and selected-window metrics, company breakdown, filter-honor option, missed-reason trends, zero denominator and no-data behavior.
- Time zone/calendar boundary, daylight saving, retries/idempotency, concurrency/revision conflict, audit, offline behavior if mobile/offline scope is accepted.
- Browser evidence for Work Plan, task detail, constraints, commitment/recommit, hand-off graph, Analysis and permission-denied states.

## 7. Open source / product decisions

1. Retrieve and crosswalk the complete Tasks App Security Permissions topic and every relevant UI field/command topic; the TOC is not a substitute for each procedure.
2. Determine whether Pull Plans, Live Pull Planning, Parking Lot and task-plan release are in ENG-10 first release or explicitly deferred.
3. Confirm exact source behavior for deleting/correcting commitment history; UI permits deleting the most recent entry, but audit behavior must be defined.
4. Validate PPC denominator semantics for multiple recommitment records using Oracle examples/data behavior. Do not choose distinct-task vs commitment-record counting by assumption.
5. Confirm all task date propagation and hand-off mode edge cases against source examples.
6. Decide whether Daily Huddle is a workflow/view over FieldTask + TaskCommitment + TaskConstraint + PPC, not a second store.
7. Confirm whether production quantities/productivity are a separate capability/data contract from PPC, with independent units/rates and calculation owner.
8. Confirm exact Field Operations menu and command-level permissions against current CUBI navigation and project roles.

## 8. Non-interference / Qoder handoff

No application code is authorized by this contract. At the last refreshed snapshot, active PRs #1974, #1983/#1980, #1711, #1971, #2006, #2001 and #1929 occupy shared workspace, authorization, identity, schema, production composition, activity/actuals, schedule and Enterprise Task paths. Re-fetch main SHA, PR heads/files and root/nested `AGENTS.md` immediately before implementation. One writer per path set; require named owner handoff.

Qoder task packet must include this contract version, base SHA, allowed/forbidden path list, integration boundary, tests, browser evidence and stop conditions. If Qoder cannot accept the task, mark BLOCKED and retain this as contract-only. Do not enable shell actions or claim feature completion.

## 9. Source status

- Cloud Tasks Overview, Task Concepts, Work Plan, hand-offs, constraints, commitments, recommitment, completion and PPC analysis: **VERIFIED** at topic level.
- Complete security permissions matrix and all detailed task field/command procedures: **MISSING / VERIFY**.
- EPPM V26 shared project/activity semantics and integration field mappings: **PARTIALLY VERIFIED**; full EPPM field mapping and authoritative link behavior must be verified before integration code.
- CUBI implementation: **NOT IMPLEMENTED / NOT VERIFIED**.


## 10. Tasks App security permission crosswalk (verified 2026-11-16)

Oracle's [Security Permissions for Tasks](https://primavera.oraclecloud.com/help/en/user/186885.htm) topic is now retrieved directly. It separates workspace-level permissions from project-level permissions.

### Workspace permission category
- Configuration: Calendars, Codes, Configured Fields, Field Labels, Reasons.

### Project permission categories
- Project: Calendars, Codes, Companies, Project.
- Schedule (Current): Activities.
- Tasks:
  - Complete Constraints for All Companies.
  - Complete Constraints for My Company.
  - Configure Task Notifications for Others.
  - Configure Task Plan.
  - Constraints.
  - Link Constraint to Aconex Package.
  - Manage Commitments and Complete All Company's Tasks.
  - Manage Commitments and Complete My Company's Tasks.
  - Manage Commitments and Complete My Tasks.
  - Tasks for All Companies.
  - Tasks for My Company.

**Contract impact:** do not flatten these into one generic `manage_field_operations` permission. CUBI must preserve company-scope tiers and distinguish configuration, task visibility, constraint completion, notification configuration, commitment management and completion authority. Map CUBI role grants to these operation-level capabilities with server-side project/company/actor checks. The source says some permissions may be optional depending on use; do not require or grant them indiscriminately.

## 11. Remaining evidence gaps (updated)

- **VERIFIED:** Tasks App security permission categories and named grants; Task Concepts; Work Plan; Hand-offs; Constraints; Commitments/Recommitments; Completion; PPC Analysis.
- **MISSING / VERIFY:** Full per-page field/command availability and exact UI-level gating; source semantics for deleting/correcting latest commitment history and downstream audit; PPC denominator behavior when a task has multiple commitment records/recommitments; Daily Huddle as a distinct page/process (no dedicated Tasks App Help topic confirmed in the reviewed TOC); Production & Productivity quantity/rate model (not equivalent to PPC); mobile/offline behavior if in scope.
- **Decision:** Daily Huddle may be a meeting workflow/projection over existing FieldTask, TaskCommitment, TaskConstraint and PPC facts, but no separate store or lifecycle is authorized until its own source and acceptance contract is complete.
- **Decision:** Production quantity/rate records and productivity calculations must be a separate typed sub-capability with its own units, numerator/denominator, period, attribution and calculation owner. PPC remains only commitment reliability.



## 12. Additional Tasks App Help inventory and Task Plan procedures (2026-11-16)

The current Oracle Primavera Cloud Help TOC was re-opened at `https://primavera.oraclecloud.com/help/en/user/toc.htm`. It confirms a larger explicit procedure inventory than the first ENG-10 crosswalk had enumerated:

- Pull Plans: overview; create; approve/release; manage existing plans; planning board; Parking Lot; add/bulk-add tasks and milestones; manage tasks and hand-offs; longest path; live pull-planning session start/end/join.
- Hand-offs: add task/milestone and hand-off; propose/accept due date; assign constraint; commit/recommit; complete; longest path; filters, task cards, notifications and Plan By options.
- Work Plan: add/import tasks; modify task details; crew size estimate; move task; due-date proposal/acceptance; constraints; commit/recommit/complete; Task Plan create/open/edit/close; swimlanes; display customization; filters; search; print.
- Constraints: create, assign task, notes, deliver, file and Aconex package linking.
- Task List: create/import/copy; assign user/activity/WBS; crew size/duration/due date; hand-offs; constraints; commit/recommit/complete; files and configured fields.
- Analysis: Tasks Analysis Overview and View Tasks Analysis Metrics.
- Separate app areas also exist for My Activities and Timesheets. Their presence in the Cloud TOC does not merge them into ENG-10; ENG-11/ENG-12 retain their own contracts and source authority.

**Important limitation:** TOC presence proves that Oracle documents these workflows; it does not establish detailed command semantics, permissions, state transitions or parity. Each procedure still needs direct page review before its behavior is accepted into the CUBI contract. In particular, Pull Plans, Live Pull Planning and Parking Lot remain first-release scope decisions, not silently included implementation scope.

### 12.1 Task Plan / swimlane details directly verified

- [Task Plan Overview](https://primavera.oracle.com/help/en/user/264813.htm): a project may have multiple task plans; plans organize task cards using swimlane categories such as assigned user, company, activity code, task code or WBS; plans may be shared and revisited; the Configure Task Plan project privilege is required to add, edit or delete plans.
- [Use Swimlanes on the Planning Board](https://primavera.oracle.com/help/en/user/264804.htm): swimlanes can combine configured categories; tasks may be moved among lanes or to/from the hopper; moving a task into a lane can change its assignment to match the lane; copy/paste duplicates tasks but does not copy hand-offs; moving a task to the hopper removes its due date; moving it back to the board assigns today or the next available work day as its start; lane visibility and filters affect the board's displayed content.

**Contract refinement:** TaskPlan is a saved, shareable planning configuration, not just a transient UI filter. Swimlane moves can mutate task assignment and dates; those commands require explicit confirmation, authorization, revision checks and audit. Copying tasks must not implicitly duplicate hand-off relationships. Hopper transitions are domain commands, not cosmetic drag-and-drop.

## 13. Updated source readiness and remaining gates

| Source area | Status after this pass | Gate |
|---|---|---|
| Tasks App top-level Help inventory (Pull Plans, Work Plan, Hand-offs, Constraints, Task List, Analysis) | VERIFIED at TOC level | Review each relevant procedure before implementing its commands |
| Task Plan overview and swimlane behavior | VERIFIED at procedure level | Confirm remaining edit/close/create example pages and exact field constraints |
| Task security permissions | VERIFIED at procedure level | Map each named Oracle permission to CUBI grants and page-level controls |
| Pull Plan approval/release, Parking Lot, live planning | DOCUMENTED IN TOC; PROCEDURE DETAILS MISSING / VERIFY | Keep deferred until exact pages, lifecycle and permissions are crosswalked |
| Daily Huddle | MISSING / VERIFY | No dedicated Tasks App Help topic identified in the current TOC |
| Production & Productivity quantity/rate model | MISSING / VERIFY | Requires independent source and calculation contract; PPC is not a substitute |
| PPC recommitment denominator and commitment correction audit | MISSING / VERIFY | Validate source examples and history semantics |
| CUBI implementation | NOT IMPLEMENTED / NOT VERIFIED | No code, runtime, UI or test implementation is claimed |


## 14. Pull Plans procedure-level verification (2026-11-16)

The previously TOC-only Pull Plans decision gate was advanced with direct retrieval of the relevant Oracle Cloud procedures:

- [Pull-Planning Overview](https://primavera.oraclecloud.com/help/en/user/294153.htm): plans work backward from a finish milestone; tasks can be staged in the Parking Lot and moved to the board; task duration, responsible company, crew size and "What I Need" information are part of planning. Plan states include In Planning and Approved; release is a distinct downstream step.
- [Working with the Pull Plans Page](https://primavera.oraclecloud.com/help/en/user/294154.htm): create a plan against a milestone or activity; inspect plan status, target duration, session date and description; withdraw approval to revise; release approved plan to Work Plan. Once released, only plan name, description and session date remain editable.
- [Approve and Release a Pull Plan](https://primavera.oraclecloud.com/help/en/user/294161.htm): requires the distinct Approve and Release to Work Plan permission. Approval freezes tasks and hand-offs; changes require withdrawal to In Planning. Approval warnings can identify disconnected tasks/milestones/hand-offs, Parking Lot tasks and chains without successors. Release can move tasks to the Work Plan Hopper or place the sequence relative to a selected finish-milestone date. Parking Lot tasks are not released; hand-offs among released items are retained.
- [Manage Existing Pull Plans](https://primavera.oraclecloud.com/help/en/user/294156.htm): delete requires Pull Plans - Delete; withdrawal requires Approve and Release to Work Plan; approved, released or live-session plans cannot be deleted; approved/released plans have restricted editable fields.
- [Use the Parking Lot](https://primavera.oraclecloud.com/help/en/user/294202.htm): stores unsequenced tasks; no hand-offs or contribution to longest path; no task milestones; hidden for approved/released plans; Add Tasks privilege required. Tasks can move to/from the Planning Board with explicit commands; filters include My Tasks, My Company's Tasks and All Tasks.
- [Live Pull-Planning Session Overview](https://primavera.oraclecloud.com/help/en/user/294162.htm) and [Start or End a Live Session](https://primavera.oraclecloud.com/help/en/user/294165.htm): live sessions are optional. The plan is read-only until a participant joins. Joined participants see Planning Board and Parking Lot changes automatically. A facilitator with Approve and Release to Work Plan starts/ends the session; participant task operations remain governed by their task privileges. Company Restricted Users are limited to invited plans and plans in which they participated. The overview specifies up to 100 participants, a 25-minute inactivity warning and 30-minute disconnect; the start/end procedure additionally documents the session ending after one hour of inactivity.
- [Bulk-add Tasks](https://primavera.oraclecloud.com/help/en/user/294186.htm): up to 100 valid tasks can be added to the Parking Lot per operation; grid, paste and Excel template input are supported; task milestones are excluded; Add-task privilege, plan status and live-session state gate availability.

**Contract refinements:**
1. Pull Plan is a distinct staged plan aggregate with explicit status, target finish object, session date, approval/withdrawal and release-to-Work-Plan transitions. It is not interchangeable with TaskPlan (saved Work Plan swimlane configuration).
2. Approval/release are separate commands and permissions. Approval freezes tasks/hand-offs; withdrawal restores editability; release transfers eligible planned items to Work Plan while excluding Parking Lot items.
3. A release operation must preserve hand-offs among released items and explicitly report excluded/unreleased items. It must not silently create CPM activities.
4. Live collaboration is optional and does not bypass task-level privileges or company-restricted visibility. Real-time session state, participant membership, inactivity timeout and read-only-until-join behavior require explicit support if this feature is in scope.
5. Parking Lot membership is a real planning state with constraints (no hand-offs, no milestones, excluded from longest path), not merely a visual container.
6. Bulk-add requires row-level validation, deterministic limits and privilege/state gating.

**Scope decision:** Pull Plans, Parking Lot, approval/release and live sessions are now sufficiently source-mapped to be considered in ENG-10 product scope; they are no longer unknown feature names. Their CUBI first-release inclusion still requires an explicit product decision and a complete acceptance/authorization map. No implementation is implied.

## 15. Updated ENG-10 evidence status

| Area | Status |
|---|---|
| Pull Plans overview, lifecycle, approval, withdrawal, release | VERIFIED at procedure level |
| Parking Lot rules and operations | VERIFIED at procedure level |
| Live pull-planning collaboration and access boundaries | VERIFIED at procedure level |
| Bulk-add tasks | VERIFIED at procedure level |
| Task Plan and Work Plan swimlanes | VERIFIED at procedure level |
| Complete CUBI first-release scope selection and API/domain design | OPEN PRODUCT DECISION |
| Daily Huddle | MISSING / VERIFY |
| Production & Productivity quantity/rate model | MISSING / VERIFY |
| PPC denominator with multiple recommitments / commitment-history correction audit | MISSING / VERIFY |
| CUBI implementation | NOT IMPLEMENTED / NOT VERIFIED |


## 16. Daily Huddle, PPC and production quantity/productivity — source closure pass (2026-11-16)

### 16.1 Daily Huddle — verified as a workflow, not a separate data owner

Oracle's current Primavera Cloud product documentation explicitly describes Daily Huddle as field coordination:
- a short (15-minute) meeting reviewing the daily plan;
- one-click task completion;
- recommitment to a new finish date with reason codes;
- a learning/feedback review of PPC and missed-commitment reasons;
- a printable daily work plan.

Source: [Oracle Primavera Cloud product tour — Daily Huddle slides](https://www.oracle.com/construction-engineering/primavera-cloud-project-management/), particularly the Daily Huddle sections. This is official product documentation, not a detailed command-level Help procedure.

**Contract decision:** Daily Huddle is a meeting/workflow and role-focused projection over existing ENG-10 FieldTask, TaskCommitment, TaskReasonCode, task completion and PPC facts. It is not a new task store, commitment ledger, duplicate PPC calculator or separate scheduler. Its commands must call the same authorized task completion/recommit operations used elsewhere. The meeting record may retain date/time, facilitator, attendees, agenda/notes and linked task IDs as an auditable meeting artifact, but must not copy task state into a second source of truth.

**Evidence limit:** The product workflow is VERIFIED at product-description level; dedicated Oracle Help procedures for a distinct Daily Huddle page, attendee/meeting lifecycle and exact button permissions remain MISSING / VERIFY. CUBI can contract the projection/meeting artifact, but cannot claim exact Oracle UI parity or reproduce undocumented meeting controls.

### 16.2 Production & Productivity — distinct typed quantity/rate capability

Oracle Primavera Cloud Scope Help documents a separate installed-quantity model:
- Scope Items represent materials/products, with original quantity, unit of measure and original productivity rate (hours required per unit); original hours are quantity × rate.
- Scope Assignments distribute scope items to work packages and carry revised quantity/hours/productivity rate.
- Progress can be recorded by rule-of-credit milestones or physical installed values.
- For physical progress, users record incremental installed quantity since the last progress date or cumulative installed quantity to date.
- Installed hours are calculated from installed quantity × revised productivity rate.
- Installed quantity and progress percent are separate from Field Task completion/PPC.

Sources:
- [Add a Scope Item](https://primavera.oraclecloud.com/help/en/user/88997.htm) (source search result; direct page retrieval unavailable in this pass).
- [Update Installed Quantity for a Scope Assignment](https://primavera.oraclecloud.com/help/en/user/89818.htm) (directly retrieved; published 2026-01-26).
- [Data Dictionary](https://primavera.oraclecloud.com/help/en/user/46503.htm) (source search result).
- [Scope Assignment REST API](https://docs.oracle.com/en/industries/construction-engineering/primavera-cloud/opcap/op-scopeitemassignment-scopeitemassignmentid-get.html) (source search result; API field definitions).

**Proposed ENG-10 sub-capability boundary — Production & Productivity:**
- 'ProductionItem': typed deliverable/material/work item, unit of measure, discipline/location/system classification.
- 'ProductionPackageAssignment': project/work-package/activity reference, planned/revised quantity, planned/revised hours, productivity rate and baseline/change provenance.
- 'ProductionProgressEntry': immutable dated incremental or cumulative installed quantity, source actor, unit, location, shift/crew attribution, evidence and revision/idempotency metadata.
- Derived measures: installed quantity, remaining quantity, physical progress %, installed hours and actual productivity rate (hours per installed unit); forecasts must be separately labelled and versioned.
- Formula policy: installed_hours = installed_quantity × revised_productivity_rate; remaining_quantity = revised_quantity − installed_quantity; actual productivity rate must use a documented positive installed quantity and actual labor-hour source. Never divide by zero or silently mix unlike units.
- Scope/work-package data remains distinct from FieldTask/TaskCommitment. A FieldTask may reference a production assignment, but task completion does not automatically assert a measured installed quantity. ENG-12 approved labor may be an actual-hour source only through a governed, reconciled posting path; do not double count hours.
- No second EVM, CPM or resource actuals engine. Production quantities/rates are Engineering project execution facts; Enterprise may consume approved rollups for portfolio/commercial reporting.

**Source boundary:** Oracle Scope Management is an adjacent Cloud source for quantity/progress semantics, not proof that P6 EPPM Team Member or Tasks App contains this capability. CUBI's Production & Productivity contract is therefore SOURCE_MAPPED / CONTRACT_PROPOSED, not P6-parity-complete. Full Scope Help, change control after baseline, work-package closeout, cost/hour entry, permissions, API write semantics and exact UI remain source-review gates.

### 16.3 PPC — formula confirmed; historical denominator remains a deliberate gate

Oracle Tasks Analysis defines PPC as completed tasks divided by task commitments. Daily values are calculated through the previous day; weekly values through the previous week; current periods are pending. The missed-commitment charts count tasks with recommitted due dates and support time/company analysis.

Sources:
- [Tasks Analysis Overview](https://primavera-au1.oraclecloud.com/help/en/user/105747.htm) (official search result; direct retrieval cache-missed).
- [Recommit to a Task on the Work Plan Page](https://primavera.oraclecloud.com/help/en/user/139410.htm) (directly retrieved; includes multiple reasons and latest-commitment deletion behavior).
- [Oracle field schedule guide](https://www.oracle.com/customer-hub/construction-engineering/primavera-cloud/primavera-cloud-getting-started-schedulers/managing-field-schedule/) (product guide confirms formula and reason analysis).

Additional confirmed semantics:
- A recommitment records a new due date, one or more missed reasons and optional comments; the commitment history is visible.
- Oracle allows deletion of the most recent commitment, after which the task displays the preceding commitment's due date.
- Changing committed due dates can move connected tasks according to Keep Hand-offs / Break Hand-offs mode.

**Do not guess the denominator implementation.** Help describes the metric as "completed tasks / task commitments", but the reviewed material does not conclusively resolve whether historical PPC periods count immutable commitment events, the latest active commitment per task at the period cutoff, or another source-defined commitment snapshot when a task is recommitted/deleted. This must be validated against Oracle examples or reproducible source data before implementing CUBI PPC. Until then, PPC can be displayed only as an explicitly provisional metric or withheld; do not certify parity.

## 17. Final ENG-10 source/contract disposition

| Slice | Disposition | Implementation status |
|---|---|---|
| Field Tasks, Task Plans, hand-offs, constraints, commitments, completion | Source-mapped; detailed source and permission gates remain | NOT IMPLEMENTED / NOT VERIFIED |
| Pull Plans, Parking Lot, approval/release, live sessions | Procedure-level source-mapped; first-release scope decision remains | NOT IMPLEMENTED / NOT VERIFIED |
| Daily Huddle | Product-workflow source verified; contract is a projection over ENG-10 facts; detailed UI/help gaps remain | NOT IMPLEMENTED / NOT VERIFIED |
| PPC | Formula and reporting windows source-verified; historical recommitment denominator unresolved | NOT IMPLEMENTED / NOT VERIFIED |
| Production & Productivity | Separate quantity/productivity model proposed from Cloud Scope sources; full source and integration mapping remain | NOT IMPLEMENTED / NOT VERIFIED |

**First-release recommendation:** deliver core Field Work Plan and task/commitment/constraint lifecycles first; include Daily Huddle as a thin meeting/projection only if its meeting artifact and permissions are approved; keep Pull Plans/live collaboration as a separately scoped increment; keep Production & Productivity behind its own data contract and unit/formula/actual-hours reconciliation; do not enable PPC as parity-complete until the recommitment denominator is empirically resolved.

No application code, APIs, persistence, schema, routes, UI, authorization, tests or runtime behavior were changed by this source/contract update.
