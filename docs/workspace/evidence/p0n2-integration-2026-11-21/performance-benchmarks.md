# P0-N.2 performance and capacity evidence

Generated from the raw JSON of a single instrumented run: `matrix-20261121T035740Z.json` and `worker-e2e-20261121T035740Z.json`. Every number in every table below is read back from those files; nothing is estimated, extrapolated or copied from an earlier run. Cells that did not complete are listed with their exact recorded error text.

## Environment

| Item | Value |
| --- | --- |
| python | 3.12.13 |
| platform | Linux-5.10.134-013.10.1.kangaroo.al8.x86_64-x86_64-with-glibc2.35 |
| machine | x86_64 |
| cpu_count | 4 |
| cpu_affinity_count | 4 |
| memory_total_kb | 8131540 |
| git_sha | 89ced6a74e660158dc4a3a1622573fa702a5577a |
| branch | feat/p0n2-integration |
| commit | 89ced6a74e660158dc4a3a1622573fa702a5577a |
| PostgreSQL | PostgreSQL 14.24 (Ubuntu 14.24-0ubuntu0.22.04.1) on x86_64-pc-linux-gnu, compiled by gcc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0, 64-bit |
| started | 2026-11-21T03:57:40.592000+00:00 |
| finished | 2026-11-21T04:56:22.070308+00:00 |
| matrix phase wall clock | 3521.4 s |

Working tree at run time (`git status --porcelain`, pre-existing edits made by other work in this session, **not** by this harness — the harness only writes the evidence files listed in Scope):

```
M scripts/p0n2_runtime_matrix.py
?? docs/workspace/evidence/p0n2-integration-2026-11-21/
```

## Exact commands

```
scripts/p0n2_runtime_matrix.py run --out-dir docs/workspace/evidence/p0n2-integration-2026-11-21/results --dsn postgresql://postgres@127.0.0.1:55432/postgres --phase-deadline 4200 --capacity-slots 1,2,4,8,16,32 --mode-budget 100000=1800
```

The orchestrator spawns one subprocess per unit; the recorded command lines (in `runs[].command` of the raw matrix JSON, in `runs[].unit_run.command` of the worker JSON, and prefixed with `$ ` in the `.log`) are:

```
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 1000 --shape chain --deadline 1795233670.675 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-00-1000-chain.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 1000 --shape wide --deadline 1795233671.525 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-01-1000-wide.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 1000 --shape mixed --deadline 1795233672.042 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-02-1000-mixed.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 1000 --shape resource-heavy --deadline 1795233673.205 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-03-1000-resource-heavy.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 1000 --shape constraint-heavy --deadline 1795233674.384 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-04-1000-constraint-heavy.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 5000 --shape chain --deadline 1795233735.837 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-05-5000-chain.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 5000 --shape wide --deadline 1795233738.765 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-06-5000-wide.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 5000 --shape mixed --deadline 1795233740.369 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-07-5000-mixed.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 5000 --shape resource-heavy --deadline 1795233745.239 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-08-5000-resource-heavy.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 5000 --shape constraint-heavy --deadline 1795233750.115 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-09-5000-constraint-heavy.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 25000 --shape chain --deadline 1795233883.634 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-10-25000-chain.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 25000 --shape wide --deadline 1795233891.138 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-11-25000-wide.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 25000 --shape mixed --deadline 1795233895.084 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-12-25000-mixed.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 25000 --shape resource-heavy --deadline 1795233908.017 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-13-25000-resource-heavy.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 25000 --shape constraint-heavy --deadline 1795233922.919 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-14-25000-constraint-heavy.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 50000 --shape chain --deadline 1795234361.680 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-15-50000-chain.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 50000 --shape wide --deadline 1795234377.327 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-16-50000-wide.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 50000 --shape mixed --deadline 1795234385.308 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-17-50000-mixed.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 50000 --shape resource-heavy --deadline 1795234412.002 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-18-50000-resource-heavy.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 50000 --shape constraint-heavy --deadline 1795234448.732 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-19-50000-constraint-heavy.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 100000 --shape chain --deadline 1795238027.075 --mode-budget 1800.0 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-20-100000-chain.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 100000 --shape wide --deadline 1795238058.432 --mode-budget 1800.0 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-21-100000-wide.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 100000 --shape mixed --deadline 1795238075.047 --mode-budget 1800.0 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-22-100000-mixed.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 100000 --shape resource-heavy --deadline 1795237680.675 --mode-budget 1800.0 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-23-100000-resource-heavy.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _cell --size 100000 --shape constraint-heavy --deadline 1795237680.675 --mode-budget 1800.0 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/cell-24-100000-constraint-heavy.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _capacity --slots 1 --deadline 1795237475.433 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/capacity-1.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _capacity --slots 2 --deadline 1795237483.927 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/capacity-2.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _capacity --slots 4 --deadline 1795237492.449 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/capacity-4.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _capacity --slots 8 --deadline 1795237498.267 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/capacity-8.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _capacity --slots 16 --deadline 1795237504.126 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/capacity-16.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _capacity --slots 32 --deadline 1795237509.957 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/capacity-32.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _projects --count 1 --deadline 1795237515.810 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/projects-1.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _projects --count 2 --deadline 1795237518.773 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/projects-2.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _projects --count 4 --deadline 1795237523.906 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/projects-4.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _projects --count 8 --deadline 1795237532.328 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/projects-8.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _projects --count 16 --deadline 1795237548.948 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/projects-16.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _worker --dsn postgresql://postgres@127.0.0.1:55432/postgres --size 1000 --mode thread --deadline 1795237402.082 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/worker-1000-thread.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _worker --dsn postgresql://postgres@127.0.0.1:55432/postgres --size 1000 --mode process --deadline 1795237403.117 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/worker-1000-process.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _worker --dsn postgresql://postgres@127.0.0.1:55432/postgres --size 5000 --mode thread --deadline 1795237404.176 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/worker-5000-thread.json
/usr/bin/python3 /data/work/repo/scripts/p0n2_runtime_matrix.py _worker --dsn postgresql://postgres@127.0.0.1:55432/postgres --size 5000 --mode process --deadline 1795237405.947 --result-file /data/work/repo/docs/workspace/evidence/p0n2-integration-2026-11-21/results/.unit-20261121T035740Z/worker-5000-process.json
```

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
- timeout policy: each cell runs in its own subprocess; every mode is bounded by signal.setitimer(ITIMER_REAL) inside the child and a hard subprocess timeout in the parent; a cell with no phase budget left is recorded SKIPPED_BUDGET; per-mode budgets (s): `{'1000': 60.0, '5000': 90.0, '25000': 150.0, '50000': 300.0, '100000': 1800.0}`; matrix phase deadline `4200.0` s

## Matrix: sequential vs parallel (slots=4) on the real engine

| size | shape | activities | relationships | constraints | seq median ms | par ms | seq CPU s | par CPU s | hash equality |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1000 | chain | 1000 | 999 | 0 | 129.6 | 134.8 | 0.260 | 0.420 | PASS |
| 1000 | wide | 1000 | 0 | 0 | 45.5 | 62.5 | 0.140 | 0.160 | PASS |
| 1000 | mixed | 1000 | 2029 | 0 | 260.4 | 154.4 | 0.530 | 0.590 | PASS |
| 1000 | resource-heavy | 1000 | 1996 | 0 | 226.1 | 201.4 | 0.460 | 0.580 | PASS |
| 1000 | constraint-heavy | 1000 | 1923 | 143 | 324.1 | 239.9 | 0.650 | 0.740 | PASS |
| 5000 | chain | 5000 | 4999 | 0 | 658.0 | 464.0 | 1.310 | 1.530 | PASS |
| 5000 | wide | 5000 | 0 | 0 | 232.8 | 254.3 | 0.470 | 0.690 | PASS |
| 5000 | mixed | 5000 | 10103 | 0 | 1,286.3 | 742.4 | 2.560 | 2.820 | PASS |
| 5000 | resource-heavy | 5000 | 9996 | 0 | 1,162.8 | 905.0 | 2.330 | 2.570 | PASS |
| 5000 | constraint-heavy | 5000 | 9575 | 715 | 3,437.9 | 2,949.9 | 6.870 | 7.120 | PASS |
| 25000 | chain | 25000 | 24999 | 0 | 3,390.9 | 2,365.3 | 3.390 | 3.950 | PASS |
| 25000 | wide | 25000 | 0 | 0 | 1,204.3 | 1,239.4 | 1.220 | 1.740 | PASS |
| 25000 | mixed | 25000 | 50671 | 0 | 6,576.5 | 3,906.8 | 6.570 | 7.400 | PASS |
| 25000 | resource-heavy | 25000 | 49996 | 0 | 7,123.2 | 5,755.3 | 7.130 | 7.680 | PASS |
| 25000 | constraint-heavy | 25000 | 47881 | 3572 | 69,367.8 | 67,287.7 | 69.370 | 70.480 | PASS |
| 50000 | chain | 50000 | 49999 | 0 | 6,917.5 | 5,332.2 | 6.910 | 8.580 | PASS |
| 50000 | wide | 50000 | 0 | 0 | 2,519.6 | 2,738.1 | 2.510 | 3.690 | PASS |
| 50000 | mixed | 50000 | 101275 | 0 | 13,502.1 | 8,518.2 | 13.510 | 15.380 | PASS |
| 50000 | resource-heavy | 50000 | 99996 | 0 | 17,711.0 | 15,162.3 | 17.710 | 18.950 | PASS |
| 50000 | constraint-heavy | 50000 | 95786 | 7143 | 289,739.9 | 284,398.3 | 289.730 | 290.760 | PASS |
| 100000 | chain | 100000 | 99999 | 0 | 14,151.0 | 10,534.2 | 14.150 | 16.970 | PASS |
| 100000 | wide | 100000 | 0 | 0 | 5,416.4 | 5,606.9 | 5.410 | 7.610 | PASS |
| 100000 | mixed | 100000 | 202707 | 0 | 27,426.3 | 16,565.0 | 27.420 | 30.240 | PASS |
| 100000 | resource-heavy | 100000 | 199996 | 0 | 48,916.5 | 43,623.0 | 48.920 | 51.250 | PASS |
| 100000 | constraint-heavy | 100000 | 191483 | 14286 | 1,163,644.8 | 1,164,731.2 | 1,163.550 | 1,177.240 | PASS |

### Matrix hashes and per-mode status

| size | shape | mode | status | engine ms (every run) | CPU s (every run) | hash | internal agreement | min total float h | max total float h |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1000 | chain | sequential | OK | 129.8, 129.3 | 0.13, 0.13 | bdb8a04616a6c001 | True | 0.0, 0.0 | 0.0, 0.0 |
| 1000 | chain | parallel | OK | 171.5, 98.2 | 0.26, 0.16 | bdb8a04616a6c001 | True | 0.0, 0.0 | 0.0, 0.0 |
| 1000 | wide | sequential | OK | 45.6, 45.5 | 0.09, 0.05 | 24e2759cc6d42df0 | True | 0.0, 0.0 | 32.0, 32.0 |
| 1000 | wide | parallel | OK | 73.8, 51.2 | 0.08, 0.08 | 24e2759cc6d42df0 | True | 0.0, 0.0 | 32.0, 32.0 |
| 1000 | mixed | sequential | OK | 255.9, 265.0 | 0.26, 0.27 | 9845018480b69b80 | True | 0.0, 0.0 | 88.0, 88.0 |
| 1000 | mixed | parallel | OK | 153.4, 155.3 | 0.29, 0.3 | 9845018480b69b80 | True | 0.0, 0.0 | 88.0, 88.0 |
| 1000 | resource-heavy | sequential | OK | 221.0, 231.2 | 0.22, 0.24 | f74a2644df81a608 | True | 0.0, 0.0 | 32.0, 32.0 |
| 1000 | resource-heavy | parallel | OK | 204.3, 198.5 | 0.29, 0.29 | f74a2644df81a608 | True | 0.0, 0.0 | 32.0, 32.0 |
| 1000 | constraint-heavy | sequential | OK | 319.2, 329.1 | 0.32, 0.33 | 3c922da3dd0b1094 | True | -8.0, -8.0 | -8.0, -8.0 |
| 1000 | constraint-heavy | parallel | OK | 250.0, 229.9 | 0.38, 0.36 | 3c922da3dd0b1094 | True | -8.0, -8.0 | -8.0, -8.0 |
| 5000 | chain | sequential | OK | 654.3, 661.7 | 0.65, 0.66 | 3d2f1f8dc31ceb4f | True | 0.0, 0.0 | 0.0, 0.0 |
| 5000 | chain | parallel | OK | 477.3, 450.6 | 0.77, 0.76 | 3d2f1f8dc31ceb4f | True | 0.0, 0.0 | 0.0, 0.0 |
| 5000 | wide | sequential | OK | 236.7, 228.9 | 0.24, 0.23 | f3e779aebd3c1c10 | True | 0.0, 0.0 | 32.0, 32.0 |
| 5000 | wide | parallel | OK | 247.3, 261.4 | 0.33, 0.36 | f3e779aebd3c1c10 | True | 0.0, 0.0 | 32.0, 32.0 |
| 5000 | mixed | sequential | OK | 1288.1, 1284.6 | 1.28, 1.28 | 067f05a0be1a27dd | True | 0.0, 0.0 | 88.0, 88.0 |
| 5000 | mixed | parallel | OK | 738.6, 746.2 | 1.39, 1.43 | 067f05a0be1a27dd | True | 0.0, 0.0 | 88.0, 88.0 |
| 5000 | resource-heavy | sequential | OK | 1164.8, 1160.7 | 1.17, 1.16 | f0a94e8caa6bdc8c | True | 0.0, 0.0 | 32.0, 32.0 |
| 5000 | resource-heavy | parallel | OK | 903.6, 906.3 | 1.27, 1.3 | f0a94e8caa6bdc8c | True | 0.0, 0.0 | 32.0, 32.0 |
| 5000 | constraint-heavy | sequential | OK | 3435.6, 3440.3 | 3.43, 3.44 | cea94bcaadcb3cd7 | True | -8.0, -8.0 | -8.0, -8.0 |
| 5000 | constraint-heavy | parallel | OK | 2978.0, 2921.9 | 3.59, 3.53 | cea94bcaadcb3cd7 | True | -8.0, -8.0 | -8.0, -8.0 |
| 25000 | chain | sequential | OK | 3390.9 | 3.39 | 84864c94f01706c0 | True | 0.0 | 0.0 |
| 25000 | chain | parallel | OK | 2365.3 | 3.95 | 84864c94f01706c0 | True | 0.0 | 0.0 |
| 25000 | wide | sequential | OK | 1204.3 | 1.22 | 7a08260e72eb8999 | True | 0.0 | 32.0 |
| 25000 | wide | parallel | OK | 1239.4 | 1.74 | 7a08260e72eb8999 | True | 0.0 | 32.0 |
| 25000 | mixed | sequential | OK | 6576.5 | 6.57 | 7c6aa1b2e001b445 | True | 0.0 | 120.0 |
| 25000 | mixed | parallel | OK | 3906.8 | 7.4 | 7c6aa1b2e001b445 | True | 0.0 | 120.0 |
| 25000 | resource-heavy | sequential | OK | 7123.2 | 7.13 | ebe781ac1c8fdd1f | True | 0.0 | 32.0 |
| 25000 | resource-heavy | parallel | OK | 5755.3 | 7.68 | ebe781ac1c8fdd1f | True | 0.0 | 32.0 |
| 25000 | constraint-heavy | sequential | OK | 69367.8 | 69.37 | 12e7a27cbf287d35 | True | -8.0 | -8.0 |
| 25000 | constraint-heavy | parallel | OK | 67287.7 | 70.48 | 12e7a27cbf287d35 | True | -8.0 | -8.0 |
| 50000 | chain | sequential | OK | 6917.5 | 6.91 | 93957c0bf146fb25 | True | 0.0 | 0.0 |
| 50000 | chain | parallel | OK | 5332.2 | 8.58 | 93957c0bf146fb25 | True | 0.0 | 0.0 |
| 50000 | wide | sequential | OK | 2519.6 | 2.51 | b801fafc255a8f79 | True | 0.0 | 32.0 |
| 50000 | wide | parallel | OK | 2738.1 | 3.69 | b801fafc255a8f79 | True | 0.0 | 32.0 |
| 50000 | mixed | sequential | OK | 13502.1 | 13.51 | 57949fd27e8cfd75 | True | 0.0 | 120.0 |
| 50000 | mixed | parallel | OK | 8518.2 | 15.38 | 57949fd27e8cfd75 | True | 0.0 | 120.0 |
| 50000 | resource-heavy | sequential | OK | 17711.0 | 17.71 | 098c29739e3b52c6 | True | 0.0 | 32.0 |
| 50000 | resource-heavy | parallel | OK | 15162.3 | 18.95 | 098c29739e3b52c6 | True | 0.0 | 32.0 |
| 50000 | constraint-heavy | sequential | OK | 289739.9 | 289.73 | 5e4e2219c14e29ce | True | -8.0 | -8.0 |
| 50000 | constraint-heavy | parallel | OK | 284398.3 | 290.76 | 5e4e2219c14e29ce | True | -8.0 | -8.0 |
| 100000 | chain | sequential | OK | 14151.0 | 14.15 | e1c4396f5c0fa98c | True | 0.0 | 0.0 |
| 100000 | chain | parallel | OK | 10534.2 | 16.97 | e1c4396f5c0fa98c | True | 0.0 | 0.0 |
| 100000 | wide | sequential | OK | 5416.4 | 5.41 | c09005a68b66a346 | True | 0.0 | 32.0 |
| 100000 | wide | parallel | OK | 5606.9 | 7.61 | c09005a68b66a346 | True | 0.0 | 32.0 |
| 100000 | mixed | sequential | OK | 27426.3 | 27.42 | 9f69dab36dd1429f | True | 0.0 | 128.0 |
| 100000 | mixed | parallel | OK | 16565.0 | 30.24 | 9f69dab36dd1429f | True | 0.0 | 128.0 |
| 100000 | resource-heavy | sequential | OK | 48916.5 | 48.92 | 349eac4729b97e51 | True | 0.0 | 32.0 |
| 100000 | resource-heavy | parallel | OK | 43623.0 | 51.25 | 349eac4729b97e51 | True | 0.0 | 32.0 |
| 100000 | constraint-heavy | sequential | OK | 1163644.8 | 1163.55 | 301b17f480b902ce | True | -8.0 | -8.0 |
| 100000 | constraint-heavy | parallel | OK | 1164731.2 | 1177.24 | 301b17f480b902ce | True | -8.0 | -8.0 |

## Capacity sweep: 25000 mixed at slots 1/2/4/8/16/32

| slots | float_workers | wall ms | CPU s | speedup vs slots=1 | hash | matches matrix cell |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 6,580.8 | 6.580 | 1.0 | 7c6aa1b2e001b445 | True |
| 2 | 1 | 6,595.3 | 6.600 | 0.998 | 7c6aa1b2e001b445 | True |
| 4 | 3 | 3,766.8 | 7.170 | 1.747 | 7c6aa1b2e001b445 | True |
| 8 | 7 | 3,802.0 | 7.190 | 1.731 | 7c6aa1b2e001b445 | True |
| 16 | 15 | 3,791.0 | 7.180 | 1.736 | 7c6aa1b2e001b445 | True |
| 32 | 31 | 3,808.7 | 7.240 | 1.728 | 7c6aa1b2e001b445 | True |

Status / error per point: slots=1: OK; slots=2: OK; slots=4: OK; slots=8: OK; slots=16: OK; slots=32: OK

## Project sweep: N concurrent 5000-activity projects, GlobalExecutionBudget(4)

| projects | wall ms | throughput proj/s | peak slots | process starts | queue wait max ms | all hashes match | status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1,105.6 | 0.905 | 4 | 1 | 0.1 | True | OK |
| 2 | 1,652.8 | 1.21 | 4 | 2 | 2.6 | True | OK |
| 4 | 1,680.4 | 2.38 | 4 | 4 | 4.2 | True | OK |
| 8 | 3,357.0 | 2.383 | 4 | 8 | 1690.8 | True | OK |
| 16 | 6,693.6 | 2.39 | 4 | 16 | 5021.9 | True | OK |

### Per-project hashes (scheduled vs that project's own sequential run)

| projects | seed | tenant | state | slots | run ms | queue wait ms | sequential hash | scheduled hash | match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 20261116 | T-p0n2-5d606e4d-00 | SUCCEEDED | 4 | 1105.4 | 0.1 | 067f05a0be1a27dd | 067f05a0be1a27dd | True |
| 2 | 20261116 | T-p0n2-ef241108-00 | SUCCEEDED | 2 | 1637.4 | 0.1 | 067f05a0be1a27dd | 067f05a0be1a27dd | True |
| 2 | 20261117 | T-p0n2-ef241108-01 | SUCCEEDED | 2 | 1650.1 | 2.6 | 36bcb72c90878cd6 | 36bcb72c90878cd6 | True |
| 4 | 20261118 | T-p0n2-b0e3f4aa-02 | SUCCEEDED | 1 | 1671.7 | 3.4 | 44699b5adfb58ffb | 44699b5adfb58ffb | True |
| 4 | 20261116 | T-p0n2-b0e3f4aa-00 | SUCCEEDED | 1 | 1680.2 | 0.1 | 067f05a0be1a27dd | 067f05a0be1a27dd | True |
| 4 | 20261117 | T-p0n2-b0e3f4aa-01 | SUCCEEDED | 1 | 1677.7 | 2.6 | 36bcb72c90878cd6 | 36bcb72c90878cd6 | True |
| 4 | 20261119 | T-p0n2-b0e3f4aa-03 | SUCCEEDED | 1 | 1676.2 | 4.2 | aca44f474c8e9e7b | aca44f474c8e9e7b | True |
| 8 | 20261116 | T-p0n2-1fa97e32-00 | SUCCEEDED | 1 | 1667.5 | 0.1 | 067f05a0be1a27dd | 067f05a0be1a27dd | True |
| 8 | 20261119 | T-p0n2-1fa97e32-03 | SUCCEEDED | 1 | 1669.5 | 4.3 | aca44f474c8e9e7b | aca44f474c8e9e7b | True |
| 8 | 20261117 | T-p0n2-1fa97e32-01 | SUCCEEDED | 1 | 1686.9 | 2.6 | 36bcb72c90878cd6 | 36bcb72c90878cd6 | True |
| 8 | 20261118 | T-p0n2-1fa97e32-02 | SUCCEEDED | 1 | 1686.1 | 3.5 | 44699b5adfb58ffb | 44699b5adfb58ffb | True |
| 8 | 20261120 | T-p0n2-1fa97e32-04 | SUCCEEDED | 1 | 1653.7 | 1667.7 | 3fe3f5b51eec23df | 3fe3f5b51eec23df | True |
| 8 | 20261121 | T-p0n2-1fa97e32-05 | SUCCEEDED | 1 | 1652.5 | 1674.0 | 2aeda0742605f9e1 | 2aeda0742605f9e1 | True |
| 8 | 20261122 | T-p0n2-1fa97e32-06 | SUCCEEDED | 1 | 1662.1 | 1689.7 | f143e030af43752e | f143e030af43752e | True |
| 8 | 20261123 | T-p0n2-1fa97e32-07 | SUCCEEDED | 1 | 1666.1 | 1690.8 | 1ca7128cd63f7957 | 1ca7128cd63f7957 | True |
| 16 | 20261116 | T-p0n2-b698fab8-00 | SUCCEEDED | 1 | 1671.0 | 0.1 | 067f05a0be1a27dd | 067f05a0be1a27dd | True |
| 16 | 20261118 | T-p0n2-b698fab8-02 | SUCCEEDED | 1 | 1667.7 | 3.5 | 44699b5adfb58ffb | 44699b5adfb58ffb | True |
| 16 | 20261117 | T-p0n2-b698fab8-01 | SUCCEEDED | 1 | 1675.9 | 2.8 | 36bcb72c90878cd6 | 36bcb72c90878cd6 | True |
| 16 | 20261119 | T-p0n2-b698fab8-03 | SUCCEEDED | 1 | 1690.8 | 4.7 | aca44f474c8e9e7b | aca44f474c8e9e7b | True |
| 16 | 20261120 | T-p0n2-b698fab8-04 | SUCCEEDED | 1 | 1650.3 | 1671.4 | 3fe3f5b51eec23df | 3fe3f5b51eec23df | True |
| 16 | 20261121 | T-p0n2-b698fab8-05 | SUCCEEDED | 1 | 1660.5 | 1672.5 | 2aeda0742605f9e1 | 2aeda0742605f9e1 | True |
| 16 | 20261122 | T-p0n2-b698fab8-06 | SUCCEEDED | 1 | 1665.8 | 1678.9 | f143e030af43752e | f143e030af43752e | True |
| 16 | 20261123 | T-p0n2-b698fab8-07 | SUCCEEDED | 1 | 1660.7 | 1695.6 | 1ca7128cd63f7957 | 1ca7128cd63f7957 | True |
| 16 | 20261124 | T-p0n2-b698fab8-08 | SUCCEEDED | 1 | 1645.9 | 3321.8 | 4e0fe55fb8864bdc | 4e0fe55fb8864bdc | True |
| 16 | 20261125 | T-p0n2-b698fab8-09 | SUCCEEDED | 1 | 1655.8 | 3333.2 | f53566bcc002748b | f53566bcc002748b | True |
| 16 | 20261126 | T-p0n2-b698fab8-10 | SUCCEEDED | 1 | 1644.3 | 3344.9 | f1eabda5f48e2807 | f1eabda5f48e2807 | True |
| 16 | 20261127 | T-p0n2-b698fab8-11 | SUCCEEDED | 1 | 1665.3 | 3356.4 | 36205e91ab4d8212 | 36205e91ab4d8212 | True |
| 16 | 20261128 | T-p0n2-b698fab8-12 | SUCCEEDED | 1 | 1649.6 | 4967.8 | 8850b340e0b689f2 | 8850b340e0b689f2 | True |
| 16 | 20261129 | T-p0n2-b698fab8-13 | SUCCEEDED | 1 | 1653.5 | 4989.2 | dc638eb68482aeed | dc638eb68482aeed | True |
| 16 | 20261130 | T-p0n2-b698fab8-14 | SUCCEEDED | 1 | 1657.5 | 4990.3 | 292dd728f5300412 | 292dd728f5300412 | True |
| 16 | 20261131 | T-p0n2-b698fab8-15 | SUCCEEDED | 1 | 1671.6 | 5021.9 | 8cd3c54d4aed9159 | 8cd3c54d4aed9159 | True |

## Worker end to end: real PostgreSQL + real SchedulingWorkerRuntime

| size | mode | state | attempts | submit ms | drain ms | e2e ms | DB submit->SUCCEEDED ms | output_hash == calculation_run_identity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1000 | thread | SUCCEEDED | 1 | 6.4 | 505.2 | 527.7 | 136.0 | True |
| 1000 | process | SUCCEEDED | 1 | 6.2 | 527.3 | 549.6 | 276.7 | True |
| 5000 | thread | SUCCEEDED | 1 | 26.8 | 1046.9 | 1090.7 | 613.7 | True |
| 5000 | process | SUCCEEDED | 1 | 27.2 | 1093.5 | 1137.1 | 789.8 | True |

### Worker run detail

- size=1000 mode=thread: job_id `cf192b528566a24ca42156bcecbccd46f4f846d68bc7fb377778f72ff9ef7e26`, tenant `T-p0n2-082bf58abc`, snapshot `S-3275ba1203c046df9c2e70c1346f6523`, state `SUCCEEDED`, attempts `1`, lease owner `None`, activity_count `1000`, output_hash `ad89e7dc0ef8578f0464414617831243ffed3a14eac9c5fe5a16c97e3ae192cf`, calculation_run_identity `ad89e7dc0ef8578f0464414617831243ffed3a14eac9c5fe5a16c97e3ae192cf`, match `True`, status `OK`
  - settings: `{"slots": 2, "poll_interval": 0.25, "job_timeout": null, "connect_timeout": 10}`, outcome: `{"claimed": 1, "succeeded": 1, "failed": 0, "cancelled": 0, "retried": 0, "lease_lost": 0, "process_starts": 0, "inline_fallbacks": 0, "cache_hits": 0, "cache_misses": 0, "peak_slots": 0, "stopped": false}`
- size=1000 mode=process: job_id `e461848d8a9e34e1addee30cd1fac25ea653952295e4ed36ea37ada55c133674`, tenant `T-p0n2-c5f3104803`, snapshot `S-ce361277d1e14227a3c315f2a8ac8cb3`, state `SUCCEEDED`, attempts `1`, lease owner `None`, activity_count `1000`, output_hash `3aa510a8d6f92f898359d8bd3449fc90b1a356cab7b7aafcca0074b7cba64ef4`, calculation_run_identity `3aa510a8d6f92f898359d8bd3449fc90b1a356cab7b7aafcca0074b7cba64ef4`, match `True`, status `OK`
  - settings: `{"slots": 2, "poll_interval": 0.25, "job_timeout": null, "connect_timeout": 10}`, outcome: `{"claimed": 1, "succeeded": 1, "failed": 0, "cancelled": 0, "retried": 0, "lease_lost": 0, "process_starts": 1, "inline_fallbacks": 0, "cache_hits": 0, "cache_misses": 0, "peak_slots": 1, "stopped": false}`
- size=5000 mode=thread: job_id `9fb3564d6e1f922b86e69f80a7f2a4fdfe94034d4725baa8a0da310a9aa35692`, tenant `T-p0n2-33285c7f0d`, snapshot `S-f7e5a2dcf8834c78abfb2c30715e3887`, state `SUCCEEDED`, attempts `1`, lease owner `None`, activity_count `5000`, output_hash `3c1f4defec75be07c27f13e6d6731fcc2a1398541f8a9e10fdb98610cfb4b0cb`, calculation_run_identity `3c1f4defec75be07c27f13e6d6731fcc2a1398541f8a9e10fdb98610cfb4b0cb`, match `True`, status `OK`
  - settings: `{"slots": 2, "poll_interval": 0.25, "job_timeout": null, "connect_timeout": 10}`, outcome: `{"claimed": 1, "succeeded": 1, "failed": 0, "cancelled": 0, "retried": 0, "lease_lost": 0, "process_starts": 0, "inline_fallbacks": 0, "cache_hits": 0, "cache_misses": 0, "peak_slots": 0, "stopped": false}`
- size=5000 mode=process: job_id `9c088b292e1d8d748e1a8e9355f88eed41ff99a6568030946bc83f139ca46fbe`, tenant `T-p0n2-5c3c8c5380`, snapshot `S-64157c8098554979966bcbdc3ae0f0fc`, state `SUCCEEDED`, attempts `1`, lease owner `None`, activity_count `5000`, output_hash `e96471ef6f125c6a27ba4dcb653b6e6e78fbbf1e5bcfa782a8b36675ee59e079`, calculation_run_identity `e96471ef6f125c6a27ba4dcb653b6e6e78fbbf1e5bcfa782a8b36675ee59e079`, match `True`, status `OK`
  - settings: `{"slots": 2, "poll_interval": 0.25, "job_timeout": null, "connect_timeout": 10}`, outcome: `{"claimed": 1, "succeeded": 1, "failed": 0, "cancelled": 0, "retried": 0, "lease_lost": 0, "process_starts": 1, "inline_fallbacks": 0, "cache_hits": 0, "cache_misses": 0, "peak_slots": 2, "stopped": false}`

## Integrity notes

- Measurement only: this harness adds scripts/p0n2_runtime_matrix.py, writes the evidence files under `docs/workspace/evidence/p0n2-integration-2026-11-21/results/`, and changes no product code, test, or configuration.
- The worker process-mode path runs against the committed `src/construction_pm/scheduling_job_executor.py` of this build, which contains the pipe-drain fix (commit 5b4cfb71 on the P0-N.2 branch, merged into this integration head): the parent drains the result pipe (non-blocking poll/recv) before joining the child. Before that fix, two exploratory 5000-activity process-mode runs deadlocked with the job child blocked in pipe_write once the pickled SchedulingJobResult exceeded the ~64 KB pipe buffer; those exploratory runs were terminated, are not part of this measurement, and their job rows were cancelled.
- constraint-heavy cells pass the fixture's own (unconstrained) project_finish to time_schedule, exactly like scripts/p0n_multi_project_benchmark.py::run_project. Because the START_NO_EARLIER_THAN list pushes work later than that finish, the recorded total float for those cells is negative; min_total_float_hours/max_total_float_hours are stored per run so the effect is visible instead of hidden.
- This host runs other work items in parallel; the same PostgreSQL instance is shared. Each worker run seeds its own unique tenant scope, so rows never overlap, but wall-clock numbers can include contention noise.

- Engine actually called: `construction_pm.scheduling.time_schedule.time_schedule`

### Post-run note corrections

A note written at run time became stale before publication; the original text is kept here so the edit is auditable rather than silent.

- was: Measurement only: this harness adds scripts/p0n2_runtime_matrix.py and the four evidence files under docs/workspace/evidence/p0n-runtime-activation-2026-11-20/ and changes no product code, test, or configuration.
- is now: Measurement only: this harness adds scripts/p0n2_runtime_matrix.py, writes the evidence files under `docs/workspace/evidence/p0n2-integration-2026-11-21/results/`, and changes no product code, test, or configuration.
- was: The worker process-mode path runs against src/construction_pm/scheduling_job_executor.py as it stands in this working tree, which carries an uncommitted fix from another work item: the parent now drains the result pipe (non-blocking poll/recv) before joining the child. Before that fix, two exploratory 5000-activity process-mode runs started by this harness deadlocked with the job child blocked in pipe_write once the pickled SchedulingJobResult exceeded the ~64 KB pipe buffer; those runs were terminated, are not part of this evidence, and their job rows were left as found (expired LEASED, cancelled by the fixing work item).
- is now: The worker process-mode path runs against the committed `src/construction_pm/scheduling_job_executor.py` of this build, which contains the pipe-drain fix (commit 5b4cfb71 on the P0-N.2 branch, merged into this integration head): the parent drains the result pipe (non-blocking poll/recv) before joining the child. Before that fix, two exploratory 5000-activity process-mode runs deadlocked with the job child blocked in pipe_write once the pickled SchedulingJobResult exceeded the ~64 KB pipe buffer; those exploratory runs were terminated, are not part of this measurement, and their job rows were cancelled.

## Recorded failures, timeouts and skipped cells

- none: every recorded cell, sweep point, project and worker run completed and matched.

## Scope note

This document and the harness are measurement only. No product code, test, configuration or committed artifact outside `docs/workspace/evidence/p0n2-integration-2026-11-21/` was changed, and nothing was deleted from the shared PostgreSQL tables: each worker run seeds its own unique tenant scope, exactly like the integration test it mirrors.

