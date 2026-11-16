# P0-G evidence — adaptive worker budget and durable job execution

Date: 2026-11-16
Tested commit: `d2fc916e` (branch `p0/adaptive-workers`, based on `3b56a4c2`)
Engine: `cubi-26.0.0`, calculation identity `p0g-worker-benchmark`

## What was built

- `src/construction_pm/scheduling_execution_budget.py` — real capacity
  detection (CPU affinity, cgroup v1/v2 CPU quota, `MemAvailable`, cgroup
  memory limit), a deterministic policy that turns it into a worker count, one
  process-wide permit set, and an adaptive dispatch controller bounded by it.
- `src/construction_pm/scheduling_job_executor.py` — the single execution loop:
  discover → claim under a lease → acquire a budget permit → run the
  caller-supplied authoritative calculation → renew the lease while it runs →
  persist the canonical result. It adds no calculation logic.
- `src/construction_pm/scheduling_job_lifecycle.py` — worker-side queue
  discovery (`find_queued`, `count_pending`, `pending_count`, `queued_jobs`) and
  renewal now persists `CANCELLED` when a cancellation request is observed.
- `src/construction_pm/postgres_scheduling_job_lifecycle.py` — the same queue
  queries over PostgreSQL.
- `scripts/scheduling_worker_benchmark.py` — real multi-process benchmark.

## Measured on this host

Host: 4 logical CPUs (affinity 4, no cgroup quota), 5.93 GiB available memory.
Derived budget: **4 workers**, limited by CPU; memory alone would allow 8.

Every worker is a separate OS process connected to the local PostgreSQL 14.24
cluster. The parent submits 32 jobs, all sharing one immutable 200-activity
fixture and one engine identity; each child claims, calculates and persists.

| Workers | Wall (ms) | Throughput (jobs/s) | Speed-up | CPU cores used | p50 latency (ms) | p95 latency (ms) | p99 latency (ms) |
|---|---|---|---|---|---|---|---|
| 1 | 1,090.1 | 29.36 | 1.00x | 0.94 | 601.0 | 1,031.6 | 1,097.7 |
| 2 | 557.4 | 57.41 | 1.96x | 1.85 | 316.4 | 518.7 | 552.6 |
| 4 | 316.4 | 101.15 | 3.45x | 3.32 | 189.4 | 294.4 | 311.2 |

Queue wait (submit → claim) is the dominant part of latency, and it is what
parallel workers actually remove:

| Workers | p50 queue wait (ms) | p95 queue wait (ms) | p50 calculation (ms) |
|---|---|---|---|
| 1 | 569.2 | 1,000.0 | 31.3 |
| 2 | 284.7 | 487.0 | 31.6 |
| 4 | 156.9 | 262.4 | 32.4 |

Per-job calculation time is flat (31.3 → 32.4 ms, +3.5% at 4 workers from shared
CPU/memory bandwidth), so the gain comes from queue overlap, not from a faster
engine.

Canonical output equality: every run observed exactly one hash,
`2719a62c5717fbd11a022e107f53b97660097d14ad607be571e29740e6b8eacf`, equal to a
single-process reference calculation of the same fixture. All 32 jobs reached
`SUCCEEDED`, all 32 results were persisted, and pending count was 0 after the
drain at every worker count.

Resident memory: each worker peaked at about 48 MiB; the sum of worker peaks is
48 MiB (1), 96 MiB (2), 191 MiB (4) and 382 MiB (8).

### Workers beyond host capacity

The benchmark refuses 8/16/32 unless `--allow-oversubscription` is passed and
records them as refused with the reason. An informational oversubscribed run
was measured at 8 workers:

| Workers | Wall (ms) | Throughput (jobs/s) | CPU cores | p50 latency (ms) |
|---|---|---|---|---|
| 8 (oversubscribed) | 332.2 | 96.34 | 3.27 | 215.9 |

8 workers on 4 CPUs were 4.8% slower than 4 workers, confirming that exceeding
the derived budget is contention, not capacity. 16 and 32 workers were not run;
no number is claimed for them.

## Verification

- `tests/scheduling/test_execution_budget.py` — 18 tests: cgroup v1/v2 and
  `meminfo` parsing, detection on synthetic `/proc` and cgroup trees, missing
  trees, CPU/memory/policy-cap limits, the process-wide permit cap under 6
  concurrent threads, singleton and environment override rules, growth and
  shrink of the adaptive target, invalid inputs.
- `tests/scheduling/test_scheduling_job_executor.py` — 9 tests: drain with the
  real engine hash, identical output at 1/2/4 workers, two executors sharing one
  global budget, retryable requeue then success, terminal failure with no
  result, cancellation while calculating, engine identity mismatch before
  calculation, adaptive target below the hard budget.
- `tests/scheduling/test_scheduling_job_lifecycle.py` — renewal now asserted as
  a cancellation observation point that persists `CANCELLED`.
- `tests/test_scheduling_job_postgres.py` — one added PostgreSQL test drains a
  real queue through the executor (7 in this file).

## Not measured

- 16 and 32 workers, multi-host PostgreSQL and a real Cloud/Desktop/Mobile
  surface: this host has 4 CPUs and only a local cluster exists, so those are
  not claimed.
- Thread-level scaling inside one process: the authoritative calculation is
  Python CPU-bound and holds the GIL, so the deployment unit is one worker
  process with one permit. No thread-pool speed-up is claimed.
- End-to-end HTTP admission/polling: no HTTP surface was added.
- Memory-limit enforcement under pressure: the budget derives a memory worker
  cap and the per-job estimate is 512 MiB, but a measured out-of-memory run was
  not performed.
