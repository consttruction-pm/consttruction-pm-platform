# P0-H evidence — intra-project parallelism in the time-aware float path

Date: 2026-11-16
Tested commit: `af8b38c0` (branch `p0/intra-project-floats`, based on `3ed3892c`)

## What was parallelized

The time-aware engine computes each activity's float independently from the
frozen early schedule, late schedule, relationships, calendars and lag
calendar. `calculate_time_floats` now accepts an execution-only `workers`
parameter that splits the sorted activity ids into contiguous chunks, evaluates
the same pure function in forked children and merges the immutable records by
id. Nothing about the inputs or the formula changed; only which process runs
it.

`time_schedule` exposes the same knob as `float_workers` and forwards it. The
default is 1 everywhere, so existing callers keep the sequential loop.

## Measured on this host

Host: 4 logical CPUs (affinity 4). `--mode time` benchmark, 2 runs after 1
warm-up, same fixture and seed, `output_sha256` compared.

| Activities | Float workers | Wall median (ms) | Speed-up | Parent CPU (ms) | Max child RSS (kB) |
|---|---|---|---|---|---|
| 5,000 | 1 | 3,350.0 | 1.00x | 3,349.6 | n/a |
| 5,000 | 2 | 2,155.5 | 1.55x | 903.0 | n/a |
| 5,000 | 4 | 1,482.7 | 2.26x | 837.9 | n/a |
| 20,000 | 1 | 13,462.5 | 1.00x | 13,461.0 | n/a |
| 20,000 | 2 | 8,516.5 | 1.58x | 3,420.1 | 53,592 |
| 20,000 | 4 | 5,923.9 | 2.27x | 3,375.5 | 53,764 |

The gain is bounded by the two passes that remain sequential: at 20,000
activities the forward and backward passes cost about 3.2 s, so 4 workers can
reach at best `1 / (0.24 + 0.76/4) ≈ 2.4x`; measured 2.27x. Parent CPU falls
from 13.5 s to 3.4 s because the float work leaves the parent, while child work
is not included in `cpu` (it is process CPU, not `RUSAGE_CHILDREN`).

Output equality: every worker count produced the same canonical hash at each
size — `3d2f1f8dc31c…` for 5,000 activities and `d6fb24752019…` for 20,000 —
and the parity tests compare every field of every record, not just the hash.

## What was deliberately not parallelized

- Date CPM forward/backward passes and the resource-leveling decision loop.
  Their steps are sequentially dependent by definition (a shift accepted in one
  iteration changes the next trial). Changing their execution order would risk
  a different V26 decision, so the existing implementation is retained
  unchanged.
- Thread-based parallelism. CPython holds the GIL for this CPU-bound Python
  code, so threads cannot speed it up; the measured path uses fork-based
  processes.
- Enabling the knob by default in a server process. `fork()` from a threaded
  process that may hold database or logging locks is unsafe, so
  `calculate_time_floats`/`time_schedule` fall back to the sequential loop when
  `threading.active_count() > 1`, and every existing caller keeps `workers=1`.
  A dedicated single-threaded worker bootstrap may opt in.

## Verification

`tests/scheduling/test_time_float_parallelism.py` — 6 tests:

- FS/SS/FF/SF edges with positive and negative lags and a float branch:
  sequential vs 2 and 3 workers compare equal field-by-field, with identical
  key order and types.
- A 200-activity deterministic network: full mapping equality.
- A 120-activity `time_schedule` run: `project_finish`, early, late and float
  mappings identical for `float_workers` 1 and 2.
- Deterministic chunking covers every id exactly once.
- Invalid worker counts (`0`, `-1`, `True`, `"2"`) raise `ValueError`.
- `Decimal` precision is identical across paths.

Full suite: 4,508 passed / 211 skipped without a database; 4,597 passed / 131
skipped with local PostgreSQL.

## Not measured

- 32+ activities per chunk with deeper calendars or time constraints: the
  measured fixture is a working-day DAG, and `time_schedule` with constraints
  would need its own parity run.
- Nested or daemon worker processes: the fork path is measured only from a
  single-threaded parent.
- Memory at very large sizes: child RSS is a maximum over children, not a sum.
