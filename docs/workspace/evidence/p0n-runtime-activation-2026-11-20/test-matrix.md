# Test matrix — P0-N.2

All results below were produced on this host (4 logical CPUs, CPython 3.12.13,
PostgreSQL 14.24 at `127.0.0.1:55432`) at feature commit `8fdb06a9` unless stated.

Commands use the repository `pytest` configuration (`testpaths=["tests"]`,
`pythonpath=["src"]`). Environment:
`P6_TEST_POSTGRES_DSN=postgresql://postgres@127.0.0.1:55432/postgres` and
`CONSTRUCTION_PM_POSTGRES_DSN` set to the same URL.

## 1. Required test families from the mission

| # | Required family | Where | Result |
| --- | --- | --- | --- |
| 1 | API/Job lifecycle | `tests/integration/test_p0n2_runtime_activation.py`, `tests/test_scheduling_job_postgres.py`, `tests/test_scheduling_job_http_routes.py`, `tests/scheduling/test_scheduling_job_production_api.py` | pass |
| 2 | Calendar variants (working-day / working-time, base inheritance, exceptions, work hours) | `tests/test_calendar_registry_production_builder.py`, `tests/test_p6_versioned_resource_calendar_resolver.py`, `tests/scheduling/test_calendar*.py`, `tests/scheduling/test_time_calendar*.py` | pass |
| 3 | Capacity 1/2/4/8/16 workers and 1/2/4/8/16 projects | `scripts/p0n2_runtime_matrix.py` (capacity + project sweeps) | see `performance-benchmarks.md` |
| 4 | Sizes 1k/5k/25k/50k/100k | `scripts/p0n2_runtime_matrix.py` | see `performance-benchmarks.md` |
| 5 | Shapes chain/wide/mixed/resource-heavy/constraint-heavy | `scripts/p0n2_runtime_matrix.py` | see `performance-benchmarks.md` |
| 6 | Hash equivalence | integration suite (`output_hash == payload.calculation_run_identity`) and benchmark sequential-vs-parallel hashes | pass |
| 7 | Snapshot/revision/calendar-version consistency | integration suite (scope/revision, missing version, base resolution), calendar builder tests | pass |
| 8 | Retrieval authorization | `...::test_job_is_not_visible_to_another_tenant_session` | pass |
| 9 | Cancellation/recovery/failure | integration cancel test; `test_expired_lease_is_recovered_and_the_job_runs_once`; `test_process_timeout_marks_the_job_failed`; `test_cancel_leased_job_is_cooperative_and_never_publishes_a_result` | pass |

## 2. Targeted run

Command (see `logs/targeted.log`):

```
P6_TEST_POSTGRES_DSN=... PYTHONPATH=src python -m pytest -q \
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

Result: **114 passed, 2 warnings** (5.51 s).

## 3. Full suite

Command (see `logs/full-suite.log`):

```
P6_TEST_POSTGRES_DSN=... CONSTRUCTION_PM_POSTGRES_DSN=... \
PYTHONPATH=src python -m pytest -q -p no:cacheprovider
```

Result: **5381 passed, 1 skipped, 6 warnings** (77.98 s).

The single skip is environmental and pre-existing:

```
SKIPPED [1] tests/validation/test_pmcontrols_oracle.py:11:
could not import 'pmcontrols': No module named 'pmcontrols'
```

No `FAILED` line appears in the log.

## 4. Area counts (collection)

| Area | Tests |
| --- | --- |
| `tests/scheduling` | 1,670 |
| Job lifecycle/production/HTTP/Postgres files | 69 |
| Core leveling files | 136 |
| Calendar repositories/resolver/context/registry files | 81 |
| `tests/integration/test_p0n2_runtime_activation.py` | 11 (requires DSN) |
| `tests/test_calendar_registry_production_builder.py` | 6 |

## 5. CI

See `final-acceptance-report.md` §CI for the exact-head check run on the final SHA.
Local results above are the pre-push evidence; CI is recorded separately and is not
inferred from these numbers.
