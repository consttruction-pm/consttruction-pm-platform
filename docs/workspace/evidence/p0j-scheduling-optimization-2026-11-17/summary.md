# P0-J phase 1–2 evidence: engine profiling and exact scheduling optimisations

* Tested commit: `81ffed5f` (`p0j/scheduling-optimization`, parent `ee9753e6`)
  for phases 1–2; `87fc5c4a` (parent `92a62afd`, the squashed merge of PR #2021)
  for phases 3–5. Every JSON records its own `environment.git_sha`.
* Reference engine for every comparison: `ee9753e6`, loaded from `git show`
  into the same process by `scripts/p0j_leveling_reference.py` (and into a
  separate worktree for the date/time benchmarks), so both sides run the same
  fixtures, the same Python and the same machine.
* Date: 2026-11-17

## Environment (measured, not assumed)

| Item | Value |
| --- | --- |
| CPU | 4 logical CPUs (`nproc` = 4, `sched_getaffinity` = 4), Linux 5.10.134 x86_64 |
| RAM | 8,131,540 kB total, ~5.8 GB available |
| cgroup limits | no v2 `cpu.max` / `memory.max` file (no cgroup CPU quota observed) |
| Python | CPython 3.12.13 |
| PostgreSQL | 14.24 (Ubuntu 14.24-0ubuntu0.22.04.1), `max_connections=100`, `shared_buffers=128MB`, `effective_cache_size=4GB`, DSN `postgresql://postgres@127.0.0.1:55432/postgres` |
| Deployment services | none used; all measurements are local engine calls |

**Honest capacity limit.** This machine has 4 effective CPUs. No run in this
document claims 8/16/32/64-worker capacity; those figures require real hardware
and are explicitly out of scope for this evidence set (see phase 5).

## Method

* Each JSON file records `repeat`, `warmup`, `count`, `median_ms`, `min_ms`,
  `max_ms`, `p95_ms`, wall and CPU time, `peak_rss_kb`, the fixture counts and
  the canonical `output_sha256` of the engine result.
* Warm-ups: 2 for ≤5,000-activity runs, 1 for 25,000/50,000-activity runs.
  Repeats: 7 for ≤5,000, 5 for 25,000, 3 for 50,000 (the larger runs are
  bounded by real runtime, not by choice of reporting).
* `peak_rss_kb` is the process high-water mark, so files that measure several
  sizes in one process show ascending RSS; it is an upper bound per size, not a
  per-run allocation figure.
* `profile_top` samples come from cProfile, which inflates absolute time by
  roughly 2–3×. They are used only to attribute *shares*, never as timing.
* No number here is extrapolated. A run that could not finish is reported as a
  timeout.

## 1. Profile of the pre-P0-J engine (what actually dominated)

Measured on `ee9753e6` with `scripts/p0j_profile.py` (phase wrappers + cProfile):

* Date CPM: Free Float `_max_holding_delay` probe search was ~70 % of the date
  path; `forward_pass`/`backward_pass` were the remainder.
* Time-aware CPM: `_free_float_limit` linear-prefix + exponential/binary probe
  search was ~76 % of the time path.
* Resource leveling: `propose_forward_leveling_within_float` rebuilt the whole
  demand ledger and rescanned every activity per overloaded period on every
  accepted one-working-day shift (~158 s at 500 activities, 18.6 s at 250).
* `propose_backward_leveling` had the same rebuild shape (45.7 s at 100
  activities, >600 s at 250).

## 2. Date CPM after the closed form

`_holding_delay_boundary` derives the holding-delay limit from working-day
index arithmetic and only falls back to probing when the lag calendar differs
from the activity calendar. The published cap (`min(bound, 9999)`, sentinel
10,000) is unchanged.

| Shape | Activities | Before (ms) | After (ms) | Speedup | Canonical hash equal |
| --- | --- | --- | --- | --- | --- |
| dag | 1,000 | 146.0 | 62.7 | 2.33× | yes |
| dag | 5,000 | 729.1 | 316.2 | 2.31× | yes |
| dag | 25,000 | 3,765.3 | 1,725.5 | 2.18× | yes |
| fan | 10,000 | 1,194.2 | 657.1 | 1.82× | yes |
| fan | 25,000 | 3,078.5 | 1,728.7 | 1.78× | yes |
| wide | 25,000 | 677.8 | 689.6 | 0.98× (no float probes in this shape) | yes |

Files: `date-dag-1k-25k.json`, `date-fan-10k-25k.json`, `date-wide-25k.json`
vs `reference-engine-date-*.json`. Hashes also equal the earlier P0 evidence
(`p0-scheduling-core-2026-11-16/optimized`).

Accuracy proof is not this table but
`tests/scheduling/test_free_float_closed_form.py`: 12 seeds × 300 random
cases × all relationship types and lags −4..5, comparing the closed form
against a reconstruction of the probe predicate, plus a full-schedule equality
check with the closed form monkey-patched away.

## 3. Time-aware CPM after the interval closed form

`_float_limit_interval_bound` computes the limit from working-time interval
arithmetic when both duration and lag are WORKING_HOUR on the same calendar;
`_verified_float_limit` verifies/adjusts the integer candidate, and every other
unit/calendar combination keeps the probe path.

| Shape | Activities | Before (ms) | After (ms) | Speedup | Canonical hash equal |
| --- | --- | --- | --- | --- | --- |
| dag | 1,000 | 682.7 | 319.5 | 2.14× | yes |
| dag | 5,000 | 3,361.7 | 1,594.0 | 2.11× | yes |
| dag | 25,000 | 17,043.9 | 8,153.0 | 2.09× | yes |
| fan | 10,000 | 5,249.9 | 3,099.8 | 1.69× | yes |

Files: `time-*.json` vs `reference-engine-time-*.json`.

The time path also fixes a real crash: `calculate_time_hours` raised
`finish must not precede start` for negative total float because the magnitude
was computed in the wrong direction before negation. Tests cover the signed
result for every relationship type and lag.

## 4. Resource leveling: rebuild → incremental ledger

Both passes now keep a per-`(resource, period)` member map, exact `Fraction`
totals, a maintained over-allocation set, a version-stamped lazy min-heap of
candidates, per-activity demand caches and an O(1) contiguous working-day
series. Candidate ordering, priority keys, protected activities, shift bounds
and every recorded (including cumulative backward) shift are unchanged.

### Forward leveling (`propose_forward_leveling_within_float`)

Same-process reference comparison (`scripts/p0j_leveling_reference.py`,
`reference-forward-100-500.json`):

| Activities | Reference (ms) | Current (ms) | Speedup | Shifts | Hash equal |
| --- | --- | --- | --- | --- | --- |
| 100 | 1,074.2 | 14.3 | 74.99× | 84 | yes |
| 250 | 18,317.6 | 48.2 | 380.29× | 226 | yes |
| 500 | 156,983.4 | 83.1 | 1,888.41× | 476 | yes |

Scaling of the current implementation (`leveling-forward-*.json`, 7 repeats,
median / p95 ms, peak RSS):

| Activities | Median | p95 | Peak RSS | Canonical hash |
| --- | --- | --- | --- | --- |
| 100 | 14 | 14 | 50,168 kB | `ef51580f…` |
| 250 | 39 | 39 | 51,548 kB | `d811889a…` |
| 500 | 83 | 90 | 54,188 kB | `23b7318418d9…` |
| 1,000 | 180 | 181 | 59,992 kB | `a3a9bc17…` |
| 5,000 | 989 | 999 | 99,008 kB | `4f34b042…` |
| 25,000 | 5,329 | 5,367 | 296,476 kB | `7c142e0b…` |
| 50,000 | 11,068 | 11,291 | 543,120 kB | `fc188c3e…` |

These hashes are byte-identical to the hashes recorded in
`p0-scheduling-core-2026-11-16/optimized/leveling-*.json`.

### Backward leveling (`propose_backward_leveling`)

| Activities | Reference (ms) | Current (ms) | Speedup | Hash equal |
| --- | --- | --- | --- | --- |
| 100 | 45,672.6 | 17.1 | 2,669.35× | yes (`53429109…`, 864 cumulative steps) |
| 250 | did not finish within 600 s (exit 124) | 52.8 | ≥ 11,400× (lower bound, no extrapolation) | n/a |

Scaling of the current implementation (`leveling-backward-*.json`):

| Activities | Median | p95 | Peak RSS | Canonical hash |
| --- | --- | --- | --- | --- |
| 100 | 17 | 23 | 50,516 kB | `53429109…` |
| 250 | 53 | 59 | 52,820 kB | `a83ad988…` |
| 500 | 113 | 121 | 56,456 kB | `954c64c6…` |
| 1,000 | 245 | 248 | 63,652 kB | `20498dac…` |
| 5,000 | 1,413 | 1,462 | 119,600 kB | `2e0f4844…` |
| 25,000 | 7,690 | 7,843 | 397,840 kB | `7509be0b…` |

## 5. Full leveling orchestration (CPM passes + forward + backward + validation)

`leveling-orchestration-20-100.json`, 7 repeats / 2 warm-ups:

| Activities | Median | Forward shifts | Backward shifts | CPM passes | Canonical hash |
| --- | --- | --- | --- | --- | --- |
| 20 | 10 | 18 | 0 | 2 | `d23faac4…` |
| 50 | 52 | 48 | 0 | 2 | `a43f0cd7…` |
| 100 | 197 | 98 | 0 | 2 | `a3da54e1…` |

Hashes are identical to `p0e-scheduling-cpm-reuse-2026-11-16/optimized`, so
the CPM-reuse behaviour from P0-E is preserved. This fixture has no residual
late-window over-allocation (documented in its builder), so backward
acceptance is measured by the dedicated backward fixture above, not here.

## 6. Where the remaining time goes (post-optimisation attribution)

cProfile shares on the current commit (`profile-*.json`; profile inflates wall
time ~2–3×, shares only):

* Date CPM 25,000 (dag): backward pass 42 %, float calculation 32 %, forward
  pass 24 %. The Free Float probe search no longer appears in the top entries.
* Time-aware CPM 5,000 (dag): float calculation 52 %, backward pass 37 %,
  forward pass 11 %.
* Forward leveling 5,000: `propose_forward_leveling_within_float` self time
  721 ms of 2,775 ms profiled; `Fraction` arithmetic 322k calls (~18 %),
  `demand_index` the remainder. Exact rational totals are deliberate: they
  guarantee that incremental add/subtract equals a full rebuild bit for bit.
* Backward leveling 5,000: self time 896 ms of 3,663 ms profiled; `Fraction`
  arithmetic 381k calls (~16 %), `demand_index` 64k calls (~11 %).

## 7. Correctness evidence tied to this commit

* `tests/scheduling/test_free_float_closed_form.py` — 39 tests: closed form
  vs probe predicate over 12 seeds × 300 cases, cap equality, full-schedule
  equality with the closed form disabled, zero probe calls.
* `tests/scheduling/test_time_float_search.py` — 71 tests in the module:
  shape × float-day equality with the interval bound disabled, bound actually
  used on hour-based fixtures (0 `_free_float_limit` calls), signed lags and
  all relationship types, WORKING_DAY fallback.
* `tests/scheduling/test_leveling_incremental_equivalence.py` — 183 tests:
  the previous rebuild algorithms are kept as an oracle and compared tuple-for-
  tuple against the incremental implementation over 80 randomized seeds per
  direction (4 calendars incl. holidays, multiple resolvers, signed/absent
  priorities, multi-resource demands, protected activities, over-allocation
  percentages, beyond-float bounds), plus two golden decision sequences.
* Full suite at this commit: `4770 passed, 211 skipped` locally (Python 3.12).

## 8. Safe parallel float execution (phase 3)

Harness: `scripts/p0j_float_parallel.py`. Every measured run executes
`time_schedule` with a `FloatExecutionPolicy`; the whole-schedule time is
reported (forward pass + backward pass + float pass), because the float pass is
the only phase that may leave the process. `--context main` runs in the main
thread (the offline/CLI runtime, where `fork` is provably safe);
`--context thread` runs inside a worker thread while holding one permit of a
`GlobalExecutionBudget`, which is exactly the Scheduling Job executor condition
(the executor always calculates on a thread). Each configuration used 2
warm-ups and 7 repeats (`thread` spawn: 5 repeats); medians, min, p95 and the
full sample list are in the JSON files.

| case | context | 1 slot | 2 slots | 4 slots | speedup at 4 | canonical hash |
| --- | --- | --- | --- | --- | --- | --- |
| 500 activities | main (fork) | 183.7 ms | 146.2 ms | 125.6 ms | 1.46× | `3c2c22ac5811…` |
| 2,000 | main (fork) | 736.0 ms | 579.1 ms | 504.1 ms | 1.46× | `215b85dad2a5…` |
| 5,000 | main (fork) | 1,864.9 ms | 1,447.6 ms | 1,229.1 ms | 1.52× | `36bcb72c9087…` |
| 25,000 | main (fork) | 9,485.3 ms | 7,512.8 ms | 6,262.4 ms | 1.51× | `c12b0931e807…` |
| 5,000 | thread, default | 1,859.8 ms | – | 1,859.1 ms | none (sequential) | `36bcb72c9087…` |
| 25,000 | thread, default | 9,490.5 ms | – | 9,464.0 ms | none (sequential) | `c12b0931e807…` |
| 5,000 | thread, `allow_spawn` | 1,844.5 ms | 2,165.2 ms | 2,470.7 ms | 0.75× | `36bcb72c9087…` |
| 25,000 | thread, `allow_spawn` | 9,436.8 ms | 10,170.6 ms | 10,311.5 ms | 0.92× | `c12b0931e807…` |

Files: `float-parallel-fork.json`, `float-parallel-threaded-default.json`,
`float-parallel-threaded-spawn.json`. `pool_start_methods` in each run records
the method actually used (`fork`, `spawn`, or empty when the pool was not
created), and `pool_slots_used` is `1 + budget.extra_peak`, so a run that
silently fell back to the sequential loop is visible instead of implied.

What the numbers establish:

* **The float values are identical at every slot count.** `hash` is the
  canonical `time_schedule_payload` SHA-256 and it is equal to the 1-slot run
  for every case, including the spawn runs where the immutable float context
  crosses a process boundary (round-trip pickling covered by
  `tests/scheduling/test_time_float_execution_policy.py`).
* **In a single-threaded process the pool is safe and pays.** The float pass
  alone is ~3.3× faster on 4 CPUs (measured separately: 4.60 s → 1.30 s at
  25k activities), which is 1.5× for the whole time-aware schedule because the
  forward and backward passes stay serial. The offline runtime
  (`OfflineSchedulingRuntime`) therefore uses this policy by default.
* **In a threaded process `fork` is never used and `spawn` is not
  profitable.** The executor runs calculations on a thread while holding a
  budget permit, so the safe alternative is `spawn`. The float context pickles
  to 11.6 MB at 25k activities; serialising it costs ~0.35 s and each child
  unpickles ~0.27 s, i.e. ~25 µs per activity of serial work against ~169 µs
  per activity of parallelisable work. At 4 slots that is a measured 0.91×,
  so `allow_spawn` defaults to `False` and the pass stays sequential. Opting in
  is one policy field, available for hosts whose transfer cost is lower.
* **Budget accounting is real.** Every pool reserved its extra slots with
  `GlobalExecutionBudget.admit_extra`, which returns only what the same
  process-wide permit set can actually grant; when no extra slot was free the
  run recorded `pool_slots_used = 1` and used the exact sequential loop.

## 9. Phase-3 limits

* 4 effective CPUs: `pool_slots_used = 4` is the measured maximum. No claim is
  made for 8/16/32/64 slots.
* `RUSAGE_CHILDREN` in spawn runs includes interpreter start-up, so
  `children_peak_rss_kb` is an upper bound per run, not the float context size.
* The fork speedup depends on the OS copy-on-write behaviour of this host; the
  spawn penalty is a property of the pickled context size and is reported as
  measured, not extrapolated.

## 10. Scheduling Job path under real concurrency (phase 5)

Harness: `scripts/p0j_job_stress.py`. This measures the queue, PostgreSQL and
worker path, not the engine: a fixed 200-activity fixture keeps every job the
same size so differences come from concurrency. Worker counts are real OS
processes running the production `SchedulingJobExecutor` over the same
PostgreSQL queue, each with one `GlobalExecutionBudget` permit. Virtual users
are real threads; each database operation leases one of 32 request-scoped
client connections and returns it immediately (an application-server model),
so pool pressure is visible as `client_pool_wait_ms` instead of silently
serialising users. Every hundredth user cancels and resubmits, so each case
contains `users` successful jobs plus `users/10` terminal cancellations.
`queue_wait_ms` is time from insert to claim across all users, i.e. real FIFO
multi-user queueing, not scheduler latency.

PostgreSQL 14.24, `max_connections=100`, 4 effective CPUs. Each cell is one
warm-up case run followed by three measured repeats (`--case-warmups 1
--case-repeats 3`); the table reports the median of the three and the JSON
keeps every repeat plus the per-cell spread. `wall_ms` ends when the last
virtual user returns, and the ~10 s worker idle grace after that is reported
separately as `drain_tail_ms`. Every case in every repeat: `status: ok`,
`error_count: 0`, `pending_after_drain: 0`, every worker `exitcode 0`, no
deadline kills.

| Users | Workers | Wall median | Spread | Jobs/s | Queue wait p50 | p95 | Status p50 | Submit p50 | p99 | CPU cores | PG conns max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | 1 | 2.652 s | 1.7 % | 41.5 | 1,258.5 ms | 2,354.0 ms | 0.13 ms | 3.98 ms | 14.61 ms | 0.62 | 34 |
| 100 | 2 | 1.361 s | 1.1 % | 80.8 | 622.8 ms | 1,153.6 ms | 0.11 ms | 3.96 ms | 14.88 ms | 1.22 | 35 |
| 100 | 4 | 0.798 s | 2.5 % | 137.9 | 329.4 ms | 523.8 ms | 0.16 ms | 4.73 ms | 30.94 ms | 2.38 | 38 |
| 500 | 1 | 9.535 s | 3.0 % | 57.7 | 6,365.1 ms | 11,685.5 ms | 8.84 ms | 9.95 ms | 199.81 ms | 0.84 | 35 |
| 500 | 2 | 6.793 s | 0.7 % | 81.0 | 2,982.8 ms | 5,315.0 ms | 5.86 ms | 17.66 ms | 228.89 ms | 1.20 | 36 |
| 500 | 4 | 4.088 s | 2.0 % | 134.6 | 1,635.1 ms | 2,563.4 ms | 6.59 ms | 14.36 ms | 178.26 ms | 2.04 | 38 |
| 1,000 | 1 | 19.137 s | 2.6 % | 57.5 | 12,501.6 ms | 22,884.1 ms | 38.37 ms | 17.22 ms | 596.68 ms | 0.84 | 35 |
| 1,000 | 2 | 13.138 s | 0.3 % | 83.7 | 5,811.3 ms | 10,519.7 ms | 12.15 ms | 19.72 ms | 518.48 ms | 1.23 | 36 |
| 1,000 | 4 | 8.467 s | 2.3 % | 129.9 | 2,972.7 ms | 4,974.5 ms | 15.62 ms | 22.90 ms | 438.50 ms | 1.95 | 38 |

Every case persisted exactly one canonical hash, equal to the engine result
computed in-process: `output_matches_engine: true`, `results_found` equal to
the succeeded count, cancelled jobs terminal (`cancelled_terminal` equal to
`cancel_requested` in all nine cases).

What the numbers establish:

* **The queue path scales with real worker capacity.** 1 → 4 workers gives
  3.32× (100 users), 2.33× (500) and 2.26× (1,000). 1 → 2 gives 1.95×, 1.40×,
  1.46×. The three measured repeats stay within 0.3–3.0% of the median wall,
  so the ordering is not run noise. The scheduler is never non-deterministic:
  the same fixture produces the same hash at every worker count.
* **The client path, not the workers, is the ceiling at high user counts.**
  CPU use never exceeds 2.38 of 4 cores, while submit p99 rises from 15 ms
  (100 users) to 597 ms (1,000 users): submissions serialise on the
  single-flight/dedup path and on connection scheduling, and `status` p50
  rises to 38 ms at one worker because 1,000 clients poll while the queue
  drains. Adding workers past the point where the client path saturates
  cannot help, and the table shows the diminishing return honestly.
* **Cancellation is exact under load.** All scripted cancels reached
  `CANCELLED`, and the 10% of users who cancel resubmit once, so each case
  persists exactly `users` succeeded + `users/10` cancelled = `1.1 × users`
  rows (110/550/1,100), matching `states`; `cancelled_terminal` equals
  `cancel_requested` in all nine cells.

Oversubscription, same harness and fixture, 100 users, `--allow-oversubscription`
(the host supplies 4 effective cores):

| Workers requested | Wall median | Spread | Jobs/s | Queue wait p50 | CPU cores | PG conns max |
| --- | --- | --- | --- | --- | --- | --- |
| 8 | 0.620 s | 1.5 % | 177.4 | 212.1 ms | 3.23 | 26 |
| 16 | 0.632 s | 3.9 % | 173.9 | 166.4 ms | 4.04 | 33 |
| 32 | 0.763 s | 3.7 % | 144.1 | 176.9 ms | 4.58 | 49 |
| 64 | 1.118 s | 50.5 % | 98.4 | 237.8 ms | 5.30 | 82 |

No case exceeded 177.4 jobs/s, and 64 processes lost 45% of that peak while
spending 5.30 cores of CPU time on 4 cores and holding 82 PostgreSQL
connections. The 64-process cell is also the only unstable one (spread 50.5 %
over 1.07–1.64 s), which is what contention looks like. This is the measured
basis for refusing worker counts above real
capacity: `scripts/p0j_job_stress.py` refuses `workers > effective_cores`
unless explicitly asked to record the oversubscribed run as simulated.

Files: `job-stress-real-4cpu.json`, `job-stress-oversubscribed.json`. Both
record `capacity`, `derived_budget`, `suppliable_workers`,
`environment.git_sha`, `case_warmups`/`case_repeats`, every individual repeat
and the per-cell `cases` aggregate; each repeat keeps its own `tenant_id`, so
no case shares rows with another.

## 11. Phase-5 limits

* 4 effective CPUs. The real matrix stops at 4 workers; 8/16/32/64 are
  recorded only as simulated and are never presented as delivered capacity.
* 32 client connections (16 in the oversubscribed runs) against
  `max_connections=100`; the measured maximum was 37, so no case reached the
  server limit. `client_pool_wait_ms` is reported so the model is auditable.
* The fixture is intentionally small and constant. Engine scaling at
  50,000/100,000 activities is measured separately in §12 and must not be
  conflated with queue throughput.
* A worker's idle grace is 10 s; `drain_tail_ms` records it and is excluded
  from `wall_ms`. `workers_terminated_at_deadline` is empty in every case, so
  no case was cut short by the outer deadline.
* Crash recovery, lease expiry and retry are covered by the unit/integration
  suites and by the P0-F evidence, not by this stress matrix: the harness does
  not kill workers mid-job.

## 12. Pure engine at 50,000 and 100,000 activities

Same fixture family (`dag`, seed 20261116) and same host as §2–§3, extended to
the two largest sizes the plan requires. Current commit: 2 warm-ups + 5 repeats
(date) and 1 warm-up + 3 repeats (time-aware); reference `ee9753e6`: 1 warm-up
+ 3 repeats. Every run's canonical hash is identical across sides and repeats.

| Mode | Activities | Reference median | p95 | Current median | p95 | Speedup | Peak RSS current | Hash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| date | 50,000 | 7,714.8 ms | 7,721.9 ms | 3,579.1 ms | 3,654.8 ms | 2.16× | 173,296 kB | `e51656b8…` |
| date | 100,000 | 15,725.3 ms | 15,754.1 ms | 7,401.6 ms | 7,494.6 ms | 2.12× | 295,648 kB | `8c36156d…` |
| time | 50,000 | 34,630.6 ms | 34,662.5 ms | 16,595.1 ms | 16,814.2 ms | 2.09× | 219,040 kB | `93957c0b…` |
| time | 100,000 | 69,038.8 ms | 69,093.0 ms | 33,641.9 ms | 33,673.8 ms | 2.05× | 387,880 kB | `e1c4396f…` |

Reference peak RSS for the same rows is 172,328 / 297,976 / 200,228 / 352,228 kB,
so current peak memory is within 1% in date mode and 9–10% higher in time mode
(the time-aware closed form keeps interval candidates the probe path did not).
The ratio is smaller
than at 25,000 (2.18× date, 2.09× time) because at these sizes the topological
order, relation expansion and result materialisation are a larger share and
none of them was parallelised.

The earlier P0 evidence at 100,000 (`p0-scheduling-core-2026-11-16/baseline`,
single run, no warm-up, `float_days=2`) is **not** used for this comparison
because it ran a different fixture condition; the reference worktree run above
is the same-condition comparison.

Files: `date-dag-50k-100k.json`, `time-dag-50k-100k.json`,
`reference-engine-date-dag-50k-100k.json`,
`reference-engine-time-dag-50k-100k.json`.

## Reproduction (phase 5 and larger sizes)

```bash
export P6_TEST_POSTGRES_DSN=postgresql://postgres@127.0.0.1:55432/postgres
python scripts/p0j_job_stress.py --users 100,500,1000 --workers 1,2,4 \
  --size 200 --polls 200 --poll-interval 0.02 --client-pool 32 \
  --git-sha <sha> --out job-stress-real-4cpu.json
python scripts/p0j_job_stress.py --users 100 --workers 8,16,32,64 \
  --size 200 --polls 200 --poll-interval 0.02 --client-pool 16 \
  --allow-oversubscription --git-sha <sha> --out job-stress-oversubscribed.json
python scripts/scheduling_core_benchmark.py --mode date --sizes 50000,100000 \
  --shape dag --warmup 2 --repeat 5 --git-sha <sha> --out date-dag-50k-100k.json
python scripts/scheduling_core_benchmark.py --mode time --sizes 50000,100000 \
  --shape dag --warmup 1 --repeat 3 --git-sha <sha> --out time-dag-50k-100k.json
python scripts/p0j_float_parallel.py --context main --sizes 500,2000,5000,25000 \
  --workers 1,2,4 --repeats 7 --warmup 2 --git-sha <sha> --out <dir>
```

Pre-P0-J reference runs use a worktree at `ee9753e6`
(`git worktree add /tmp/p0j-head ee9753e6`) and the same commands with
`--out reference-*.json`.

## Limits of this evidence

* 4 effective CPUs; no multi-worker or multi-node claim is made here.
* Peak RSS is process high-water; files with several sizes in one process
  over-attribute RSS to the later sizes.
* Backward leveling at 250 activities could not be measured on the reference
  engine within 600 s; the reported speedup is a lower bound.
* PostgreSQL is on the hot path only for §10; §12 and §2–§4 are pure engine
  calls with no database timing.
* `RUSAGE_CHILDREN` in spawn runs includes interpreter start-up, so
  `children_peak_rss_kb` is an upper bound per run, not the float context size.
* The fork speedup depends on the OS copy-on-write behaviour of this host; the
  spawn penalty is a property of the pickled context size and is reported as
  measured, not extrapolated.
