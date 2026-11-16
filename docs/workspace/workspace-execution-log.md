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

## 2026-11-03 — Restore the canonical visual workspace as the default login destination

**Root cause found by comparing the accepted entry-flow decision with the deployed `main` source:**
- The accepted product flow is **Home → Login → Visual Project Workspace → Sign out → Home**.
- The public Pages assembly already passed `/app?project=preview-rps-01` to the hosted login form, but direct login/session recovery could fall back to bare `/app`.
- The route selector in `workspace-visual-demo-route.ts` only selected the visual shell when the preview project ID was explicitly present. Bare `/app` therefore fell through to the API/live workspace.
- The session-recovery action in `main.ts` also appended `view=live` to any remembered project, including the selected preview project. This explicitly bypassed the visual shell.
- The previous recovery change existed only on the unmerged visual-audit branch, so it did not repair the published `main` route.

**Correction committed to `main`:**
- Bare `/app` (including locale-only query strings) now opens the visual workspace by default.
- Explicit `view=live` continues to open the API-backed workspace; an explicitly selected non-preview project remains live.
- Session-recovery routing now sends no-project and preview-project sessions to `/app?project=preview-rps-01`.
- Regression tests cover bare `/app`, locale-only query, preview ID, explicit live mode, explicit project mode, and session-recovery destinations.
- The same default-route correction was mirrored to the visual-audit branch. The independent Tracking Details-tab gap found by its CI run was also implemented with page-specific Projects, Layout, Data, Profiles, Variance and History tabs.

**Required verification:** GitHub Pages deployment and hosted browser journey must be checked after the main-branch workflow completes. Do not claim the hosted page is fixed until Home → Login → visual shell and Sign out → Home are confirmed in the deployed site.

## 2026-11-15 — Activity window acceptance and V26 traceability

Audited against the real `main` head `bbacdaa0` and the bundle the preview
actually serves, not the TypeScript sources. 28 browser suites, 351/351 numeric
checks, 249 screenshots, zero uncaught exceptions and zero API 5xx; the only
console line is the deliberate `WBS_HIERARCHY_CYCLE` refusal. Evidence bundle:
`docs/workspace/evidence/activity-window-v26-2026-11-15/`, with per-surface
Version 26 topic titles, live Help URLs and real 303-page guide pages in
`v26-traceability.md`; the 815-page PDF remains **MISSING / VERIFY**.

One product defect fixed: `positionMenu` sent a tall context menu to the
top-left corner instead of clamping next to the pointer. Two test scopes were
corrected without weakening a threshold: the toolbar suite now measures the
command icon instead of a grip glyph, and the relationship-drawing gesture
scrolls both endpoint rows into the Gantt pane before dragging.

Continuation point: the Activity window is accepted; the next units are WBS,
toolbars, project windows, calendars, resources, Baseline and the remaining
main-environment sections. The Activity window evidence is not merged yet.

## 2026-11-15 — WBS delete reassignment branch

The V26 delete prompt's second branch now exists: deleting a leaf that still has
activity assignments can move those assignments to its WBS parent and delete the
element atomically, through `activity_action=reassign_to_parent` on
`DELETE /p6/wbs/{id}`. Children still block the delete and the cascade branch
stays unavailable until an audited activity-delete capability exists. Browser
suite `wbs-cut-copy-paste-v26` grew from 24 to 29 checks with scenario `05b`,
which creates a leaf and an assigned activity, deletes through the new branch and
reads the activity on the parent. Tested code `e820a008`; evidence in
`docs/workspace/evidence/wbs-003-cut-copy-paste-2026-11-15/`.

Continuation point after merge: toolbars, project windows, calendars, resources,
Baseline and the remaining main-environment sections.

### 2026-11-15 — Calendars base-calendar inheritance (CAL-003, `fd3ff6e9`)

The V26 project-calendar dialog exposes "Inherit Holidays and Exceptions from
Global Calendar". `P6CalendarAPI.update` stored whatever reference the client
sent without validation while `create` checked the base inline. One
`_resolve_base_calendar` helper now validates both: complete pair, stored
master, matching kind, stored snapshot, no self-reference and no cycle back to
the edited calendar. The General tab renders `data-calendar-base` over
same-kind stored calendars with an explicit "Do not inherit" option; the
payload keeps the stored pair when omitted and clears it on `null`.

Evidence: `docs/workspace/evidence/calendars-v26-2026-11-15/` — 9/9 + 5/5 +
6/6 scenarios (calendars, jalali, usage), 20 screenshots, zero
exceptions/console errors/API 5xx at `fd3ff6e9`. Full gates: 4335 Python
passed (204 skipped), 1166 + 15 web tests, clean typecheck/build.

Continuation point after merge: the same Help topic's month-year grid,
recurring exceptions and weekday-column bulk change; then resources, Baseline
and the remaining main-environment sections.

### 2026-11-15 — Calendars month grid (CAL-002, `244d7aed`)

The V26 project calendar dialog is a month-year grid: click a date then
Nonwork or Standard, click a weekday's column label to apply the change to
every instance in the month. CUBI only had a workweek table and an exception
list. A new Calendar Month tab now renders the month in Gregorian or Jalali
over the stored snapshot and exceptions, writes a nonwork exception for
Nonwork, deletes a stored exception for Standard, and applies the last chosen
action to every visible instance of a weekday from its heading. The pure
helpers (`calendarWeekday`, `calendarMonthAnchor`, `shiftCalendarMonth`,
`buildCalendarMonth`) are unit tested, including Aban 1405 and year-boundary
navigation.

Evidence: `docs/workspace/evidence/calendars-v26-2026-11-15/summary-month-grid.md`
— 10/10 + 6/6 + 6/6 scenarios, 24 screenshots, zero exceptions/console
errors/API 5xx at `244d7aed`. Gates: 1168 + 15 web tests, clean typecheck and
build.

Continuation point after merge: recurring exceptions and the Time Periods
dialog from the same Help topic; then resources, Baseline and the remaining
main-environment sections.

### 2026-11-16 — P0 scheduling core baseline and exact hot-path optimizations (`d764c81d`)

Issue #1992. P0-A..P0-D executed against the reference engine at `e0285036`:
deterministic heap topological ordering for both CPM paths, bounded search for
Time-Aware Free Float, and a demand index/ledger for forward resource leveling.
Every benchmarked case keeps a byte-identical canonical result hash; the
pre-change float scan and list ordering remain in the tree as differential
oracles. Measured on this 4-CPU/8-GB Python 3.12 host: time-aware 100k DAG
165.3 -> 68.2 s, date wide 100k 3.64 -> 3.04 s, date fan 25k 5.94 -> 3.01 s,
float-stress slack 80 7.76 -> 0.21 s, leveling 250 161.2 -> 18.5 s.

Evidence: `docs/workspace/evidence/p0-scheduling-core-2026-11-16/`. Gates:
4,449 Python tests passed (204 skipped). No worker, queue, single-flight or
PostgreSQL concurrency claim is made; those phases are not implemented.

Continuation point after merge: P0-E count and reduce provably identical CPM
work in leveling orchestration, keeping final CPM and final resource-load
validation authoritative; then P0-F durable scheduling jobs.
