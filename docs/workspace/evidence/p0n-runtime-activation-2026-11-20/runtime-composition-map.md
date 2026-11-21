# Runtime composition map — P0-N.2 (2026-11-20)

Branch: `feat/p0n2-runtime-activation`
Base: `ae6e72e4` (`main`)
Feature head at measurement time: `5b4cfb71`
Environment: `environment.json` in this directory.

## 1. Web runtime (request path)

```
api/index.py
  └─ deployment.production_runtime.ProductionRuntime            production_runtime.py:299
       ├─ settings / PostgresConnectionPool
       ├─ schema.initialize_production_schema                  deployment/schema.py
       │    ├─ PostgresCalendarMasterRepository.initialize()
       │    ├─ PostgresCalendarSnapshotRepository.initialize()
       │    ├─ PostgresCalendarWorkHourRepository.initialize()
       │    ├─ PostgresCalendarExceptionRepository.initialize()
       │    └─ initialize_scheduling_job_schema()
       ├─ RequestConnection (ContextVar proxy)                 production_runtime.py
       ├─ PostgresCalendarMasterRepository(RequestConnection)   production_runtime.py:363
       ├─ PostgresCalendarSnapshotRepository(RequestConnection) production_runtime.py:364
       ├─ PostgresCalendarExceptionRepository(RequestConnection)production_runtime.py:365
       ├─ PostgresCalendarWorkHourRepository(RequestConnection) production_runtime.py:366
       ├─ _calendar_registry_for_scope_factory(...)             production_runtime.py:271
       ├─ PostgresSchedulingJobRepository(RequestConnection)    production_runtime.py:375
       └─ http.production_composition.build_project_lifecycle_wsgi_app(
              scoped_calendar_registry_factory=...,
              scheduling_job_repository=...,
              runner=None)                                      production_runtime.py:376-381
```

`build_project_lifecycle_wsgi_app` (`src/construction_pm/http/production_composition.py`)
constructs `ProjectLifecycleWsgiApp` → `ProjectLifecycleHttpRoutes`, and passes the
scoped factory and the job repository to
`AuthoritativeScheduleQueryProvider`
(`src/construction_pm/backend_p0/authoritative_schedule_query.py`). The provider calls
`_registry_for(snapshot.scope)`, so every request evaluates against calendars read for
that snapshot's own tenant/project/revision.

Routes served by this runtime (unchanged contracts, now backed by the real engine):

| Route | Owner | Execution |
| --- | --- | --- |
| `POST /api/v1/schedule/query` | `AuthoritativeScheduleQueryProvider.execute` | synchronous evaluation of the persisted snapshot |
| `POST /api/v1/scheduling/jobs` | `scheduling_job_api` | persists `QUEUED`; **does not execute here** |
| `GET /api/v1/scheduling/jobs/{id}` | `scheduling_job_api` | status/attempts/last_error |
| `POST /api/v1/scheduling/jobs/{id}/cancel` | `scheduling_job_api` | `CANCELLED` before claim |
| `GET /api/v1/scheduling/jobs/{id}/result` | `scheduling_job_api` | published result and `output_hash` |

The web runtime is constructed with **no runner**, so execution endpoints cannot run
inside a request context. This is deliberate: see §3.

## 2. Worker runtime (execution path)

```
deployment/scheduling_worker.py
  SchedulingWorkerRuntime
    ├─ ThreadLocalConnection(dsn)          one autocommit connection per thread
    ├─ initialize_production_schema()      via a dedicated connection
    ├─ GlobalExecutionBudget(slots)
    ├─ PostgresCalendar*Repository(ThreadLocalConnection)
    ├─ build_calendar_registry_for_scope() scoped factory
    ├─ AuthoritativeScheduleQueryProvider (float_execution policy from slots)
    ├─ SchedulingJobService(PostgresSchedulingJobRepository(...))
    └─ SchedulingEngineJobRunner(
           provider=provider,                 thread mode
           child_database_url=dsn)            process mode
```

Entry points: `python -m construction_pm.deployment.scheduling_worker --once|--drain|--forever`.
Settings come from `CONSTRUCTION_PM_DATABASE_URL`,
`CONSTRUCTION_PM_SCHEDULING_WORKER_MODE` (`thread|process`),
`CONSTRUCTION_PM_SCHEDULING_WORKER_OWNER`,
`CONSTRUCTION_PM_SCHEDULING_WORKER_SLOTS`,
`CONSTRUCTION_PM_SCHEDULING_WORKER_POLL`,
`CONSTRUCTION_PM_SCHEDULING_WORKER_JOB_TIMEOUT`.

Process mode crosses the process boundary with only a picklable DSN and job:
`run_scheduled_job_in_child(dsn, job, slots)` reconnects and rebuilds every repository
inside the child (`scheduling_job_runner.py`). No live connection or ContextVar is
pickled.

## 3. Why execution is not in the request

Measured constraints in the previous implementation:

* `RequestConnection` binds one psycopg connection per HTTP request via a ContextVar.
* The thread executor renews leases from a heartbeat thread; a ContextVar set in the
  request thread is not visible there, and one psycopg connection is not safe for
  concurrent threads.
* Process placement must pickle the calculate callable; a runner holding a live
  connection cannot be pickled.

The worker owns its connections and its budget, which also makes capacity control
(`CONSTRUCTION_PM_WORKER_SLOTS`, `GlobalExecutionBudget`) explicit rather than
per-request.

## 4. Data flow for one job

1. `POST /api/v1/scheduling/jobs` validates the snapshot and persists a `QUEUED` job
   with the single-flight key `(tenant, project, dedup_scope, fingerprint)`.
2. Worker `run_once` leases with a CAS on `revision`, writes `LEASED`, and executes.
3. `AuthoritativeScheduleQueryProvider.execute` loads the immutable snapshot and
   calculation context, builds the scope-bound registry, and runs `time_schedule`.
4. `answer_to_job_result` requires at least one `source_ref` and publishes
   `output_hash = source_refs[0].content_hash` with the payload.
5. `put_result` then CAS `SUCCEEDED`. Failures map to
   `SchedulingExecutionError("<category>:<code>", retryable=...)`; the operator sees
   the closed-set reason in `last_error`.
6. `GET .../result` returns the persisted payload; its
   `calculation_run_identity` equals `output_hash` (proved in the integration suite).

## 5. Composition invariants checked by tests

| Invariant | Test |
| --- | --- |
| Production source no longer contains `_calendar_registry_not_wired` or `SCHEDULE_QUERY_NOT_DEPLOYED` | `tests/integration/test_p0n2_runtime_activation.py::test_production_runtime_source_no_longer_contains_the_wiring_blocker` |
| Registry is built from rows, not defaults | `...::test_calendar_registry_is_built_from_persisted_calendars` |
| Registry is scope-bound and hash-stable | `...::test_calendar_registry_is_scoped_and_hash_is_stable` |
| Unknown version fails closed | `...::test_missing_calendar_version_fails_closed_without_latest_fallback` |
| Unknown base fails closed | `...::test_unregistered_base_calendar_fails_closed` |
| HTTP submit → worker → result | `...::test_http_submit_runs_on_real_worker_and_result_is_retrieved` |
| Cross-tenant reads are denied | `...::test_job_is_not_visible_to_another_tenant_session` |
