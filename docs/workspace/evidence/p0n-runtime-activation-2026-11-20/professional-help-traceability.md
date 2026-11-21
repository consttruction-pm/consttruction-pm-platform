# Professional Help traceability — P0-N.2

## 1. Reference identity

| Item | Value |
| --- | --- |
| Oracle help set | Primavera P6 Professional Help, Version 26 |
| HTML help (authoritative for behavior) | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm |
| Attached PDF | `p6-professional-help.pdf`, 815 pages, 3,105,001 bytes |
| PDF document ID / date | G57535-02 / 9 October 2026 |
| PDF SHA-256 | `0746e8521d9f3bac85b1b6c4ec7fabfd139cc4bf79ae59b03a1a3ee1f8e9dc0b` |
| Extract used | `pdftotext -layout`; page numbers below are **absolute PDF pages** (page 1 = cover) |
| Professional User Guide (supporting only) | https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/index.html |

The PDF and the HTML help are two renderings of the same Version 26 help set. The
EPPM help set is a different product and is **not** a substitute; see
`two-environment-reference-map.md`.

## 2. Scope of this matrix

Rows cover the capabilities that the P0-N.2 runtime activation actually exercises:
calendar definitions and assignment, schedule calculation, constraints, float/critical
path, leveling, job execution, multi-project execution, baselines, progress and
portfolio-level reporting. Desktop-only visual behavior (toolbars, layouts, Gantt
drawing) is outside this runtime evidence and is not claimed.

Status vocabulary (as required by the mission):
`MATCH`, `PARTIAL`, `MISSING`, `NOT APPLICABLE`, `BLOCKED_EXTERNAL`.

All GitHub paths are on branch `feat/p0n2-runtime-activation` and can be opened at
`https://github.com/consttruction-pm/consttruction-pm-platform/blob/feat/p0n2-runtime-activation/<path>`.

## 3. Matrix

| Environment | Oracle Help Topic | Oracle URL | PDF Page | GitHub Reference | CUBI Module | Current Behavior | Required Behavior | Gap | Implementation | Test | Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P6 Professional V26 | Calendars | https://docs.oracle.com/cd/G48902_01/client_help/en_US/calendars.htm | 159 | `src/construction_pm/calendar_master_repository.py` | Calendar master + snapshot repositories | Calendars are persisted with id, version, kind, name, record revision and calendar type | Calendar definitions are versioned, scope-bound and immutable per revision | None for the calculation path; no desktop calendar dialog | Persisted master/snapshot rows; registry built per scope | `tests/test_calendar_master_repository.py`, `tests/test_calendar_snapshot_repository.py`, `tests/test_calendar_registry_production_builder.py` | `calendar-registry-traceability.md` | MATCH |
| P6 Professional V26 | Project Calendars | https://docs.oracle.com/cd/G48902_01/client_help/en_US/projectcalendars.htm | 161 | `src/construction_pm/calendar_master_repository.py` | Project calendar (`calendar_type='project'`) | Project calendars are created, edited and read through the calendar API | A project calendar is addressable as `calendar_id@calendar_version` | Calendar UI forms are out of scope here | `p6_calendar_api.py`, `p6_calendar_read_api.py` | `tests/test_p6_calendar_api.py` | `logs/targeted.log` | PARTIAL |
| P6 Professional V26 | Create a project calendar | https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_project_calendar.htm | 161 | `src/construction_pm/calendar_master_repository.py` | Project calendar write path | Create/save with optimistic revision checks | Reject stale revisions, duplicate references, invalid kinds/types | No desktop wizard | `SQLite/PostgresCalendarMasterRepository.save` | `tests/test_calendar_master_repository.py` | `logs/full-suite.log` | PARTIAL |
| P6 Professional V26 | Global Calendars | https://docs.oracle.com/cd/G48902_01/client_help/en_US/globalcalendars.htm | 164 | `src/construction_pm/calendar_master_repository.py` | Global calendar (`calendar_type='global'`) | Global calendars are storable and addressable | Explicit reference resolves; no implicit default calendar | Default-global-calendar fallback is intentionally not implemented | Kind/type validation only | `tests/test_calendar_registry_production_builder.py` | `calendar-registry-traceability.md` | PARTIAL |
| P6 Professional V26 | Resource Calendars | https://docs.oracle.com/cd/G48902_01/client_help/en_US/resourcecalendars.htm | 166 | `src/construction_pm/p6_versioned_resource_calendar_resolver.py` | Resource calendar registration | Resource calendars are resolved version-pinned for resource capacity | Same calendar arithmetic as project calendars, own definition | Personal vs shared calendar distinction is not modeled | `build_calendar_registry_for_scope`, `WorkingTimeResolver` | `tests/test_p6_versioned_resource_calendar_resolver.py`, `tests/scheduling/test_activity_calendar_resource_leveling.py` | `logs/full-suite.log` | PARTIAL |
| P6 Professional V26 | Defining default hours per time period in calendars | https://docs.oracle.com/cd/G48902_01/client_help/en_US/defining_default_hours_per_time_period_in_calendars.htm | 160 | `src/construction_pm/calendar_work_hours_repository.py` | Work-hour rules | Persisted weekly rules are applied to the snapshot before registration | Work hours/standard work week must change calculation results | Dated detailed rules without a date key fail closed | `apply_weekly_work_hour_rules` | `tests/test_calendar_registry_production_builder.py::test_weekly_work_hour_rule_changes_the_registered_definition` | `logs/targeted.log` | MATCH |
| P6 Professional V26 | Assign a calendar to an activity | https://docs.oracle.com/cd/G48902_01/client_help/en_US/assign_a_calendar_to_an_activity.htm | 201 | `src/construction_pm/calendar_master_repository.py`, `src/construction_pm/scheduling/calendar_context.py` | Activity calendar assignment | `activity_calendar_assignment` rows produce `CalendarReference` per activity | Activity calendar must override the project calendar | No bulk assignment UI | Assignment repository + `SchedulingCalendarContext` | `tests/scheduling/test_activity_calendar_context.py` | `logs/full-suite.log` | MATCH |
| P6 Professional V26 | Choose a calendar for relationship lag | https://docs.oracle.com/cd/G48902_01/client_help/en_US/choose_a_calendar_for_relationship_lag.htm | 296 | `src/construction_pm/calendar_master_repository.py`, `src/construction_pm/scheduling/calendar_context.py` | Relationship lag calendar | Successor, project default and 24-hour options are persisted and validated | Lag arithmetic uses the selected calendar | 24-hour option cannot carry a reference (enforced) | `RelationshipLagCalendarAssignmentMaster` | `tests/scheduling/test_calendar_context.py`, `tests/test_calendar_context_validation.py` | `logs/full-suite.log` | MATCH |
| P6 Professional V26 | Schedule a project | https://docs.oracle.com/cd/G48902_01/client_help/en_US/schedule_a_project.htm | 294 | `src/construction_pm/scheduling/time_schedule.py`, `src/construction_pm/backend_p0/authoritative_schedule_query.py` | Authoritative time-aware scheduler | Forward/backward pass, floats and project finish computed from immutable inputs | Deterministic result independent of worker count | — | `time_schedule` + snapshot evaluation | `tests/scheduling`, `tests/integration/test_p0n2_runtime_activation.py` | `logs/full-suite.log`, `performance-benchmarks.md` | MATCH |
| P6 Professional V26 | Types of constraints / Enter activity constraints | https://docs.oracle.com/cd/G48902_01/client_help/en_US/enter_activity_constraints.htm | 295 | `src/construction_pm/scheduling/time_constraints.py` | Constraint application | Six closed-set constraint kinds are applied in the forward/backward pass | Constraints restrict dates without inventing dates | ASAP and P6's full dialog set are not all modeled | `TimeActivityConstraint`, `TimeConstraintType` | `tests/scheduling/test_constraints.py`, `tests/scheduling/test_time_constraints.py`, `tests/scheduling/test_backward_constraints.py` | `logs/full-suite.log` | PARTIAL |
| P6 Professional V26 | Define critical activities | https://docs.oracle.com/cd/G48902_01/client_help/en_US/define_critical_activities.htm | 290 | `src/construction_pm/scheduling/time_schedule.py`, `src/construction_pm/scheduling/schedule_options.py` | Float and critical-path computation | Floats are computed and returned per activity | Critical status respects a configurable float threshold | Threshold is exposed on the desktop options path, not yet on the time-aware job path | `critical_activity_float_threshold` | `tests/scheduling/test_time_float_search.py`, `tests/scheduling/test_time_float_parallelism.py` | `logs/full-suite.log` | PARTIAL |
| P6 Professional V26 | Calculate multiple float paths | https://docs.oracle.com/cd/G48902_01/client_help/en_US/calculate_multiple_float_paths.htm | 292 | `src/construction_pm/scheduling/schedule.py` | Multiple float paths | Implemented in the desktop scheduling engine | Longest-path ranking with an optional ending activity | Not yet wired into the time-aware worker path | `_multiple_float_paths` | `tests/scheduling/test_time_float_search.py` and related float suites | `logs/full-suite.log` | PARTIAL |
| P6 Professional V26 | Level resources / Leveling priority definitions | https://docs.oracle.com/cd/G48902_01/client_help/en_US/level_resources.htm | 300 | `src/construction_pm/scheduling/resource_leveling.py`, `src/construction_pm/p6_persisted_resource_leveling_resolver.py` | Resource leveling | Persisted leveling ranges/priorities resolve; leveling engine reorders within limits | Leveling respects priority and does not move mandatory dates | Not part of the durable job path in this change | Leveling engine + persisted resolver | `tests/scheduling/test_resource_leveling.py`, `tests/scheduling/test_leveling_scheduler.py`, `tests/scheduling/test_leveling_cross_project_priority.py` | `logs/full-suite.log` | PARTIAL |
| P6 Professional V26 | Job Services / Automating processes with Job Services | https://docs.oracle.com/cd/G48902_01/client_help/en_US/automating_processes_with_job_services.htm | 434 | `src/construction_pm/deployment/scheduling_worker.py`, `src/construction_pm/scheduling_job_lifecycle.py` | Durable scheduling jobs | Submit/queue/lease/execute/result with dedup, cancel, recovery | Jobs execute outside the request, exactly once, with a durable result | No recurring cron-style job definition UI | Worker + lifecycle service | `tests/integration/test_p0n2_runtime_activation.py`, `tests/test_scheduling_job_postgres.py` | `job-lifecycle-evidence.md` | PARTIAL |
| P6 Professional V26 | Working with multiple projects | https://docs.oracle.com/cd/G48902_01/client_help/en_US/workingwithmultipleprojects.htm | 507 | `src/construction_pm/scheduling_worker_scheduler.py`, `src/construction_pm/scheduling_execution_budget.py` | Multi-project execution | A global budget dispatches projects; per-project results keep their own hash | Fair capacity sharing, no over-subscription | Leveling across projects is separate | `GlobalWorkerScheduler`, `GlobalExecutionBudget` | `tests/scheduling/test_worker_scheduler.py`, `performance-benchmarks.md` | `multi-project-budget-evidence.md` | MATCH |
| P6 Professional V26 | Baselines / Creating Baselines | https://docs.oracle.com/cd/G48902_01/client_help/en_US/creatingbaselines.htm | 266 | `src/construction_pm/p6_baseline_api.py`, `src/construction_pm/p6_baseline_capture.py` | Baselines | Capture, update and query baseline activity/assignment data | Baseline is revision-pinned and immutable after capture | Not exercised by the runtime-activation path | Baseline repositories and APIs | `tests/test_p6_baseline_api.py`, `tests/test_p6_baseline_capture.py`, `tests/test_p6_baseline_update.py` | `logs/full-suite.log` | PARTIAL |
| P6 Professional V26 | Updating progress | https://docs.oracle.com/cd/G48902_01/client_help/en_US/updating_progress.htm | 280 | `src/construction_pm/p6_activity_progress_api.py`, `src/construction_pm/activity_progress_history.py` | Progress update | Activity progress and history are persisted and readable | Actuals feed the calculation through the snapshot | Not exercised by the runtime-activation path | Progress API + history | `tests/test_activity_progress_history.py`, `tests/test_p6_postgres_baseline_activity.py` | `logs/full-suite.log` | PARTIAL |
| P6 Professional V26 | Checking schedules | https://docs.oracle.com/cd/G48902_01/client_help/en_US/101393.htm | 296 | — | Schedule health checker | No P6-style schedule checker (logic/constraint/float quality report) | Report schedule-quality findings | Entire checker | Not implemented | — | `known-limitations.md` | MISSING |
| P6 Professional V26 | Summarize project data | https://docs.oracle.com/cd/G48902_01/client_help/en_US/summarize_project_data.htm | 433 | `src/construction_pm/scheduling/forward_pass.py` | Summarization | Calendars/forward pass compute dates; no project summarization service | Persist summarized project totals | Summarization service/UI | Not implemented as a job | `tests/scheduling/test_time_schedule_pipeline_parallelism.py` (engine only) | `known-limitations.md` | MISSING |
| P6 Professional V26 | Budgeting | https://docs.oracle.com/cd/G48902_01/client_help/en_US/budgeting.htm | 263 | `src/construction_pm/p6_earned_value_read_model.py` | Budgeting / earned value | EV read model exists; no budgeting workflow in this scope | Budget and spending plan totals | Workflow and UI | Not part of P0-N.2 | `tests/test_p6_earned_value_read_model.py` | `known-limitations.md` | MISSING |
| P6 Professional V26 | View a profile of resource allocation across all projects | https://docs.oracle.com/cd/G48902_01/client_help/en_US/view_a_profile_of_resource_allocation_across_all_projects.htm | 356 | — | Cross-project resource profile | No cross-project allocation profile read model | Allocation histogram across projects | Entire view | Not implemented | — | `known-limitations.md` | MISSING |

## 4. Notes on the gaps

* `PARTIAL` never means “assumed working”. Each partial row names the exact missing
  piece. For the runtime path the missing pieces are UI/workflow surfaces, not
  calculation behavior.
* `MISSING` rows are outside the P0-N.2 runtime activation. They are recorded so the
  matrix is honest, not hidden.
* No `BLOCKED_EXTERNAL` row: no Oracle access, credential or third-party dependency
  blocked any inspected topic. The only external artifact is the owner-supplied PDF,
  which was present, hashed and mapped.

## 5. HTML ↔ PDF cross-check

For every row above, the topic title was located in the HTML TOC
(`https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm`) and the same heading
was located in the PDF by exact heading match. Where a topic heading repeats (e.g. a
chapter landing page and a task page), the page of the first task-level occurrence is
recorded. `Calendars` appears at PDF page 159 as the chapter landing page; the
task-level pages are recorded separately (161, 164, 166).
