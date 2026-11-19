# P0-N stability follow-up — shared SQLite snapshot reads

Pinned to code commit `6d89de5e` (tree `0284dded`, recorded in
`tested-tree.txt`) plus the docs commit `02ce356b`; every run listed here was
executed on that branch.

## Symptom

The post-merge suite on `main` at `d54cf847` (docs-only) reported
`1 failed, 5160 passed, 132 skipped`:

```
FAILED tests/scheduling/test_scheduling_job_authoritative_path.py::test_job_path_runs_the_authoritative_snapshot_engine_end_to_end
assert summary.succeeded == 3  ->  assert 1 == 3
process_starts=0, failed=2
```

The same test had failed once earlier (before P0-N) and then passed five
consecutive isolated runs and two full suites, so it was initially recorded as
flaky. It is not: it is a real thread-safety defect in the persistence adapter.

## Root cause

`SQLiteScheduleInputSnapshotRepository` is shared by the executor's worker
threads. `check_same_thread=False` permits cross-thread calls but does not make
interleaved statement execution safe: one thread's `execute` can reset another
thread's statement. The provider then reads a missing or foreign row and raises
`ValueError: SCHEDULE_INPUT_SNAPSHOT_NOT_FOUND`, which the executor records as
`FAILED`.

Direct probe (`regression-before-fix.log`, eight threads x 2,000 reads on one
shared connection) returns, depending on interleaving:
`INVALID_PROJECT_REVISION`, `INVALID_SNAPSHOT_TIMESTAMP`, `REVISION_CONFLICT`,
`INVALID_SNAPSHOT_HASH`, and
`sqlite3.InterfaceError: bad parameter or other API misuse`.

## Fix

`src/construction_pm/schedule_input_snapshot_repository.py`: every connection
access (`save`, `get`, `list`, `migrate_calculation_identity`) is serialised by
a reentrant per-repository lock (`RLock`, because migration re-enters `get`).
No query, revision rule, persisted content, or calculation path changed.

Regression test:
`tests/test_schedule_input_snapshot_repository.py::test_sqlite_shared_connection_is_safe_for_concurrent_readers`
(eight threads x 250 `get` + `list` calls). With the lock disabled it fails
3 of 3 runs; with the lock it passes.

## Artifacts

| artifact | command |
|---|---|
| `regression-before-fix.log` | probe harness reproducing the failure with the lock bypassed (`failed 3 of 3 runs without the lock`) |
| `p0j-repeat-20.log` | `for i in $(seq 1 20); do python -m pytest -q tests/scheduling/test_scheduling_job_authoritative_path.py; done` (20 x `3 passed`) |
| `scheduling-and-repository.log` | `python -m pytest -q tests/test_schedule_input_snapshot_repository.py tests/scheduling` -> 1,684 passed |
| `full-suite.log` | `python -m pytest -q -p no:cacheprovider` with `P6_TEST_POSTGRES_DSN`/`CONSTRUCTION_PM_POSTGRES_DSN` set -> 5,340 passed, 1 skipped, 0 failed |
| `post-fix-quick.json/.log` | `python scripts/p0n_multi_project_benchmark.py --quick --repeats 1 --skip-sweep --skip-soak --skip-baselines --skip-executor` -> 8/8 scenarios hash=ok, cache cold/warm ok |
| `post-fix-full.json/.log` | `python scripts/p0n_multi_project_benchmark.py --out ...` -> 24/24 scenario repeats hash=ok, sweep 1/2/4/8/16/32 hash=ok, executor 8/8 succeeded (process mode), cache warm 10/10 hits, soak RSS growth 0.0 MB |

`environment.json` records the host; `source-sha256.txt` pins the changed files;
`tested-tree.txt` pins the tested commit and tree.

## What did not change

Every scenario repeat (24/24), capacity point (6/6), executor job (8/8) and
cache hit (10/10) in the post-fix full benchmark matched the run's sequential
baseline hash. Scenario E reproduces in 3,899 ms (2.57 projects/s) against
3,933 ms in the P0-N report, and the capacity sweep at 1/2/4/8/16/32 slots in
13,605 / 6,939 / 3,926 / 3,674 / 3,531 / 4,124 ms against 13,689 / 6,952 /
3,955 / 3,682 / 3,671 / 4,180 ms — the same shape, within run-to-run
variation. The executor ends 8/8 succeeded with `process_starts=8`,
`peak_slots=4`, and the soak keeps RSS flat at 94.3 MB with
`slots_held_after=0`.
