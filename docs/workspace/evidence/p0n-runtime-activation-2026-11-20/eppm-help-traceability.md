# EPPM Help traceability — P0-N.2

## 1. Reference identity

| Item | Value |
| --- | --- |
| Oracle help set | Primavera P6 EPPM Help, Version 26 |
| HTML help (authoritative) | https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm |
| Canonical source record | `docs/enterprise/CUBI_ENTERPRISE_PRIMAVERA_P6_EPPM_HELP_PARITY_V26.md` |
| User guides library | https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/user.html |
| Team Member help (separate set) | https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/toc.htm |

There is **no EPPM PDF** in this task. EPPM page references are therefore HTML topics
only; the `PDF Page` value is `N/A (HTML)` by design, not `MISSING`. The Professional
PDF is not a substitute for EPPM topics and vice versa (`two-environment-reference-map.md`).

All topic URLs below were read from the official EPPM V26 HTML table of contents
(`/p6help/en/toc.htm`). None was guessed.

## 2. Matrix

GitHub paths resolve at
`https://github.com/consttruction-pm/consttruction-pm-platform/blob/feat/p0n2-runtime-activation/<path>`.

| Environment | Oracle Help Topic | Oracle URL | PDF Page | GitHub Reference | CUBI Module | Current Behavior | Required Behavior | Gap | Implementation | Test | Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P6 EPPM V26 | About Calendars | https://docs.oracle.com/cd/G48897_01/p6help/en/17940.htm | N/A (HTML) | `src/construction_pm/calendar_master_repository.py` | Calendar master/snapshot repositories | Global, project and resource calendars are versioned and scope-bound | Enterprise calendars resolve revision-pinned | No enterprise calendar administration UI | Persisted rows + registry builder | `tests/test_calendar_registry_production_builder.py` | `calendar-registry-traceability.md` | MATCH |
| P6 EPPM V26 | Creating Global Calendars | https://docs.oracle.com/cd/G48897_01/p6help/en/38682.htm | N/A (HTML) | `src/construction_pm/calendar_master_repository.py` | Global calendar storage | `calendar_type='global'` supported | Global definition reusable by projects | No default-global fallback | Repository validation | `tests/test_calendar_master_repository.py` | `logs/full-suite.log` | PARTIAL |
| P6 EPPM V26 | Configuring the Standard Work Week for Global Calendars | https://docs.oracle.com/cd/G48897_01/p6help/en/44166.htm | N/A (HTML) | `src/construction_pm/calendar_work_hours_repository.py` | Work-hour rules | Weekly work-hour rules change the registered definition | Standard work week controls arithmetic | Detailed dated rules require a date key | `apply_weekly_work_hour_rules` | `tests/test_calendar_registry_production_builder.py` | `logs/targeted.log` | MATCH |
| P6 EPPM V26 | Creating Project Calendars | https://docs.oracle.com/cd/G48897_01/p6help/en/38683.htm | N/A (HTML) | `src/construction_pm/calendar_master_repository.py` | Project calendar | Project calendars stored with revision checks | Project calendar addressable by id@version | No enterprise calendar form | `p6_calendar_api.py` | `tests/test_p6_calendar_api.py` | `logs/full-suite.log` | PARTIAL |
| P6 EPPM V26 | Setting Work Hours Per Period for a Project Calendar | https://docs.oracle.com/cd/G48897_01/p6help/en/44170.htm | N/A (HTML) | `src/construction_pm/calendar_work_hours_repository.py` | Work-hour persistence | Persisted rules applied before registration | Per-period hours alter dates | Dated mode without date key fails closed | Work-hour repository | `tests/test_calendar_registry_production_builder.py` | `logs/targeted.log` | MATCH |
| P6 EPPM V26 | Creating Resource Calendars | https://docs.oracle.com/cd/G48897_01/p6help/en/38681.htm | N/A (HTML) | `src/construction_pm/p6_versioned_resource_calendar_resolver.py` | Resource calendar | Resource calendars resolve own definition | Version-pinned resource capacity | Personal/shared distinction absent | `build_calendar_registry_for_scope` | `tests/test_p6_versioned_resource_calendar_resolver.py` | `logs/full-suite.log` | PARTIAL |
| P6 EPPM V26 | Assigning Calendars to Resources | https://docs.oracle.com/cd/G48897_01/p6help/en/36458.htm | N/A (HTML) | `src/construction_pm/p6_versioned_resource_calendar_resolver.py` | Resource calendar assignment | Resource calendar chosen by stored reference | Assignment drives resource capacity | No bulk UI | Resolver registration | `tests/scheduling/test_activity_calendar_resource_leveling.py` | `logs/full-suite.log` | PARTIAL |
| P6 EPPM V26 | About Scheduling Projects | https://docs.oracle.com/cd/G48897_01/p6help/en/38594.htm | N/A (HTML) | `src/construction_pm/scheduling/time_schedule.py` | Authoritative scheduler | Forward/backward pass and floats from immutable inputs | Deterministic across worker counts | — | `time_schedule` | `tests/scheduling` | `logs/full-suite.log` | MATCH |
| P6 EPPM V26 | Configuring General Scheduling Options | https://docs.oracle.com/cd/G48897_01/p6help/en/37939.htm | N/A (HTML) | `src/construction_pm/scheduling/schedule_options.py` | Scheduling options | Options are validated and applied by the desktop engine | Options affect dates, lag calendar and float threshold | Time-aware job path does not expose every desktop option | `TimeScheduleOptions` | `tests/test_schedule_options_validation.py` | `logs/full-suite.log` | PARTIAL |
| P6 EPPM V26 | Configuring Advanced Scheduling Options | https://docs.oracle.com/cd/G48897_01/p6help/en/37940.htm | N/A (HTML) | `src/construction_pm/scheduling/schedule_options.py` | Advanced options | Multiple float paths and lag-calendar options exist on the desktop path | Advanced options preserved in calculation | Not wired into the durable worker path | `multiple_float_paths_*` | `tests/test_schedule_options_validation.py` | `logs/full-suite.log` | PARTIAL |
| P6 EPPM V26 | About Critical Path Activities | https://docs.oracle.com/cd/G48897_01/p6help/en/6623.htm | N/A (HTML) | `src/construction_pm/scheduling/time_schedule.py` | Critical path/float | Floats computed for every activity | Critical set follows the configured threshold | Threshold not on the time-aware job path | Float computation | `tests/scheduling/test_time_float_search.py` | `logs/full-suite.log` | PARTIAL |
| P6 EPPM V26 | About Resource Leveling | https://docs.oracle.com/cd/G48897_01/p6help/en/37757.htm | N/A (HTML) | `src/construction_pm/scheduling/resource_leveling.py` | Resource leveling | Leveling engine reorders within constraints | Respect priorities and mandatory dates | Not in durable job path | Leveling engine | `tests/scheduling/test_resource_leveling.py` | `logs/full-suite.log` | PARTIAL |
| P6 EPPM V26 | Leveling Project Resources | https://docs.oracle.com/cd/G48897_01/p6help/en/44311.htm | N/A (HTML) | `src/construction_pm/p6_persisted_resource_leveling_resolver.py` | Persisted leveling | Persisted priority/ranges feed leveling | Admin-configured priorities honored | No enterprise leveling UI | Resolver + engine | `tests/test_persisted_resource_leveling_resolver.py` | `logs/full-suite.log` | PARTIAL |
| P6 EPPM V26 | About Updating Progress | https://docs.oracle.com/cd/G48897_01/p6help/en/6626.htm | N/A (HTML) | `src/construction_pm/p6_activity_progress_api.py` | Progress update | Progress and history persisted | Actuals flow into the snapshot | Not exercised in P0-N.2 | Progress API | `tests/test_activity_progress_history.py` | `logs/full-suite.log` | PARTIAL |
| P6 EPPM V26 | About Baselines | https://docs.oracle.com/cd/G48897_01/p6help/en/6630.htm | N/A (HTML) | `src/construction_pm/p6_baseline_api.py` | Baselines | Capture/update/query baseline data | Revision-pinned baseline | Not exercised in P0-N.2 | Baseline APIs | `tests/test_p6_baseline_api.py` | `logs/full-suite.log` | PARTIAL |
| P6 EPPM V26 | Summarizing Projects | https://docs.oracle.com/cd/G48897_01/p6help/en/7984.htm | N/A (HTML) | — | Project summarization | No summarization service | Persist summarized project totals | Entire service | Not implemented | — | `known-limitations.md` | MISSING |
| P6 EPPM V26 | Running the Project Checker | https://docs.oracle.com/cd/G48897_01/p6help/en/101298.htm | N/A (HTML) | — | Project checker | No P6-style project checker | Report schedule-quality findings | Entire checker | Not implemented | — | `known-limitations.md` | MISSING |
| P6 EPPM V26 | About Project Scheduled Services | https://docs.oracle.com/cd/G48897_01/p6help/en/46217.htm | N/A (HTML) | `src/construction_pm/deployment/scheduling_worker.py` | Project scheduled services | Durable one-shot jobs execute on a worker | Scheduled/recurring service definitions execute exactly once per trigger | No recurrence/trigger scheduler | Worker + job lifecycle | `tests/integration/test_p0n2_runtime_activation.py` | `job-lifecycle-evidence.md` | PARTIAL |
| P6 EPPM V26 | Creating Project Scheduled Services | https://docs.oracle.com/cd/G48897_01/p6help/en/44525.htm | N/A (HTML) | `src/construction_pm/scheduling_job_lifecycle.py` | Scheduled service definition | Job request/run parameters persisted | Durable definition with audit | No service-definition record/UI | Job request/result records | `tests/test_scheduling_job_postgres.py` | `job-lifecycle-evidence.md` | PARTIAL |
| P6 EPPM V26 | Configuring Project Preferences for Multiple Projects | https://docs.oracle.com/cd/G48897_01/p6help/en/101110.htm | N/A (HTML) | `src/construction_pm/scheduling_worker_scheduler.py` | Multi-project execution | Global budget dispatches multiple projects | Fair, bounded concurrency | Cross-project leveling absent | `GlobalWorkerScheduler` | `tests/scheduling/test_worker_scheduler.py` | `multi-project-budget-evidence.md` | MATCH |
| P6 EPPM V26 | About the Check Resource Overallocation Service | https://docs.oracle.com/cd/G48897_01/p6help/en/49465.htm | N/A (HTML) | `src/construction_pm/p6_resource_leveling_read_adapter.py` | Overallocation read path | Leveling read adapter exposes demand/overallocation | Service reports overallocation per period | No enterprise service wrapper | Read adapter | `tests/test_p6_resource_leveling_read_adapter.py` | `logs/full-suite.log` | PARTIAL |

## 3. Interpretation boundaries

* EPPM scheduling is a server capability; the CUBI equivalent is the worker runtime and
  its durable jobs. A Professional-only command is not used to justify an EPPM row.
* EPPM `Project Scheduled Services` includes recurrence and server-side triggers. CUBI
  currently implements the durable one-shot execution half; recurrence is recorded as
  a gap, not claimed.
* EPPM reporting/portfolio/budgeting workflows are outside the P0-N.2 runtime scope and
  are not marked as parity.

## 4. Verification method

1. Read `docs/enterprise/CUBI_ENTERPRISE_PRIMAVERA_P6_EPPM_HELP_PARITY_V26.md` for the
   canonical source set and product-boundary rules.
2. Fetch `/p6help/en/toc.htm` and extract every topic href used above; no URL is
   constructed from a guessed filename.
3. Cross-check each CUBI claim against a source path or test path that exists in this
   tree; unrunnable claims are marked `MISSING`, not inferred.
