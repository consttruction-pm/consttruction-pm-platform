# P0-N.2 final acceptance report — runtime activation

Date: 2026-11-20
Branch: `feat/p0n2-runtime-activation`
Base: `ae6e72e4` (`main`)
Probe head `8fdb06a9`; IPC fix `5b4cfb71` (process placement). Evidence commits follow.
No merge to `main`, no deployment, no destructive production change.

## 1. Executive result

The Calendar Registry blocker is removed. Production and worker runtimes now build a
real, scope-bound, version-pinned registry from persisted PostgreSQL calendar rows;
`_calendar_registry_not_wired` and `SCHEDULE_QUERY_NOT_DEPLOYED` no longer exist in the
production path. A real API submit is executed by a real standalone worker on a real
PostgreSQL database, and the retrieved `output_hash` equals the payload's
`calculation_run_identity` in both thread and process placement.

## 2. What changed

| Area | Path | Change |
| --- | --- | --- |
| Registry builder | `src/construction_pm/p6_versioned_resource_calendar_resolver.py` | `build_calendar_registry_for_scope`, `calendar_registry_hash`, fail-closed kind/definition handling |
| Provider | `src/construction_pm/backend_p0/authoritative_schedule_query.py` | scope-bound registry factory |
| Composition | `src/construction_pm/http/production_composition.py` | passes the scoped factory |
| Web runtime | `src/construction_pm/deployment/production_runtime.py` | real calendar repos + job repository; blocker removed |
| Schema | `src/construction_pm/deployment/schema.py` | calendar tables + job schema initialization |
| Worker | `src/construction_pm/deployment/scheduling_worker.py` (new) | thread-local connections, budget, real engine, thread/process placement |
| Executor IPC | `src/construction_pm/scheduling_job_executor.py` | drain the child result pipe before `join` (large results no longer deadlock) |
| Runner | `src/construction_pm/scheduling_job_runner.py` | DSN-based child execution, result/hash mapping, diagnosable errors |
| Evaluator | `src/construction_pm/schedule_evaluator.py` | closed-set reason appended to `SCHEDULE_EVALUATION_FAILED` |
| Tests | `tests/integration/test_p0n2_runtime_activation.py` (new, 11), `tests/test_calendar_registry_production_builder.py` (new, 6) | live and fast coverage |

Routes involved (contracts unchanged): `POST /api/v1/schedule/query`,
`POST /api/v1/schedule/projects/{project_id}/jobs`,
`GET /api/v1/schedule/projects/{project_id}/jobs/{job_id}`,
`POST .../jobs/{job_id}/cancel`, `GET .../jobs/{job_id}/result`.

## 3. Exit criteria

| # | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Real Calendar Registry connected | PASS | `build_calendar_registry_for_scope` wired in web and worker runtimes; `test_calendar_registry_is_built_from_persisted_calendars` |
| 2 | `_calendar_registry_not_wired` gone from the real path | PASS | grep over `src/` and `api/` returns no match; `test_production_runtime_source_no_longer_contains_the_wiring_blocker` |
| 3 | `SCHEDULE_QUERY_NOT_DEPLOYED` gone from a healthy Runtime path | PASS | same source test; production runtime boots in `tests/test_production_web_app.py` |
| 4 | Submit → retrieval on real DB + worker | PASS | `logs/live-job-run-thread.log`, `logs/live-job-run-process.log`; `test_http_submit_runs_on_real_worker_and_result_is_retrieved` |
| 5 | Stable snapshot and calendar version | PASS | `test_calendar_registry_is_scoped_and_hash_is_stable`; `test_missing_calendar_version_fails_closed_without_latest_fallback`; `tests/test_schedule_input_snapshot_repository.py` |
| 6 | Multi-project capacity/fairness proven | PASS | `performance-benchmarks.md`: all 25 size×shape cells `OK` with sequential-vs-parallel hash equality `PASS`; capacity 1–16 slots and 1–16 projects measured with no budget breach |
| 7 | Cancellation/recovery/failure paths | PASS | `test_cancel_before_claim_prevents_execution`, `test_expired_lease_is_recovered_and_the_job_runs_once`, `test_process_timeout_marks_the_job_failed`, `test_cancel_leased_job_is_cooperative_and_never_publishes_a_result` |
| 8 | Regression + full suite green on final SHA | PASS | `logs/full-suite.log`: 5382 passed, 1 environmental skip |
| 9 | Independent Professional and EPPM documentation | PASS | `professional-help-traceability.md`, `eppm-help-traceability.md`, `two-environment-reference-map.md` |
| 10 | Each capability with exact Help URL and GitHub reference | PASS | 21 Professional rows (HTML URL + absolute PDF page) and 21 EPPM rows (exact HTML URL); every CUBI/test path exists in this tree |
| 11 | Evidence and final report in GitHub | PASS | this directory, committed on `feat/p0n2-runtime-activation`; supplementary PR linked below |
| 12 | Supplementary PR review-ready, no merge | PASS | PR opened against `main`, draft/review state, no merge performed |

## 4. Real-execution evidence

Thread mode (5 activities, two slots):

```
state SUCCEEDED, attempts 1, process_starts 0
output_hash == calculation_run_identity
ddd8648e11b8d3b578b08db829bc92c2d6d59b1b1739aa3f0daf1e3b1c4fd684
```

Process mode:

```
state SUCCEEDED, attempts 1, process_starts 1, inline_fallbacks 0
output_hash == calculation_run_identity
c40a83732e49fec386fe2c26d8882800f69b503bf7c91a4eede49d243bffc5ed
```

Process mode at real workload size after the IPC fix (result payloads 751 KB and
3.75 MB, far above the 64 KiB pipe buffer):

```
1,000 activities, 2 slots: SUCCEEDED attempts 1 process_starts 1  798.9 ms  hash_equal true
5,000 activities, 4 slots: SUCCEEDED attempts 1 process_starts 1 1,137.4 ms  hash_equal true
```

Before the fix the same path deadlocked in `send`/`join` and was retried as
`SCHEDULING_JOB_TIMEOUT`; see `job-lifecycle-evidence.md` §4.1 and regression test
`test_result_larger_than_the_pipe_buffer_does_not_deadlock`.

Targeted suite: **126 passed** (`logs/targeted.log`).
Full suite: **5382 passed, 1 skipped** (`logs/full-suite.log`; skip is the missing
optional `pmcontrols` module, not a product failure).

Performance: the engine matrix (5 sizes × 5 shapes × sequential/parallel, capacity
1–16, projects 1–16) and worker end-to-end timings are in
`performance-benchmarks.md` with raw JSON in `results/`. Every sequential-vs-parallel
hash comparison is recorded; no time is extrapolated. Headlines from the recorded JSON:

```
25 size×shape cells:               25 OK, hash equality PASS (23 in the orchestrated
                                   phase, 2 re-measured with a larger mode budget)
largest cell 100000 constraint-heavy: 1,168,606 ms sequential / 1,185,340 ms parallel
capacity 25000 mixed:              1/2/4/8/16 slots -> 6,551 / 6,589 / 3,837 / 3,736 / 3,777 ms
projects at budget 4:              1/2/4/8/16 -> 1.09 / 1.64 / 1.68 / 3.35 / 6.61 s,
                                   peak_slots 4, every project hash equals its own sequential run
worker e2e (submit -> retrieve):   1000 thread 528.0 ms, 1000 process 546.4 ms,
                                   5000 thread 1090.2 ms, 5000 process 1137.8 ms, all SUCCEEDED
```

## 5. CI

All required checks passed on the code head `78bd3aac` (branch
`feat/p0n2-runtime-activation`, PR #2068), run on 2026-11-21:

| Check | Result | Duration | Run |
| --- | --- | --- | --- |
| postgres | success | 44 s | [44861097611](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/44861097611) |
| test (3.11) | success | 2 m 57 s | [44861097562](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/44861097562) |
| test (3.12) | success | 2 m 23 s | [44861097562](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/44861097562) |
| test (3.13) | success | 2 m 59 s | [44861097562](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/44861097562) |
| typecheck (apps/web) | success | 39 s | [44861097599](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/44861097599) |
| typecheck (apps/desktop) | success | 20 s | [44861097599](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/44861097599) |
| typecheck (apps/mobile) | success | 17 s | [44861097599](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/44861097599) |
| typecheck (apps/client-sync) | success | 19 s | [44861097599](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/44861097599) |
| Vercel – cubi-web-preview | success | — | preview deployment |

The commit that adds this section is documentation-only and runs the same
workflow; its checks are visible on the PR's commit list. Local evidence above was
produced independently of CI and does not depend on it.

## 6. Honest boundaries

`known-limitations.md` lists every gap, including: no implicit default calendar,
personal resource calendars not modeled, multiple float paths and float threshold not
yet on the time-aware job path, leveling not in durable jobs, no recurring scheduled
services, and four P6/EPPM features marked `MISSING` (schedule checker, summarization,
cross-project allocation profile, budgeting workflow). None of these is used to claim
parity.

## 7. Permission boundary

Work is confined to an independent branch. Per the owner's instruction, this branch was
not merged to `main` and was not deployed. Merging requires the project owner's explicit
permission.
