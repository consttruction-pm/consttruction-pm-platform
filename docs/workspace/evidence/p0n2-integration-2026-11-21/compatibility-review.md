# Compatibility review: P0-N.2 against main `c34ac05e`

The P0-N.2 branch was cut from `ae6e72e4`. Main moved 84 commits (59 non-merge)
ahead of that point, reaching `c34ac05e`. Nothing from main was reverted or
overwritten during the port; this file records what changed, what overlapped, and
how each overlap was resolved.

## 1. What main added

| Area | Evidence in the history | Source impact |
| --- | --- | --- |
| AI Workbench | #2093 `eed937de`, #2094 `a5049966`, #2095 `6d54e904`, #2096 `c34ac05e` | New `src/construction_pm/ai_workbench/` package (envelope, intents, orchestrator, studios, http), `production_web` entries, `AIWorkbenchHttpMiddleware` in the production runtime |
| Global administration | `73f15acf`, `ad47fc9a`, `7fa8bef0` | `global_administration.py`, `global_administration_http.py`, one `initialize()` call in `deployment/schema.py` |
| Enterprise surface | PRs #2070–#2092 (`enterprise_workbench_http.py`, `enterprise_task_sqlite_repository.py`, `apps/web/src/enterprise/*`) | New middleware and repository; `production_web` serves `/cubi` and `/ai-workbench` shells |
| Authentication / session | `c07aeb39` and the identity store work | `identity_session.py` gains `locked_at`, `expires_at`, `must_change_password`, `last_login_at`, `mark_login`, `_account_open`; session revocation on logout |
| Preview runtime | `preview/runtime.py`, `preview/server.py`, `preview/storage.py` | Local preview composition and concurrency changes |
| Public site / i18n | 22 commits (ten locales, 25 routes, capabilities, help registries) | `apps/web/public`, `apps/web/site`, generated registries |
| Scheduling / compute core | **no commits** | `src/construction_pm/scheduling/`, `scheduling_job_executor.py`, `scheduling_job_runner.py`, `postgres_scheduling_job_lifecycle.py`, `authoritative_schedule_query.py`, `p6_versioned_resource_calendar_resolver.py` and `schedule_evaluator.py` are untouched by main |
| Database | `deployment/schema.py` +2 lines; identity and global-administration tables | The only schema change on main is `PostgresGlobalAdministrationStore(connection).initialize()` |

The absence of scheduling changes is significant: the P0-N.2 compute path (durable
job lifecycle, thread/process placement, the result-pipe fix) lands on an unchanged
execution core, so its behaviour is determined by the branch's own code and tests.

## 2. What P0-N.2 changes, relative to main

`git diff --name-only origin/main...HEAD` is the authoritative list (9 source files
plus the new harness and 3 test files). In brief:

- `deployment/production_runtime.py`: builds the four calendar repositories, the
  scoped calendar-registry factory and `PostgresSchedulingJobRepository`, passes
  them into `build_project_lifecycle_wsgi_app`, and keeps main's middleware order.
- `deployment/scheduling_worker.py` (new): standalone durable worker over PostgreSQL.
- `deployment/schema.py`: initializes the calendar tables and the scheduling job
  schema after main's identity/global-administration/lifecycle initializers.
- `scheduling_job_executor.py`, `scheduling_job_runner.py`,
  `p6_versioned_resource_calendar_resolver.py`, `schedule_evaluator.py`,
  `backend_p0/authoritative_schedule_query.py`, `http/production_composition.py`:
  runtime activation, calendar resolution and the pipe-drain fix.
- `scripts/p0n2_runtime_matrix.py`, `tests/integration/test_p0n2_runtime_activation.py`,
  `tests/scheduling/test_scheduling_job_executor_process.py`,
  `tests/test_calendar_registry_production_builder.py`: measurement and proof.

## 3. Overlap and conflict

Only two files are touched by both sides:

| File | Main's change | P0-N.2's change | Resolution |
| --- | --- | --- | --- |
| `src/construction_pm/deployment/production_runtime.py` | `datetime`/`Callable` imports, AI Workbench middleware, `_workbench_data_date`, `PostgresProjectScheduleSettingsRepository` | calendar repositories, scoped registry factory, `PostgresSchedulingJobRepository`, job wiring into the lifecycle app | One conflict hunk, the import block. Both imports kept: `PostgresSchedulingJobRepository` for the durable job surface and `PostgresProjectScheduleSettingsRepository` for the Workbench data date. Composition order is main's: lifecycle app → Global Administration → Enterprise tasks → AI Workbench → `ProductionWebApp`. |
| `src/construction_pm/deployment/schema.py` | `PostgresGlobalAdministrationStore(connection).initialize()` | four calendar repository initializers and `initialize_scheduling_job_schema(connection)` | Auto-merged by line distance. Final order: identity → global administration → enterprise tasks → organization access → lifecycle → P6 repositories → calendar tables → scheduling job schema. |

No other file needed a manual decision. The merge commit is `89ced6a7`; its message
records the same reasoning.

## 4. Invariants checked after the merge

| Invariant | Check | Result |
| --- | --- | --- |
| Main-only modules were not altered | `git diff --quiet origin/main HEAD -- <12 files>` for `production_web.py`, `identity_session.py`, `global_administration*.py`, `ai_workbench/*`, `enterprise_workbench_http.py`, `enterprise_task_sqlite_repository.py`, `preview/*`, `knowledge/sqlite_store.py` | identical |
| P0-N.2 modules were preserved | `git diff --quiet a26269c6 HEAD -- <branch src files>` for the seven non-overlapping files | identical; only the two overlapping files differ, and those differences are main's own additions |
| All HTTP surfaces stay mounted | new live test `test_production_composition_keeps_every_http_surface_wired` walks `runtime.api_app._app` through the assembled `ProductionRuntime` | chain is `AIWorkbenchHttpMiddleware → EnterpriseTaskHttpMiddleware → GlobalAdministrationHttpMiddleware → P6 app`, length 4 |
| AI Workbench still reads the same data | A/B suites on `origin/main` worktree vs integration head, 264 tests each | 264 passed / 15 subtests on both; see `logs/ab-workbench-*.log` |
| Schema covers both sides | `initialize_production_schema` source inspected and compared with the regenerated Vercel copy | both sets present, identical |
| Vercel build path carries the merged runtime | `node apps/web/scripts/prepare-vercel-runtime.mjs`, then compare `apps/web/vercel-runtime/src/...` with `src/...` | byte-identical; blocker strings absent |

## 5. What the Workbench actually consumes

The AI Workbench is a deterministic command layer shared by Engineering and
Enterprise. It owns no scheduler and no project facts; it delegates reads to
`lifecycle_api.open_project` / `get_project`, and its `schedule-scenario` and
`project-analysis` studios declare `read_route="/api/projects/{project_id}/p6/schedule"`.
That is the same authoritative Schedule Query route the P0-N.2 calendar registry and
durable job repository feed. Activating the runtime therefore improves what the
Workbench reads; it does not bypass or reimplement it, and the A/B suites confirm
the workbench behaviour is unchanged.

## 6. Deliberate non-actions

- No AI Workbench, Enterprise, Global Administration, preview or public-site file was
  edited to make the merge pass.
- No test was weakened or deleted; the only test edits are the new deadlock
  regression test (previous work item) and the new composition invariant test.
- `apps/web/vercel-runtime/` is git-ignored and generated at build time; it was
  regenerated locally for verification and is not committed.
