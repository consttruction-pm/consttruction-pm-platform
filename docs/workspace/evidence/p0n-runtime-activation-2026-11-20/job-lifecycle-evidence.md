# Durable job lifecycle evidence — P0-N.2

Scope: submit → execute → retrieve on a real PostgreSQL database with a real worker,
including deduplication, cancellation, recovery and failure paths. The web runtime does
not execute jobs; the standalone worker does (`runtime-composition-map.md`).

## 1. State machine

`QUEUED → LEASED → SUCCEEDED | FAILED | CANCELLED`

| Transition | Guard |
| --- | --- |
| submit | validates the snapshot/run parameters; single-flight key `(tenant, project, dedup_scope, fingerprint)`; `stable_job_id` |
| claim/lease | CAS on `revision`; one winner across connections/processes |
| renew | lease CAS; heartbeat thread in thread mode, parent thread in process mode |
| complete | `put_result` first, then CAS to `SUCCEEDED` |
| cancel | allowed before claim; a leased job observes cooperative cancellation |
| recover | `recover_expired` reclaims an expired lease; exhausted attempts → `FAILED` |

## 2. Worker implementation

`src/construction_pm/deployment/scheduling_worker.py`

* `ThreadLocalConnection`: one autocommit psycopg connection per thread, so the
  heartbeat and the executing thread never share a connection.
* `SchedulingWorkerSettings.from_environment`: database URL, mode, owner, slots
  (1–128), poll interval, job timeout, connect timeout.
* `SchedulingWorkerRuntime`: initializes schema on a dedicated connection, creates the
  global budget, calendar repositories, scoped registry factory, provider, job service
  and runner. `run_once`, `drain`, `run_forever`, `snapshot`, `close`.
* Process placement: `run_scheduled_job_in_child(dsn, job, slots)` reconnects inside the
  child and rebuilds every repository from the DSN; only a picklable job crosses the
  boundary.

Result integrity: `answer_to_job_result` refuses a provider answer without a source
reference (`SCHEDULING_JOB_RESULT_WITHOUT_SOURCE`) or without mapping data, and
publishes `output_hash = source_refs[0].content_hash`.

Failure diagnosability: `execute_job_with_provider` maps `BackendApplicationError` to
`SchedulingExecutionError("<category>:<code>")`. `schedule_evaluator.py` appends the
closed-set reason to `SCHEDULE_EVALUATION_FAILED:<detail>`, so a missing calendar is
observable as e.g. `validation:SCHEDULE_EVALUATION_FAILED:calendar not registered:
CAL-ABSENT@1`.

## 3. Live proof (PostgreSQL 14.24 + real worker)

File: `tests/integration/test_p0n2_runtime_activation.py` — **11 passed**.

| Test | Behaviour proved |
| --- | --- |
| `test_http_submit_runs_on_real_worker_and_result_is_retrieved` | HTTP submit → `QUEUED` → real worker → `SUCCEEDED`; `output_hash == payload.calculation_run_identity` |
| `test_duplicate_submit_is_single_flight_and_runs_once` | second submit returns the same `job_id`; final `attempts == 1` |
| `test_missing_calendar_makes_the_real_job_fail_closed` | `FAILED`; `last_error` carries `CAL-ABSENT@1`; no default calendar substituted |
| `test_cancel_before_claim_prevents_execution` | `CANCELLED`; `attempts == 0` |
| `test_process_placement_runs_in_a_real_child_process` | `process_starts >= 1`, `SUCCEEDED` |
| `test_job_is_not_visible_to_another_tenant_session` | other-tenant GET returns 403; its own job is cancelled |

Complementary suites (real PostgreSQL or in-memory service):

```
tests/test_scheduling_job_postgres.py                       9 passed
tests/scheduling/test_scheduling_job_lifecycle.py           ...
tests/scheduling/test_scheduling_job_production_api.py      (includes two-worker, recovery, process timeout)
tests/scheduling/test_scheduling_job_executor_process.py    (12 tests: cancellation, lease renewal, pipe-buffer regression)
tests/test_scheduling_job_http_routes.py                    ...
```

Key companion tests:

* `test_postgres_expired_lease_is_recovered_by_another_worker`
* `test_postgres_two_connections_recover_one_expired_lease_with_parameters`
* `test_two_workers_never_execute_the_same_job_twice`
* `test_expired_lease_is_recovered_and_the_job_runs_once`
* `test_process_timeout_marks_the_job_failed`
* `test_result_larger_than_the_pipe_buffer_does_not_deadlock`
* `test_cancellation_terminates_the_child_and_releases_slots`
* `test_lease_is_renewed_while_the_child_calculates`
* `test_cancel_leased_job_is_cooperative_and_never_publishes_a_result`
* `test_postgres_result_is_immutable_per_job`

## 4. Observed output

Direct run on 2026-11-20 (real PostgreSQL, real worker), 5 activities, two slots:

Thread mode (`logs/live-job-run-thread.log`):

```
submitted QUEUED job 4d613d4c… state QUEUED
finished  SUCCEEDED attempts 1
drain     {"claimed": 1, "succeeded": 1, "failed": 0, "cancelled": 0,
           "retried": 0, "lease_lost": 0, "process_starts": 0,
           "inline_fallbacks": 0, "cache_hits": 0, "cache_misses": 0,
           "peak_slots": 0, "stopped": false}
output_hash               ddd8648e11b8d3b578b08db829bc92c2d6d59b1b1739aa3f0daf1e3b1c4fd684
calculation_run_identity  ddd8648e11b8d3b578b08db829bc92c2d6d59b1b1739aa3f0daf1e3b1c4fd684
hash_equal                true
last_error                null
```

Process mode (`logs/live-job-run-process.log`):

```
submitted QUEUED job 885be1af… state QUEUED
finished  SUCCEEDED attempts 1
drain     {"claimed": 1, "succeeded": 1, "failed": 0, "cancelled": 0,
           "retried": 0, "lease_lost": 0, "process_starts": 1,
           "inline_fallbacks": 0, "cache_hits": 0, "cache_misses": 0,
           "peak_slots": 1, "stopped": false}
output_hash               c40a83732e49fec386fe2c26d8882800f69b503bf7c91a4eede49d243bffc5ed
calculation_run_identity  c40a83732e49fec386fe2c26d8882800f69b503bf7c91a4eede49d243bffc5ed
hash_equal                true
last_error                null
```

The two runs used different random tenants/snapshots, so the hashes differ by input;
within each run the published hash equals the payload identity. `process_starts = 1`
proves the process run executed in a child, and `inline_fallbacks = 0` proves it did
not silently fall back to the parent.

### 4.1 Defect found and fixed during activation: child-result pipe deadlock

Process placement initially timed out for real workloads while the 4-activity
integration test passed. Root cause was in `scheduling_job_executor.py`, not in the
engine:

* the child published the pickled result with `sender.send(("ok", result))`;
* the parent waited for the child to exit (`process.join`) **before** reading the
  pipe (`receiver.poll` / `recv`).

A child whose result exceeds the OS pipe buffer stays blocked inside `send` until the
parent drains it, so the parent and child waited on each other until
`job_timeout`, and the job was retried as `SCHEDULING_JOB_TIMEOUT`. Small results
(below the buffer) exited and passed, which is why only the 4-activity test was green.

Fix: `_reap_process_jobs` now drains the pipe with a non-blocking `poll`/`recv` into
`_ProcessJob.payload` **while the child may still be alive**, and only then checks
existence/timeout; `_finish_process_job` publishes the already-read payload instead
of reading after `join`. EOF or a truncated pickle is treated as "no payload" and
still reported as `CHILD_EXITED_WITHOUT_RESULT`.

Regression test `tests/scheduling/test_scheduling_job_executor_process.py::
test_result_larger_than_the_pipe_buffer_does_not_deadlock` publishes a 2 MB payload
(well above the pipe buffer):

```
old code: 1 failed in 60.34s  (succeeded=0, retried=1, job_timeout=60)
new code: 12 passed in 5.11s
```

## 5. Targeted suite

`logs/targeted.log` (commit `8fdb06a9`):

```
114 passed, 2 warnings in 5.51s
```

Command:

```
P6_TEST_POSTGRES_DSN=postgresql://postgres@127.0.0.1:55432/postgres \
PYTHONPATH=src python -m pytest -q \
  tests/integration/test_p0n2_runtime_activation.py \
  tests/test_calendar_registry_production_builder.py \
  tests/test_scheduling_job_postgres.py \
  tests/test_scheduling_job_http_routes.py \
  tests/test_schedule_query_production_composition.py \
  tests/test_production_web_app.py \
  tests/test_production_readiness.py \
  tests/scheduling/test_scheduling_job_production_api.py \
  tests/scheduling/test_scheduling_job_authoritative_path.py
```

## 6. GitHub references

* `src/construction_pm/scheduling_job_lifecycle.py`
* `src/construction_pm/postgres_scheduling_job_lifecycle.py`
* `src/construction_pm/scheduling_job_runner.py`
* `src/construction_pm/scheduling_job_executor.py`
* `src/construction_pm/deployment/scheduling_worker.py`
* `src/construction_pm/schedule_evaluator.py`
* `tests/integration/test_p0n2_runtime_activation.py`

Published on `feat/p0n2-runtime-activation` at `8fdb06a9`.
