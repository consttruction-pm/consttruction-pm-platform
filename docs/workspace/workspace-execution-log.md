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
- Every project opened through the live bootstrap now writes `view=live` into its shareable URL; refresh and sign-in recovery preserve the real project route.
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

## Binding visual-audit continuation rule

All subsequent visual work must follow [`reference/visual-audit-governing-principles.md`](reference/visual-audit-governing-principles.md). Record each page/window/menu/dialog/chart separately in GitHub with its Version 26 source, exact gaps, implementation paths, changes, tests, screenshot evidence, commit SHA and status. Do not report or mark a page complete from a catalogue or passing text test alone. Gantt and chart colour/style controls and their rendered effects are required in the current phase; only final CUBI-wide theme harmonization is deferred. Keep the PR unmerged while any required audit item is unverified or CI is failing.


## 2026-11-03 — Continued page-by-page visual correction (PR #1698)

| Page/window/component | Version 26 source | Subcomponents | Appearance / defaults vs options | CUBI implementation | Gaps and changes | Verification | Visual evidence | Commit | Status |
|---|---|---|---|---|---|---|---|---|---|
| Global menu nested commands | Menu Bar / Edit Menu / context-sensitive command enablement | Nested submenu items, Delete command, disabled reason and keyboard semantics | Disabled state must be explicit when no live selection/permission check exists; reason text accompanies disabled action | apps/web/src/workspace-visual-demo.ts → renderMenus / MENUS | Fixed nested submenu renderer so child actions with a reason are rendered disabled and expose the reason, matching top-level menu behavior. | Regression covered by Workspace menu hierarchy exposes project, organization, tools and administration commands; exact-head CI pending after this update. | Browser screenshot not yet captured; do not mark Verified. | 9032a1b1f772ef224e506ec55c2d6b406bfe5f1e | Implemented-unverified |
| Module register Details pane | Main Windows / Details pane configuration; page-specific Details inventories in the governing master audit | Resources, Roles, Calendars, Documents, Expenses, Thresholds, Issues, Risks, Reports, Tracking, Cost & Financial Control, Progress & Field Control, Procurement, Changes & Claims, Organization and Comments | Each page uses its own tab inventory; tab labels localize and the selected-record identity remains in the pane header. Generic fallback remains only for windows without a dedicated inventory. | apps/web/src/workspace-visual-demo.ts → renderTableWindow / pageDetailTabs | Replaced the five-tab generic strip on mapped module pages with page-specific tabs for dates, rates, shifts, cash flow, EVM, physical progress, delivery, entitlement, evidence, history and other required sections. These remain visual previews; record-specific service binding and persistence are not claimed. | Added English coverage across 12 page families and Persian RTL assertions in workspace-visual-demo.test.ts; exact-head CI pending. | Browser screenshots at desktop and compact widths not yet captured; status remains Implemented-unverified. | 7acf8f7638a18efb5dba7788c1a5afb24ff8d633 | Implemented-unverified |

| 2026-11-03 | Workspace menu availability correction | Reversed the incorrect rule that disabled every menu command carrying a "reason". All reference menu entries now remain visible and selectable for visual-shell inventory/audit; unconnected commands are marked "Preview only" with the reason in the tooltip, rather than removed or disabled. Context-sensitive disabled controls (for example destructive context-menu actions without a selection) remain governed separately. | `apps/web/src/workspace-visual-demo.ts`; `apps/web/src/workspace-visual-demo.test.ts` | Added assertions that preview-only menu entries retain `data-vd-action`, display the preview note, and are not disabled. Runtime test/CI and screenshot verification pending. | Implemented-unverified |

| 2026-11-03 | Superseding correction — menu option visibility and disabled semantics | Corrected the earlier over-broad disabled rule. All commands remain rendered in their menu/submenu. A command is disabled only when its action explicitly declares `disabled: true` for a context condition; that item remains visible with native disabled semantics and an explanatory reason. A `reason` by itself means preview-only/unwired and must never disable or hide the command. | `apps/web/src/workspace-visual-demo.ts`; `apps/web/src/workspace-visual-demo.test.ts` | Added explicit disabled state for context-dependent Delete, Link/Unlink, Fill Down, Find Next and Launch; added assertions separating disabled state from preview-only metadata. Exact-head CI and browser screenshot verification still required. | Implemented-unverified |
