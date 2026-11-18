# V28 Menu, Toolbar, Context-Menu and Shortcut Audit

- PDF: G57535-02, October 2026 (815 pages).
- HTML Help: HTTP 403 (BLOCKED).
- Running registry at `b3df87eb6` (HEAD when this audit started; code changes in this
  stage are uncommitted until the V28 commit).
- Status vocabulary: **مطابق و تأییدشده** · **پیاده‌سازی‌شده ولی آزمون‌نشده** · **ناقص** · **غایب** · **محدودیت مستند و مشخص** · **VERIFY/BLOCKED**.

## 1. Menu bar

| PDF fact | PDF page | CUBI state | Status |
|---|---:|---|---|
| Menu bar cannot be hidden; commands grouped in File, Edit, View, Project, Enterprise, Tools, Admin (DB-connected), Help | 25 | Same eight menus; menu bar always rendered | **مطابق و تأییدشده** |
| File: New, Open, Close All, Page Setup, Print Setup, Print Preview, Print, Import, Export, Send Project, Check In/Out, Select Portfolio, Commit, Refresh, Exit | 13–14 (hot keys), 25–… | New/Open/Layout/Properties/Import-Export/Print/Refresh/Close window | **ناقص**: Page Setup, Print Setup, Close All, separate Import/Export, Send, Check In/Out, Select Portfolio, Commit, Exit absent |
| Edit: Cut, Copy, Paste, Add, Delete, Dissolve, Assign (Resources/Roles/Activity Codes/Predecessors/Successors), Link/Unlink, Fill Down, Select All, Find/Find Next/Replace, Spell Check, User Preferences | 14 | 14 commands incl. Undo/Redo layout, Find, Link/Unlink, Fill Down/Dissolve (disabled) | **ناقص**: Add submenu, Assign submenu, Replace, Spell Check absent; clipboard/delete blocked by contract |
| View: Layout, Show on Top/Bottom, Timescale, Filter By, Group and Sort By, Progress Spotlight, Attachments, Table Font and Row, Arrange Children, Chart Box Template, Chart Font and Colors, Hint Help, Status Bar, Zoom, Expand/Collapse, Toolbars | 14–15 | 46 commands: Columns, Filters, Group/Sort, Timescale, Bars, Font/Row, Preferences, Line Numbers, zoom/fit, WBS/Gantt/Details toggles, layouts, themes, toolbar families | **ناقص**: Progress Spotlight, Attachments, Arrange Children, chart box/font, Hint Help, Status Bar toggle absent; equivalent layout/zoom/filter/group commands present |
| Project: Activities, Resource Assignments, WBS, Expenses, Work Products and Documents, Thresholds, Issues, Risks, Set Default Project | 15 | 17 commands: properties, WBS/activity add/edit, relationships, schedule, formula, assign resources/predecessors/successors, baselines, compare, progress | **ناقص**: Expenses, WPD, Thresholds, Issues, Risks, Set Default Project absent or delegated to windows |
| Enterprise: Projects, EPS, Tracking, Portfolios, Resources, Roles, OBS, Resource Codes, Project Codes, Activity Codes, Calendars, Resource Shifts, Step Templates, Cost Accounts | 15 | 7 commands: Projects, Resources, Assignments, Roles, Calendars, UDFs, Forms | **ناقص**: EPS, Tracking, Portfolios, OBS, code dictionaries, shifts, step templates, cost accounts absent |
| Tools: Schedule, Level, Apply Actuals, Update Progress, Costs, Summarize, Period Performance, Global Change, Thresholds, Issues, Reports, Publish | 15 + chapter 11 | 10 commands: Forms, Search, Preferences, Reports, CSV, Backup, Print preview, Report wizard, Language, Shortcuts | **ناقص**: schedule/level/actuals/update progress/costs/summarize/period performance/global change absent from Tools (some exist in Project) |
| Help: Help topics, About, What's New, Feedback | 15 | 2 commands: Keyboard shortcuts, About CUBI | **ناقص** (help source blocked) |

No command is counted as complete because it appears in the registry. Rows above
distinguish present-and-tested entry points from absent PDF commands.

## 2. Toolbars

PDF reference (Contents, printed page ii; chapters at printed pages 46–78) defines
**18 toolbar families**:

Action, Administrator, Assign, Bottom Layout, Dictionaries, Display, Edit,
Enterprise, Find, Layout, Move, Print, Project, Publish, Reports, Standard, Tools,
Top Layout.

CUBI implements **11 declared families / 57 buttons**: workspace, edit, layout,
view, project, activities, wbs, gantt, resources, reports, tools. The `reports`
family currently has no buttons.

| Gap | Classification | Status |
|---|---|---|
| Missing families: Action, Administrator, Assign, Bottom Layout, Dictionaries, Display, Enterprise, Find, Move, Print, Publish, Standard, Top Layout | Functional/visual gap; many commands exist in menus instead | **ناقص** |
| Button visuals: 53 distinct CUBI icons, tooltip/title, enabled/disabled with reason, hover/focus/pressed, overflow control | Implemented and verified | **مطابق و تأییدشده** (visual acceptance + toolbars suite) |
| Customize toolbar / drag icons / lock toolbars / create custom toolbar (PDF printed pages 19–22) | No customization surface | **غایب** |
| Reports family declared with no buttons | Empty by design but misleading | **ناقص** (D-V28-02) |

## 3. Context menus

| PDF fact | PDF page | CUBI state | Status |
|---|---:|---|---|
| Right-click any element or white space to open a shortcut menu | 38 | 11 context kinds: table row/header/empty/WBS band, Gantt activity/link/WBS/timescale/empty, network activity/link | **مطابق و تأییدشده** for Activities surfaces; exhaustive per-object contents not enumerated in the PDF |
| Selection-aware commands; Shift/Ctrl multi-selection | 38 | Selection-aware commands; Shift/Ctrl selection verified | **مطابق و تأییدشده** |

## 4. Keyboard

| PDF fact | PDF page | CUBI state | Status |
|---|---:|---|---|
| "Using Hot Keys" lists **two-step menu accelerators** (`Alt-F, N`, `Alt-E, T`, `Alt-V, O`, `Alt-P, A`, `Alt-N, P`, …) | 13–15 | Menu access keys (Alt+F/E/V/P/N/T/H/A) and 24 Ctrl/function shortcuts; **no two-step Alt-sequence dispatcher** | **ناقص** — D-V28-01 |
| Hot keys exist only where listed; otherwise no hot key | 13 | CUBI Ctrl catalog is an intentional CUBI convention; it must not be presented as the PDF's hot-key list | **محدودیت مستند و مشخص** |
| Grid arrows/Home/End/PageUp/PageDown/Enter, Details tablist arrows, dialog focus | 38 (selection), chapter 2 | Implemented and browser-verified | **مطابق و تأییدشده** |
| Ctrl+A, Ctrl+F, F5, F9, Shift+F9, F1, Shift+F12 | CUBI convention / PDF menu equivalents | Verified in the shell and responsive suites | **مطابق و تأییدشده** as CUBI bindings |

The two-step accelerator dispatcher is the largest keyboard gap. Implementing it
requires changes to `workspace-desktop-shell.ts` (also touched by open PRs #1716
and #1711), so it is recorded with an owner dependency instead of being edited
under an active ownership conflict.

## 5. Actions proposed for the next increment

1. Implement the two-step Alt accelerator dispatcher after #1716/#1711 merge, with a
   unit test for every listed PDF sequence.
2. Map the 18 PDF toolbar families onto CUBI toolbars; add missing families or
   explicitly mark unsupported commands unavailable.
3. Remove or populate the empty Reports family.
4. Add Page Setup / Print Setup / Close All / Replace / Spell Check as either real
   commands or disabled entries with reasons.
