# P0 scheduling core optimization — baseline and exact-equivalence evidence

Date: 2026-11-16
Branch: `p0/scheduling-core-optimization`
Reference (baseline) commit: `e02850361300c494477148bd5e426d2516534ad5`
Optimized commit: `d764c81d6de834390f335971f9069c5a64b8228b`

Scope: P0-A (baseline), P0-B (deterministic heap topological ordering), P0-C
(Time-Aware Free Float bounded search) and P0-D (forward resource leveling
demand index/ledger). No scheduling option, calculation, validation, calendar
rule, relationship behaviour, Float rule, leveling rule or cost calculation was
removed, simplified or bypassed.

## Environment (measured, not assumed)

Source: `environment.json`.

| Item | Value |
|---|---|
| CPU | 4 logical CPUs, AMD EPYC, observed 2250 MHz, affinity 4 |
| Effective CPU quota | no cgroup `cpu.max` limit exposed in this sandbox |
| RAM | 8,131,540 kB total, 5,822,720 kB available at start |
| OS / kernel | Linux 5.10.134, x86_64, glibc 2.35 |
| Python | CPython 3.12.13 |
| Process start method | one fresh Python process per measurement; no threads, no workers |

Consequences recorded honestly:

- The Python 3.11 / 3.12 / 3.13 matrix cannot be produced here (only 3.10 and
  3.12 binaries exist); it must come from the GitHub Actions Python matrix.
- 16 / 32 / 64+ worker counts cannot be genuinely supplied on 4 CPUs. Those
  P0-G matrix rows are **NOT MEASURED**, not estimated.

## Fixtures

`src/construction_pm/scheduling/benchmark_fixtures.py` builds pure functions of
`(size, shape, seed)`. A small explicit LCG is used instead of `random` so the
same seed yields the same network on any Python version. Durations are
`index % 5 + 1` working days; the date calendar has four fixed 2026 holidays.
Time-aware fixtures use a 08:00–12:00 / 13:00–17:00 calendar with holidays and
8-hour-per-day durations.

| Shape | Structure | Purpose |
|---|---|---|
| `chain` | `i-1 -> i` | deep network, ready queue of 1 |
| `wide` | no relationships | largest possible ready frontier |
| `dag` | spine + 1–2 extra backward edges per node (~1.9 edges/node) | default realistic DAG |
| `fan` | node 0 -> all, all -> last | maximal ready-set churn |
| `mixed` | DAG with FS/SS/FF/SF and lags -1/0/1/2 | relationship coverage |
| `slack` | long spine + short activities feeding the last node | large Free Float for the P0-C search |

Deliberately not yet in the fixtures, therefore not measured: constraints,
Data Date, progressed activities, cross-project relationships, shared
resources, cost/rate inputs. Those remain P0-E..P0-I work.

## Method

- Each measurement runs in a fresh process, one size per process, so
  `peak_rss_kb` is attributable to that size.
- `wall` and `cpu` are `time.perf_counter` / `time.process_time` samples;
  tables below use the median. Fixture construction is timed separately
  (`fixture_build_ms`) and excluded from engine wall time.
- `output_sha256` is SHA-256 over a canonical, key-sorted JSON serialisation of
  the complete engine result: every early/late date, duration, remaining date,
  Total Float, Free Float, critical flag, Float Path/Order, project finish,
  mode, diagnostics (date path); every early/late datetime, duration unit,
  float value/unit/critical flag and project finish (time path); every ordered
  leveling shift with its new dates and consumed/remaining float.
- The harness records an error object instead of extrapolating when a size
  cannot complete.

Reproduce a row:

```bash
python3 scripts/scheduling_core_benchmark.py --mode date --sizes 100000 \
  --shape dag --repeat 1 --git-sha <sha> --out out.json
```

Baseline rows were produced from a worktree at `e0285036` containing only the
new fixture module and CLI (untracked). Optimized rows were produced from the
working tree that became `d764c81d`; the four anchor rows were re-run on the
committed SHA itself (`optimized/anchors/`).

## Results — Date-Based CPM (`schedule()`)

Sizes 1k–50k from `baseline/date-dag-1k-50k.json` and
`optimized/date-dag-1k-50k-and-100k-in-process.json`; 100k from the standalone
files. Median wall time, ms.

| Shape | Size | Baseline | Optimized | Change | Hash equal |
|---|---|---|---|---|---|
| dag | 1,000 | 150.0 | 149.0 | 1.01x | yes |
| dag | 5,000 | 727.2 | 726.1 | 1.00x | yes |
| dag | 25,000 | 3,725.9 | 3,708.4 | 1.00x | yes |
| dag | 50,000 | 7,697.8 | 7,651.0 | 1.01x | yes |
| dag | 100,000 | 15,441.7 | 15,505.4 | 1.00x (noise) | yes |
| wide | 25,000 | 704.5 | 666.9 | 1.06x | yes |
| wide | 100,000 | 3,640.4 | 3,040.0 | 1.20x | yes |
| fan | 10,000 | 1,643.1 | 1,172.4 | 1.40x | yes |
| fan | 25,000 | 5,944.7 | 3,011.3 | 1.97x | yes |

Peak RSS: 100k DAG 227,524 kB optimized vs 227,304 kB baseline; 100k wide
227,868 vs 163,408 kB (the empty relationship set makes the baseline smaller;
the heap adds no material memory).

Interpretation: the heap removes the quadratic ready-list shift and the
re-sorts, which is dominant only when the ready frontier is large (`wide`,
`fan`). For the spine-dominated `dag` shape the engine is bound by calendar
arithmetic, so the change is neutral there, as expected from the algorithm.

## Results — Time-Aware CPM + Float (`time_schedule()`)

`float_days=2` keeps the project finish two working days past the earliest
finish, so Free Float is realistic rather than pinned at the sentinel.

| Shape | Size | Baseline | Optimized | Change | Hash equal |
|---|---|---|---|---|---|
| dag | 1,000 | 1,700.8 | 680.1 | 2.50x | yes |
| dag | 5,000 | 8,266.7 | 3,348.9 | 2.47x | yes |
| dag | 25,000 | 41,009.1 | 17,103.8 | 2.40x | yes |
| dag | 50,000 | 83,052.4 | 34,270.9 | 2.42x | yes |
| dag | 100,000 | 165,300.2 | 68,235.6 | 2.42x | yes |
| wide | 25,000 | 1,944.1 | 1,917.7 | 1.01x | yes |
| fan | 10,000 | 6,769.8 | 6,577.0 | 1.03x | yes |

Peak RSS 100k DAG: 286,568 kB baseline / 286,724 kB optimized.

### Float-search stress (`slack` shape, `float_days=1`)

| Size | Max Free Float observed | Baseline | Optimized | Change | Hash equal |
|---|---|---|---|---|---|
| 40 | 472 h | 993.9 | 54.0 | 18.4x | yes (`4ffbec4b…`) |
| 80 | 952 h | 7,756.9 | 208.1 | 37.3x | yes (`4b503155…`) |

The legacy scan is quadratic in the Free Float magnitude because each probe
re-adds the delay from the activity start. The bounded search evaluates at
most ~30 delays, so the gain grows with the slack, exactly as expected.

## Results — Forward Resource Leveling (`propose_forward_leveling_within_float`)

Waves of 8 activities over 2 resources, demand 4 units/period, capacity 8,
Total Float 10, so the pass accepts real shifts.

| Size | Baseline | Optimized | Change | Ordered shifts | Hash equal |
|---|---|---|---|---|---|
| 100 | 9,421.2 | 1,071.7 | 8.8x | 66 | yes (`ef51580f…`) |
| 250 | 161,182.7 | 18,472.7 | 8.7x | 168 | yes (`d811889a…`) |
| 500 | not measured | 158,261.6 | — | 336 | n/a |

- Reference-engine leveling at 1,000 activities was attempted with a 300 s
  budget and did not complete; 250 activities took 161 s on the reference
  engine. The remaining P0-A leveling sizes (1k/5k/25k/50k/100k) are therefore
  **NOT MEASURABLE on this host with the reference algorithm** and no numbers
  are invented for them.
- The optimized pass is still superlinear (250 -> 500 is 8.6x) because the
  algorithm still accepts exactly one working-day shift per iteration. The
  ledger removes repeated date arithmetic and repeated per-period scans, not
  the one-shift-per-iteration decision schedule. Further reduction requires
  changing the accepted-decision sequence and is out of P0-D scope.
- Every accepted shift, its order, new start/finish and consumed/remaining
  float is byte-identical to the reference (`leveling_payload` hash).

## Exact-equivalence evidence

1. Every row in every table has the same `output_sha256` in `baseline/` and
   `optimized/`. No row differs.
2. Anchor rows re-run on the committed SHA itself:

| Anchor | Hash | Reference hash |
|---|---|---|
| date dag 1,000 | `9c6c4a26…` | `9c6c4a26…` |
| time dag 1,000 | `2509bb16…` | `2509bb16…` |
| time slack 40 | `4ffbec4b…` | `4ffbec4b…` |
| leveling 100 | `ef51580f…` | `ef51580f…` |

3. Golden leveling shift hashes captured from the reference engine before the
   ledger change (`leveling_case` 40/60/110 -> `f4c24a36…`, `7fd94ae8…`,
   `f0b17920…`) still match; they are asserted in
   `tests/scheduling/test_benchmark_fixtures.py`.
4. Full Python suite: **4,446 passed, 204 skipped** at the code commit
   `d764c81d`, and **4,449 passed, 204 skipped** with the golden leveling-hash
   assertions added in the accompanying evidence/verification commit. Added
   tests:
   - `tests/scheduling/test_topological_order.py` — differential comparison of
     the heap against the literal pre-P0-B list algorithm over 25 seeded DAGs
     (including duplicate edges, disconnected components, cycles, unknown
     references, lexicographic edge cases such as `A10` < `A2`);
   - `tests/scheduling/test_time_float_search.py` — boundary equivalence at
     F = 0,1,2,7,8,9,16,17,1000,9998,9999,10000,20000 and the no-boundary
     sentinel, probe-count bound, schedule-level differential with the legacy
     scan restored by monkeypatch for 5 shapes x 2 float offsets, and
     monotonicity of duration/lag arithmetic across holidays and signed lags;
   - `tests/scheduling/test_benchmark_fixtures.py` — fixture reproducibility,
     forward-only edges, canonical-hash determinism and leveling golden hashes.

## Measurement caveats

- The host is shared and not frequency-stable. A time-path case measured
  1.7x slower in a later session with an identical hash and identical input
  counts (same fixture), which is host variability, not product behaviour.
  Therefore: (a) every baseline/optimized pair above is a back-to-back,
  same-session comparison; (b) `baseline/time-dag-recheck.json` exists solely
  to document that recheck; (c) absolute values are not a capacity claim.
- The 100k date row inside `date-dag-1k-50k-and-100k-in-process.json` was
  produced in a process that had already scheduled smaller sizes. Its peak RSS
  (294,620 kB) includes retained memory from earlier sizes and must not be read
  as a 100k figure; use `date-dag-100k.json` (227,524 kB) instead.
- The 3.11/3.13 matrix, PostgreSQL-backed scheduling runs, concurrency tests,
  queue-wait/throughput and multi-worker speedup are outside this slice and
  are not claimed.

## What remains (P0-E..P0-I)

Measured facts that drive the next phases:

- Leveling orchestration still runs an initial, intermediate and final CPM and
  a CPM per backward candidate; the reference engine at 250 activities already
  costs 161 s in the proposal pass, so repeated full CPM must be counted and
  bounded before any worker pooling.
- The time-aware path costs ~0.68 ms/activity at 100k with a tight float; the
  date path ~0.155 ms/activity. There is no intra-project parallelism and no
  durable job lifecycle yet; both are unmeasured because they do not exist at
  this commit.
- No single-flight/result cache exists; no worker supervisor exists.
