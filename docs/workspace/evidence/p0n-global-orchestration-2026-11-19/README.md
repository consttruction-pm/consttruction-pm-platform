# P0-N — global orchestration, process placement and adaptive cache (2026-11-19)

Tested tree: commit `c9e15f0c596a013e4c94c7c4e4483cedfe8ce0e7`, tree
`b6ae4bc9ca7ceb514a572a878c7bbc9067cb67de`, branch `p0n-global-scheduler`.

Host: 4 logical CPUs (AMD EPYC, `sched_getaffinity` = 4), 8,131,540 kB RAM,
CPython 3.12.13, Linux 5.10 (x86_64). Full fingerprint in `environment.json`.

Every number below comes from the real engine on this host. Nothing is
extrapolated; a scenario that cannot finish is recorded as an error in the raw
JSON rather than estimated.

## What was run

| artifact | command |
|---|---|
| `benchmark-full.json/.log` | `python scripts/p0n_multi_project_benchmark.py --out .../benchmark-full.json` |
| `affinity-two-cpus.json/.log` | `taskset -c 0,1 python scripts/p0n_multi_project_benchmark.py --repeats 1 --only E_ten_large --skip-sweep --skip-soak --skip-baselines --budget 4` |
| `pytest-scheduling.log` | `python -m pytest tests/scheduling -q` |
| `pytest-postgres-adapter.log` | `python -m pytest tests/scheduling/test_p0n_postgres_adapter.py tests/test_scheduling_job_postgres.py -q` (DSN set) |
| `pytest-full-suite.log` | `python -m pytest -q -p no:cacheprovider` (DSN set) |
| `hashes.csv` | derived from `benchmark-full.json` (sequential vs every parallel run) |
| `source-sha256.txt`, `artifact-sha256.txt` | SHA-256 of the changed sources and of these artifacts |

Environment for the PostgreSQL runs:
`P6_TEST_POSTGRES_DSN=postgresql://postgres@127.0.0.1:55432/postgres`.

## Result (3 repeats, medians, budget 4)

| scenario | projects | wall ms | proj/s | P95 job ms | P95 wait ms | CPU % | peak RSS MB |
|---|---|---|---|---|---|---|---|
| A one large | 1 | 993 | 1.01 | 993 | 0 | 39.3 | 227 |
| B two large | 2 | 1,437 | 1.39 | 1,383 | 2 | 30.8 | 174 |
| C four large | 4 | 1,609 | 2.49 | 1,592 | 3 | 75.3 | 280 |
| D eight large | 8 | 3,352 | 2.39 | 1,812 | 1,579 | 74.7 | 290 |
| E ten large | 10 | 3,933 | 2.54 | 1,825 | 1,981 | 85.9 | 293 |
| F 10 large + 5 small | 15 | 4,240 | 3.54 | 1,811 | 2,155 | 85.6 | 291 |
| G 10 large + 20 small | 30 | 5,021 | 5.97 | 1,795 | 2,796 | 87.1 | 294 |
| H 10 large staggered | 10 | 3,960 | 2.52 | 1,824 | 1,979 | 85.6 | 293 |

Sequential on the same host: 30 projects 17,287 ms; ten large 13,397 ms.
Speedups: 10 large 3.41×, 30-project mix 3.44×, single 5k project 1.41× wall
(engine float pass 1,120 → 671 ms, 1.67×, P0-M reproduced).

Small-project latency: worst queue wait 88–93 ms when 10 large projects are
queued (F), 921–927 ms with 20 small projects also competing (G).

## Capacity sweep (ten large projects, one run per budget)

| slots | wall ms | CPU % | peak RSS MB | voluntary ctx switches |
|---|---|---|---|---|
| 1 | 13,689 | 24.7 | 132 | 2,593 |
| 2 | 6,952 | 48.5 | 186 | 1,315 |
| 4 | 3,955 | 85.5 | 292 | 745 |
| 8 | 3,682 | 92.8 | 505 | 695 |
| 16 | 3,671 | 93.1 | 601 | 691 |
| 32 | 4,180 | 95.2 | 1,039 | 1,381 |

Throughput saturates at 8 slots on four CPUs; 32 oversubscribes and loses 12%
against 16 while nearly doubling memory.

## Baselines

| shape | projects | wall ms | CPU % |
|---|---|---|---|
| sequential, one at a time | 4 large | 4,757 | 25.1 (1 core) |
| thread executor shape, 4 threads | 4 large | 5,093 | 25.1 (GIL) |
| `GlobalWorkerScheduler`, process mode | 4 large | 1,609 | 75.3 |

## Durable executor end to end

4 large + 4 small submitted through `SchedulingJobService`, executed by
`SchedulingJobExecutor(execution_mode="process")` on the in-memory adapter:
1,618 ms, 82.4% CPU, 8/8 process starts, `peak_slots = 4`, `slots_held = 0`
after the run, 8/8 persisted hashes equal to the sequential engine, 0 failures.
Sequential for the same eight projects: 5,635 ms (3.48×).

## Cache

Cold pass 3,939 ms with 0/10 hits; warm pass 0.2 ms with 10/10 hits, four
tenants isolated, 3,618 bytes stored, 0 evictions, 0 rejected entries.

## Soak

Eight iterations of two large projects (16 calculations): 11,567 ms total,
parent RSS 93.0 MB at every iteration (0.0 MB growth), `slots_held = 0` and
`budget.active = 0` after every iteration.

## Affinity cap

`taskset -c 0,1` (two CPUs) with budget 4 on the ten large projects:
7,416 ms at 46.3% of four CPUs = 1.85 of the two available cores (93%),
13.6 s of job CPU. The budget saturates whatever the OS actually grants.

## Correctness

`hashes.csv` lists the sequential and the parallel canonical hash for every
project in the catalogue: all 30 match. The same equality holds in every repeat
of every scenario (see `benchmark-full.json`, `hashes_match: true`) and on the
PostgreSQL adapter (`pytest-postgres-adapter.log`).

Tests: `tests/scheduling` 1,656 passed; full suite 5,161 passed, 132 skipped,
0 failed. New in P0-N: 47 tests across `test_worker_scheduler.py` (20),
`test_schedule_result_cache.py` (13), `test_scheduling_job_executor_process.py`
(11), `test_p0n_postgres_adapter.py` (3).

## What was not measured

* No application/API entry point instantiates `SchedulingJobExecutor`, so
  "end to end" means the executor loop with the service and adapter, not an
  HTTP request path. Wiring is P0-J scope.
* No cgroup v2 memory-limit run was possible in this sandbox; the cache's
  low-memory behaviour is covered by unit tests (`adapt` with an explicit
  `available_bytes`) and the soak, not by an OS-enforced memory cap.
* 16/32-worker caps are measured as scheduler budgets on four CPUs; they are
  not a claim about a 32-core host.
* Wavefront parallelism for forward/backward remains unimplemented and
  unmeasured here; P0-M's measurement is the reference.
