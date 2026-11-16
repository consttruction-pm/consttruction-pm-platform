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
