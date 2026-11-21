# Measured limits and non-claims

All numbers below are read from `results/matrix-20261121T035740Z.json` and
`results/worker-e2e-20261121T035740Z.json` (rendered in
[performance-benchmarks.md](performance-benchmarks.md)). Nothing on this page is
extrapolated beyond what was measured. The host is a 4-logical-CPU sandbox with
8 GB RAM; the same PostgreSQL instance is shared with the test suites.

## 1. Constraint-heavy cost grows quadratically, not linearly

| activities | constraints | seq median ms | par median ms | seq/par |
| --- | --- | --- | --- | --- |
| 1,000 | 143 | 324.1 | 239.9 | 1.35 |
| 5,000 | 715 | 3,437.9 | 2,949.9 | 1.17 |
| 25,000 | 3,572 | 69,367.8 | 67,287.7 | 1.03 |
| 50,000 | 7,143 | 289,739.9 | 284,398.3 | 1.02 |
| 100,000 | 14,286 | 1,163,644.8 | 1,164,731.2 | 1.00 |

Doubling the size from 25k to 50k multiplies the time by 4.18 (sequential) and
4.23 (parallel); 50k to 100k multiplies it by 4.02 and 4.10. That is quadratic
growth with size. The unconstrained `mixed` shape over the same sizes grows
linearly (6,576.5 → 13,502.1 → 27,426.3 ms, about 2.03× per doubling), so the
quadratic term is specific to the `START_NO_EARLIER_THAN` constraint set, not to
the engine's baseline.

At 100,000 activities the constraint-heavy cell takes **1,163.6 s sequential and
1,164.7 s parallel** (about 19.4 minutes per mode), versus 27.4 s / 16.6 s for
`mixed` of the same size. That is a 42× / 70× cost multiplier.

Consequences that are measured, not predicted:

- Parallel placement gives almost no speedup on constraint-heavy cells: parallel
  costs 0.74× the sequential time at 1k but 0.86× at 5k, 0.97× at 25k, 0.98× at
  50k and 1.00× at 100k. The more constrained work there is, the less of it can
  run concurrently.
- The 100k constraint-heavy cell needed the per-mode budget raised from the
  default 180 s to 1,800 s (`--mode-budget 100000=1800`); even at that budget it
  used about 1,164 s per mode. The 1,000–50,000 constraint cells fit in their
  default budgets.

What is **not** claimed: the cause of the quadratic term, an upper bound on size,
or that the same curve holds for other constraint mixes. Only this fixture
(`TimeActivityConstraint(START_NO_EARLIER_THAN)` on every seventh activity,
`time_network(..., "dag")`) was measured.

## 2. Capacity saturates at 4 slots on this host

25000 `mixed`, one run per slot count:

| slots | float workers | engine ms | speedup vs 1 |
| --- | --- | --- | --- |
| 1 | 1 | 6,580.8 | 1.000 |
| 2 | 1 | 6,595.3 | 0.998 |
| 4 | 3 | 3,766.8 | 1.747 |
| 8 | 7 | 3,802.0 | 1.731 |
| 16 | 15 | 3,791.0 | 1.736 |
| 32 | 31 | 3,808.7 | 1.728 |

There is a real gain from 1 to 4 slots (1.75×) and then **no further gain from 8,
16 or 32**: 16 and 32 are within 0.5% of 4 and of each other. The host has 4
logical CPUs, so the plateau coincides with the core count; this measurement
cannot separate "CPU-bound" from "critical path" as the cause, because no larger
host was available. What is measured is: on this hardware and this fixture, extra
slots beyond 4 buy nothing.

What is **not** claimed: how the runtime behaves at 16 or 32 workers on a host with
more cores, or on multiple hosts. Only this 4-CPU host was measured, and at this
size the answer is "no gain beyond 4 slots".

## 3. Concurrent projects queue behind a 4-slot budget

5000 `mixed` per project, `GlobalExecutionBudget(4)`:

| projects | wall ms | throughput proj/s | peak slots | max queue wait ms |
| --- | --- | --- | --- | --- |
| 1 | 1,105.6 | 0.905 | 4 | 0.1 |
| 2 | 1,652.8 | 1.210 | 4 | 2.6 |
| 4 | 1,680.4 | 2.380 | 4 | 4.2 |
| 8 | 3,357.0 | 2.383 | 4 | 1,690.8 |
| 16 | 6,693.6 | 2.390 | 4 | 5,021.9 |

Throughput plateaus at about **2.39 projects/s** from 4 projects onward, and the
extra work turns into queue wait (5.0 s at 16 projects). Peak slots stay at 4,
which is the configured budget and also the CPU count; the measurement shows the
plateau but cannot say which of the two binds first. Every project still finished
with its own sequential hash (`hashes_match=true`, 16/16 jobs `SUCCEEDED`).

## 4. Process-placement limits

- The process path starts one real child per job (worker e2e: `process_starts=1`,
  `peak_slots=1` at 1000 activities and `peak_slots=2` at 5000).
- The result travels through a `multiprocessing.Pipe`; the parent now drains it
  before joining, so results larger than the ~64 KB pipe buffer no longer
  deadlock. The regression test uses a ~2 MB payload and passes in seconds.
- No measurement was made of process start-up cost at high churn, nor of behaviour
  when the OS cannot fork. Those are out of scope here.

## 5. Measurement conditions

- Wall-clock numbers include contention from the shared sandbox and the shared
  PostgreSQL server. Pass/fail and hash equality do not depend on timing.
- Each worker run seeds its own tenant scope, so no row is shared or deleted.
- The 100k constraint-heavy cell is the only one that ran for ~39 minutes total;
  the orchestration phase deadline (4,200 s) applies to matrix cells only, not to
  the capacity, project or worker phases.
