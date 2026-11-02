# CUBI Visual Workspace Master Audit

Scope: visual shell only. API, persistence, calculation logic and service wiring are out of scope until the visual design is complete.

CUBI must expose the full professional project-controls desktop workspace: complete menu bar, nested menus, toolbars, window tabs, left navigation tree, contextual command bars, layout options and page-specific Details tabs. CUBI additions are additive and must never displace baseline functions. All visible but unwired commands must be marked visual-only/disabled and must not claim success or invent data. Customer-facing UI/help must use CUBI vocabulary and branding only.

## Persistent shell
1. App identity/status strip: CUBI, project, revision, user, connection/sync, language, calendar display, theme.
2. Menu bar: Workspace, Edit, View, Project, Organization, Tools, Administration, Help.
3. Main toolbar groups: Standard, Project, Layout, Schedule, Selection/Navigation, CUBI Tools.
4. Breadcrumb/context: Business Domain > optional Portfolio > Project > active window, revision and Data Date.
5. Window tabs: global and project windows, active/dirty state, close, reorder, keyboard cycling and tab groups.
6. Work area: collapsible left tree, central page, contextual Details pane, adjustable splitters.
7. Layout bar: layout, view, filter, group/sort, columns, timescale and bars.
8. Status bar: project, Data Date, baseline, layout, filter, selected count, user/role, save/sync and help.

## Menu catalogue
- Workspace: New/Open/Close Project, Close All, Save/Save All, Recent Projects, Import/Export, Print Preview, Page Setup, Print, Project Backup/Restore, Workspace Backup/Restore, Recovery, Sign Out, Exit.
- Edit: Undo/Redo/History, Cut/Copy/Paste/Paste Special, Fill Down/Across, Add Project/WBS/Activity/Relationship/Resource/Role/Assignment/Expense/Document/Issue/Risk/Threshold/Form, Edit/Delete/Duplicate, Dissolve Activity, Link/Unlink, Assign Resources/Roles/Codes/Predecessors/Successors/Documents, Renumber IDs, Global Change, Find/Replace, Select All, Preferences.
- View: Layout New/Open/Save/Save As/Import/Export; Show on Top Table/Gantt/Network/Chart/Usage Spreadsheet/Profile; Show on Bottom Details/Usage Profiles/Trace Logic/None; Bottom Layout Options; Columns; Filters; Group and Sort; Timescale; Bars; Bar Chart Options; Progress Line/Spotlight; Attachments; Line Numbers; Critical Path; Check Schedule; Font/Row; Chart Colors/Templates; Arrange/Align Children; Zoom; Expand/Collapse; Toolbars; Tab Groups; Tile; Full Screen; Theme.
- Project: Activities, Additional Activities View, WBS, Resource Assignments, Assign/Maintain Baselines, Expenses, Work Products & Documents, Thresholds, Issues, Risks, Set Default Project, Project Details, Codes, Defaults, Notebook, Calendars, UDFs.
- Organization: Projects/Business Domains, Portfolios, Responsibility Structure, Resources, Roles, Global/Project/Resource Calendars, Workweeks/Hours/Exceptions/Holidays, Project/Activity/Resource/Role Codes, UDFs, Resource Curves/Shifts, Cost Accounts, Funding Sources, Currencies, Financial Periods.
- Tools: Schedule, Level Resources, Apply Actuals, Update Progress, Recalculate Assignment Costs, Summarize, Store Period Performance, Global Change, Monitor Thresholds, Issue Navigator, Reports/Groups/Batches/Designer/Preview/Distribution, Form Builder, Smart Guide, Engineering Assistant, Search, Quality Checks, Import Validation.
- Administration: Users, Teams, Access/Security Profiles, Permissions, Preferences, Categories, Currencies, Financial Periods, System Defaults, Audit Log, Retention/Recovery.
- Help: Workspace Guide, Context Help, Shortcuts, What's New, Documentation Library, About CUBI.

## Page and Details inventory
| Window | Main view | Required Details tabs |
|---|---|---|
| Projects | Business Domain/Portfolio/Project tree + register/table/chart/Gantt | General, Dates, Defaults, Resources, Settings, Codes, Notebook, Budget Log, Spending Plan, Budget Summary, Funding, Baselines, Documents, History, UDFs |
| Activities | Table/Gantt, Activity Network, usage spreadsheets | General, Status, Resources, Predecessors, Successors, Relationships, Codes, Notebook, Steps, WPs & Docs, Expenses, Issues, Risks, Summary, UDFs, Update History |
| WBS | WBS table/chart | General, Status, Resources, Earned Value, WPs & Docs, Notebook, Issues, Risks, UDFs, History |
| Resource Assignments | Assignment table grouped by resource/activity, usage profile | General, Activity, Resource, Units & Costs, Dates, Curves, Notes, History |
| Resources | Resource hierarchy/chart/usage | General, Details, Units & Prices, Roles, Codes, Calendars, Shifts, Curves, UDFs, Notebook, History |
| Roles | Role hierarchy/rates | General, Resources, Price/Unit Rates, Limits, Codes, UDFs, History |
| Calendars | Calendar list + workweek/hour editor | General, Workweek, Work Hours, Exceptions/Holidays, Assignments, Resource Use, History |
| Documents | Document register | General, File Locations, Assignments, WBS Links, Activity Links, Revisions, History |
| Expenses | Expense register | General, Activity, Cost, Dates, Accrual, Category, Documents, History |
| Thresholds | Threshold register/monitor | General, Parameters, WBS/Activity Assignments, Monitoring, History |
| Issues | Issue register | General, Status, Priority, Responsible, Activity/WBS Links, Notebook, Documents, History |
| Risks | Risk register/probability-impact chart | General, Probability & Impact, Response, Owners, Schedule Impact, Cost Impact, WBS/Activity Links, Documents, History |
| Reports | Catalog/groups/batches/run/preview | Definition, Parameters, Data Scope, Preview, Distribution, Run History |
| Tracking | Tracking layouts/profiles | Projects, Layout, Data, Profiles, Variance, History |
| Form Builder (CUBI) | Designer canvas, field palette, properties | Form, Header, Fields, Validation, Conditional Logic, Workflow, Permissions, Library, Version, Preview, History |
| Cost & Financial Control (CUBI) | Cost register/cash flow/forecast | General, Budget, Actual Cost, Commitments, Forecast, Cash Flow, EVM, Funding, Change/Claim Links, Documents, History |
| Progress & Field Control (CUBI) | Period progress/field records | General, Status, Quantities, Physical Progress, Daily Reports, Labour, Equipment, Evidence, Approvals, History |
| Procurement (CUBI) | Procurement register | General, Supplier, Package, Quantities, Dates, Cost, Delivery, Activity/WBS Links, Documents, History |
| Changes & Claims (CUBI) | Notices/change/claims/impact | General, Notice, Change, Entitlement, Schedule Impact, Cost Impact, Decision, Evidence, Correspondence, History |

The Details pane title identifies the object and record. With no selection it shows page-level context. It changes with the active window and selected record, preserves a valid selected tab, and never leaks stale details from another page. Tab order/visibility are configurable per window/layout.

## Contextual command bars
Each page has its own horizontal contextual bar below the global toolbar; the right-edge CUBI Add (+) bar remains separate and never overlays data. Shared commands: Add, Open, Edit, Delete, Duplicate, Copy/Paste, Save/Cancel, Undo/Redo, Refresh, Assign, Link/Unlink, Move, Indent/Outdent, Filter, Group, Sort, Columns, Layout, Export, Print, Details, Help, More. Page-specific commands include baseline/schedule/trace logic for Activities; child/sibling/milestones for WBS; roles/rates/shifts/curves for Resources; usage/spreads for Assignments; workweek/exceptions for Calendars; upload/link/version/launch for Documents; accrual/cash-flow for Expenses/Cost; owner/response/monitor for Issues/Risks/Thresholds; run/preview/distribute for Reports; and field/rule/workflow/preview/version for Form Builder.

## Left navigation
Current Project: Activities, WBS, Resource Assignments, Expenses, Documents, Issues, Risks, Thresholds, Baselines, Cost, Progress, Procurement, Changes & Claims, Forms.
Organization: Projects/Business Domains, Portfolios, Resources, Roles, Calendars, Codes, UDFs, Cost Accounts, Funding Sources, Resource Curves.
Insights: Reports, Tracking, Dashboards, Smart Guide.
Administration: Users, Teams, Security, Preferences, Audit.
Workspace: Recent Windows, Saved Layouts, Form Libraries, Appearance.

## CUBI-only additions
Form Builder has two distinct libraries: Organization Form Library (reusable governed templates) and Project Form Library (project-specific forms and tailored versions). Form headers support JPG/PNG, including transparent PNG. It also includes sections, fields, validation, conditional logic, workflow, approval, preview and version history. Other additive areas: Engineering Intelligence Assistant, daily field reports, labour/equipment, inspections, quality/NCR, safety, punch/closeout, procurement/materials, notices/changes/claims, Theme Manager and contextual Add (+).

## Completion evidence
The shell is complete only after running-app proof that all menus/submenus open and are keyboard accessible; every window opens as a tab; each page has its own Details tabs and contextual bar; table/Gantt/network/chart/profile/spreadsheet options are present; layout dialogs are complete; English/Persian and LTR/RTL are tested; desktop/tablet/mobile layouts are tested; and no control falsely reports execution. A menu catalogue or static placeholder is not proof of completion.

## Internal reference set
Parity source: P6 Professional desktop Version 26 User Guide and Help, including Menu Bar, Project Menu, View Menu, Main Windows and Administration Menu:
- https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm
- https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
- https://docs.oracle.com/cd/F51303_01/client_help/en_US/menu_bar.htm
- https://docs.oracle.com/cd/F51303_01/client_help/en_US/49096.htm
- https://docs.oracle.com/cd/G48902_01/client_help/en_US/49095.htm
- https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/using_main_windows.htm
- https://docs.oracle.com/cd/G48902_01/client_help/en_US/49099.htm


## Multilingual UI and public website requirement (2026-11-02)

Supported language targets: English (en), Persian (fa), German (de), Chinese Simplified (zh), Arabic (ar), French (fr), Japanese (ja), and Korean (ko).

- Arabic is RTL. Persian remains RTL. English, German, French, Japanese, Korean and Simplified Chinese are LTR.
- The authenticated visual workspace language selector must expose all registered languages, preserve the current project, selected object, open page, layout, calendar mode and unsaved drafts when switching, and update document lang/dir, navigation, menus, command bars, Details tabs, dialogs, forms, tables, charts, reports, assistant and status bar.
- Public website must provide translated, indexable route sets for Home, Platform, Solutions, Resources, Contact and Pricing in each published language. Each route must include correct lang/dir, translated title/description/OG metadata, canonical and reciprocal hreflang links, localized navigation/footer and correct language switcher.
- A language may be registered in the workspace before its public website routes are published. Do not advertise an unavailable website route or create a dead link. Do not treat English fallback as completed translation.
- Translation packs use stable translation IDs and are verified/activated through the existing language-pack lifecycle. The visual command shell and generic UI translation helpers must resolve activated pack strings before English fallback.
- Fonts must cover Arabic/Persian shaping, French diacritics, Japanese kana/kanji, Korean Hangul and Chinese glyphs. Layouts must be checked for clipping, wrapping, line height, mixed-direction identifiers, numbers and dates.
- Acceptance: complete translation coverage report for every shipped page and workspace surface; RTL/LTR visual tests; locale-specific SEO route tests; language-switch preservation tests; screenshots for all eight languages at desktop and mobile breakpoints.


## Desktop-style visual composition and no-flat-page rule (mandatory)

The workspace is a multi-window desktop workbench, not one long web page and not a dashboard of full-width cards. The following geometry is mandatory at desktop widths:

```
┌ CUBI identity / project context / user / sync / language / theme ┐
├ Menu bar: Workspace | Edit | View | Project | Organization | Tools | Administration | Help ┤
├ Standard toolbar / Project toolbar / Layout toolbar / Schedule toolbar ┤
├ Window tabs: Projects × | Activities × | WBS × | Resources × | ... ┤
├ Project breadcrumb + Data Date + active baseline + layout name ┤
├ Navigation tree ┬ Contextual page command bar (horizontal) ┬ Right Add (+) rail ┤
│                 ├ Top layout: register/grid | chart/Gantt/network ┤
│                 ├ Bottom layout: page-specific Details tabs ┤
├ Status bar: selection count | filter | grouping | revision | save/sync | hints ┤
```

- The navigation tree is a collapsible, independently resizable left pane. It contains expandable Organization, Projects, Current Project, Resources & Calendars, Reports & Tracking, CUBI Controls, and Administration nodes. Tree expansion, selected node and width are retained per user.
- The center is a window surface. Each open window is a tab, not a stacked full-page route. Switching tabs preserves that window's layout, selection, scroll position, filter, grouping, sort, column widths and detail-tab choice. Closing a dirty window prompts Save / Discard / Cancel.
- The active window has its own page title, breadcrumb, contextual horizontal command bar, layout-options strip and content. Commands are enabled/disabled by active window, selection, permission and layout.
- The right-edge Add (+) rail is a narrow icon-only vertical strip, independent of the horizontal page command bar. It must not cover the grid, Gantt, details pane or status bar. Its contextual command opens a compact anchored menu/dialog, not a full-width page.
- Top and bottom layouts are separated by a draggable splitter. The top layout may itself split horizontally between a table/tree and a synchronized chart. Left navigation, top/bottom and table/chart splitters have minimum/maximum bounds, keyboard adjustment and reset-to-default.
- The Details area is docked below the active window's main view by default, with configurable top/bottom/left/right/hidden placement. It is not a generic full-width section appended beneath the whole site. It has a title strip, record identity, tab strip, tab content and independent scroll.
- At narrow widths, use a deliberate compact workspace mode: collapsible navigation drawer, horizontal window-tab scroller, overflow menus, and stacked top/details panes with explicit splitter/expand controls. Never shrink desktop controls into an unreadable single horizontal strip.
- No page may render every control, form and tab as one uninterrupted wide column. Use compact toolbars, tabbed dialogs, grouped property panels, anchored menus, split panes and modal/wizard flows.

## Window-specific top-layout and visual mode matrix

| Window | Primary modes | Secondary/bottom modes | Required visual controls |
|---|---|---|---|
| Projects | Project table; project bar chart; project Gantt/profile; hierarchy/register | Project Details; budget/spending profile | EPS/domain/portfolio tree, project table columns, grouping/sorting/filtering, top/bottom selectors, timescale, bars, chart labels, project defaults |
| Activities | Activity table; Gantt; Activity Network; activity usage spreadsheet | Activity Details; Resource Usage spreadsheet/profile; Trace Logic | WBS grouping, line numbers, multi-level group/sort, multi-filter, columns, bars, relationships, baseline/progress/data-date lines, critical path, timescale, zoom, row/font controls |
| WBS | WBS table/tree; WBS chart | WBS Details; earned-value/profile where applicable | hierarchy expand/collapse, indent/outdent, child/sibling, WBS code/sequence, chart style, group/sort/filter |
| Resource Assignments | Assignment table; resource usage spreadsheet; resource profile/histogram | Assignment Details; Activity/Resource details | group by resource/activity, units/time, cost/time, curves, period scale, over-allocation indicators |
| Resources | Resource hierarchy/table; resource usage/profile | Resource Details; role/rate/calendar details | resource breakdown, availability, max units/time, price/rate types, roles, calendars, shifts, curves |
| Roles | Role hierarchy/table; role rate chart | Role Details | role limits, price/unit rates, effective dates, resources using role |
| Calendars | Calendar register; workweek editor; time-scale preview | Calendar Details; assignment/use list | global/project/resource calendar scope, standard workweek, per-day work intervals, exceptions, holidays, recurring patterns, effective dates, copy calendar, assign calendar |
| Documents | Document register/list | Document Details; linked activities/WBS | file location, version/revision, status, category, permissions, launch/preview, links |
| Expenses | Expense table; cost/time profile | Expense Details | accrual type, amount, unit, activity, category, dates, cost account, actual/planned |
| Thresholds | Threshold register; monitoring chart | Threshold Details; affected objects | parameter, threshold type, WBS/activity scope, tolerance, monitor/alert state |
| Issues | Issue register; priority/status chart | Issue Details; activity/WBS links, history | owner, responsible, priority, status, due date, notes, notifications, documents |
| Risks | Risk register; probability-impact matrix; exposure chart | Risk Details; response and impact | probability, impact dimensions, expected value, response, owner, schedule/cost exposure, links |
| Reports | Report catalog; groups; batches | Definition/parameters; preview; run history | wizard, data scope, filters, columns, grouping, sorting, page setup, print/export, distribution |
| Tracking | Project table; project bar chart; project Gantt/profile; resource analysis | Tracking Details; spreadsheet/profile | global/user layouts, project explorer, summarize state, cost/schedule/EVM, resource spread |
| Form Builder (CUBI) | Designer canvas + field palette + properties inspector | Form preview; validation/workflow/version tabs | organization library vs project library, header image JPG/PNG, transparent PNG, sections, field types, required rules, conditions, approvals, responsive preview |

Every mode above must be selectable through the active window's Top Layout / Bottom Layout / Layout Options controls. A missing capability must be explicitly marked as not yet available; it must not be silently omitted from the design catalogue.

## Complete layout, menu and dialog inventory

### Layout and view dialogs
- New/Open/Save/Save As Layout; layout scope (private user / shared project); import/export; duplicate, rename, delete and restore default.
- Top Layout selector; Bottom Layout selector; Bottom Layout Options; Show/Hide Details; reset pane arrangement.
- Columns dialog: available/selected columns, search, add/remove, reorder, width, alignment, title override, freeze/pin, auto-fit and restore defaults.
- Filters dialog: standard and user filters, nested AND/OR groups, field/operator/value, null/blank checks, date-relative values, save/share/duplicate/delete, combine filters and clear all.
- Group & Sort dialog: multiple grouping levels, hierarchy/path grouping, multiple sort keys, ascending/descending, group band formatting, empty groups, page breaks, auto-reorganize.
- Timescale dialog: calendar basis, major/minor intervals, labels, fiscal periods, week/month/quarter/year, start/end, non-work time display, zoom presets and fit project.
- Bars dialog: bar definitions, order, show/hide, shape, pattern, fill/outline, labels above/inside/below, left/right label fields, filter, legend and baseline/actual/remaining/critical/summary/milestone/relationship styles.
- Gantt/chart options: gridlines, non-work shading, data-date line, progress line, baseline bars, relationship lines, critical highlighting, bar labels, legend, chart scale, print scale.
- Network options: activity node fields, node size, relationship type labels, lag labels, critical path emphasis, layout direction, spacing, align/arrange, zoom and fit.
- Usage spreadsheet/profile options: time period, bucket size, units/cost/remaining/actual, cumulative/non-cumulative, curves, histogram, stacked/overlay, limits and over-allocation bands.
- Font/Color/Row dialog: font family/size, row height, group band styles, semantic status colors, high contrast and restore defaults.
- Tab configuration: available tabs, shown tabs, order, default tab, per-window saved configuration.

### Calendar windows and dialogs
- Calendar scope selector: Global / Project / Resource; calendar register with name, type, owner, hours per day/week/year, base calendar and status.
- Workweek editor: each weekday individually marked working/non-working; one or more work intervals per day; split shifts; overnight shift handling; copy day; apply pattern to selected weekdays.
- Exceptions: date range, one-off or recurring, working/non-working, replacement hours, description/category; public holidays and project shutdowns.
- Calendar preview: month and week views with working/non-working days, exception markers, selected date details and effective working hours.
- Assignment dialog: assign project calendar, activity calendar and resource calendar; show inheritance/source and override; compare calendars.
- Date presentation calendar (Jalali/Gregorian) is independent of the working-time calendar and independent of UI language. Show both concepts separately in labels and selectors.
- Calendar chooser must support search, favorites/recent, preview and explicit scope; never conflate a Jalali display setting with a working calendar definition.

### Project and object property dialogs
- Project Properties wizard/dialog uses tabbed sections: General, Dates, Defaults, Resources, Settings, Codes, Notebook, Budget, Funding, Baselines, Documents, UDFs and History.
- Activity Properties dialog: General, Status, Dates, Duration, Constraints, Relationships, Resources, Codes, Steps, Expenses, Documents, Issues/Risks, UDFs and History.
- WBS Properties dialog: General, Status, Responsible, Dates, Resources, Earned Value, Codes, Documents, Notebook, Issues/Risks, UDFs and History.
- Resource/Role Properties dialog: General, Details, Units & Prices, Availability, Roles, Calendars, Shifts, Curves, Codes, UDFs and History.
- Relationship dialog: predecessor, successor, FS/SS/FF/SF type, lag/lead value and unit, lag calendar, relationship notes and validation summary.
- Baseline dialog: create, assign primary/secondary/tertiary, copy, compare, restore/replace and remove, with impact confirmation.
- Schedule dialog: data date, selected/all projects, scheduling options summary, log/detail options, schedule/check schedule actions and results summary. This is a visual inventory only; calculations remain outside the shell scope.
- Resource Leveling dialog: selected/all resources, priority rules, preserve minimum float, within-float option, date range, level all/selected and result summary.
- Import/Export wizard: source/target, format, mapping, calendar/date-system mapping, code mapping, validation preview, warnings/errors and completion summary.
- Print/Page Setup: page size, orientation, margins, scaling, repeat headers, date/calendar display, legend, title/footer, page breaks and print preview.

### Workspace, organization and administration dialogs
- Open Project / Project Picker: searchable hierarchy, recent/favorites, status, owner, date, permission, open/close and multi-project selection where allowed.
- User Preferences: language, direction, date display calendar, number format, units, time zone, theme, default window, startup layout, tooltips, shortcuts and accessibility.
- Organization dictionaries: codes/categories, UDF definitions, cost accounts, currencies, financial periods, funding sources, resource curves and shifts.
- Access dialogs: users, teams, roles, profiles, project membership, invitation, permission matrix and effective-access preview.
- Recovery dialogs: unsaved changes, autosave/recovery list, backup/restore, revision history and restore-point confirmation.
- Find/Search: scope, object type, fields, exact/contains, filters, result list and navigate-to-record.
- Global Change: selection criteria, fields/values, preview of affected records, validation, approval and execution confirmation; visual-only until separately implemented.

## Menu chart and command presentation rules

- Menus are real hierarchical dropdowns with submenu arrows, separators, icons, disabled states, keyboard mnemonics and shortcut hints. Hover/focus opens submenus without navigating away; click/Enter activates; Escape closes; arrow keys navigate; focus is trapped only inside modal dialogs.
- Menu contents are context-sensitive. A command not applicable to the active window is disabled with a concise reason, not removed from the global menu.
- Toolbar groups use compact labeled icons and separators. Each command has tooltip, accessible name, shortcut, enabled state and overflow placement at smaller widths.
- The contextual command bar changes with the active window and selected record; it is never a second global menu and never duplicates every possible command at once.
- Selection-sensitive actions show the target object and affected count before destructive changes. Dialogs use tabs/sections and scroll within their own body; the entire workspace must not become a long scrolling form.
- Window tabs, menus, toolbars, navigation, content and Details are separate regions with independent scroll where appropriate. The browser page itself should not horizontally scroll at standard desktop resolutions.
- Icons must have consistent CUBI meaning across themes. Use a centralized icon registry; do not expose competitor branding or source UI labels.

## Additional parity coverage and source map

The Version 26 desktop guide explicitly describes eleven main windows, independent window tabs, per-window Display/Layout Options bars, top/bottom layouts, columns, grouping/sorting/filtering and tracking layouts. The visual audit must cover the desktop Professional client, not substitute a web-only project page or EPPM page.

Primary official desktop references:
- User Guide contents and chapter map: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm
- Main windows and tabbed window behavior: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/using_main_windows.htm
- View menu and Top/Bottom Layout/Bottom Layout Options: https://docs.oracle.com/cd/G48902_01/client_help/en_US/49095.htm
- Activities window and its grid/Gantt/network/detail windows: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/89935.html
- Tracking and tracking layouts: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/tracking.htm
- Tracking layout types: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/types_of_tracking_layouts.htm
- Project Details and project defaults: https://docs.oracle.com/cd/F74771_01/English/User_Guides/p6_pro_user/defining_project_details.htm
- Project Defaults tab and activity ID numbering: https://docs.oracle.com/cd/F51303_01/client_help/en_US/defaults_tab_-_project_details.htm
- P6 Professional Version 26 complete help index: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/index.html

## Audit gate and current state

This document is the target design inventory, not proof that the current app already renders these elements. Current branch implementation remains partial: the Projects surface has a first register/details composition and the global menu/toolbar shell is a visual catalogue. The complete independent windows, navigation tree, multi-window tabs, contextual bars, calendar editor, all view/layout dialogs and all page-specific Details surfaces remain acceptance-gated. Do not call the skin complete until each item is represented in the running application and exercised in browser screenshots/E2E at desktop and responsive breakpoints.


## Implementation progress update — desktop workbench shell (2026-11-02)

The following structural shell slice is now implemented in the PR branch and covered by renderer tests:

- Left navigation is now a labeled, grouped tree on desktop, with project, planning/execution, resources/cost, project information and CUBI tool groups. At tablet/mobile widths it intentionally collapses to a compact icon rail.
- The workspace now renders a horizontal window strip for the nine existing primary modules. Selecting a tab uses the existing workspace menu callback and updates the selected state without replacing the whole shell.
- The active module now has its own compact horizontal contextual command bar. Only commands with existing owning workflows are enabled; unavailable visual commands explain that they are not connected.
- The right edge is now a separate contextual command rail with Add (+), followed by the existing comments/notes/documents/risk shortcuts. The Add popup inventories create targets but disables them until the corresponding real create workflow is connected.
- Calendars, Roles, Tracking and Thresholds are exposed in the navigation tree as explicitly unavailable entries, not silently omitted.
- CSS is mirrored byte-for-byte between apps/web/styles.css and apps/web/public/styles.css; responsive widths have dedicated rules.

**Still not complete:** the nine module tabs are navigation between current workspace surfaces, not yet a full independent multi-window manager with per-window saved state and close/dirty prompts. Most listed secondary windows, page-specific top-layout modes, page-specific Details panes, calendar editor, full layout dialogs, functional Add workflows, and browser screenshot review remain outstanding. This is an incremental conversion of the shell, not final visual parity.


## Owner-approved completion sequence and preservation decisions (2026-11-02)

The product owner confirms that visual-shell implementation is to continue without spending Qoder Credits for the current no-credit period. The assistant should implement and verify bounded changes directly where repository tooling permits; it must not ask Qoder to perform work until the user's daily allowance is available again.

The next visual implementation work is ordered as follows. This is an execution order, not a claim that these items are already implemented:

1. **Real window manager:** replace the current nine-tab navigation proxy with a true per-window registry/state model. Opening a module creates or activates its window; tabs have stable instance IDs, active state, close, reorder, keyboard cycling and tab groups. Project context and per-window view state must not leak between windows.
2. **Dirty-state lifecycle:** add explicit dirty tracking and Save / Discard / Cancel close confirmation. Do not fabricate persistence: if save is not wired for a window, explain that state cannot yet be saved and prevent silent data loss.
3. **Window-specific surfaces:** implement the highest-priority professional windows in dependency order: Projects, Activities, WBS, Resource Assignments, Resources, Roles, Calendars, Documents, Expenses, Issues, Risks, Thresholds, Reports and Tracking. Each must own its page layout and selection context rather than reusing one generic list.
4. **Per-window Details:** implement each window's required Details tabs from the table above, including empty-selection page context and selected-record identity; preserve tab selection per window instance.
5. **Layout/view controls:** implement top/bottom layout selectors and the corresponding dialogs (columns, filters, multi-level group/sort, timescale, bars, network, usage spreadsheet/profile, font/row, tab configuration). A control must be functional or explicitly disabled with a reason.
6. **Calendar editor:** implement Global / Project / Resource calendar scope, workweek intervals, split/overnight shifts, exceptions/holidays, preview and assignment dialogs. Keep Jalali/Gregorian display separate from working-time calendars.
7. **Contextual command workflows:** connect Add/Edit/Delete/Assign/Link and page-specific commands only to real owning workflows and permission-checked APIs. Do not present success for visual-only controls.
8. **Visual acceptance:** run actual browser E2E and capture the reference desktop viewport plus tablet/mobile and RTL/LTR screenshots; compare against the latest available P6 Professional release (Version 26 and its latest applicable 26.x release/update). The owner's 2026-11-02 decision supersedes Version 22 as the controlling visual baseline. Version 22 imagery is historical only; do not retain its geometry where it conflicts with the latest release. Preserve Timeline/Gantt proportions of the latest-release reference; no arbitrary resizing.

### Qoder credit-aware workflow decision

Before any future Qoder prompt, inspect the Qoder model/tier, context size and displayed estimate. Qoder meters Credits rather than a universal fixed number of prompt tokens; actual usage must be read from the account Usage panel and never inferred from prompt length or code size. Manual repository inspection, manual editing, ordinary terminal commands, Git operations and manually running tests do not themselves invoke a paid model. AI Ask/Chat/Agent/Quest/Knowledge operations may consume Credits.

Every future Qoder prompt must be one repository-aware bounded work package, include known files and prior work, require implementation plus local tests and fixes in the same run, and request exact final SHA and evidence. The assistant must independently review the returned code and outputs. GitHub Actions is a later integration gate, not the primary fast feedback loop. Avoid repeat prompts unless a concrete remaining defect or new requirement is identified.

### Acceptance distinction for the calculation core

Lack of a licensed direct P6 execution is not a blocker to implementation or documented-rule numeric tests. Keep three evidence levels separate: documented-rule/golden-case numeric verification, independent code/output review, and direct same-scenario P6 comparison. Only the last claim remains unavailable until direct reference execution can be performed. This calculation-core rule also governs any shell command that displays calculation results; the visual layer must never create a second calculation authority.


## Superseding owner instruction — latest P6 release governs (2026-11-02)

The product owner explicitly replaced Version 22 as the controlling visual baseline and requires the **latest available P6 Professional release** to govern CUBI's complete visual shell. Oracle's official documentation set currently identifies Version 26. The latest 26.x patch/update must be checked before each visual audit; Oracle's 2026 What's New documentation lists P6 Professional 26.10; confirm the exact Professional client build and availability from the current release notes before treating an update as installed. Use the current Version 26 User Guide, Help, Visualizer Help, release notes and all relevant official topics to inventory the current menus, windows, bars, dialogs, layouts, columns, filters, grouping/sorting, timescale, calendars and workflows. Version 22 screenshots are no longer acceptance references and may be retained only as historical comparison material. If current screenshots are unavailable, reconstruct behavior and layout from current official documentation and explicitly flag visual uncertainty; do not silently fall back to Version 22.

Official current documentation: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/ . Current patch discovery: https://community.oracle.com/mosc/categories/primavera_-_prim .
