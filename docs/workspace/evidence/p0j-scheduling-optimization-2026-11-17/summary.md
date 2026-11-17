# P0-J phase 1–2 evidence: engine profiling and exact scheduling optimisations

* Tested commit: `81ffed5f` (`p0j/scheduling-optimization`, parent `ee9753e6`)
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

## Reproduction

```bash
python scripts/scheduling_core_benchmark.py --mode date --shape dag \
  --sizes 1000,5000,25000 --repeat 7 --warmup 2 --git-sha <sha> --out date.json
python scripts/scheduling_core_benchmark.py --mode time --shape dag \
  --sizes 1000,5000 --repeat 7 --warmup 2 --git-sha <sha> --out time.json
python scripts/scheduling_core_benchmark.py --mode leveling \
  --sizes 100,250,500,1000,5000 --repeat 7 --warmup 2 --git-sha <sha> --out leveling.json
python scripts/scheduling_core_benchmark.py --mode backward-leveling \
  --sizes 100,250,500,1000,5000 --repeat 7 --warmup 2 --git-sha <sha> --out backward.json
python scripts/p0j_leveling_reference.py --mode forward --sizes 100,250,500 \
  --reference-rev ee9753e6 --repeat 1 --git-sha <sha> --out reference-forward.json
python scripts/p0j_leveling_reference.py --mode backward --sizes 100 \
  --reference-rev ee9753e6 --repeat 1 --git-sha <sha> --out reference-backward.json
python scripts/p0j_profile.py --mode leveling --size 5000 --repeat 3 --warmup 1 \
  --profile-top 10 --git-sha <sha> --out profile.json
```

## Limits of this evidence

* 4 effective CPUs; no multi-worker or multi-node claim is made here.
* Peak RSS is process high-water; files with several sizes in one process
  over-attribute RSS to the later sizes.
* Backward leveling at 250 activities could not be measured on the reference
  engine within 600 s; the reported speedup is a lower bound.
* PostgreSQL was verified available for the job-path work but is not on the
  hot path of these pure-engine benchmarks, so no DB timing is claimed here.
