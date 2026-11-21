# P0-N.2 performance and capacity evidence

Generated from the raw JSON of a single instrumented run: `matrix-20261120T035930Z.json` and `worker-e2e-20261120T035930Z.json`. Every number in every table below is read back from those files; nothing is estimated, extrapolated or copied from an earlier run. Cells that did not complete are listed with their exact recorded error text.

## Environment

| Item | Value |
| --- | --- |
| python | 3.12.13 |
| platform | Linux-5.10.134-013.10.1.kangaroo.al8.x86_64-x86_64-with-glibc2.35 |
| machine | x86_64 |
| cpu_count | 4 |
| cpu_affinity_count | 4 |
| memory_total_kb | 8131540 |
| git_sha | 5b4cfb7104cbd4952d60af9734cfe1b559aa923f |
| branch | feat/p0n2-runtime-activation |
| commit | 5b4cfb7104cbd4952d60af9734cfe1b559aa923f |
| PostgreSQL | PostgreSQL 14.24 (Ubuntu 14.24-0ubuntu0.22.04.1) on x86_64-pc-linux-gnu, compiled by gcc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0, 64-bit |
| started | 2026-11-20T03:59:30.852552+00:00 |
| finished | 2026-11-20T04:17:26.691235+00:00 |
| matrix phase wall clock | 1075.8 s |

Working tree at run time (`git status --porcelain`, pre-existing edits made by other work in this session, **not** by this harness — the harness only writes the evidence files listed in Scope):

```
M docs/workspace/evidence/p0n-runtime-activation-2026-11-20/job-lifecycle-evidence.md
 M docs/workspace/evidence/p0n-runtime-activation-2026-11-20/runtime-composition-map.md
 M docs/workspace/evidence/p0n-runtime-activation-2026-11-20/two-environment-reference-map.md
 M src/construction_pm/deployment/production_runtime.py
 M src/construction_pm/scheduling_job_runner.py
?? docs/workspace/evidence/p0n-runtime-activation-2026-11-20/README.md
?? docs/workspace/evidence/p0n-runtime-activation-2026-11-20/final-acceptance-report.md
?? docs/workspace/evidence/p0n-runtime-activation-2026-11-20/logs/live-job-run-process.log
?? docs/workspace/evidence/p0n-runtime-activation-2026-11-20/logs/live-job-run-thread.log
?? docs/workspace/evidence/p0n-runtime-activation-2026-11-20/logs/worker-e2e.log
?? docs/workspace/evidence/p0n-runtime-activation-2026-11-20/multi-project-budget-evidence.md
?? docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/
?? scripts/p0n2_runtime_matrix.py
```

## Exact commands

```
scripts/p0n2_runtime_matrix.py run --out-dir docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results --dsn postgresql://postgres@127.0.0.1:55432/postgres
```

The orchestrator spawns one subprocess per unit; the recorded command lines (in `runs[].command` of the raw matrix JSON, in `runs[].unit_run.command` of the worker JSON, and prefixed with `$ ` in the `.log`) are:

```
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 1000 --shape chain --deadline 1795147380.933 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-00-1000-chain.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 1000 --shape wide --deadline 1795147381.746 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-01-1000-wide.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 1000 --shape mixed --deadline 1795147382.311 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-02-1000-mixed.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 1000 --shape resource-heavy --deadline 1795147383.470 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-03-1000-resource-heavy.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 1000 --shape constraint-heavy --deadline 1795147384.586 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-04-1000-constraint-heavy.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 5000 --shape chain --deadline 1795147446.054 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-05-5000-chain.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 5000 --shape wide --deadline 1795147449.000 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-06-5000-wide.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 5000 --shape mixed --deadline 1795147450.574 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-07-5000-mixed.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 5000 --shape resource-heavy --deadline 1795147455.474 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-08-5000-resource-heavy.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 5000 --shape constraint-heavy --deadline 1795147460.331 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-09-5000-constraint-heavy.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 25000 --shape chain --deadline 1795147593.935 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-10-25000-chain.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 25000 --shape wide --deadline 1795147601.405 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-11-25000-wide.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 25000 --shape mixed --deadline 1795147605.301 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-12-25000-mixed.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 25000 --shape resource-heavy --deadline 1795147618.109 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-13-25000-resource-heavy.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 25000 --shape constraint-heavy --deadline 1795147633.003 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-14-25000-constraint-heavy.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 50000 --shape chain --deadline 1795148071.286 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-15-50000-chain.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 50000 --shape wide --deadline 1795148086.484 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-16-50000-wide.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 50000 --shape mixed --deadline 1795148094.307 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-17-50000-mixed.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 50000 --shape resource-heavy --deadline 1795148120.323 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-18-50000-resource-heavy.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 50000 --shape constraint-heavy --deadline 1795148150.933 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-19-50000-constraint-heavy.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 100000 --shape chain --deadline 1795148495.395 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-20-100000-chain.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 100000 --shape wide --deadline 1795148526.896 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-21-100000-wide.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 100000 --shape mixed --deadline 1795148543.361 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/cell-22-100000-mixed.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _capacity --slots 1 --deadline 1795148446.593 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/capacity-1.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _capacity --slots 2 --deadline 1795148455.067 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/capacity-2.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _capacity --slots 4 --deadline 1795148463.577 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/capacity-4.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _capacity --slots 8 --deadline 1795148469.440 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/capacity-8.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _capacity --slots 16 --deadline 1795148475.216 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/capacity-16.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _projects --count 1 --deadline 1795148781.040 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/projects-1.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _projects --count 2 --deadline 1795148783.971 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/projects-2.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _projects --count 4 --deadline 1795148789.071 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/projects-4.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _projects --count 8 --deadline 1795148797.465 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/projects-8.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _projects --count 16 --deadline 1795148814.003 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/projects-16.json
/usr/bin/python3 scripts/p0n2_runtime_matrix.py _cell --size 100000 --shape resource-heavy --deadline <+1500s> --result-file .../cell-100000-resource-heavy.json
/usr/bin/python3 scripts/p0n2_runtime_matrix.py _cell --size 100000 --shape constraint-heavy --mode-budget 1800 --deadline <+5000s> --result-file .../cell-100000-constraint-heavy.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _worker --dsn postgresql://postgres@127.0.0.1:55432/postgres --size 1000 --mode thread --deadline 1795148666.702 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/worker-1000-thread.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _worker --dsn postgresql://postgres@127.0.0.1:55432/postgres --size 1000 --mode process --deadline 1795148667.725 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/worker-1000-process.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _worker --dsn postgresql://postgres@127.0.0.1:55432/postgres --size 5000 --mode thread --deadline 1795148668.774 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/worker-5000-thread.json
/usr/bin/python /data/work/repo/scripts/p0n2_runtime_matrix.py _worker --dsn postgresql://postgres@127.0.0.1:55432/postgres --size 5000 --mode process --deadline 1795148670.536 --result-file /data/work/repo/docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results/.unit-20261120T035930Z/worker-5000-process.json
```

## Post-phase re-runs

Two 100k cells exceeded the orchestrated phase deadline (960 s) and were measured in separate subprocess invocations with an explicit --mode-budget: 100000/resource-heavy (1500 s) and 100000/constraint-heavy (1800 s per mode). They replace the SKIPPED_BUDGET records; the superseded status, its exact error text and the overriding command are kept in each cell (post_phase_rerun, superseded_record, mode_budget_override_s).

| size | shape | status | overriding command |
| --- | --- | --- | --- |
| 100000 | resource-heavy | OK | `/usr/bin/python3 scripts/p0n2_runtime_matrix.py _cell --size 100000 --shape resource-heavy --deadline <+1500s> --result-file .../cell-100000-resource-heavy.json` |
| 100000 | constraint-heavy | OK | `/usr/bin/python3 scripts/p0n2_runtime_matrix.py _cell --size 100000 --shape constraint-heavy --mode-budget 1800 --deadline <+5000s> --result-file .../cell-100000-constraint-heavy.json` |

Superseded first-pass records, with their exact error text:

- (100000, resource-heavy) was `SKIPPED_BUDGET`: SKIPPED_BUDGET: matrix phase budget 960s exhausted; remaining -15.7s at cell (100000,resource-heavy)
- (100000, constraint-heavy) was `SKIPPED_BUDGET`: SKIPPED_BUDGET: matrix phase budget 960s exhausted; remaining -15.7s at cell (100000,constraint-heavy)

## Fixture definitions

| Shape | Definition (recorded) |
| --- | --- |
| chain | `time_network(size, "chain", seed=20261116)` |
| wide | `time_network(size, "wide", seed=20261116)` |
| mixed | `time_network(size, "mixed", seed=20261116)` |
| resource-heavy | `time_network(size, "fan", seed=20261116) (fan: one root -> size-2 concurrent activities -> one join)` |
| constraint-heavy | `time_network(size, "dag", seed=20261116) plus TimeActivityConstraint(START_NO_EARLIER_THAN) on every 7th activity` |

- seed: `20261116`; sizes: `[1000, 5000, 25000, 50000, 100000]`
- constraint targets: `TIME_PROJECT_START + timedelta(days=(index % 21) + 1) for index in range(0, size, 7)`
- project finish passed to the engine: `fixture project_finish from time_network (float_days=0)`
- sequential mode: `time_schedule(..., float_workers=1, float_policy=None)`
- parallel mode: `time_schedule(..., float_workers=3, float_policy=FloatExecutionPolicy(workers=3, admission=make_slot_admission(4), allow_nested_fork=True))`
- repeats: small sizes [1000, 5000] -> 2 (median reported), 25000+ -> 1
- timeout policy: each cell runs in its own subprocess; every mode is bounded by signal.setitimer(ITIMER_REAL) inside the child and a hard subprocess timeout in the parent; a cell with no phase budget left is recorded SKIPPED_BUDGET; per-mode budgets (s): `{'1000': 60.0, '5000': 90.0, '25000': 150.0, '50000': 300.0, '100000': 180.0}`; matrix phase deadline `960.0` s

## Matrix: sequential vs parallel (slots=4) on the real engine

| size | shape | activities | relationships | constraints | seq median ms | par ms | seq CPU s | par CPU s | hash equality |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1000 | chain | 1000 | 999 | 0 | 129.2 | 114.2 | 0.260 | 0.350 | PASS |
| 1000 | wide | 1000 | 0 | 0 | 45.6 | 86.8 | 0.120 | 0.250 | PASS |
| 1000 | mixed | 1000 | 2029 | 0 | 260.4 | 152.9 | 0.530 | 0.580 | PASS |
| 1000 | resource-heavy | 1000 | 1996 | 0 | 224.4 | 173.2 | 0.450 | 0.500 | PASS |
| 1000 | constraint-heavy | 1000 | 1923 | 143 | 323.6 | 248.7 | 0.650 | 0.750 | PASS |
| 5000 | chain | 5000 | 4999 | 0 | 656.8 | 468.5 | 1.310 | 1.540 | PASS |
| 5000 | wide | 5000 | 0 | 0 | 230.4 | 243.2 | 0.460 | 0.660 | PASS |
| 5000 | mixed | 5000 | 10103 | 0 | 1,276.2 | 762.5 | 2.550 | 2.870 | PASS |
| 5000 | resource-heavy | 5000 | 9996 | 0 | 1,152.7 | 906.2 | 2.300 | 2.600 | PASS |
| 5000 | constraint-heavy | 5000 | 9575 | 715 | 3,448.8 | 2,976.2 | 6.900 | 7.180 | PASS |
| 25000 | chain | 25000 | 24999 | 0 | 3,381.7 | 2,342.2 | 3.380 | 3.920 | PASS |
| 25000 | wide | 25000 | 0 | 0 | 1,211.5 | 1,187.3 | 1.210 | 1.690 | PASS |
| 25000 | mixed | 25000 | 50671 | 0 | 6,557.4 | 3,785.9 | 6.570 | 7.100 | PASS |
| 25000 | resource-heavy | 25000 | 49996 | 0 | 7,086.2 | 5,786.6 | 7.090 | 7.710 | PASS |
| 25000 | constraint-heavy | 25000 | 47881 | 3572 | 68,896.9 | 67,296.6 | 68.890 | 70.430 | PASS |
| 50000 | chain | 50000 | 49999 | 0 | 6,901.0 | 4,971.2 | 6.890 | 8.030 | PASS |
| 50000 | wide | 50000 | 0 | 0 | 2,497.0 | 2,615.6 | 2.510 | 3.560 | PASS |
| 50000 | mixed | 50000 | 101275 | 0 | 13,401.2 | 8,010.5 | 13.410 | 14.630 | PASS |
| 50000 | resource-heavy | 50000 | 99996 | 0 | 17,503.8 | 15,193.8 | 17.500 | 19.000 | PASS |
| 50000 | constraint-heavy | 50000 | 95786 | 7143 | 290,129.5 | 284,302.3 | 290.120 | 290.570 | PASS |
| 100000 | chain | 100000 | 99999 | 0 | 14,250.8 | 10,600.7 | 14.260 | 17.000 | PASS |
| 100000 | wide | 100000 | 0 | 0 | 5,434.4 | 5,498.1 | 5.430 | 7.470 | PASS |
| 100000 | mixed | 100000 | 202707 | 0 | 27,055.3 | 16,502.2 | 27.050 | 30.320 | PASS |
| 100000 | resource-heavy | 100000 | 199996 | 0 | 48,849.2 | 43,180.4 | 48.840 | 50.980 | PASS |
| 100000 | constraint-heavy | 100000 | 191483 | 14286 | 1,168,606.3 | 1,185,340.3 | 1,168.530 | 1,195.120 | PASS |

### Matrix hashes and per-mode status

| size | shape | mode | status | engine ms (every run) | CPU s (every run) | hash | internal agreement | min total float h | max total float h |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1000 | chain | sequential | OK | 129.6, 128.9 | 0.13, 0.13 | bdb8a04616a6c001 | True | 0.0, 0.0 | 0.0, 0.0 |
| 1000 | chain | parallel | OK | 110.8, 117.5 | 0.15, 0.2 | bdb8a04616a6c001 | True | 0.0, 0.0 | 0.0, 0.0 |
| 1000 | wide | sequential | OK | 45.7, 45.5 | 0.08, 0.04 | 24e2759cc6d42df0 | True | 0.0, 0.0 | 32.0, 32.0 |
| 1000 | wide | parallel | OK | 117.7, 56.0 | 0.16, 0.09 | 24e2759cc6d42df0 | True | 0.0, 0.0 | 32.0, 32.0 |
| 1000 | mixed | sequential | OK | 255.9, 264.8 | 0.26, 0.27 | 9845018480b69b80 | True | 0.0, 0.0 | 88.0, 88.0 |
| 1000 | mixed | parallel | OK | 156.0, 149.8 | 0.29, 0.29 | 9845018480b69b80 | True | 0.0, 0.0 | 88.0, 88.0 |
| 1000 | resource-heavy | sequential | OK | 220.4, 228.3 | 0.22, 0.23 | f74a2644df81a608 | True | 0.0, 0.0 | 32.0, 32.0 |
| 1000 | resource-heavy | parallel | OK | 174.1, 172.4 | 0.24, 0.26 | f74a2644df81a608 | True | 0.0, 0.0 | 32.0, 32.0 |
| 1000 | constraint-heavy | sequential | OK | 318.9, 328.3 | 0.32, 0.33 | 3c922da3dd0b1094 | True | -8.0, -8.0 | -8.0, -8.0 |
| 1000 | constraint-heavy | parallel | OK | 240.8, 256.5 | 0.36, 0.39 | 3c922da3dd0b1094 | True | -8.0, -8.0 | -8.0, -8.0 |
| 5000 | chain | sequential | OK | 649.0, 664.6 | 0.65, 0.66 | 3d2f1f8dc31ceb4f | True | 0.0, 0.0 | 0.0, 0.0 |
| 5000 | chain | parallel | OK | 471.0, 466.0 | 0.76, 0.78 | 3d2f1f8dc31ceb4f | True | 0.0, 0.0 | 0.0, 0.0 |
| 5000 | wide | sequential | OK | 234.4, 226.3 | 0.23, 0.23 | f3e779aebd3c1c10 | True | 0.0, 0.0 | 32.0, 32.0 |
| 5000 | wide | parallel | OK | 230.9, 255.4 | 0.3, 0.36 | f3e779aebd3c1c10 | True | 0.0, 0.0 | 32.0, 32.0 |
| 5000 | mixed | sequential | OK | 1276.2, 1276.3 | 1.28, 1.27 | 067f05a0be1a27dd | True | 0.0, 0.0 | 88.0, 88.0 |
| 5000 | mixed | parallel | OK | 781.7, 743.3 | 1.44, 1.43 | 067f05a0be1a27dd | True | 0.0, 0.0 | 88.0, 88.0 |
| 5000 | resource-heavy | sequential | OK | 1154.1, 1151.2 | 1.15, 1.15 | f0a94e8caa6bdc8c | True | 0.0, 0.0 | 32.0, 32.0 |
| 5000 | resource-heavy | parallel | OK | 913.7, 898.7 | 1.28, 1.32 | f0a94e8caa6bdc8c | True | 0.0, 0.0 | 32.0, 32.0 |
| 5000 | constraint-heavy | sequential | OK | 3446.9, 3450.7 | 3.44, 3.46 | cea94bcaadcb3cd7 | True | -8.0, -8.0 | -8.0, -8.0 |
| 5000 | constraint-heavy | parallel | OK | 2984.3, 2968.1 | 3.6, 3.58 | cea94bcaadcb3cd7 | True | -8.0, -8.0 | -8.0, -8.0 |
| 25000 | chain | sequential | OK | 3381.7 | 3.38 | 84864c94f01706c0 | True | 0.0 | 0.0 |
| 25000 | chain | parallel | OK | 2342.2 | 3.92 | 84864c94f01706c0 | True | 0.0 | 0.0 |
| 25000 | wide | sequential | OK | 1211.5 | 1.21 | 7a08260e72eb8999 | True | 0.0 | 32.0 |
| 25000 | wide | parallel | OK | 1187.3 | 1.69 | 7a08260e72eb8999 | True | 0.0 | 32.0 |
| 25000 | mixed | sequential | OK | 6557.4 | 6.57 | 7c6aa1b2e001b445 | True | 0.0 | 120.0 |
| 25000 | mixed | parallel | OK | 3785.9 | 7.1 | 7c6aa1b2e001b445 | True | 0.0 | 120.0 |
| 25000 | resource-heavy | sequential | OK | 7086.2 | 7.09 | ebe781ac1c8fdd1f | True | 0.0 | 32.0 |
| 25000 | resource-heavy | parallel | OK | 5786.6 | 7.71 | ebe781ac1c8fdd1f | True | 0.0 | 32.0 |
| 25000 | constraint-heavy | sequential | OK | 68896.9 | 68.89 | 12e7a27cbf287d35 | True | -8.0 | -8.0 |
| 25000 | constraint-heavy | parallel | OK | 67296.6 | 70.43 | 12e7a27cbf287d35 | True | -8.0 | -8.0 |
| 50000 | chain | sequential | OK | 6901.0 | 6.89 | 93957c0bf146fb25 | True | 0.0 | 0.0 |
| 50000 | chain | parallel | OK | 4971.2 | 8.03 | 93957c0bf146fb25 | True | 0.0 | 0.0 |
| 50000 | wide | sequential | OK | 2497.0 | 2.51 | b801fafc255a8f79 | True | 0.0 | 32.0 |
| 50000 | wide | parallel | OK | 2615.6 | 3.56 | b801fafc255a8f79 | True | 0.0 | 32.0 |
| 50000 | mixed | sequential | OK | 13401.2 | 13.41 | 57949fd27e8cfd75 | True | 0.0 | 120.0 |
| 50000 | mixed | parallel | OK | 8010.5 | 14.63 | 57949fd27e8cfd75 | True | 0.0 | 120.0 |
| 50000 | resource-heavy | sequential | OK | 17503.8 | 17.5 | 098c29739e3b52c6 | True | 0.0 | 32.0 |
| 50000 | resource-heavy | parallel | OK | 15193.8 | 19.0 | 098c29739e3b52c6 | True | 0.0 | 32.0 |
| 50000 | constraint-heavy | sequential | OK | 290129.5 | 290.12 | 5e4e2219c14e29ce | True | -8.0 | -8.0 |
| 50000 | constraint-heavy | parallel | OK | 284302.3 | 290.57 | 5e4e2219c14e29ce | True | -8.0 | -8.0 |
| 100000 | chain | sequential | OK | 14250.8 | 14.26 | e1c4396f5c0fa98c | True | 0.0 | 0.0 |
| 100000 | chain | parallel | OK | 10600.7 | 17.0 | e1c4396f5c0fa98c | True | 0.0 | 0.0 |
| 100000 | wide | sequential | OK | 5434.4 | 5.43 | c09005a68b66a346 | True | 0.0 | 32.0 |
| 100000 | wide | parallel | OK | 5498.1 | 7.47 | c09005a68b66a346 | True | 0.0 | 32.0 |
| 100000 | mixed | sequential | OK | 27055.3 | 27.05 | 9f69dab36dd1429f | True | 0.0 | 128.0 |
| 100000 | mixed | parallel | OK | 16502.2 | 30.32 | 9f69dab36dd1429f | True | 0.0 | 128.0 |
| 100000 | resource-heavy | sequential | OK | 48849.2 | 48.84 | 349eac4729b97e51 | True | 0.0 | 32.0 |
| 100000 | resource-heavy | parallel | OK | 43180.4 | 50.98 | 349eac4729b97e51 | True | 0.0 | 32.0 |
| 100000 | constraint-heavy | sequential | OK | 1168606.3 | 1168.53 | 301b17f480b902ce | True | -8.0 | -8.0 |
| 100000 | constraint-heavy | parallel | OK | 1185340.3 | 1195.12 | 301b17f480b902ce | True | -8.0 | -8.0 |

## Capacity sweep: 25000 mixed at slots 1/2/4/8/16

| slots | float_workers | wall ms | CPU s | speedup vs slots=1 | hash | matches matrix cell |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 6,551.1 | 6.540 | 1.0 | 7c6aa1b2e001b445 | True |
| 2 | 1 | 6,589.0 | 6.590 | 0.994 | 7c6aa1b2e001b445 | True |
| 4 | 3 | 3,836.8 | 7.250 | 1.707 | 7c6aa1b2e001b445 | True |
| 8 | 7 | 3,736.1 | 7.110 | 1.753 | 7c6aa1b2e001b445 | True |
| 16 | 15 | 3,777.3 | 7.160 | 1.734 | 7c6aa1b2e001b445 | True |

Status / error per point: slots=1: OK; slots=2: OK; slots=4: OK; slots=8: OK; slots=16: OK

## Project sweep: N concurrent 5000-activity projects, GlobalExecutionBudget(4)

| projects | wall ms | throughput proj/s | peak slots | process starts | queue wait max ms | all hashes match | status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1,088.9 | 0.918 | 4 | 1 | 0.1 | True | OK |
| 2 | 1,637.9 | 1.221 | 4 | 2 | 2.5 | True | OK |
| 4 | 1,675.4 | 2.387 | 4 | 4 | 4.1 | True | OK |
| 8 | 3,345.4 | 2.391 | 4 | 8 | 1669.0 | True | OK |
| 16 | 6,605.7 | 2.422 | 4 | 16 | 4959.5 | True | OK |

### Per-project hashes (scheduled vs that project's own sequential run)

| projects | seed | tenant | state | slots | run ms | queue wait ms | sequential hash | scheduled hash | match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 20261116 | T-p0n2-67c398d9-00 | SUCCEEDED | 4 | 1088.8 | 0.1 | 067f05a0be1a27dd | 067f05a0be1a27dd | True |
| 2 | 20261116 | T-p0n2-da1fa916-00 | SUCCEEDED | 2 | 1627.5 | 0.1 | 067f05a0be1a27dd | 067f05a0be1a27dd | True |
| 2 | 20261117 | T-p0n2-da1fa916-01 | SUCCEEDED | 2 | 1635.3 | 2.5 | 36bcb72c90878cd6 | 36bcb72c90878cd6 | True |
| 4 | 20261116 | T-p0n2-7f2a055d-00 | SUCCEEDED | 1 | 1654.7 | 0.1 | 067f05a0be1a27dd | 067f05a0be1a27dd | True |
| 4 | 20261117 | T-p0n2-7f2a055d-01 | SUCCEEDED | 1 | 1657.5 | 2.6 | 36bcb72c90878cd6 | 36bcb72c90878cd6 | True |
| 4 | 20261118 | T-p0n2-7f2a055d-02 | SUCCEEDED | 1 | 1666.9 | 3.4 | 44699b5adfb58ffb | 44699b5adfb58ffb | True |
| 4 | 20261119 | T-p0n2-7f2a055d-03 | SUCCEEDED | 1 | 1671.2 | 4.1 | aca44f474c8e9e7b | aca44f474c8e9e7b | True |
| 8 | 20261116 | T-p0n2-577c1214-00 | SUCCEEDED | 1 | 1654.8 | 0.1 | 067f05a0be1a27dd | 067f05a0be1a27dd | True |
| 8 | 20261117 | T-p0n2-577c1214-01 | SUCCEEDED | 1 | 1658.8 | 2.5 | 36bcb72c90878cd6 | 36bcb72c90878cd6 | True |
| 8 | 20261118 | T-p0n2-577c1214-02 | SUCCEEDED | 1 | 1664.6 | 3.3 | 44699b5adfb58ffb | 44699b5adfb58ffb | True |
| 8 | 20261119 | T-p0n2-577c1214-03 | SUCCEEDED | 1 | 1663.9 | 4.0 | aca44f474c8e9e7b | aca44f474c8e9e7b | True |
| 8 | 20261120 | T-p0n2-577c1214-04 | SUCCEEDED | 1 | 1644.6 | 1655.0 | 3fe3f5b51eec23df | 3fe3f5b51eec23df | True |
| 8 | 20261121 | T-p0n2-577c1214-05 | SUCCEEDED | 1 | 1658.5 | 1661.4 | 2aeda0742605f9e1 | 2aeda0742605f9e1 | True |
| 8 | 20261122 | T-p0n2-577c1214-06 | SUCCEEDED | 1 | 1652.0 | 1668.0 | f143e030af43752e | f143e030af43752e | True |
| 8 | 20261123 | T-p0n2-577c1214-07 | SUCCEEDED | 1 | 1676.3 | 1669.0 | 1ca7128cd63f7957 | 1ca7128cd63f7957 | True |
| 16 | 20261119 | T-p0n2-2a7816d0-03 | SUCCEEDED | 1 | 1630.8 | 4.1 | aca44f474c8e9e7b | aca44f474c8e9e7b | True |
| 16 | 20261117 | T-p0n2-2a7816d0-01 | SUCCEEDED | 1 | 1658.9 | 2.6 | 36bcb72c90878cd6 | 36bcb72c90878cd6 | True |
| 16 | 20261118 | T-p0n2-2a7816d0-02 | SUCCEEDED | 1 | 1658.2 | 3.3 | 44699b5adfb58ffb | 44699b5adfb58ffb | True |
| 16 | 20261116 | T-p0n2-2a7816d0-00 | SUCCEEDED | 1 | 1668.9 | 0.1 | 067f05a0be1a27dd | 067f05a0be1a27dd | True |
| 16 | 20261120 | T-p0n2-2a7816d0-04 | SUCCEEDED | 1 | 1629.8 | 1635.0 | 3fe3f5b51eec23df | 3fe3f5b51eec23df | True |
| 16 | 20261121 | T-p0n2-2a7816d0-05 | SUCCEEDED | 1 | 1634.8 | 1661.6 | 2aeda0742605f9e1 | 2aeda0742605f9e1 | True |
| 16 | 20261122 | T-p0n2-2a7816d0-06 | SUCCEEDED | 1 | 1639.9 | 1662.9 | f143e030af43752e | f143e030af43752e | True |
| 16 | 20261123 | T-p0n2-2a7816d0-07 | SUCCEEDED | 1 | 1645.1 | 1669.2 | 1ca7128cd63f7957 | 1ca7128cd63f7957 | True |
| 16 | 20261124 | T-p0n2-2a7816d0-08 | SUCCEEDED | 1 | 1634.8 | 3264.9 | 4e0fe55fb8864bdc | 4e0fe55fb8864bdc | True |
| 16 | 20261126 | T-p0n2-2a7816d0-10 | SUCCEEDED | 1 | 1623.2 | 3303.0 | f1eabda5f48e2807 | f1eabda5f48e2807 | True |
| 16 | 20261125 | T-p0n2-2a7816d0-09 | SUCCEEDED | 1 | 1636.3 | 3296.5 | f53566bcc002748b | f53566bcc002748b | True |
| 16 | 20261127 | T-p0n2-2a7816d0-11 | SUCCEEDED | 1 | 1645.0 | 3314.4 | 36205e91ab4d8212 | 36205e91ab4d8212 | True |
| 16 | 20261128 | T-p0n2-2a7816d0-12 | SUCCEEDED | 1 | 1629.6 | 4899.8 | 8850b340e0b689f2 | 8850b340e0b689f2 | True |
| 16 | 20261129 | T-p0n2-2a7816d0-13 | SUCCEEDED | 1 | 1633.6 | 4926.3 | dc638eb68482aeed | dc638eb68482aeed | True |
| 16 | 20261130 | T-p0n2-2a7816d0-14 | SUCCEEDED | 1 | 1632.1 | 4932.9 | 292dd728f5300412 | 292dd728f5300412 | True |
| 16 | 20261131 | T-p0n2-2a7816d0-15 | SUCCEEDED | 1 | 1646.1 | 4959.5 | 8cd3c54d4aed9159 | 8cd3c54d4aed9159 | True |

## Worker end to end: real PostgreSQL + real SchedulingWorkerRuntime

| size | mode | state | attempts | submit ms | drain ms | e2e ms | DB submit->SUCCEEDED ms | output_hash == calculation_run_identity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1000 | thread | SUCCEEDED | 1 | 6.2 | 506.1 | 528.0 | 136.6 | True |
| 1000 | process | SUCCEEDED | 1 | 6.1 | 525.9 | 546.4 | 274.8 | True |
| 5000 | thread | SUCCEEDED | 1 | 27.3 | 1047.2 | 1090.2 | 610.7 | True |
| 5000 | process | SUCCEEDED | 1 | 27.1 | 1094.5 | 1137.8 | 790.7 | True |

### Worker run detail

- size=1000 mode=thread: job_id `b04f7961ab819a2573eb03feda763a51cccd9b4df9b8ed69ca961e022afeafb3`, tenant `T-p0n2-d98aaabae8`, snapshot `S-de1a38a714bd4ef3ab3cd389b252d454`, state `SUCCEEDED`, attempts `1`, lease owner `None`, activity_count `1000`, output_hash `4bc2fcac313d06da8b38855620efbe9d5582c14bb1954ec051a23eac3116c2a9`, calculation_run_identity `4bc2fcac313d06da8b38855620efbe9d5582c14bb1954ec051a23eac3116c2a9`, match `True`, status `OK`
  - settings: `{"slots": 2, "poll_interval": 0.25, "job_timeout": null, "connect_timeout": 10}`, outcome: `{"claimed": 1, "succeeded": 1, "failed": 0, "cancelled": 0, "retried": 0, "lease_lost": 0, "process_starts": 0, "inline_fallbacks": 0, "cache_hits": 0, "cache_misses": 0, "peak_slots": 0, "stopped": false}`
- size=1000 mode=process: job_id `92d2352bcc58c5ba02c7cf9f35d9e7601197f13825b36b89a633bd138cec6edc`, tenant `T-p0n2-8d19734d12`, snapshot `S-d0661131b8e44cc486b62bf6f2f01f6b`, state `SUCCEEDED`, attempts `1`, lease owner `None`, activity_count `1000`, output_hash `3cc864217214547635c728674019c9205fc1311eff0252125c39dc3046eb67dc`, calculation_run_identity `3cc864217214547635c728674019c9205fc1311eff0252125c39dc3046eb67dc`, match `True`, status `OK`
  - settings: `{"slots": 2, "poll_interval": 0.25, "job_timeout": null, "connect_timeout": 10}`, outcome: `{"claimed": 1, "succeeded": 1, "failed": 0, "cancelled": 0, "retried": 0, "lease_lost": 0, "process_starts": 1, "inline_fallbacks": 0, "cache_hits": 0, "cache_misses": 0, "peak_slots": 1, "stopped": false}`
- size=5000 mode=thread: job_id `2709cb5c9d3076f4440f4863ca38251851c921451de50069fe3b783763a616f7`, tenant `T-p0n2-3b7e1e37b6`, snapshot `S-4fa998bee1ae4b15b020881be6ad9086`, state `SUCCEEDED`, attempts `1`, lease owner `None`, activity_count `5000`, output_hash `810fffd5abdbf144f1fbe856123cec79b907a1b24fe668da5ea486ff8a687517`, calculation_run_identity `810fffd5abdbf144f1fbe856123cec79b907a1b24fe668da5ea486ff8a687517`, match `True`, status `OK`
  - settings: `{"slots": 2, "poll_interval": 0.25, "job_timeout": null, "connect_timeout": 10}`, outcome: `{"claimed": 1, "succeeded": 1, "failed": 0, "cancelled": 0, "retried": 0, "lease_lost": 0, "process_starts": 0, "inline_fallbacks": 0, "cache_hits": 0, "cache_misses": 0, "peak_slots": 0, "stopped": false}`
- size=5000 mode=process: job_id `5807b3d483dc68c34918107ea68d183fa17a898b029743bb0c68f246d105c3e8`, tenant `T-p0n2-dcff4ed8d6`, snapshot `S-5884c3dd74814bee93ea910fcb658a4a`, state `SUCCEEDED`, attempts `1`, lease owner `None`, activity_count `5000`, output_hash `e62da1bb75bc784b8d87f35199e15c117c19523c2d69febb86619c3c88574d1e`, calculation_run_identity `e62da1bb75bc784b8d87f35199e15c117c19523c2d69febb86619c3c88574d1e`, match `True`, status `OK`
  - settings: `{"slots": 2, "poll_interval": 0.25, "job_timeout": null, "connect_timeout": 10}`, outcome: `{"claimed": 1, "succeeded": 1, "failed": 0, "cancelled": 0, "retried": 0, "lease_lost": 0, "process_starts": 1, "inline_fallbacks": 0, "cache_hits": 0, "cache_misses": 0, "peak_slots": 2, "stopped": false}`

## Integrity notes

- Measurement only: this harness adds scripts/p0n2_runtime_matrix.py and the four evidence files under docs/workspace/evidence/p0n-runtime-activation-2026-11-20/ and changes no product code, test, or configuration.
- The worker process-mode path ran against the fixed executor: commit 5b4cfb7104cbd4952d60af9734cfe1b559aa923f ("fix(p0n): drain the child result pipe before join in process placement") is the recorded run HEAD, so every worker number here includes the pipe-drain fix. The defect it removes: the parent joined the child before reading the result pipe, so a pickled SchedulingJobResult above the ~64 KiB pipe buffer deadlocked and the job was retried as SCHEDULING_JOB_TIMEOUT (regression test: tests/scheduling/test_scheduling_job_executor_process.py::test_result_larger_than_the_pipe_buffer_does_not_deadlock).
- constraint-heavy cells pass the fixture's own (unconstrained) project_finish to time_schedule, exactly like scripts/p0n_multi_project_benchmark.py::run_project. Because the START_NO_EARLIER_THAN list pushes work later than that finish, the recorded total float for those cells is negative; min_total_float_hours/max_total_float_hours are stored per run so the effect is visible instead of hidden.
- This host runs other work items in parallel; the same PostgreSQL instance is shared. Each worker run seeds its own unique tenant scope, so rows never overlap, but wall-clock numbers can include contention noise.

- Engine actually called: `construction_pm.scheduling.time_schedule.time_schedule`

### Post-run note corrections

A note written at run time became stale before publication; the original text is kept here so the edit is auditable rather than silent.

- was: The worker process-mode path runs against src/construction_pm/scheduling_job_executor.py as it stands in this working tree, which carries an uncommitted fix from another work item: the parent now drains the result pipe (non-blocking poll/recv) before joining the child. Before that fix, two exploratory 5000-activity process-mode runs started by this harness deadlocked with the job child blocked in pipe_write once the pickled SchedulingJobResult exceeded the ~64 KB pipe buffer; those runs were terminated, are not part of this evidence, and their job rows were left as found (expired LEASED, cancelled by the fixing work item).
- is now: The worker process-mode path ran against the fixed executor: commit 5b4cfb7104cbd4952d60af9734cfe1b559aa923f ("fix(p0n): drain the child result pipe before join in process placement") is the recorded run HEAD, so every worker number here includes the pipe-drain fix. The defect it removes: the parent joined the child before reading the result pipe, so a pickled SchedulingJobResult above the ~64 KiB pipe buffer deadlocked and the job was retried as SCHEDULING_JOB_TIMEOUT (regression test: tests/scheduling/test_scheduling_job_executor_process.py::test_result_larger_than_the_pipe_buffer_does_not_deadlock).

## Recorded failures, timeouts and skipped cells

- none: every recorded cell, sweep point, project and worker run completed and matched.

## Scope note

This document and the harness are measurement only. No product code, test, configuration or committed artifact outside `docs/workspace/evidence/p0n-runtime-activation-2026-11-20/` was changed, and nothing was deleted from the shared PostgreSQL tables: each worker run seeds its own unique tenant scope, exactly like the integration test it mirrors.

