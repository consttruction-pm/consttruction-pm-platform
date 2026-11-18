# P0-K evidence: exact working-day index for calendar arithmetic

* Tested commit: `2c194851` (`p0k/working-day-index`, parent `20778a03`, the
  merged P0-J main). Every JSON records its own `environment.git_sha`.
* Baseline: `20778a03` in a separate worktree (`/tmp/p0k-base`), same machine,
  same Python, same fixtures, same CLI flags. The baseline numbers in
  `baseline-*.json` were captured in this worktree, not copied from an older
  document; `baseline-date-dag-25k-recheck.json` is a second 25k run taken
  after the change to prove the baseline had not drifted.
* Date: 2026-11-18

## Environment (measured)

| Item | Value |
| --- | --- |
| CPU | 4 logical CPUs (`nproc` = 4, `sched_getaffinity` = 4), Linux 5.10.134 x86_64 |
| RAM | 8,131,540 kB total |
| Python | CPython 3.12.13 |
| PostgreSQL | 14.24 on `127.0.0.1:55432` (used only by the test suite; no benchmark touches it) |
| Deployment services | none; all measurements are local engine calls |

## What changed

`WorkingTimeResolver` answered every working-day question with a day-by-day
loop (`next_working_day`, `previous_working_day`, `normalize_*`,
`add_working_duration`, `subtract_working_duration`, `calculate_duration`,
`working_days_between`). On long-duration activities — and on sparse "slack"
networks where dates span years — those loops dominate the CPM passes.

For calendars whose definition is a plain working-weekday set plus canonical
holiday dates, the resolver now builds an exact index over integer ordinals:

* `rank(ordinal)` = working weekdays in `[1, ordinal]` (divmod by 7 plus a
  precomputed per-weekday prefix) minus the count of holiday ordinals that
  fall on working weekdays (`bisect_right`). A holiday on a non-working
  weekday removes nothing, exactly like `is_working_day`.
* `add`/`subtract` invert `rank` inside a bracket derived from the day count
  (earliest/latest possible ordinal, widened only by weekend density and
  holiday slack), so the bisection visits zero to a few ordinals.
* `working_days_between` and `calculate_duration` use the same cumulative
  counts instead of scanning days.
* `next`/`previous`/`normalize` still use the direct `is_working` predicate.

**Nothing about the calendar definition, the working-day rules, the inclusive
duration semantics or the error messages changed.** The original loops are
still present verbatim and remain the runtime path for calendars whose
effective holidays are not the `holidays` attribute (exception overlays) and
for calendars without any working day. They are also the executable oracle in
`tests/scheduling/test_working_day_index_equivalence.py`.

## Correctness evidence

Differential module `tests/scheduling/test_working_day_index_equivalence.py`
(32 tests, passes at `2c194851`). The oracle is the pre-change loop code,
copied verbatim into the test module.

| Dimension | Coverage |
| --- | --- |
| Calendars | Mon–Fri; Mon–Fri with weekday/weekend holidays; Mon–Sat; all 7 days with a 40-day contiguous holiday block; sparse `{0,2,4}` weekdays; Jalali calendar with Jalali holidays |
| Predicate | `index.is_working` vs `calendar.is_working_day` for 800 consecutive days per calendar |
| Step ops | `next`/`previous`/`normalize_start`/`normalize_finish` compared for every day of an 800-day window per calendar |
| Durations | 1,500 randomized add/subtract cases per calendar (durations 0–399), 400 randomized `calculate_duration` and `working_days_between` cases per calendar, multi-year durations 0/1/5/20/260/1,000/5,000 |
| Semantics | weekend holidays not subtracted twice; 40-day holiday block; holiday-ordinal list only holds holidays on working weekdays |
| Preservation | exception overlays and empty-weekday calendars keep the legacy path (`_day_index is None`); duration validation messages, finish-before-start message, `OverflowError` at the date range, Jalali boundary conversion |

Full suite at `2c194851`:

```
P6_TEST_POSTGRES_DSN=postgresql://postgres@127.0.0.1:55432/postgres python -m pytest -q
4921 passed, 131 skipped in 50.46s
```

The same suite without the DSN also passes (4,831 passed, 212 skipped — the 81
extra skips are the Postgres modules). During one full-suite run on the
intermediate revision the timing-sensitive
`test_job_path_is_isolated_between_tenants_and_projects` failed once; it
passed immediately in module isolation and in both full-suite runs at the
tested SHA. It exercises an in-memory job repository and worker-thread budget,
not calendar arithmetic.

## Benchmark: same fixtures, same flags, both sides

`scripts/scheduling_core_benchmark.py`, `--shape dag --seed 20261116`,
warm-ups/repeats as recorded per file. Median wall time, `peak_rss_kb`, and
canonical `output_sha256`; every hash is byte-identical between the two sides.

| Mode | Size | Baseline ms | New ms | Speedup | Baseline RSS kB | New RSS kB |
| --- | --- | --- | --- | --- | --- | --- |
| date | 1,000 | 61.8 | 48.3 | 1.28× | 52,088 | 52,068 |
| date | 5,000 | 317.6 | 253.3 | 1.25× | 61,976 | 61,792 |
| date | 25,000 | 1,665.6 | 1,335.1 | 1.25× | 111,984 | 112,644 |
| date | 100,000 | 7,427.2 | 6,058.4 | 1.23× | 295,016 | 297,608 |
| time | 1,000 | 314.4 | 315.3 | 1.00× | 52,644 | 52,552 |
| time | 5,000 | 1,567.5 | 1,573.6 | 1.00× | 66,112 | 66,504 |
| time | 25,000 | 8,076.9 | 8,058.3 | 1.00× | 133,400 | 133,376 |
| leveling | 100 | 14.2 | 13.9 | 1.02× | 50,220 | 50,208 |
| leveling | 500 | 82.4 | 82.3 | 1.00× | 54,440 | 54,368 |
| leveling | 5,000 | 992.1 | 980.1 | 1.01× | 98,836 | 98,860 |

Time-aware scheduling is unchanged because it does not route through
working-day date arithmetic; that is the expected scope boundary, and it is
also a control: the change does not perturb paths it should not touch.

### Cross-shape date runs (5,000 activities, 3 repeats, 1 warm-up)

| Shape | Baseline ms | New ms | Speedup | Hash equal |
| --- | --- | --- | --- | --- |
| chain | 217.8 | 180.2 | 1.21× | yes |
| wide | 121.3 | 89.2 | 1.36× | yes |
| fan | 324.9 | 258.8 | 1.26× | yes |
| mixed | 5,179.2 | 267.8 | 19.3× | yes |
| slack | 43,564.9 | 188.1 | 231.6× | yes |

`mixed` and `slack` build long lags/durations, where the legacy code stepped
through every calendar day per call; the index removes that per-day cost while
producing identical dates (all output hashes equal, run status `ok`).

### Where the time went (25,000-activity date run, cProfile + phase timers)

| Phase | Baseline ms (share) | New ms (share) |
| --- | --- | --- |
| backward pass | 722.8 (42.5%) | 561.5 (41.9%) |
| float calculation | 534.6 (31.4%) | 388.2 (29.0%) |
| forward pass | 420.2 (24.7%) | 362.2 (27.0%) |
| total wall | 1,701 | 1,340 |

Before, the top self-time was `calendar.to_gregorian` (2,582,623 calls,
828.8 ms) and `is_working_day` (1,387,312 calls in two frames, 797.7 ms
combined), fed by `next_working_day` (245,754), `previous_working_day`
(241,509), `add_working_duration` (195,759) and `subtract_working_duration`
(168,643). After, no `is_working_day` frame appears in the top sample, and the
remaining calendar cost is the two duration entry points themselves.

cProfile inflates absolute time; it is used here only for attribution.

## Limits of this evidence

* Only the shapes, seeds and sizes in the JSON files were measured. Nothing is
  extrapolated.
* Time-aware (`time`) mode shows no gain; its arithmetic is a different path
  and is intentionally untouched.
* The Jalali coverage is property/differential testing, not a measured
  benchmark.
* A single 4-CPU machine; no claim is made about larger hardware.

## Reproduction

```bash
# correctness
P6_TEST_POSTGRES_DSN=postgresql://postgres@127.0.0.1:55432/postgres python -m pytest -q
python -m pytest tests/scheduling/test_working_day_index_equivalence.py -q

# benchmarks (new)
python scripts/scheduling_core_benchmark.py --mode date --sizes 1000,5000,25000 \
    --shape dag --seed 20261116 --repeat 5 --warmup 2 --git-sha 2c194851 --out /tmp/new-date.json
python scripts/scheduling_core_benchmark.py --mode time --sizes 1000,5000,25000 \
    --shape dag --seed 20261116 --repeat 3 --warmup 1 --git-sha 2c194851 --out /tmp/new-time.json
python scripts/scheduling_core_benchmark.py --mode leveling --sizes 100,500,5000 \
    --shape dag --seed 20261116 --repeat 5 --warmup 2 --git-sha 2c194851 --out /tmp/new-level.json

# benchmarks (baseline, in a worktree at 20778a03)
git worktree add /tmp/p0k-base 20778a03
cd /tmp/p0k-base && python scripts/scheduling_core_benchmark.py --mode date \
    --sizes 1000,5000,25000 --shape dag --seed 20261116 --repeat 5 --warmup 2 \
    --git-sha 20778a03 --out /tmp/base-date.json
```
