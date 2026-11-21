# Test matrix on the integrated head

Every result below was produced on `feat/p0n2-integration`, merge commit
`89ced6a7` plus the harness/test/evidence changes committed with it, against
PostgreSQL 14.24 at `127.0.0.1:55432`, CPython 3.12.13 on this 4-CPU host.

Environment for every command:

```bash
export P6_TEST_POSTGRES_DSN=postgresql://postgres@127.0.0.1:55432/postgres
export CONSTRUCTION_PM_POSTGRES_DSN="$P6_TEST_POSTGRES_DSN"
export PYTHONPATH=src
```

## 1. Required families, with the node that proves each

| # | Family | Exact node(s) | Where it ran |
| --- | --- | --- | --- |
| 1 | PostgreSQL job lifecycle | `tests/test_scheduling_job_postgres.py` (whole file), `tests/integration/test_p0n2_runtime_activation.py` | targeted + full |
| 2 | Thread placement | `test_http_submit_runs_on_real_worker_and_result_is_retrieved`, `test_duplicate_submit_is_single_flight_and_runs_once`, worker e2e `size=1000/5000 mode=thread` | targeted + benchmark |
| 3 | Process placement | `test_process_placement_runs_in_a_real_child_process`, `tests/scheduling/test_scheduling_job_executor_process.py`, worker e2e `size=1000/5000 mode=process` | process-placement run + benchmark |
| 4 | Result larger than the pipe buffer | `test_result_larger_than_the_pipe_buffer_does_not_deadlock` | process-placement run |
| 5 | Cancellation | `test_cancel_before_claim_prevents_execution`, `test_cancel_route_terminates_a_queued_job`, `test_cancellation_terminates_the_child_and_releases_slots`, `test_cancellation_while_calculating_never_publishes_a_result`, `test_cancel_queued_job_is_terminal`, `test_cancel_leased_job_is_cooperative_and_never_publishes_a_result`, `test_cancel_before_execution_prevents_the_calculation` | targeted + scheduling + full |
| 6 | Recovery | `test_postgres_expired_lease_is_recovered_by_another_worker`, `test_postgres_two_connections_recover_one_expired_lease_with_parameters`, `test_expired_lease_is_recovered_and_reclaimable`, `test_expired_lease_with_cancellation_request_is_cancelled`, `test_expired_lease_is_recovered_and_the_job_runs_once` | targeted + scheduling + full |
| 7 | Multi-tenancy | `test_job_is_not_visible_to_another_tenant_session`; project sweep runs 16 distinct tenants on the shared database | targeted + benchmark |
| 8 | Regression | full suite, `-p no:cacheprovider` | full-suite log |
| 9 | Calendar variants | `tests/test_calendar_registry_production_builder.py`, `tests/test_p6_versioned_resource_calendar_resolver.py`, the nine `tests/scheduling/test_*calendar*.py` files | calendar log |
| 10 | Workbench / Enterprise unaffected | the 20-file A/B set below, run on `origin/main` and on the integrated head | A/B logs |

## 2. Runs

### 2.1 Targeted integration set — `logs/targeted.log`

```
pytest -q -p no:cacheprovider \
  tests/integration/test_p0n2_runtime_activation.py \
  tests/test_calendar_registry_production_builder.py \
  tests/test_scheduling_job_postgres.py \
  tests/test_scheduling_job_http_routes.py \
  tests/test_schedule_query_production_composition.py \
  tests/test_production_web_app.py \
  tests/test_production_readiness.py \
  tests/scheduling/test_scheduling_job_production_api.py \
  tests/scheduling/test_scheduling_job_authoritative_path.py \
  tests/scheduling/test_scheduling_job_executor_process.py
```

Result: **134 passed, 2 warnings in 10.78 s**. The two warnings are the
pre-existing unregistered `pytest.mark.postgres` marker and import-time notices;
no failure and no skip.

### 2.2 Full suite — `logs/full-suite.log`

```
pytest -q -p no:cacheprovider
```

Result: **5492 passed, 1 skipped, 6 warnings, 15 subtests passed in 81.07 s**.
The skip is the pre-existing environmental one:

```
SKIPPED tests/validation/test_pmcontrols_oracle.py:11
could not import 'pmcontrols': No module named 'pmcontrols'
```

The count is 5492 rather than the pre-merge 5382 because main added its own tests
(AI Workbench, enterprise, preview, site) and this branch adds the composition and
deadlock tests; no test was removed.

### 2.3 Scheduling directory — `logs/scheduling.log`

```
pytest -q -p no:cacheprovider tests/scheduling
```

Result: **1671 passed, 1 warning in 33.65 s**.

### 2.4 Calendar family — `logs/calendar.log`

```
pytest -q -p no:cacheprovider \
  tests/test_calendar_registry_production_builder.py \
  tests/test_p6_versioned_resource_calendar_resolver.py \
  tests/scheduling/test_calendar.py tests/scheduling/test_calendar_context.py \
  tests/scheduling/test_calendar_exceptions.py tests/scheduling/test_calendar_resolution.py \
  tests/scheduling/test_calendar_system.py tests/scheduling/test_time_calendar.py \
  tests/scheduling/test_time_calendar_boundaries.py \
  tests/scheduling/test_activity_calendar_context.py \
  tests/scheduling/test_activity_calendar_resource_leveling.py
```

Result: **118 passed in 0.42 s**.

### 2.5 Process placement and the pipe-buffer regression — `logs/process-placement.log`

```
pytest -q -p no:cacheprovider -k "pipe_buffer or process" \
  tests/scheduling/test_scheduling_job_executor_process.py \
  tests/integration/test_p0n2_runtime_activation.py
```

Result: **13 passed, 11 deselected in 5.99 s**.

### 2.6 Live worker end to end

`results/worker-e2e-20261121T035740Z.json`: four runs against real PostgreSQL,
all `SUCCEEDED`, `attempts=1`, `hash_match=true`:

| size | mode | state | process starts | e2e ms |
| --- | --- | --- | --- | --- |
| 1000 | thread | SUCCEEDED | 0 | 527.7 |
| 1000 | process | SUCCEEDED | 1 | 549.6 |
| 5000 | thread | SUCCEEDED | 0 | 1090.7 |
| 5000 | process | SUCCEEDED | 1 | 1137.1 |

### 2.7 Workbench / Enterprise A/B — `logs/ab-workbench-main.log`, `logs/ab-workbench-integration.log`

Identical command on both trees (20 files covering AI Workbench HTTP and
orchestration, enterprise dashboard/repository/identity/organization/tasks/workbench,
global administration, identity session, preview runtime/concurrency, Vercel
entrypoint, and the three live PostgreSQL enterprise integration files):

| Tree | Result |
| --- | --- |
| `origin/main` = `c34ac05e` worktree | **264 passed, 15 subtests passed in 11.09 s** |
| integrated head | **264 passed, 15 subtests passed in 9.91 s** |

Same tests, same counts; the duration difference is host noise on a shared 4-CPU
sandbox.

### 2.8 Benchmarks

The full matrix, the capacity sweep at 1/2/4/8/16/32 slots, the project sweep and
the worker end-to-end runs are in
[performance-benchmarks.md](performance-benchmarks.md), rendered from
`results/matrix-20261121T035740Z.json` and
`results/worker-e2e-20261121T035740Z.json`. Every one of the 25 cells reported
`OK` and `hash equality PASS`; all 6 capacity points matched the 25000-mixed cell
hash; all 5 project points matched each project's own sequential hash.

## 3. How to read these results

- The targeted set is the mission checklist; the full suite is the regression
  guard, including main's new surfaces.
- Nothing here is inferred from the earlier P0-N.2 run: every log in `logs/` was
  produced on this integrated head, and every benchmark number is read from the
  JSON of this run.
- Wall-clock numbers include contention from the shared host; the pass/hash
  results do not depend on timing.
