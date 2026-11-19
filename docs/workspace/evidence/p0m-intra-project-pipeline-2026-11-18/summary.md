# P0-M — True intra-project parallel scheduling core (backward/float pipeline)

Tested working tree: `main` `9408552bcfb2b0e874333845a3ba437b8430a46b` + the P0-M change.
Recorded source hashes of the tested tree:

```
ad140c437021bc3ee606fe3bad640436f62f64a38d3f57b332e0a5eaea47e9bb  src/construction_pm/scheduling/time_schedule.py
9063762be9b9c7e97d17c5536985737c5a8ab6fd46fa659bb9b3376edf5a7fcd  tests/scheduling/test_time_schedule_pipeline_parallelism.py
```

Baseline for the "before" hashes: `9408552b` in a detached worktree at
`/tmp/p0m-baseline` (same host, same session), i.e. merged main after P0-L.

Environment: 4 CPUs (AMD EPYC), 8,131,540 kB RAM, CPython 3.12.13, Linux
x86_64, PostgreSQL 14.24 for the job-path tests. Fixtures:
`src/construction_pm/scheduling/benchmark_fixtures.py`, seed `20261116`
(Mon–Fri 08:00–12:00 / 13:00–17:00, holidays 2026-01-06 / 02-17 / 03-20,
`float_days=0`).

## 1. Architecture status before the change

One canonical engine: `time_forward_pass` → `time_backward_pass` →
`calculate_time_floats` inside `time_schedule`. The only intra-project
parallelism that existed was the opt-in P0-H/P0-J **post-hoc** per-activity
float pass (`_parallel_time_floats`: fork pool, chunked `pool.map`, admitted by
`GlobalExecutionBudget`, merged in sorted id order). It ran *after* the serial
backward pass, so the backward pass and the float pass were sequential phases.
No forward/backward wavefront, no producer/consumer overlap.

## 2. Measured bottlenecks (sequential Oracle path)

Wall medians per phase, same fixtures, warm-up plus 5 (1k/5k) or 3 (25k)
repeats; 100k with 2 repeats (`phases-1k-5k-25k.json`, `phases-100k.json`).
`prep` is fixture construction and includes the fixture's own forward pass used
to derive `project_finish` (0.72 s of the 25k value, 3.19 s of the 100k value);
`topo` is a separate `heap_topological_order` timing on the same graph.

| size | prep ms | topo ms | forward ms | backward ms | float ms | assembly ms | hashing ms | total ms | float share |
|---|---|---|---|---|---|---|---|---|---|
| 1,000 | 37.43 | 0.89 | 26.29 | 88.93 | 108.44 | 10.34 | 4.05 | 237.95 | 45.6 % |
| 5,000 | 193.33 | 4.79 | 132.98 | 446.79 | 543.63 | 53.50 | 20.68 | 1,210.06 | 44.9 % |
| 25,000 | 1,002.09 | 28.21 | 744.30 | 2,351.17 | 2,801.71 | 286.69 | 109.08 | 6,248.33 | 44.8 % |
| 100,000 | 4,301.49 | 134.23 | 3,188.12 | 9,441.85 | 11,206.96 | 1,152.30 | 459.68 | 25,448.91 | 44.0 % |

CPU/wall utilisation of these sequential runs is 1.00 (single thread); peak RSS
56/82/208/627 MB at 1k/5k/25k/100k.

`cProfile` self time by category (share of the 14.8 s instrumented 25k run;
the 100k run, 59.7 s instrumented, has the same shape):

| category | 25k share | 100k share | what it is |
|---|---|---|---|
| calendar arithmetic | 57.7 % | 58.7 % | `TimeAwareWorkingTimeResolver` / `CalendarAwareResolver` / `WorkingTimeCalendar` methods (`intervals_for`, `normalize_*`, add/subtract duration/lag) |
| engine glue | 31.4 % | 31.3 % | dataclass construction, dict/map bookkeeping, `time_schedule_payload` |
| backward pass body | 4.4 % | 4.1 % | `time_backward_pass` self time |
| float phase body | 3.3 % | 2.9 % | `_time_float_for_activity`, `_float_limit_interval_bound`, `_verified_float_limit` |
| forward pass body | 2.0 % | 1.7 % | `time_forward_pass` self time |
| relationship evaluation | 1.1 % | 1.1 % | `_latest_predecessor_start`, `_add_signed_lag`, `_ss_successor_start`, `_inverse_lag` |
| topological ordering | 0.2 % | 0.3 % | `heap_topological_order` |

Call counts at 25k: `intervals_for` 3,197,982; `normalize_start` 435,168;
`normalize_finish` 312,288; `add_duration` 266,523; `subtract_lag` 239,405;
`add_lag` 143,643; `_latest_predecessor_start` 47,881;
`_verified_float_limit` 47,881; `_time_float_for_activity` 25,000;
`heap_topological_order` 1. Per-activity cost on the benchmark DAG is
28.9 µs forward and 94.0 µs backward (measured, `wavefront-25k.json`).

The float phase (44–46 % of the run) is the only phase whose activities are
mutually independent *and* whose inputs are complete: an activity's float reads
its own late record, the whole early map, its outgoing relationships and the
calendar registry. The backward pass produces one final late record at a time.

## 3. Wavefront parallelism: measured, and why it stays sequential

A level-synchronous forward/backward pass needs one barrier per dependency
level. On the mandated fixtures the graph is a spine with forward shortcuts:
`depth == size`, `width_max == 1` (`dag`, `chain`, `mixed` shapes, all sizes).
Measured pool round trip (identity task, 15 samples) is 0.129 ms with 3
children and 4.671 ms with 1 child (bimodal, min 0.133 ms). Even at the cheaper
0.129 ms the wavefront overhead at 25k is 25,000 × 0.129 ms = 3,225 ms against a
722 ms serial forward pass (4.47× worse before any computation; 5.76× on the
chain shape, 3.11× on mixed). The same holds for the backward pass, whose
per-activity cost is higher but whose width is also 1.

For completeness the `fan` shape (depth 3, width 24,998) and `wide` shape
(depth 1, width 25,000) were measured too: the barrier overhead there is
0.39 ms / 0.13 ms versus 762.63 ms / 378.35 ms of serial forward work, so a
wavefront *could* pay on wide graphs. Those shapes are not part of the mandated
benchmark matrix, and a wavefront implementation would be new scheduling
architecture, not reuse of the existing engine; it is recorded here as a
measured opportunity, not implemented and not claimed.

Decision: forward and backward stay sequential; the parallelism is placed where
every mandated fixture has width-independent work — the float pass.

## 4. The change: backward/float producer-consumer pipeline

`src/construction_pm/scheduling/time_schedule.py`

* `time_backward_pass(..., *, on_late=...)` calls an optional hook with each
  activity id and its final `TimeScheduledActivity` immediately after storing
  it. The default is `None` and the loop is unchanged; the hook cannot alter
  `late` (it receives the record, not the map).
* `_time_float_for_activity(context, activity_id, late_item=None)` accepts the
  activity's own late record instead of reading `late[activity_id]`. The
  calculation reads no other late entry (the Free Float probe uses early dates
  only), so the value is identical by construction; the equivalence is tested
  against the mapping lookup for every activity of a network.
* `_FloatPipeline` batches `(id, late)` pairs (target ≈32 batches per project,
  clamps 16…1024 → 30…1,020 activities per batch on the benchmark sizes; one
  pair is ~108 bytes serialized) and dispatches them with `apply_async` while
  the parent keeps walking back. `finish()` flushes the last partial batch,
  waits for every handle and merges in sorted id order — the same mapping the
  sequential loop returns.
* `_float_pipeline` context manager: it yields `None` (the historical path)
  unless a safe start method exists (single-threaded parent, no pool already
  active, `fork` available; `spawn` only when the policy explicitly allows it
  and the context pickles), the granted budget exceeds one slot, at least 256
  activities remain, and the pool actually starts. It holds the process-wide
  `_FLOAT_POOL_GUARD` and releases it on every exit path; the parent keeps one
  granted slot and the pool gets `granted − 1` children.
* `time_schedule` selects the policy once and, when `workers > 1`, creates the
  pipeline *before* the backward pass (so forked children inherit the immutable
  float context), passes `pipeline.submit` as `on_late`, and takes floats from
  `pipeline.finish()`. Any decline falls back to the previous code path
  verbatim, including the post-hoc parallel float pass. `float_workers` is
  validated up front on every path, because the pipeline path no longer calls
  `calculate_time_floats`, which used to be the only validator.
* `_fork_is_safe` / `_spawn_is_safe` are extracted from
  `_select_float_start_method`, which keeps its exact semantics.

No second engine: children run `_time_float_for_activity` from the same module
with the same registry and context. No new scheduling rule, no change to
decision order, no change to any date, float, critical flag or payload field.

## 5. Equality evidence

`tests/scheduling/test_time_schedule_pipeline_parallelism.py` (20 tests, 1/2/4
and 8 worker slots):

* mixed network (spine + forward shortcuts with rotating FS/SS/FF/SF and lags
  0/4/−1/2/8, plus six unconnected activities) at 1 vs 2 vs 4 slots: payload,
  mapping key order, project finish identical; the pipeline really ran (batch
  count and dispatch count asserted).
* across calendars and exception layers (project/site/fast/lag calendars,
  two non-work days, one detailed-work-hours day, per-activity override);
  DST transition in `America/New_York`; earliest/latest constraints; actual
  start with out-of-sequence SS and a data date; every fixture shape
  (`wide`, `fan`, `slack`, `mixed`, `chain`, `dag`); a bounded Free Float
  window (`float_days=3`); workers exceeding activities; determinism across
  repeats; equality with the post-hoc parallel float path field by field.
* exact fallbacks: threaded process (pool creation blocked), below the
  activity threshold (pipeline class replaced by an exploding stub), admission
  granting one slot (budget `extra_peak <= 1`, `active == 0`), pool already
  active, backward-pass failure (guard released, next call succeeds).
* the hook itself: invoked exactly once per activity, after its successors;
  `late_item` equals the mapping lookup; a pipeline context with an empty late
  map raises `KeyError` rather than inventing a value (the pipeline never uses
  it).

Full suite on the tested tree (with `CONSTRUCTION_PM_POSTGRES_DSN` and
`P6_TEST_POSTGRES_DSN`): **5,292 passed, 1 skipped, 4 warnings in 68.67 s**
(`full-suite.log`), which is the P0-L baseline (5,272 passed, 1 skipped) plus
exactly the 20 new tests.

## 6. Benchmark matrix

Sequential/2/4 slots, median and nearest-rank p95 of whole `time_schedule`
runs, one fresh process per configuration (warm-up + 5 repeats at 1k/5k/10k,
3 at 25k/50k/100k). `pipeline` = the new path through
`time_schedule(float_workers=w)`; `posthoc` = serial backward + chunked
parallel float through the same engine functions (the P0-H/P0-J shape).
Every canonical SHA-256 in the matrix is identical within a size and equal to
the baseline (section 8).

| size | workers | pipeline median | pipeline p95 | speedup | efficiency | posthoc median | posthoc speedup |
|---|---|---|---|---|---|---|---|
| 1,000 | 1 | 225.4 ms | 236.3 ms | 1.00× | 1.00 | 224.2 ms | 1.00× |
| 1,000 | 2 | 167.8 ms | 175.7 ms | 1.34× | 0.67 | 182.8 ms | 1.23× |
| 1,000 | 4 | 152.5 ms | 160.5 ms | 1.48× | 0.37 | 157.4 ms | 1.42× |
| 5,000 | 1 | 1,138.8 ms | 1,143.3 ms | 1.00× | 1.00 | 1,115.9 ms | 1.00× |
| 5,000 | 2 | 780.0 ms | 793.8 ms | 1.46× | 0.73 | 895.3 ms | 1.25× |
| 5,000 | 4 | 669.3 ms | 693.3 ms | 1.70× | 0.43 | 771.1 ms | 1.45× |
| 10,000 | 1 | 2,281.5 ms | 2,289.3 ms | 1.00× | 1.00 | 2,290.9 ms | 1.00× |
| 10,000 | 2 | 1,546.2 ms | 1,568.1 ms | 1.48× | 0.74 | 1,842.6 ms | 1.24× |
| 10,000 | 4 | 1,371.1 ms | 1,391.1 ms | 1.66× | 0.42 | 1,555.6 ms | 1.47× |
| 25,000 | 1 | 5,825.9 ms | 5,891.5 ms | 1.00× | 1.00 | 5,833.8 ms | 1.00× |
| 25,000 | 2 | 4,250.2 ms | 4,306.9 ms | 1.37× | 0.69 | 4,735.3 ms | 1.23× |
| 25,000 | 4 | 3,583.8 ms | 3,615.2 ms | 1.63× | 0.41 | 3,978.6 ms | 1.47× |
| 50,000 | 1 | 11,990.0 ms | 11,990.3 ms | 1.00× | 1.00 | 11,917.5 ms | 1.00× |
| 50,000 | 2 | 8,930.2 ms | 8,997.6 ms | 1.34× | 0.67 | 9,635.5 ms | 1.24× |
| 50,000 | 4 | 7,608.5 ms | 7,827.3 ms | 1.58× | 0.39 | 8,246.8 ms | 1.45× |
| 100,000 | 1 | 24,202.1 ms | 24,230.4 ms | 1.00× | 1.00 | 24,187.0 ms | 1.00× |
| 100,000 | 2 | 18,051.6 ms | 18,541.5 ms | 1.34× | 0.67 | 19,639.0 ms | 1.23× |
| 100,000 | 4 | 15,012.9 ms | 15,350.5 ms | 1.61× | 0.40 | 16,447.0 ms | 1.47× |

CPU and utilisation (median total CPU of parent + children, and total CPU /
wall):

| size | sequential CPU | 2 slots CPU | 2 slots util | 4 slots CPU | 4 slots util | child-worker util (4 slots) |
|---|---|---|---|---|---|---|
| 1,000 | 225.4 ms | 291.4 ms | 1.74 | 281.6 ms | 1.85 | 0.29 |
| 5,000 | 1,138.7 ms | 1,336.1 ms | 1.71 | 1,260.8 ms | 1.88 | 0.30 |
| 10,000 | 2,281.3 ms | 2,573.8 ms | 1.67 | 2,557.2 ms | 1.87 | 0.29 |
| 25,000 | 5,825.5 ms | 6,680.4 ms | 1.57 | 6,570.6 ms | 1.83 | 0.28 |
| 50,000 | 11,989.0 ms | 13,553.7 ms | 1.52 | 13,448.8 ms | 1.77 | 0.26 |
| 100,000 | 24,201.0 ms | 27,450.8 ms | 1.52 | 26,956.2 ms | 1.80 | 0.27 |

IPC and payload (parent-side only; the payload is the `(id, late)` batch):

| size | batches | bytes/activity | mean batch | submit (all batches) | drain wait at 2 / 4 slots |
|---|---|---|---|---|---|
| 1,000 | 33 | 116.6 | 3,533 B | 0.25 ms | 25.1 / 2.0 ms |
| 5,000 | 33 | 109.6 | 16,600 B | 0.33–0.44 ms | 73.3 / 3.1 ms |
| 10,000 | 33 | 108.7 | 32,933 B | 0.36–0.57 ms | 199.8 / 6.9 ms |
| 25,000 | 33 | 108.2 | 81,942 B | 0.45–0.65 ms | 684.2 / 11.3 ms |
| 50,000 | 49 | 108.1 | 110,277 B | 0.64–1.04 ms | 1,529.3 / 120.8 ms |
| 100,000 | 98 | 108.1 | 110,277 B | 1.1–2.05 ms | 2,877.0 / 119.5 ms |

Serialization + submission costs 0.25–2.05 ms per whole project, against a
measured gain of 9.19 s at 100k (0.02 % of the gain). The drain wait is the
last part of the float work that the children had not finished when the parent
left the backward loop; at 2 slots the single child is the bottleneck
(float ≈ 11.2 s vs backward ≈ 9.4 s at 100k), which is why 2 slots stop at
1.34×, while at 4 slots the parent's own work (forward + backward + assembly +
hash) is the floor.

## 7. Cost model, validated against the measurements

The pipeline removes the float phase from the critical path, so the wall time
cannot go below the parent's serial work `forward + backward + assembly +
hashing` (plus dispatch overhead). From the phase table:

| size | parent floor | measured 4-slot wall | overhead | measured speedup |
|---|---|---|---|---|
| 1,000 | 129.61 ms | 152.5 ms | 22.9 ms (pool start) | 1.48× |
| 5,000 | 653.95 ms | 669.3 ms | 15.3 ms | 1.70× |
| 25,000 | 3,491.24 ms | 3,583.8 ms | 92.6 ms | 1.63× |
| 100,000 | 14,243.53 ms | 15,012.9 ms | 769.4 ms | 1.61× |

The measured result lands within 2–5 % of the floor at 5k–100k (17 % at 1k,
where fork start-up is paid over only 225 ms of work). Children CPU matches the
sequential float phase (e.g. 25k: 3.00 s vs 2.80 s; 100k: 11.94 s vs 11.21 s,
the difference being pool start and batch handling), so no work is duplicated.
Adding more than 3 children cannot help on a 4-CPU host because `float/3` is
already below the parent's serial time; that is the structural limit of this
pipeline, not a tuning parameter.

## 8. Canonical hashes before/after

Sequential Oracle path, baseline `9408552b` versus the tested tree:

| fixture | baseline | after | equal |
|---|---|---|---|
| time dag 1k | `bdb8a04616a6c001…` | `bdb8a04616a6c001…` | yes |
| time dag 5k | `3d2f1f8dc31ceb4f…` | `3d2f1f8dc31ceb4f…` | yes |
| time dag 25k | `84864c94f01706c0…` | `84864c94f01706c0…` | yes |
| time dag 100k | `e1c4396f5c0fa98c…` | `e1c4396f5c0fa98c…` | yes |
| time mixed 25k | `7c6aa1b2e001b445…` | `7c6aa1b2e001b445…` | yes |

At 1/2/4 slots and in both modes (`pipeline`, `posthoc`) the hashes are also
equal to these within each size (`matrix-raw.json`, field
`all_hashes_identical: true` in `comparison.json`).

## 9. Memory

Parent peak RSS (whole process, `ru_maxrss`) is dominated by the schedule
mapping and grows with the input on both paths: 53 → 569 MB sequential at
1k → 100k. With 4 slots the parent peaks at 56.6 / 80.7 / 108.3 / 204.1 /
355.2 / 669.7 MB (1k/5k/10k/25k/50k/100k), i.e. +2 % to +18 % over sequential
at 100k. Summed child RSS peaks at 120 / 184 / 251 / 447 / 770 / 1,450 MB; the
children hold the forked read-only engine plus their batch/result buffers, and
the sum overcounts shared copy-on-write pages. The pipeline holds at most
`batch_size` late records plus the outstanding batches, so its own footprint is
bounded by ≈ 1,020 records × 108 B ≈ 110 kB per batch in flight; no growth with
the number of activities beyond the result mapping that the sequential path also
builds.

## 10. Remaining limits (measured, not assumed)

* The plan is two-phase by construction: the parent's forward and backward
  passes are serial on these fixtures (width 1), so the attainable speedup is
  bounded by the float share (44–46 %), i.e. ≈ 1.79–1.85× at best; measured
  1.61–1.70× at 4 slots.
* With only 2 granted slots the single child is the bottleneck at ≥25k
  (drain 0.68 s at 25k, 2.88 s at 100k), so 2 slots give 1.34–1.48×.
* 1k pays fork start-up (17 % above the parent floor) and the 256-activity
  threshold deliberately disables the pipeline below that size; smaller
  networks use the exact sequential loop (and the post-hoc float path when it is
  safe and worthwhile).
* Result unpickling happens in the parent (async result handler). At 100k the
  4-slot parent CPU is 15.02 s against 14.24 s of serial forward + backward +
  assembly + hashing, so transport and merge add ≈0.78 s (5.2 %). Shipping
  compact tuples instead of dataclasses is a measured opportunity, not
  implemented.
* `spawn` stays off by default: it must pickle the whole float context per
  child (the P0-J measurement was 25 µs/activity against 169 µs of work), so a
  non-forking process falls back to the sequential loop unless a caller
  explicitly opts in.
* Wide graphs (`fan`, `wide`) have the level width that would make a forward
  or backward wavefront viable (measured barrier cost 0.13–0.39 ms per level,
  depth 1–3 at 25k). That is a different architecture; P0-M did not build it and
  does not claim it.
* Single-run variance on a 4-CPU cloud host is real: the 100k x2 p95 in the
  first pass included one 25.8 s run while a `git worktree` checkout was
  running; the affected 1k/10k/100k configurations were re-measured on an idle
  host and the clean rows are the ones reported here.

## 11. Reproduction

```bash
# phase table + cProfile attribution (sequential Oracle path)
python3 <evidence>/p0m_phase_profile.py 1000,5000,25000 5 /tmp/phases-1k-25k.json
python3 <evidence>/p0m_phase_profile.py 100000 2 /tmp/phases-100k.json

# wavefront cost model (level structure + measured pool round trip)
python3 <evidence>/p0m_wavefront.py 25000 /tmp/wavefront-25k.json

# benchmark matrix (one fresh process per configuration)
python3 <evidence>/p0m_drive.py 1000,5000,10000,25000,50000,100000 5,5,5,3,3,3 \
    /tmp/matrix.json pipeline,posthoc
python3 <evidence>/p0m_compare.py /tmp/matrix.json /tmp/comparison.json

# equality / fallback suite
python3 -m pytest tests/scheduling/test_time_schedule_pipeline_parallelism.py -q
```

`p0m_matrix.py` implements the two modes and the pipeline instrumentation;
`p0m_drive.py` runs each configuration in its own process and samples the summed
descendant RSS from outside (the pipeline refuses to fork a process with live
threads, so the timing process itself must stay single-threaded).
