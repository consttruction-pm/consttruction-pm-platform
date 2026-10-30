# CUBI Workspace Execution Log

Required by the workspace execution order. Update after every merged unit. The GitHub merge commit is the durable source of truth; this file records the exact continuation point.

## Current programme

Goal: a professional CUBI project-controls workspace with desktop-tool structure — menu bar, toolbars, window tabs, resizable layouts, Activity table + Gantt + Activity Details, WBS-default grouping, saved layouts, and a complete project-creation flow from business domain to schedule.

Scope guard: authenticated workspace and project-management surfaces only. Public homepage, pricing, SEO and marketing pages are untouched.

## Status by phase

| Phase | Description | Status |
| --- | --- | --- |
| 1 | Oracle P6 Professional v26 documentation review | Completed 2026-10-30; evidence in `reference/oracle-p6-reference-index.md` |
| 2 | Visual/workspace analysis | Structural review completed; pixel-level screenshot comparison still open |
| 3 | Blueprint documents | Completed in this unit (`docs/workspace/**`) |
| 4 | Workspace shell implementation | In progress: Unit A (menubar, toolbar, window tabs, window persistence) merged |
| 5 | Project creation flow | Partial (name/description/start/date system only) |
| 6 | Menu/window functionality | Not started |
| 7 | Technical wiring | Existing APIs preserved; new wiring not started |
| 8 | Responsive/multilingual | Existing fa/en + Jalali/Gregorian retained; shell responsive work pending |
| 9 | Quality control | Existing suites retained; new E2E pending per unit |
| 10 | GitHub delivery | This docs unit follows implement → test → commit → PR → CI → merge |

## Unit history

| Unit | Branch / PR | Merge SHA | Tests / evidence |
| --- | --- | --- | --- |
| Preview brand-asset 404 (logo/favicon) | `fix/preview-brand-asset-fallback` / #1650 | `45411b7` | `pytest tests/test_preview_runtime.py` 13 passed; PR CI 7/7; main CI 8/8; live 200 for `/`, `/fa/`, logo, favicon |
| Workspace blueprint | `docs/workspace-p6-blueprint` / #1651 | `8bdb4e2` | Docs only; PR CI 7/7; main CI 8/8 |
| Unit A — desktop shell | `feat/workspace-desktop-shell` / pending | pending | `workspace-windows` (6) + `workspace-desktop-shell` (6) tests; `tsc --noEmit` clean; 420 + 13 tests pass; live preview verified tabs/commands/persistence |

## Exact continuation point

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
