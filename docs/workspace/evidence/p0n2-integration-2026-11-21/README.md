# P0-N.2 integration onto current main

This directory is the evidence for rebasing the P0-N.2 runtime activation work onto
the current repository state. It is not a success note: it contains the raw runs,
the compatibility review, the conflict decisions, the re-executed test families and
the measured limits.

## Position

| Item | Value |
| --- | --- |
| Repository | `consttruction-pm/consttruction-pm-platform` |
| P0-N.2 pull request | #2068 |
| Original branch | `feat/p0n2-runtime-activation` at `a26269c6` |
| Shared base | `ae6e72e4` |
| `origin/main` at integration time | `c34ac05e` (84 commits ahead of the base, 59 non-merge) |
| Integration branch | `feat/p0n2-integration` |
| Merge commit (main + P0-N.2) | `89ced6a7` |
| Evidence run commit | `89ced6a7` plus the harness/test/evidence changes in this branch |

Hard limits observed: **main was not merged into, Production was not changed, and no
production deployment was performed.** The integration branch is the only output.

## What was done, in order

1. Read the 84 commits main added since `ae6e72e4` and reviewed them by area:
   AI Workbench, production runtime, scheduling/compute, database/schema,
   authentication/session, preview and web entry points. See
   [compatibility-review.md](compatibility-review.md).
2. Cut `feat/p0n2-integration` from `origin/main` and merged `a26269c6` into it,
   so main's capabilities are the base and P0-N.2 is the ported change, never the
   reverse.
3. Resolved the only conflict (`production_runtime.py`, import block) by
   architectural responsibility, not by side selection. `schema.py` auto-merged.
4. Adapted the calendar registry, worker, process executor and job lifecycle to the
   merged composition and proved the middleware order with a new live test.
5. Re-ran the required test families on PostgreSQL, thread and process placement,
   cancellation, recovery, multi-tenancy and the full regression suite.
6. Re-ran the complete sequential/parallel benchmark matrix with hash equality, the
   capacity sweep at 1/2/4/8/16/32 slots, the project sweep and the live worker
   end-to-end runs.
7. Measured the constraint-heavy limits separately instead of extrapolating, and
   recorded where capacity stops scaling on this 4-CPU host.

## Evidence inventory

| File | Content |
| --- | --- |
| [compatibility-review.md](compatibility-review.md) | Main's 84 commits by area, the two overlapping files, the conflict resolution and the invariants checked |
| [integration-report.md](integration-report.md) | Before/after comparison, changed files, resolved defects, remaining limitations, commit/PR/CI record |
| [test-matrix.md](test-matrix.md) | Required test families mapped to exact node IDs, commands and results |
| [performance-benchmarks.md](performance-benchmarks.md) | Rendered only from the raw JSON of this run: 25 matrix cells, 6 capacity points, 5 project points, 4 worker runs |
| [known-limitations.md](known-limitations.md) | Measured constraint-heavy behaviour and capacity saturation, with no unmeasured scalability claims |
| `results/matrix-20261121T035740Z.json` | Raw matrix, capacity and project measurements |
| `results/matrix-20261121T035740Z.log` | Orchestrator log with every spawned command |
| `results/worker-e2e-20261121T035740Z.json` | Raw live worker runs on real PostgreSQL |
| `logs/*.log` | Targeted, full-suite, scheduling, calendar, process-placement and A/B logs |

## Reproduce

PostgreSQL 14.24 was used at `127.0.0.1:55432`:

```bash
export P6_TEST_POSTGRES_DSN=postgresql://postgres@127.0.0.1:55432/postgres
export CONSTRUCTION_PM_POSTGRES_DSN="$P6_TEST_POSTGRES_DSN"
export PYTHONPATH=src

python3 scripts/p0n2_runtime_matrix.py run \
  --out-dir docs/workspace/evidence/p0n2-integration-2026-11-21/results \
  --dsn "$P6_TEST_POSTGRES_DSN" \
  --phase-deadline 4200 --capacity-slots 1,2,4,8,16,32 --mode-budget 100000=1800

python3 scripts/p0n2_runtime_matrix.py report \
  --matrix docs/workspace/evidence/p0n2-integration-2026-11-21/results/matrix-20261121T035740Z.json \
  --worker docs/workspace/evidence/p0n2-integration-2026-11-21/results/worker-e2e-20261121T035740Z.json \
  --md docs/workspace/evidence/p0n2-integration-2026-11-21/performance-benchmarks.md
```

Test commands are listed verbatim in [test-matrix.md](test-matrix.md).
