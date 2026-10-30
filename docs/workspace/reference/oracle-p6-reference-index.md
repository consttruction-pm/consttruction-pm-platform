# P6 Professional Desktop v26 Reference Index

Status: Phase 1 evidence record for the CUBI workspace programme.
Reviewed: 2026-10-30.
Reference product: Oracle Primavera P6 Professional, version 26, desktop help and user guides.

This index records which official pages were reviewed, what each page contributed, and which gaps remain. It is a source register, not a copy of Oracle documentation. Oracle and Primavera names are recorded here for traceability only; the CUBI interface must use its own vocabulary (see `../architecture/p6-to-cubi-mapping-matrix.md`).

## Sources reviewed

| Area | Official page | Contribution |
| --- | --- | --- |
| Help TOC | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm | Complete section map: workspace basics, toolbars/menus, projects, EPS, WBS, calendars, resources/roles, activities, relationships, scheduling, leveling, layouts, Gantt, network, trace logic, tracking, reporting, administration |
| User guide TOC | https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm | User-guide task structure |
| User guide (HTML) | https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/index.html | Same task structure in web form |
| Admin guide | https://docs.oracle.com/cd/G48902_01/English/admin/p6_pro_admin/toc.htm | Administrative preferences/categories, security, financial periods, currencies, UDF/code dictionaries |
| Menu bar overview | https://docs.oracle.com/cd/G48902_01/client_help/en_US/menu_bar.htm | Menu set: File, Edit, View, Project, Enterprise, Tools, Admin, Help |
| File menu | https://docs.oracle.com/cd/G48902_01/client_help/en_US/49093.htm | Project lifecycle, import/export, portfolio, commit/refresh, recent projects |
| Edit menu | https://docs.oracle.com/cd/G48902_01/client_help/en_US/49094.htm | Undo, clipboard, add/delete/dissolve, assign submenu, link/unlink, renumber, fill down, find/replace, user preferences |
| View menu | https://docs.oracle.com/cd/G48902_01/client_help/en_US/49095.htm | Layout control, top/bottom layouts, columns, timescale, filters, grouping, progress line, critical path, toolbars, tab groups |
| Project menu | https://docs.oracle.com/cd/G48902_01/client_help/en_US/49096.htm | Activities, additional activities view, resource assignments, WBS, baselines, expenses, documents, thresholds, issues, risks |
| Enterprise menu | https://docs.oracle.com/cd/G48902_01/client_help/en_US/49097.htm | Projects, EPS, tracking, portfolios, resources, roles, OBS, code dictionaries, UDFs, calendars, shifts, step templates, cost accounts, funding, images, curves |
| Tools menu | https://docs.oracle.com/cd/G48902_01/client_help/en_US/49098.htm | Schedule, level, apply actuals, update progress, costs, summarize, period performance, global change, thresholds, issues, reports, publish |
| Admin menu | https://docs.oracle.com/cd/G48902_01/client_help/en_US/49099.htm | Users, security profiles, preferences, categories, currencies, financial period calendars |
| Help menu | https://docs.oracle.com/cd/G48902_01/client_help/en_US/49100.htm | Local/online help, about, what's new, feedback |
| Main windows | https://docs.oracle.com/cd/G48902_01/client_help/en_US/using_main_windows.htm | Window set, window tabs, global vs project windows, layout options bar, context-sensitive enablement |
| Activity Details | https://docs.oracle.com/cd/G48902_01/client_help/en_US/activity_details.htm | Tab set and customization through Bottom Layout Options |
| Status bar / layout options bar | https://docs.oracle.com/cd/G48902_01/client_help/en_US/using_the_status_bar_and_display_layout_options_bar.htm | Status fields: portfolio, access mode, data date, baseline, job status, user, database alias/type; layout name and filter name |
| Layout toolbar | https://docs.oracle.com/cd/G48902_01/client_help/en_US/layout_toolbar.htm | New/Open/Save/Save As layout, Bars, Columns, Timescale, Filter, Group and Sort, Line Numbers, Table Font and Row, User Preferences |
| Filter dialog | https://docs.oracle.com/cd/G48902_01/client_help/en_US/filter_a_layout.htm | Any/All parameter rows, Is operator, Value, Add/Delete/order |
| Activity Table | https://docs.oracle.com/cd/G48902_01/client_help/en_US/activitytable.htm (fetch timed out; TOC topic confirmed) | Table layout, column management, sorting/grouping/filtering; details verified through View/Edit menu topics |
| Toolbars | standard, project, action, edit, display, assign, tools, enterprise, administrator, dictionaries, find, move, print, publish, reports, top layout, bottom layout (individual `*_toolbar.htm` pages) | Complete or near-complete command inventory; see `../architecture/workspace-toolbar-inventory.md` |
| Layout pages | `ganttchart.htm`, `activitynetwork.htm`, `tracelogic.htm`, `overview.htm` (TOC) | Gantt, network and trace-logic view capabilities listed in the TOC and used in the window inventory |

## Fetch limitations recorded honestly

- `activitytable.htm` timed out once and was not re-fetched; its capability list is taken from the TOC plus the View/Edit menu pages that operate on the table.
- `menu,toolbar,andiconreference.htm` (index page with commas in the filename) failed to fetch. Each toolbar page was fetched individually instead.
- `customize_activity_details.htm` returned HTTP 403; the tab list and customization path were taken from `activity_details.htm`.
- Oracle help figures were not downloaded as image assets. Phase 2 visual review is therefore structural (menu/command/window behaviour and published layout descriptions), not pixel-level. Any visual comparison against Oracle screenshots must be done manually before claiming pixel parity.
- Two pages (Print toolbar and Top Layout toolbar) required a retry and succeeded on the second attempt.

## Version and edition boundary

The reference is the **desktop Professional** edition. The following commands are explicitly marked EPPM-only or server-only by Oracle and are not targets for the CUBI desktop-style workspace:

- Check In / Check Out / Send to Unifier / Job Status / Job Services (server or EPPM database)
- Tasks tab in Activity Details (EPPM only)
- Assign Activity Step Templates via toolbar (desktop has no menu command)
- Budgeted/unbudgeted project data and portfolio web publishing are out of scope until a CUBI server feature exists

Conversely, the Risks view and Activity Details > Risks are Professional-only and therefore in scope when the risk data model exists.

## Downstream documents

- `oracle-p6-menu-reference.md` — command inventory per menu
- `oracle-p6-window-reference.md` — windows, layouts, tabs, status bar, dialogs
- `../architecture/workspace-information-architecture.md`
- `../architecture/workspace-navigation-map.md`
- `../architecture/workspace-window-inventory.md`
- `../architecture/workspace-dialog-inventory.md`
- `../architecture/workspace-form-field-inventory.md`
- `../architecture/workspace-toolbar-inventory.md`
- `../architecture/workspace-layout-specification.md`
- `../architecture/p6-to-cubi-mapping-matrix.md`
- `../workspace-execution-log.md`
