# V30 — Test matrix and results

Environment: Hasan’s local Qoder Desktop, Python 3.11.4, Node 24.22.1, real Chrome (headless CDP).
No Vercel, no deployment, no production database was used.

## Static and unit

| Check | Command | Result |
|---|---|---|
| TypeScript (web) | `npx tsc --noEmit` | pass, 0 errors |
| Production build | `npm run build` | pass (main, landing, assistant bundles) |
| Web unit tests | `npx tsx --test src/*.test.ts` | **1200 pass, 0 fail** |
| Clipboard planner | `src/workspace-activity-clipboard.test.ts` | 3 pass |
| Replace/Fill Down planner | `src/workspace-activity-bulk.test.ts` | 3 pass |
| Gantt attachments client | `src/workspace-gantt-attachments.test.ts` | 8 pass |
| Desktop shell / toolbar rails | included in the 1200 | pass |

## Python / API

| Check | Command | Result |
|---|---|---|
| Full suite | `py -3 -m pytest -q` excluding the 8 modules that import Unix-only `resource` | **4707 pass, 224 skipped, 4 failed** |
| New edit tests | `tests/test_p6_activity_edit_commands.py` | 7 pass |
| Gantt attachments | `tests/test_p6_gantt_attachment.py` | 5 pass |
| Attachment HTTP | `tests/test_gantt_attachment_http_routes.py` | 3 pass |
| Activity repository / related | `tests/test_activity_master_repository.py` | pass |

The 4 failures are pre-existing Windows-environment failures unrelated to this branch:

- `tests/scheduling/test_leveling_cpm_reuse.py` (2) imports `construction_pm.scheduling.benchmark_fixtures`,
  which imports the Unix-only `resource` module.
- `tests/scheduling/test_scheduling_job_lifecycle.py` (1) has the same `resource` import path.
- `tests/test_vercel_preview_runtime.py` (1) asserts a `/tmp/...` prefix; Windows returns
  `\tmp\...` via `WindowsPath`.

The 8 collection-error modules (`scheduling/test_benchmark_fixtures`, `test_free_float_closed_form`,
`test_offline_schedule_runtime`, `test_scheduling_job_executor`, `test_time_float_execution_policy`,
`test_time_float_parallelism`, `test_time_float_search`, `test_report_export`) all import the same
Unix-only `resource` module and cannot be collected on Windows. They are not silently skipped:
this is the exact command output.

## Browser E2E (dedicated port 4200, SQLite `.preview/v30-attachments.sqlite3`)

| Suite | Result | Evidence |
|---|---|---|
| Gantt attachments (`gantt-attachments-v30.mjs`) | pass, 11 steps, 8 screenshots | `gantt-attachments-v30.json` |
| Edit commands + clipboard + replace/fill/spell (`activity-edit-v30.mjs`) | pass, 10 steps, 6 screenshots | `activity-edit-v30.json` |
| Visual matrix (`visual-matrix-v30.mjs`) | pass, 36 cells + 12 dialog cells, 84 screenshots | `visual/visual-matrix-v30.json` |

Covered by the browser suites: curtain create/draw/hide/reload/show/edit/delete, stale 409, viewer
403, text/notebook marks, delete leaf/refuse linked/stale 409, dissolve SF+FF→SF, copy/paste,
cut/paste, Replace preview+persist, Fill Down, Spell Check save, and the six-theme/two-language/
three-size layout assertions.

## Shared core regression

No scheduling, CPM, float, calendar, leveling, EVM or cost code was changed. The 4707-passing
Python suite includes the shared-core tests; the only failures are the Windows path/`resource`
issues above. The new code reads scheduling values only through existing repositories and the
Activity Master contract.

## Commands used to start the preview

```bash
PYTHONPATH=src py -3 -m construction_pm.preview \
  --web-root apps/web \
  --database .preview/v30-attachments.sqlite3 \
  --port 4200 --reset
```

Server log: `.preview/v30-server.log` (not committed). The port was stopped after the runs.
