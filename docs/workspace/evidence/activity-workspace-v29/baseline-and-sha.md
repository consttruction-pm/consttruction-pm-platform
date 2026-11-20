# V29 — Baseline, ownership and working-tree state

- Date: 2026-11-19 (Asia/Tehran working session; mission resumed from V28).
- Repository: `consttruction-pm/consttruction-pm-platform`
- Branch: `feat/2047-activity-workspace-v26`
- PR: **#2048** (OPEN, MERGEABLE at the V28 head `60d98f8f…`; continued, not duplicated)
- Issue: #2047

## Starting baseline (V28, verified before this increment)

| Ref | SHA |
|---|---|
| V28 code | `2b7d035a1fc459ea71f8563bb8e285b218aa957f` |
| V28 documentation HEAD | `60d98f8fe8f7a13ce7ad77e8f3d07bdc33f274c6` |

The branch and PR were re-read from GitHub at the start; nothing was assumed from the
V28 report. The working tree was clean before the first edit. The final tested SHA is
recorded in `final-acceptance-report.md` and in each E2E JSON (`testedCodeSha`).

## Other active PRs and shared files

| PR | State at start | Head | Relevant changed files |
|---|---|---|---|
| #1716 | OPEN, **CONFLICTING** | `a170c87a9…` | `apps/web/src/main.ts`, `workspace-view.ts`, `workspace-desktop-shell.ts`, `workspace-command-shell.ts`, both `styles.css`, `preview/server.py` |
| #1711 | OPEN | — | `workspace-desktop-shell.ts`, `workspace-engineering-shells.ts`, both `styles.css`, `preview/runtime.py`, production composition |
| #1983 | OPEN | — | `workspace-activity-details.ts`/test, `workspace-view.ts`, `workspace-issues.ts`, `workspace-risks.ts`, `workspace-thresholds.ts`, `backend_p0/workspace_read_provider.py`, issue/risk/step APIs, both `styles.css` |

Rules applied:

- No force push, no branch deletion, no history rewrite, no stashing.
- No other PR's unpublished change was reverted or replaced.
- V29 changes in shared files are **additive**: new optional constructor arguments,
  new route branches, new tab content, new commands/families, new CSS blocks.
- The step API/repository extension keeps the existing create-only `upsert` and its
  immutability test; editing uses new `replace`/`delete` methods.
- Imports in `workspace-activity-details.ts` were kept compatible with the existing
  signatures; `enhanceActivityDetails` still accepts the same four arguments.

## Files changed in this increment

Backend:

- `src/construction_pm/p6_activity_children.py` (new: Activity Codes + Notebook, SQLite)
- `src/construction_pm/p6_activity_step_api.py` (read DTO percent + write API)
- `src/construction_pm/p6_activity_step_repository.py` (replace/delete/completion)
- `src/construction_pm/http/project_lifecycle_routes.py` (child + step-write routes)
- `src/construction_pm/http/production_composition.py` (optional API plumbing)
- `src/construction_pm/preview/runtime.py` (preview composition)

Frontend:

- `apps/web/src/workspace-activity-children.ts` (new client contract + parsers)
- `apps/web/src/workspace-activity-steps.ts` (stored `percent_complete`)
- `apps/web/src/workspace-activity-details.ts` (Codes, Notebook, Steps, WPs & Docs writes)
- `apps/web/src/workspace-desktop-shell.ts` (two-step Alt dispatcher, PDF shortcut corrections)
- `apps/web/src/workspace-toolbar-registry.ts` (Move, Standard, Top Layout; Project/Reports names)
- `apps/web/e2e/activity-children-v29.mjs`, `activity-conflict-v29.mjs`,
  `activity-views-v29.mjs`, `visual-matrix-v29.mjs`
- `apps/web/styles.css`, `apps/web/public/styles.css` (Alt hint only)

Tests:

- `tests/test_p6_activity_children.py`, `tests/test_p6_activity_step_write_api.py`,
  `tests/test_activity_children_http_routes.py`
- updated `tests/test_p6_activity_step_api.py`
- updated unit tests in `workspace-activity-steps.test.ts`, `workspace-activity-details.test.ts`,
  `workspace-desktop-shell.test.ts`, `workspace-toolbar-rails.test.ts`, `workspace-view.test.ts`
