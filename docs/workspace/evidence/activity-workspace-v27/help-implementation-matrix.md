# V27 Help-to-Implementation Matrix — Activities Workspace

- Issue #2047 · PR #2048 · Branch `feat/2047-activity-workspace-v26`
- Tested head: `b71cd61f46ebe358d1b15eee21068977b03493cf`
- Reference status: HTML Help returns 403; supplied PDF missing (see `help-topic-inventory.md`).
  "Help coverage" below means the topic is represented in the project crosswalk,
  not that today's fetch succeeded.

Statuses: **مطابق و تأییدشده** · **پیاده‌سازی‌شده ولی آزمون‌نشده** · **ناقص** ·
**غایب** · **محدودیت مستند و مشخص** · **VERIFY** · **BLOCKED**

| Help area | CUBI implementation | Help coverage | Functional status | Evidence |
|---|---|---|---|---|
| Workspace anatomy, window tabs, status bar | Desktop shell, window strip, status bar, preview banner | Crosswalk: `using_main_windows.htm` | **مطابق و تأییدشده** (browser-verified) | `workspace-shell-v26` 7/7, `workspace-window-tabs-v26` 11/11, `workspace-canonical-v26` |
| Menu bar | 8 menus, 118 commands, localized labels, disabled reasons, check marks | Crosswalk: menu pages 49093–49100 | **مطابق و تأییدشده** | `toolbars-v26` 6/6, `toolbar-rails-v26`, `workspace-desktop-shell.test.ts` |
| Toolbars and icon states | 57 buttons in 11 declared families, window-aware enablement, pressed states | Crosswalk: `*_toolbar.htm` | **مطابق و تأییدشده** (visual states) | `toolbars-v26`, `toolbar-rails-v26`, responsive 11/11 |
| Keyboard shortcuts and hot keys | 24 catalog shortcuts + Alt+1…9 window binding; conflict-free matching inside text fields | Crosswalk: `use_shortcut_menus.htm` | **مطابق و تأییدشده** | `workspace-desktop-shell.test.ts`, responsive scenario 06 |
| Shortcut (context) menus | 11 context kinds: table row/header/empty/WBS band, Gantt activity/link/WBS/timescale/empty, network activity/link | Crosswalk: `use_shortcut_menus.htm` | **مطابق و تأییدشده** | `context-menus-v26`, `register-context-menus-v26` |
| Layout lifecycle | Open / Save / Save As / New / Reset / Import / Export; revision guard; viewer read-only | Crosswalk: layout pages | **مطابق و تأییدشده** with server limit: one layout per project/view | `layout-selector-v26` 15/15, `layout-trace-v26` |
| Activity Table columns | Add/remove/reorder, width, title, alignment, visibility, pin/freeze, Copy From | Crosswalk: `define_activity_table_columns.htm` | **مطابق و تأییدشده** | `activity-columns-v26` 11/11, `field-chooser-v26` 4/4 |
| Percent Complete Type column | `activity.percent_complete_type` in registry, read model and seeded layout; enum DURATION/UNITS/PHYSICAL/SCOPE | Crosswalk: activity table/details | **مطابق و تأییدشده** (new in V27) | `activity-percent-complete-v27` at `b71cd61f4` |
| Filters | Filters dialog, Any/All, typed operators, 7 built-in filters, saved custom filters, live preview, replace/highlight | Crosswalk: filter pages | **مطابق و تأییدشده** | `activity-filters-v26`, `workspace-activity-filters.test.ts` |
| Group and Sort | Ordered multi-level grouping, sort levels, WBS path/hierarchy bands, collapse/expand | Crosswalk: grouping pages | **مطابق و تأییدشده** | `activity-group-sort-v26`, `layout-selector-v26` |
| Gantt chart | Bars, milestones, summaries, critical color, progress, baseline, links, labels, data date, progress line, timescale, zoom/fit, scroll sync | Crosswalk: Gantt pages | **مطابق و تأییدشده** (visual, not pixel-level vs vendor screenshots) | `gantt-options`, `gantt-fit`, `gantt-bar-styles`, `activity-gantt-overlays`, `gantt-scroll-sync` |
| Activity Network and Trace Logic | Network view, trace logic view, navigation and preferences | Crosswalk: network/trace pages | **پیاده‌سازی‌شده ولی آزمون‌نشده** for full interaction depth | `activity-network-v26`, `activity-trace-logic-v26` |
| Usage Profile / Spreadsheet | Bottom layout usage profile and spreadsheet from stored assignment periods | Crosswalk: usage pages | **پیاده‌سازی‌شده ولی آزمون‌نشده** (no direct V27 re-run) | `activity-usage-v26` |
| Activity Details — 17 tabs | General, Status, Resources, Predecessors, Successors, Relationships, Codes, Notebook, Steps, WPs & Docs, Expenses, Issues, Risks, Summary, UDFs, Update History, Calendar (CUBI) | Crosswalk: `activity_details.htm`; customization 403 | **ناقص** overall (write gaps below) | `activity-details-v26` (17 tabs, writes, keyboard EN/FA), `activity-general-edit-v26` |
| General tab editing | Revision-guarded PATCH, six activity types, four duration types, four percent-complete types, five leveling priorities, grid/Gantt re-read after save, Persist across reload | Crosswalk: activity/edit pages | **مطابق و تأییدشده** | `activity-general-edit-v26` at `b71cd61f4` (gridRefresh true, persistence true) |
| Resources / Expenses / Issues writes (Details tabs) | Through their services with typed validation | Crosswalk partial | **مطابق و تأییدشده** for the Details write path | `activity-details-v26` write checks; unit repositories |
| Codes tab | Displays stored assignments; **no HTTP assignment route** | **VERIFY** (no Help page held) | **ناقص** — CONTRACT/API GAP | See `backend-contract-matrix.md` R4 |
| Notebook tab | Shows stored topics if present; **no persistence service** | **VERIFY** | **ناقص** — CONTRACT/API GAP | R5 |
| Steps tab | Read-only list; repository has upsert but **no write route** | **VERIFY** | **ناقص** — CONTRACT/API GAP | R6 |
| WPs & Docs tab | Read-only associations; **no per-activity link route** | **VERIFY** | **ناقص** — CONTRACT/API GAP | R7 |
| Risks tab | Read model only; no risk write contract | **VERIFY** | **ناقص** | — |
| Update History | Read-only progress history from the service | Crosswalk: progress pages | **پیاده‌سازی‌شده ولی آزمون‌نشده** | `progress-history-v26` |
| Calendar (CUBI) tab | Project calendar, Gregorian/Jalali, working week, exceptions | Crosswalk: `edit_a_project_calendar.htm` | **مطابق و تأییدشده** as a CUBI extension | `calendars-jalali-v26`, `activity-details-v26` tab render |
| Progress / Update Progress | Progress window and per-activity update | Crosswalk: progress pages | **پیاده‌سازی‌شده ولی آزمون‌نشده** | `activity-baseline-v26`, `progress-history-v26` |
| Baselines | Assign and compare baselines | Crosswalk: baseline dialogs | **پیاده‌سازی‌شده ولی آزمون‌نشده** | `activity-baseline-v26` |
| WBS window and bands | Hierarchy, status, weighted milestones, cut/copy/paste | Crosswalk: WBS pages | **مطابق و تأییدشده** | `wbs-hierarchy`, `wbs-status-milestones`, `wbs-cut-copy-paste`, `activity-wbs-band`, `activity-wbs-collapse` |
| Tables font/row | Font family/size, row height, colors, persisted | Crosswalk: font/row page | **مطابق و تأییدشده** | `activity-table-font-v26` |
| User-defined fields | UDF values read/write per subject area | Crosswalk: UDF page | **پیاده‌سازی‌شده ولی آزمون‌نشده** | `activity-udf-values-v26` |
| Localization and RTL | English and Persian, RTL geometry, localized labels and disabled reasons | Crosswalk: general | **مطابق و تأییدشده** | `workspace-responsive` scenario 10, `activity-details` keyboard RTL |
| Visual parity with vendor screenshots | Structural and token parity only; vendor figures not downloaded or reproduced | n/a | **محدودیت مستند و مشخص** | `visual-fidelity-matrix.md` |
| Reports / Admin depth | Entry points and windows exist; report authoring and admin depth out of Activity scope | Crosswalk partial | **ناقص** (out of scope for this PR) | `reports-v26`, `administration-v26` |

## Acceptance statement

No blanket "full parity" claim is made. Every **مطابق و تأییدشده** row above has
a browser or unit test executed in this environment; every gap states what is
missing and who owns it. The largest remaining functional gaps are the four
Activity Details contract gaps (Codes, Notebook, Steps, document links) and the
unavailable official Help source.
