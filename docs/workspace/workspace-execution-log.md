# CUBI Workspace Execution Log

Required by the workspace execution order. Update after every merged unit. The GitHub merge commit is the durable source of truth; this file records the exact continuation point.

## Current programme

Goal: a professional CUBI project-controls workspace with desktop-tool structure — menu bar, toolbars, window tabs, resizable layouts, Activity table + Gantt + Activity Details, WBS-default grouping, saved layouts, and a complete project-creation flow from business domain to schedule.

Scope guard: authenticated workspace and project-management surfaces only. Public homepage, pricing, SEO and marketing pages are untouched.

## Status by phase

| Phase | Description | Status |
| --- | --- | --- |
| 1 | Oracle P6 Professional v26 documentation review | Completed 2026-10-30; evidence in `reference/oracle-p6-reference-index.md` |
| 2 | Visual/workspace analysis | Completed 2026-10-30; screenshot comparison in `visual-qa-report.md` |
| 3 | Blueprint documents | Completed in this unit (`docs/workspace/**`) |
| 4 | Workspace shell implementation | Visual shell complete in preview (21 windows, 36 dialogs, 43 screenshots); technical wiring not started |
| 5 | Project creation flow | Partial (name/description/start/date system only) |
| 6 | Menu/window functionality | Visual destinations complete in demo mode; real commands pending visual approval |
| 7 | Technical wiring | Existing APIs preserved; new wiring not started (by design) |
| 8 | Responsive/multilingual | fa/en + RTL verified in the visual demo at 1366/1440/1920; real-data responsive work pending |
| 9 | Quality control | 422 TS + 13 preview + 13 Python tests pass; full preview E2E (80 checks) green; exhaustive visual audit; merged in #1653 (main CI 11/11) |
| 10 | GitHub delivery | This docs unit follows implement → test → commit → PR → CI → merge |

## Unit history

| Unit | Branch / PR | Merge SHA | Tests / evidence |
| --- | --- | --- | --- |
| Preview brand-asset 404 (logo/favicon) | `fix/preview-brand-asset-fallback` / #1650 | `45411b7` | `pytest tests/test_preview_runtime.py` 13 passed; PR CI 7/7; main CI 8/8; live 200 for `/`, `/fa/`, logo, favicon |
| Workspace blueprint | `docs/workspace-p6-blueprint` / #1651 | `8bdb4e2` | Docs only; PR CI 7/7; main CI 8/8 |
| Unit A — desktop shell | `feat/workspace-desktop-shell` / #1652 | `7abc29a` | `workspace-windows` (6) + `workspace-desktop-shell` (6) tests; `tsc --noEmit` clean; 422 + 13 tests pass; live preview verified tabs/commands/persistence |
| Visual shell (demo) | `feat/workspace-visual-shell` / #1653 | `5d509c7` | 43 screenshots + `visual-audit.json`: 21/21 windows, 36/36 dialogs, 121 commands, 17/17 detail tabs, 0 errors; 422 TS + 13 preview + 13 Python tests pass; preview E2E 80/80; PR CI 8/8 on `b6f7a9d`; main CI 11/11 on `5d509c7`; `tsc --noEmit` and build clean; styles byte-identical |

## Visual preview route handoff (2026-10-31)

- The shared hosted preview URL `/app?project=preview-rps-01` opens the 21-window visual workspace shell directly after login.
- This is a clearly labelled visual sample surface; it is not the persisted project data or a scheduling calculation.
- The authenticated data-backed workspace remains available at `/app?project=preview-rps-01&view=live`; leaving the visual shell selects that live route.
- Browser E2E now covers both directions: canonical deep link → visual shell, then Return to workspace → live project grid.

## Exact continuation point

Visual shell status (2026-10-30): every menu, submenu, toolbar button, window, dialog, detail tab, timescale and layout option opens a real visual destination in the local preview; see `visual-qa-report.md` and `screenshots/visual/`. Formula, API and database wiring has deliberately **not** started and must wait for visual approval.

After Unit A (desktop shell) merged:

1. **Unit A — Workspace shell** (done): menu bar with 8 groups, command registry, main toolbar, window tabs, window open/close persistence; every command opens a real surface or is disabled with a localized reason.
2. **Unit B — Activities window**: Activity Details tabs (General, Status, Resources, Predecessors, Successors, Summary), splitter-based layout, tab choice persistence; wire to existing activity/relationship/assignment APIs.
3. **Unit C — Layout dialogs**: Columns, Filters, Group and Sort, Timescale, Layout Manager against the existing layout API; WBS default enforced.
4. **Unit D — Project creation**: Business Domain → Identity (ID) → Configuration (calendar/organisation) → Development (WBS/activities seed), revision-safe and tested end to end.
5. **Unit E — Network/Trace Logic and baselines**: independent views and baseline UI over existing persistence.

Do not start Unit B before Unit A is merged and its E2E is green on main.

## Guardrails

- Never claim an unimplemented command works. Disabled commands must state the missing capability.
- Never weaken or delete tests to make CI green.
- Never commit secrets, tokens or customer data.
- Never bypass protected branches; merge only through PR with green CI on the exact SHA.
- Keep schedule calculations in the Shared Domain/Calculation Core; the workspace never computes them.
- Preserve the required settings: `{duration: working-day, calendar: jalali-gregorian, lag: working, constraints: hybrid, mode: both}`.

## Decision log

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-10-30 | Reference is desktop Professional v26, not EPPM | Edition boundary; EPPM-only commands retired |
| 2026-10-30 | CUBI keeps 8 top-level menus but renames Enterprise→Organization and Admin→Administration | Independent vocabulary; no Oracle names in UI |
| 2026-10-30 | Four persistent toolbar groups instead of 18 strips | Usability; optional toolbars can be shown |
| 2026-10-30 | Activities default grouping/sort = WBS | Required professional behaviour; matches current `activityGroupBy: "wbs"` |
| 2026-10-30 | Discussion/Feedback/Tasks tabs deferred/retired for v1 | Desktop value and edition boundary; revisit with collaboration model |
