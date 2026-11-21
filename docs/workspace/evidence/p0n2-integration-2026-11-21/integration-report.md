# Integration report: P0-N.2 on main `c34ac05e`

This is the delivery record for `feat/p0n2-integration`: what changed relative to
main, what the port did to the measured behaviour, what was fixed on the way, and
what remains limited. Raw evidence is in this directory; no merge to main and no
deployment was performed.

## 1. Before / after

| Dimension | Before (P0-N.2 branch `a26269c6`, based on `ae6e72e4`) | After (integrated head on `c34ac05e`) |
| --- | --- | --- |
| Main's capabilities | 84 commits behind main | Base is main; AI Workbench, global administration, enterprise surface, identity changes, preview and public site all present |
| Source files changed vs main | 9 source files, harness, 3 test files | Same 9/3, plus a composition test; no file from main was altered |
| Production composition | no calendar registry / job repository in the runtime | calendar registry factory + `PostgresSchedulingJobRepository` wired before main's middleware stack; order unchanged |
| Full suite | 5382 passed, 1 skipped | **5492 passed, 1 skipped, 15 subtests**, 81 s |
| Targeted set | 126 passed | **134 passed** (main added tests to the same files, plus the new composition test) |
| Process placement | deadlock for results above the ~64 KB pipe buffer | fixed; ~2 MB payload regression test passes in seconds; live 5000-activity process job succeeds |
| Matrix cells | 25 cells, all hash PASS | 25 cells, all `OK` and hash `PASS`; numbers within noise of before |
| Capacity points | 1/2/4/8/16 | 1/2/4/8/16/32; 32 measured at 1.728× vs 1 slot |
| Workbench / Enterprise | not on the branch base | A/B identical: 264 passed / 15 subtests on main and on the integrated head |

### Sequential/parallel medians, before vs after

Same fixture, same seed, same host class. Full table in
[performance-benchmarks.md](performance-benchmarks.md).

| size | shape | seq before → after (ms) | par before → after (ms) |
| --- | --- | --- | --- |
| 1,000 | chain | 129.2 → 129.6 | 114.2 → 134.8 |
| 1,000 | mixed | 260.4 → 260.4 | 152.9 → 154.4 |
| 5,000 | mixed | 1,276.2 → 1,286.3 | 762.5 → 742.4 |
| 25,000 | mixed | 6,557.4 → 6,576.5 | 3,785.9 → 3,906.8 |
| 50,000 | mixed | 13,401.2 → 13,502.1 | 8,010.5 → 8,518.2 |
| 100,000 | mixed | 27,055.3 → 27,426.3 | 16,502.2 → 16,565.0 |
| 100,000 | constraint-heavy | 1,168,606.3 → 1,163,644.8 | 1,185,340.3 → 1,164,731.2 |
| 100,000 | resource-heavy | 48,849.2 → 48,916.5 | 43,180.4 → 43,623.0 |

Large cells are within about ±2%; small parallel cells at 1,000 activities move by
10–30% because each is a median of two sub-second runs on a shared host. The
integration did not change the engine, so no systematic shift is expected or
observed.

## 2. Changed files

Relative to main (`git diff --name-only origin/main...HEAD`), production code:

| File | Role in the port |
| --- | --- |
| `src/construction_pm/deployment/production_runtime.py` | binds calendar repositories, the scoped registry factory and the scheduling job repository; keeps main's middleware order |
| `src/construction_pm/deployment/scheduling_worker.py` | new standalone durable worker over PostgreSQL |
| `src/construction_pm/deployment/schema.py` | adds calendar and scheduling-job initializers after main's initializers |
| `src/construction_pm/backend_p0/authoritative_schedule_query.py` | authoritative schedule read path |
| `src/construction_pm/http/production_composition.py` | composition helper for the runtime |
| `src/construction_pm/p6_versioned_resource_calendar_resolver.py` | versioned calendar resolution and hashing |
| `src/construction_pm/schedule_evaluator.py` | calendar-aware evaluation |
| `src/construction_pm/scheduling_job_executor.py` | pipe-drain fix for process placement |
| `src/construction_pm/scheduling_job_runner.py` | durable job runner |

Measurement and proof:

| File | Role |
| --- | --- |
| `scripts/p0n2_runtime_matrix.py` | benchmark/report harness; this branch adds `--phase-deadline`, `--capacity-slots` and `--mode-budget`, capacity up to 32, and renders every table from the raw JSON |
| `tests/integration/test_p0n2_runtime_activation.py` | live PostgreSQL proof; adds `test_production_composition_keeps_every_http_surface_wired` |
| `tests/scheduling/test_scheduling_job_executor_process.py` | adds the >64 KB payload deadlock regression test |
| `tests/test_calendar_registry_production_builder.py` | calendar registry builder proof |
| `docs/workspace/evidence/p0n-runtime-activation-2026-11-20/` | the earlier branch evidence, carried over unchanged |
| `docs/workspace/evidence/p0n2-integration-2026-11-21/` | this evidence |

No file under `src/construction_pm/ai_workbench/`, `global_administration*`,
`enterprise_*`, `preview/*`, `identity_session.py` or `apps/web/` was modified by
the port.

## 3. Problems found and resolved

1. **Process-placement deadlock (product defect).** The parent joined the child
   before reading the `multiprocessing.Pipe`; a result larger than the ~64 KB pipe
   buffer left both sides blocked until the job timeout. Fixed in `5b4cfb71` by
   draining the pipe before join, with `test_result_larger_than_the_pipe_buffer_does_not_deadlock`
   as the guard. Reverting the fix reproduces a 60 s timeout; with it, the test
   passes in seconds and the live 5000-activity process job succeeds.
2. **Merge conflict in `production_runtime.py`.** Only the import block conflicted.
   Both imports are required by different responsibilities (durable job surface
   vs Workbench data date); both were kept and the composition order from main was
   preserved unchanged.
3. **Schema merge.** `schema.py` auto-merged but needed inspection: main's global
   administration initializer and the branch's four calendar initializers plus
   `initialize_scheduling_job_schema` must all run. Verified in the source and in
   the regenerated Vercel copy.
4. **Silent surface shadowing was untested.** Added a live test that walks the
   assembled `ProductionRuntime.api_app` and asserts
   `AIWorkbench → EnterpriseTask → GlobalAdministration → P6`, so a future merge
   that drops a middleware fails in CI instead of at runtime.
5. **Stale "uncommitted fix" note in the previous evidence.** The earlier run's
   JSON described the pipe fix as uncommitted; it is commit `5b4cfb71` and is part
   of this head. The note was corrected in this run's JSON and the original text is
   preserved in `note_corrections`, rendered under "Post-run note corrections".
6. **Stale generated Vercel runtime.** `apps/web/vercel-runtime/` is git-ignored
   and rebuilt from `src/` at build time. Regenerated locally and verified
   byte-identical to `src/` with the blocker strings absent.

## 4. Remaining limitations

- Constraint-heavy fixtures grow approximately quadratically with size and gain
  almost nothing from parallel placement; the 100k cell takes about 19.4 min per
  mode. See [known-limitations.md](known-limitations.md).
- Capacity on this host saturates at 4 slots; 8, 16 and 32 slots measure within
  0.5% of each other. No claim is made about larger hosts.
- Concurrent-project throughput plateaus at ~2.39 projects/s with 4 budget slots;
  the remainder becomes queue wait.
- Wall-clock numbers carry shared-host noise; hash equality and pass/fail do not.
- The repository does not schedule CI for docs-only commits; CI is recorded on the
  last code-bearing commit of this branch, exactly as stated in §5.

## 5. Commit, PR and CI

| Item | Value |
| --- | --- |
| Integration branch | `feat/p0n2-integration` |
| Merge commit | `89ced6a7 merge(p0n): integrate P0-N.2 runtime activation onto main c34ac05e` |
| Evidence commit | to be filled at push time |
| Pull request | to be filled at push time |
| CI on the final code-bearing commit | to be filled at push time |

This section is completed with the exact run URLs/status after the branch is
pushed; nothing here is pre-declared.
