# Activity Workspace — Version 26 Surface Inventory and Verification

Issue #2047 · PR #2048 · branch `feat/2047-activity-workspace-v26`
Verified code head: `f96478f` (working tree: evidence files generated after the commit).
Environment: Hasan's Qoder Desktop on Windows, local full-stack preview
(`construction_pm.preview`, real WSGI API, SQLite repositories, Shared Domain core).

Official reference: the Oracle HTML Help host returns **HTTP 403** from this
network (`docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm` and the two
Version 26 product index pages). Topic names below are the ones already carried by
the acceptance matrix from earlier verified crosswalks; they are not re-fetched in
this run. The approximately 815-page PDF remains **MISSING / VERIFY**.
The earlier crosswalk `docs/workspace/architecture/v26-window-traceability-and-acceptance-matrix.md`
already records **88 distinct official Help topic pages** for the Activity window,
table, Gantt, layouts, filters, grouping and dialogs; this inventory maps the
running surfaces to those topics rather than inventing new URLs.

The browser language is pinned to `en-US` in the shared harness so English
assertions are deterministic on a Persian-locale Windows host. Persian RTL
scenarios opt in through `cubi:workspace-locale=fa`.

## 1. Windows, panes and shell

| Surface | Implementation surface | Verified by |
|---|---|---|
| Activities window with window tabs | `workspace-desktop-shell.ts`, `workspace-view.ts` | `workspace-canonical-v26`, `workspace-shell-v26`, `activity-details-v26` |
| Activity Table | `#cp-activity-grid`, read model cells | `activity-columns-v26`, `activity-scope-v26`, `activity-table-font-v26` |
| Gantt chart | `#cp-gantt`, stored schedule facts only | `gantt-bar-styles-v26`, `activity-gantt-overlays-v26`, `gantt-scroll-sync-v26` |
| Activity Details pane | `workspace-activity-details.ts` | `activity-details-v26`, `activity-general-edit-v26` |
| Left module rail and right rail | P6-style shell | `toolbar-rails-v26`, `workspace-shell-v26` |
| Status bar / preview banner | `workspace-desktop-shell.ts`, preview server | `workspace-shell-v26` |
| Window switching / closing | `workspace-windows.ts`, desktop shell | `workspace-canonical-v26`, `workspace-window-tabs-v26` (reorder + reload persistence) |
| Pane split and responsive geometry | `styles.css` (shared) | `workspace-responsive-v26` — **1280×720 fails**, see §9 |

## 2. Main menu bar

Every menu item is a command, a window selector, or carries a localized disabled
reason; nothing is decorative. Counts below are produced from
`getDesktopMenus` with full capabilities and include separators excluded.

| Menu | Commands | Unavailable with reason | Notable groups |
|---|---:|---:|---|
| File | 10 | 0 | New/Open project, Open/Save/Save As layout, Project properties, Import/Export, Print, Refresh, Close window |
| Edit | 14 | 6 | Undo/Redo layout, clipboard (unavailable), Find, Group by WBS, reverse sort, Select All, Link, Unlink, Fill Down/Dissolve (unavailable) |
| View | 46 | 0 | Columns, Filters, Group and Sort, Timescale, Bars, Font/Row, User Preferences, Line Numbers, expand/collapse, zoom/fit, WBS/Gantt/Details toggles, top/bottom layout, 6 themes, toolbar-family toggles, open-window list |
| Project | 17 | 5 | Properties, Add WBS/activity, Edit activity, Relationships, Schedule (F9), options, formula, reference, assign resources/predecessors/successors, leveling/baselines/compare/progress (unavailable) |
| Enterprise | 7 | 1 | Projects, Resources, Assignments, Roles, Calendars, UDFs (unavailable), Forms & Workflows |
| Tools | 10 | 1 | Forms, Search, Preferences, Reports, CSV import/export, Backup, Print preview, Report wizard (unavailable), Language, Shortcuts |
| Admin (role-gated) | 12 | 4 | Settings, Preferences, Language, Calendar display, Users/Security/Currencies/Audit (unavailable), Permission matrix, Categories, Financial periods, Recovery |
| Help | 2 | 0 | Keyboard shortcuts (F1), About CUBI Workspace |

Verification: `workspace-desktop-shell.test.ts` (menu labels in EN/FA, shortcut
uniqueness/executability, one window-tab strip), `toolbars-v26`,
`toolbar-rails-v26`, `workspace-canonical-v26`, `activity-scope-v26` (menus stay in
the viewport at 1280/1366/1920, RTL included).

## 3. Toolbars

57 toolbar buttons in 11 families (`workspace`, `edit`, `layout`, `view`,
`project`, `activities`, `wbs`, `gantt`, `resources`, `reports`, `tools`), 7 of
which state a missing service instead of pretending to run. Family visibility is
window-aware; the View menu can hide/show each family. The approved Activity/Gantt
split is untouched; the obsolete 53.5% layout is not present.

Verification: `toolbar-rails-v26`, `toolbars-v26`, `workspace-responsive-v26`
(toolbar navigation and compact mode; the suite aborts at the 1280×720 geometry
assertion before the later viewports).

## 4. Context menus

Eleven context kinds resolve commands from the selected object and selection
state: table activity, table header, empty table, table WBS band, Gantt activity,
Gantt link, network activity, network link, Gantt WBS band, Gantt timescale and
empty Gantt. Commands route to the same registry as menus; destructive commands
confirm; unavailable commands explain why.

Verification: `context-menus-v26` (keyboard invocation, dismissal, per-surface
command sets), `register-context-menus-v26` (project register surfaces),
`activity-relationships-v26` (link context actions).

## 5. Dialogs and selectors

| Dialog | State | Verification |
|---|---|---|
| Columns (available/selected, subject filter, add/remove all, width, title, alignment, visibility, pin/freeze, Copy From) | Implemented on the layout API | `activity-columns-v26` (11 scenarios) |
| Filters (categories, Any/All, rows, operators, typed values, replace/highlight, preview, apply, clear) | Implemented | `activity-filters-v26` |
| Group and Sort (ordered group levels, sort levels, WBS bands) | Implemented | `activity-group-sort-v26`, `layout-selector-v26` |
| Timescale / zoom / fit | Implemented | `gantt-options-v26`, `gantt-fit-v26` |
| Bar Styles and bar filters | Implemented | `gantt-bar-styles-v26` |
| Table Font and Row | Implemented | `activity-table-font-v26` |
| User Preferences | Implemented (presentation, persisted) | `workspace-desktop-shell.test.ts`, `toolbars-v26` |
| Layout selector (open/rename/export/import, dirty state, Save) | Implemented; viewer is read-only | `layout-selector-v26` (15 scenarios) |
| Collapse To | Implemented | `activity-wbs-collapse-v26` |
| Activity create / edit (General editor) | Implemented with revision guard | `activity-general-edit-v26`, `workspace-activity-general.test.ts` |
| Customize Activity Details tabs | Implemented, browser-local | `activity-details-v26` |
| Project properties, Import/Export, Print, Forms | Implemented panels/dialogs | `workspace-canonical-v26`, `activity-scope-v26` |
| Activity code assignment | **No HTTP contract** | blocked, see §9 |
| Notebook persistence, step writes, per-activity document assignment | **No HTTP contract** | blocked, see §9 |

## 6. Activity Details tabs

All 17 tabs render (16 official + CUBI Calendar). General editing is
revision-guarded; Resources, Expenses and Issues write through their services;
Steps, Update History, Risks, WPs & Docs and Calendar read authoritative
services or declare the documented limitation; Codes/Notebook state the missing
contract instead of inventing values.

A cleared selection now renders one explicit state message
(`data-details-empty-state`) in the active tab instead of showing blank fields as
stored values. It is localized and adds no height beyond the active panel.

Verification: `activity-details-v26` (tabs, keyboard EN + FA, write paths,
unauthorized state, stale-response guard, customize persistence, empty selection),
`activity-general-edit-v26` (6/4/4 option catalogues, revision conflict, reload),
`activity-udf-values-v26`, `activity-usage-v26`, `activity-trace-logic-v26`.

## 7. Activity Table and Gantt

Table: columns, widths, titles, alignment, visibility, pin/freeze, sorting,
ordered grouping, WBS path bands, expand/collapse, filters, selection and
multi-selection, keyboard roving focus, scope filtering, line numbers, table font
and row density, layout persistence and viewer read-only. All cells come from the
read model; unknown values stay empty.

Gantt: bars, milestones, summary bars, critical colour, progress, baseline,
relationship arrows, labels, data date, progress line and sight lines, timescale
(day–year), zoom, fit, horizontal/vertical scrolling synchronized with the table,
selection synchronization, WBS alignment and bar styles. No second scheduling
engine exists in the browser.

Verification: `activity-columns-v26`, `activity-filters-v26`,
`activity-group-sort-v26`, `activity-wbs-band-v26`, `activity-wbs-collapse-v26`,
`activity-grid-keyboard-v26`, `activity-multi-select-v26`, `activity-scope-v26`,
`activity-scale-v26`, `activity-table-font-v26`, `activity-baseline-v26`,
`gantt-options-v26`, `gantt-fit-v26`, `gantt-bar-styles-v26`,
`activity-gantt-overlays-v26`, `gantt-scroll-sync-v26`,
`activity-relationships-v26`, `activity-network-v26`.

## 8. Keyboard, accessibility, localization

Details tablist: ArrowLeft/Right, Home/End, wrap-around, one tab in the tab order,
focus/selection/panel move together and follow the rendered direction in RTL.
Grid: arrows, Home/End, PageUp/PageDown, Enter/Space, Shift+F10 / ContextMenu,
visible focus, roving tabindex. Menus: access keys, arrow navigation, Escape,
type-ahead. Dialogs: focus handling, validation messages, cancel/confirm.

Persian RTL is exercised by `activity-details-v26`, `activity-filters-v26`,
`activity-group-sort-v26`, `activity-scale-v26`, `activity-wbs-collapse-v26`,
`activity-scope-v26`, `layout-selector-v26` and the General editor at 1280/1920.
Locale switching is browser-local and survives reload.

## 9. Blockers and handoffs

| ID | Classification | Evidence | Owner / next action |
|---|---|---|---|
| R1 | SHARED-FILE OWNERSHIP CONFLICT | `workspace-responsive-v26` scenario 01: at 1280×720 `#workspace` is 521px tall while `.cp-p6 .cp-p6-workspace` keeps `min-height: 540px` (`apps/web/styles.css:5446`), so a 19px workspace scroller appears. The preview banner reserves 46px; the shell chrome is 139px and the status bar 14px. | Shell owners #1716/#1711/#1983: relax the workspace floor (or reduce chrome) so 1280×720 fits. Do not change the approved split ratio. |
| R2 | SHARED-FILE OWNERSHIP CONFLICT | Grid refresh after a Details save still needs the next project read; the callback belongs to `main.ts` / `workspace-view.ts`. | Owners of #1716/#1711/#1983: call the project read after `ACTIVITY_GENERAL_SAVED`. |
| R3 | READ-MODEL GAP | `activity.percent_complete_type` is absent from `workspace_read_provider.py`; the General editor shows it from the Activity Master record only. | #1983: add the cell to the read model, then a table column and test. |
| R4 | CONTRACT/API GAP | No HTTP assignment route for Activity Codes. | Platform: define assign/remove endpoints with revision guard. |
| R5 | CONTRACT/API GAP | No persisted Notebook topic service; the Comments rail is browser-local. | Platform: define notebook topic CRUD. |
| R6 | CONTRACT/API GAP | No write route for Steps. | Platform: define step create/update/delete. |
| R7 | CONTRACT/API GAP | No per-activity document assignment route. | Platform: define the link contract. |
| R8 | OFFICIAL REFERENCE UNAVAILABLE | Oracle Help returns 403 in this environment; PDF missing. | Supply the PDF or allow Help access; no invented topic URLs. |

## 10. Test execution record

All commands below ran in Qoder against `f96478f` with a fresh preview database
per suite (`--database .preview/e2e-<suite>.sqlite3`).

| Command | Result |
|---|---|
| `npm run typecheck` | 0 errors |
| `npm run build` | success |
| `npm test` | 1178 source + 15 preview-server tests passed, 0 failed |
| `pytest tests/backend_p0/test_workspace_read*.py tests/contracts/test_workspace_control_room_read_contract.py tests/test_preview_runtime.py tests/test_activity_master_repository.py tests/test_activity_validation.py` | 99 passed |
| Activity V26 browser suites (21 listed in the master order) | All passed |
| `activities-v26-scenarios`, `wbs-hierarchy`, `wbs-status-milestones`, `wbs-cut-copy-paste`, `layout-trace`, `workspace-window-tabs`, `workspace-visual-acceptance` | All passed |
| Shell/menu/dialog suites (`toolbars`, `toolbar-rails`, `context-menus`, `register-context-menus`, `workspace-canonical`, `workspace-shell`, `layout-selector`) | All passed |
| `workspace-responsive-v26` | Failed at scenario 01 (R1); later viewports not reached |

Per-suite evidence JSON and screenshots are under the sibling
`*-v26-2026-11-18` directories.
