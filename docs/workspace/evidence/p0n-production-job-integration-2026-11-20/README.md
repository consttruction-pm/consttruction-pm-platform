# P0-N production job integration — evidence (2026-11-20)

Acceptance: a real API request submits a job, a worker executes it on the
optimized engine, and the same API returns the status and the result.

## Tested tree

```
commit 1b19e6172e7daeb70926d01c68d3f2a77e6d5fd5
tree   ac863807186fb6639d530d156d89780bfdfe63b6
parent f43df215e39ac0e58f4a3c005fec647af0398238
```

Exact source and test hashes are in `source-sha256.txt`; log hashes in
`artifact-sha256.txt`. Environment in `environment.json` (4 CPUs, CPython
3.12.13, PostgreSQL at `127.0.0.1:55432`).

## Commands and results

All commands ran from the repository root with
`P6_TEST_POSTGRES_DSN=postgresql://postgres@127.0.0.1:55432/postgres` and the
repository `pytest` configuration (`testpaths=["tests"]`,
`pythonpath=["src"]`).

| Log | Command | Result |
| --- | --- | --- |
| `targeted.log` | `python -m pytest tests/scheduling/test_scheduling_job_production_api.py tests/test_scheduling_job_http_routes.py tests/test_schedule_query_production_composition.py tests/test_scheduling_job_postgres.py -q` | 37 passed |
| `broader.log` | `python -m pytest tests/scheduling tests/test_scheduling_job_postgres.py tests/test_scheduling_job_http_routes.py tests/test_schedule_query_production_composition.py tests/test_project_lifecycle_http_routes.py tests/test_project_lifecycle_wsgi.py tests/test_authoritative_schedule_query.py -q` | 1,827 passed |
| `full-suite.log` | `python -m pytest -q` | 5,186 passed, 132 skipped, 0 failed |

The 132 skips are pre-existing environment-conditional skips; the log contains
no `FAILED` line.

## What the tests prove

* `test_submit_drain_status_and_result_match_the_direct_engine_hash` — the
  published `output_hash` equals a direct
  `AuthoritativeScheduleQueryProvider.execute` of the same snapshot.
* `test_process_mode_calculates_in_a_child_and_publishes_the_same_hash` — a
  real child process (`process_starts == 1`, `inline_fallbacks == 0`), the same
  hash, and a cache hit with no second process start on the repeat run.
* `test_process_timeout_marks_the_job_failed` — the job ends `FAILED` with
  `SCHEDULING_JOB_TIMEOUT`.
* `test_expired_lease_is_recovered_and_the_job_runs_once` — a lease left by a
  stopped worker is recovered on the next tick and executed exactly once
  (`attempts == 2`).
* `test_two_workers_never_execute_the_same_job_twice` — one invocation across
  two concurrent workers.
* `test_single_flight_deduplicates_a_queued_submission`,
  `test_same_fingerprint_with_different_run_parameters_conflicts` — no
  duplicate work, no parameter substitution under one fingerprint.
* `test_other_tenant_and_project_cannot_read_the_job`,
  `test_cross_scope_echo_and_missing_snapshot_are_rejected` — tenant and
  project isolation on read and submit.
* `test_worker_token_guards_tick_and_status`,
  `test_job_routes_require_a_session_and_worker_routes_require_the_token` —
  worker endpoints need `X-Worker-Token`; no token configured returns 404.
* `test_synchronous_schedule_query_route_is_unchanged` and the composition
  tests — `POST /api/v1/schedule/query` keeps its contract and response.
* `test_postgres_persists_run_parameters_and_deduplicates_by_identity`,
  `test_postgres_two_connections_recover_one_expired_lease_with_parameters` —
  the PostgreSQL adapter stores and restores the run parameters.

## Manual acceptance run

A standalone run against the real provider (SQLite snapshot, calculation
context repository, in-memory job store) reproduced the acceptance path:

```
submitted QUEUED {'activity_count': '3', 'project_revision': '4',
                  'relationship_count': '0', 'roles': '["project_admin"]',
                  'snapshot_id': 'S1'}
tick      {'claimed': 1, 'succeeded': 1, ...} idle True
state     SUCCEEDED
hash equal True
workload guard SCHEDULING_JOB_WORKLOAD_MISMATCH
missing snapshot SCHEDULING_JOB_SNAPSHOT_NOT_FOUND 404
```

## Known limit

`ProductionRuntime` still raises `SCHEDULE_QUERY_NOT_DEPLOYED` from
`_calendar_registry_not_wired`; the deployed runtime cannot compose a provider
that resolves calendars yet. The job routes are wired at the composition seam
and proven end-to-end with a real calendar registry.
