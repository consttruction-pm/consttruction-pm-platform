# P0-L — Time-aware working-day capacity index and resolver memoisation

Tested code commit: `9909695fef7d1a4ee5ff4a93784f40a92b6090f7`
Baseline: `afc8c70152717426333977a6ad4aab15143031e8` (main after P0-K), compared
in a detached worktree at `/tmp/p0l-baseline` on the same host in the same
session.

Environment: 4 CPUs (affinity), 8,131,540 kB RAM, CPython 3.12.13, Linux
x86_64. Fixtures: `tests/scheduling/benchmark_fixtures.py`, seed `20261116`
(Mon–Fri 08:00–12:00 / 13:00–17:00, holidays 2026-01-06 / 02-17 / 03-20,
naive calendar). Every timing is the CPU median of whole `time_schedule`
runs, 3 repeats (2 for 100k) with the harness warm-up.

## 1. Bottlenecks

Profiling the pre-change code at 25k activities (`profile-before-time-dag-25k.txt`,
`cProfile`, 46.8 s instrumented):

- `add_working_hours` 893,214 calls / 7.18 s self, `subtract_working_hours`
  624,572 / 3.63 s; both walked **every interval of every date** in the span
  and called `datetime.combine` 17.2 M times.
- `calculate_working_hours` 145,762 calls visited each date in the span with
  the same per-interval loop.
- `CalendarResolverRegistry._registered_resolver` 1,238,984 calls / 1.35 s and
  `_resolved_exception_layers` 1,238,984 / 1.15 s rebuilt validation and
  overlay layers for the same immutable reference on every activity.
- `_duration_microseconds` 1,517,786 calls spent time in `Decimal(str(...))`
  for values that arrive as exact `int`/`Decimal`.

The instrumentation (`call-counts-before-25k.json`) confirms the duplication:
`_combine` 8.31 M and `_timedelta_microseconds` 2.73 M cold calls for a single
25k schedule; `resolve` was called 558,051 times for two calendar references.

## 2. Changes

`src/construction_pm/scheduling/time_calendar.py`

- `_DayCapacity` profile per **effective interval tuple** (`_capacity_for`):
  each interval's capacity is `_wall_microseconds(start, end)`, which is exactly
  what the old loop measured with `combine(date, end) - combine(date, start)`.
  Both datetimes are built with the caller's tzinfo object, so CPython
  subtracts wall-clock fields and the UTC offset cancels — a DST transition
  cannot change an intra-date length, so the profile needs no date or zone key.
  Non-positive intervals record 0, because the loop guard never consumes them.
- `add_working_hours` / `subtract_working_hours` walk the first (partial) day
  exactly as before, then skip whole days by `profile.total` and only build
  datetimes on the day that contains the answer. The answered day is still
  walked interval by interval with the original guards.
- `calculate_working_hours` measures both boundary days exactly, adds middle
  days from `profile.capacities`, and keeps the **verbatim** day-by-day loop
  (`_calculate_working_hours_by_day`) when `start.tzinfo is not finish.tzinfo`,
  where instant comparison can reverse date ordering. The single-date branch is
  verbatim.
- `_duration_microseconds` returns `value * 3_600_000_000` for `int` values in
  `[0, 10**15)` (well inside 28-digit context precision, so the old Decimal
  product could not have rounded either) and skips the `Decimal(str(...))`
  round-trip for plain `Decimal`. Negative/oversized ints, floats, bools,
  NaN/Infinity and sub-microsecond values take the original path with the
  original messages.

`src/construction_pm/scheduling/calendar_context.py`

- `CalendarResolverRegistry.resolve` memoises the validated, overlay-built view
  keyed by `(calendar_id, calendar_version, kind, system)`. The registry copies
  every mapping in `__init__`, exposes no mutator, and only successes are
  cached, so a second call cannot skip a validation error and cannot serve a
  view built from different mappings.

No scheduling rule, calendar definition, float rule, decision order, worker
behaviour or error message was changed. No second engine or parallel path was
added; the original loops remain in the codebase as the test oracle and as the
mixed-zone fallback.

## 3. Correctness proof

1. **Oracle differential** — `tests/scheduling/test_time_capacity_index_equivalence.py`
   (86 tests, 9.7 s) keeps a verbatim copy of the previous loops
   (`OracleTimeResolver`, including the `_require_datetime` prologues) and
   compares value and exception (type and message) for add, subtract,
   normalize, calculate and interval lookup over:
   5 calendars (split, dense, single-interval, bridge-over-lunch, night,
   seven-day, weekend, Jalali-system) × 5 zones (naive, UTC, fixed +03:30,
   America/New_York, Europe/London), probe dates around DST transitions and
   holidays, large durations (123.5 h, 2,080 h, 2,000 h), overflow past
   `date.max`/`date.min`, invalid durations and non-datetime inputs,
   fractional round trips, pickling, capacity-profile equality over 400 days,
   exception overlays and inherited layers, mixed-zone `calculate_working_hours`,
   and an end-to-end `time_schedule` built on an **oracle-backed registry**
   (24 activities, 2 calendars, FS/SS/FF/SF, lags 0/±8/16, 1 vs 2 workers,
   identical fingerprint).
2. **Mutation check** — adding `+1` µs to `_wall_microseconds` is detected
   (`mutation-check-1us.log`), so the suite is sensitive to a one-microsecond
   capacity error.
3. **Canonical hashes** — every benchmark output hash is identical to the
   baseline (`comparison.json`): time 1k/5k/25k/100k, mixed 5k/25k, date
   1k/5k/25k, leveling 100/1k/5k, backward leveling 100/1k/5k. Successor
   counts, project finishes and float values are part of the hash.

## 4. Tests

- New differential module: **86 passed** in 9.7 s.
- Full suite on the tested commit: **5,272 passed, 1 skipped, 0 failed**
  (`full-suite-branch.log`).
- Baseline worktree: **5,186 passed, 1 skipped** — the difference is exactly
  the 86 new tests.
- One run showed a single failure in
  `test_scheduling_job_authoritative_path.py::test_job_path_runs_the_authoritative_snapshot_engine_end_to_end`
  (`succeeded=1/3`). It reproduces **identically on the unmodified baseline**
  (`job-path-flake-repro-baseline-afc8c701.log`) and on the branch
  (`job-path-flake-repro-branch.log`) with `InterfaceError: bad parameter or
  other API misuse` and `ValueError: SCHEDULE_INPUT_SNAPSHOT_NOT_FOUND`: a
  pre-existing SQLite shared-connection race in the in-memory job harness,
  unrelated to calendar arithmetic (no job-path or SQLite code was touched).
  Three later full-suite runs were clean.

## 5. Benchmarks (CPU median, same host, same fixtures)

| Mode | Size | Before | After | Speedup | Hash equal | Peak RSS before → after |
| --- | --- | --- | --- | --- | --- | --- |
| time | 1,000 | 319.6 ms | 223.9 ms | **1.43×** | yes | 54,896 → 52,480 kB |
| time | 5,000 | 1,598.7 ms | 1,134.0 ms | **1.41×** | yes | 67,180 → 66,156 kB |
| time | 25,000 | 8,104.5 ms | 5,792.7 ms | **1.40×** | yes | 134,640 → 133,088 kB |
| time | 100,000 | 33,361.4 ms | 23,960.1 ms | **1.39×** | yes | 384,984 → 385,112 kB |
| time mixed | 5,000 | 1,763.4 ms | 1,284.6 ms | **1.37×** | yes | 66,176 → 65,920 kB |
| time mixed | 25,000 | 9,084.6 ms | 6,686.1 ms | **1.36×** | yes | 131,660 → 132,580 kB |
| date | 1,000 | 55.7 ms | 56.0 ms | 1.00× | yes | — |
| date | 5,000 | 253.7 ms | 257.5 ms | 0.99× | yes | — |
| date | 25,000 | 1,351.0 ms | 1,363.9 ms | 0.99× | yes | — |
| leveling | 100 / 1k / 5k | 44.5 / 183.2 / 991.9 ms | 47.8 / 183.7 / 989.8 ms | 1.00× (noise) | yes | — |
| backward leveling | 100 / 1k / 5k | 47.1 / 231.9 / 1,336.2 ms | 45.2 / 232.9 / 1,334.8 ms | 1.00× (noise) | yes | — |

RSS is flat: −2.4 % at 1k, −0.1 % at 100k; the +0.7 % at mixed 25k is within
the ±1 % run-to-run spread seen on this host. Non-time modes are unchanged
within noise and keep identical output.

Phase attribution at 25k (`phase-attribution-*.jsonl`):

| Phase | Before | Capacity index only | Index + resolver memo |
| --- | --- | --- | --- |
| forward | 910.8 ms | 815.7 ms | 703.9 ms |
| backward | 2,953.8 ms | 2,573.1 ms | 2,292.1 ms |
| float | 4,152.1 ms | 2,904.5 ms | 2,743.6 ms |
| total | 8,044.9 ms | 6,336.0 ms | 5,789.0 ms |

The float pass gains most (1.51×) because it repeatedly measures short spans.
The capacity index alone accounts for 8,044.9 → 6,336.0 ms; the registry memo
plus the Decimal fast path accounts for 6,336.0 → 5,789.0 ms (≈9 %).

Call counts, cold 25k (`call-counts-*.json`): `_combine` 8,313,518 →
4,744,168 (−43 %), `_timedelta_microseconds` 2,732,667 → 1,397,271 (−49 %),
`_capacity_for` 1,474,360 calls with one cache entry per resolver;
`_registered_resolver` / `_resolved_exception_layers` fall out of the profile
entirely after memoisation (previously 1,238,984 calls each at 1.35 s / 1.15 s
self time).

## 6. Limits

- The capacity profile is exact because intra-date subtraction is wall-clock
  for a shared tzinfo object; this is proven by the DST cases in the
  differential suite, not assumed from a per-date table.
- Whole-day skipping assumes the day lies strictly between the endpoint dates.
  Mixed-tzinfo endpoints are detected and routed to the verbatim loop.
- The capacity memo is bounded at 4,096 distinct daily shapes and is a pure
  cache; clearing it cannot change a result.
- The registry memo is only safe because `CalendarResolverRegistry` copies its
  inputs and has no mutator. A new registry must be built for new calendar
  mappings, exactly as before.
- `_duration_microseconds` keeps the original validation for every value type
  except non-negative `int < 10**15` and plain `Decimal`, where the results are
  provably identical.
- Time-aware CPM at 100k still takes ~24 s on this 4-CPU host; the remaining
  cost is dominated by `time_schedule` bookkeeping and the float search, not by
  calendar capacity.

## 7. Reproduce

```bash
# baseline worktree
git worktree add /tmp/p0l-baseline afc8c701

# differential suite (branch)
PYTHONPATH=src python3 -m pytest tests/scheduling/test_time_capacity_index_equivalence.py -q

# benchmarks, run once from each tree
python3 scripts/scheduling_core_benchmark.py --mode time --sizes 1000,5000,25000 \
    --shape dag --repeat 3 --seed 20261116 --out /tmp/out.json
```

Evidence files: `comparison.json`, `profile-{before,after}-time-dag-25k.txt`,
`phase-attribution-{before,capacity-only,after}.jsonl`,
`call-counts-{before,after}-{5k,25k}.json`, `*time*dag*.json`,
`time-mixed-5k-25k.json`, `time-capacity-only-dag-5k-25k.json`,
`date-*`, `leveling-*`, `backward-leveling-*`, `mutation-check-1us.log`,
`full-suite-*.log`, `job-path-flake-repro-*.log`.
