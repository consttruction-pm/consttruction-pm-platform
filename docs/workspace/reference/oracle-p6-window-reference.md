# P6 Professional Desktop v26 Window Reference

Status: Phase 1 inventory of windows, layouts, tabs, bars and dialog families.
Source: Oracle P6 Professional v26 help; see `oracle-p6-reference-index.md` for page-level evidence.

## Window model

- Main windows open as **tabs** below the active tab title bar. Selecting a tab activates that window; the `X` closes it.
- Each window has a **top layout** and an optional **bottom layout**, selected from the top and bottom layout toolbars or the View menu.
- Each window has a **layout options bar** at the top-left showing the current layout name and filter name. Clicking it opens the window's display commands.
- **Enterprise windows** (Projects, Resources, Reports, Tracking) stay open until closed manually.
- **Project windows** (WBS, Activities, Resource Assignments, WPs & Docs, Project Expenses, Project Thresholds, Project Issues, Risks) close when all projects close.
- A **status bar** at the bottom shows portfolio, access mode, data date, current baseline, job status, user, database alias and database type.
- Menu commands and toolbar icons enable/disable according to the active window and the active layout (for example, Gantt commands are unavailable in a pure table view).

## Main windows

| Window | Group | Purpose | Typical top layout | Typical bottom layout |
| --- | --- | --- | --- | --- |
| Projects | Enterprise | EPS hierarchy and project list; open/manage projects | Project table; chart/bar views | Project details, Gantt/profile |
| Resources | Enterprise | Resource hierarchy, resource details and assignment summaries | Resource table; chart view | Resource details, usage |
| Reports | Enterprise | Create, edit, run, import/export reports | Report list | Report details |
| Tracking | Enterprise | Progress layouts against a data date | Tracking layout (table/Gantt/profile) | Layout details |
| WBS | Project | Build and edit the project WBS | WBS table or chart | WBS details |
| Activities | Project | Activity table + Gantt/network and Activity Details | Table + Gantt, or table + Activity Network | Activity Details; usage profiles/spreadsheets; Trace Logic |
| Resource Assignments | Project | Assignments for all open projects grouped by resource | Assignment table/spreadsheet | Assignment details |
| WPs & Docs | Project | Work products and documents | Document table | Document details, file launch |
| Project Expenses | Project | Activity expense items | Expense table | Expense details |
| Project Thresholds | Project | WBS/activity thresholds | Threshold table | Threshold details |
| Project Issues | Project | Issues, history, notifications | Issue table | Issue details/history |
| Risks | Project | Risk register and exposure | Risk table | Risk details |

Window-specific layout options and internal tab details for every window are not published as a single table in the help. The Activity Details tab set is published and is the model for CUBI's detail-panel tabs.

## Activities window composition

1. **Activity Table** on the left, **Gantt Chart** (or Activity Network) on the right, inside the top layout.
2. **Activity Details** in the bottom layout, with configurable tabs.
3. A **Display/Layout Options bar** with layout name, filter name and commands.
4. Optional bottom views: Activity Usage Spreadsheet, Activity Usage Profile, Resource Usage Spreadsheet, Resource Usage Profile, Trace Logic, or no bottom layout.

The top layout can also be **table only**, **Gantt only**, or **Activity Network**; the bottom layout can be hidden to give the top layout the full work area.

## Activity Details tabs

Customization: Display Options bar > **Bottom Layout Options**, or right-click the tab area > **Customize Activity Details**. Users choose which tabs appear and their order.

| Tab | Availability | Content / CUBI target |
| --- | --- | --- |
| General | Standard | Activity ID, name, type, duration, calendar, WBS, responsible manager, dates |
| Status | Standard | Status, percent complete, actual/remaining dates and durations, suspend/resume |
| Resources | Standard | Resource/role assignments, units, costs, curves |
| Predecessors | Standard | Predecessor list, relationship type, lag |
| Successors | Standard | Successor list, relationship type, lag |
| Codes | Standard | Activity code assignments |
| Tasks | EPPM only | Not in desktop scope |
| Discussion | Standard | Threaded discussion |
| Notebook | Standard | Notebook topics and entries |
| Steps | Standard | Activity steps and weights |
| Feedback | Standard | Feedback items |
| WPs & Docs | Standard | Work products and documents |
| Expenses | Standard | Expense items for the activity |
| Summary | Standard | Roll-up values from the activity's WBS/summary |
| Relationships | Standard | Combined relationship view |
| Risks | Professional only | Risk assignments and exposure |
| UDFs | Standard | User-defined fields |
| Update History | Standard | Change history |

Above every tab: Previous/Next activity navigation, Activity ID, Activity Name and Project fields.

## Status bar

Fields, left to right: current portfolio name, access mode, data date, current baseline, job status, current user name, database alias, database type (`Professional` or `EPPM` in the reference product).

CUBI equivalent must show only data it actually owns: project, data date, current baseline (or `None`), active layout, filter name, user/role, connection mode (`Local preview` / `Server`), sync state. Never show a database alias that the browser cannot know.

## Layout options bar

Shows layout name and filter name and opens window-specific display commands. CUBI will render it as the **Layout Bar** above the working area, with the same two names plus a menu button.

## Dialog families

| Dialog | Opened from | Main controls (as published) |
| --- | --- | --- |
| Open Project | File > Open | Project list, open action |
| Select a Portfolio | File > Select Project Portfolio | Portfolio list |
| Print / Page Setup / Print Setup / Print Preview | File menu, Print toolbar | Printer, page geometry, scaling, margins, header/footer, HTML publish |
| Import / Export wizard | File menu, Action toolbar | Source/target format, project/resource/role selection, mapping |
| Columns | View > Columns, Layout toolbar | Available/selected columns, order, width, alignment, title |
| Filters | View > Filter By > Customize; Layout bar > Filters | Any/All rows, field, operator, value, Add/Delete, order |
| Group and Sort | View > Group and Sort By | Grouping bands, sort fields and direction, summary/totals options |
| Timescale | View > Timescale, Layout toolbar | Timescale format, range, date labels, fiscal year settings |
| Bars | View > Bars | Bar definitions, filters, styles, labels, timescale |
| Bar Chart Options | View > Barchart Options | Gantt display, relationship lines, background, legend, data date |
| Table, Font and Row | View > Table Font and Row | Font, size, colour, row height |
| Collapse To | View > Collapse To | Target grouping band |
| Activity Network options | View > Activity Network | Box template, arrangement, fonts/colours, layout open/save |
| Trace Logic preferences | Trace Logic bottom view | Predecessor/successor depth and display |
| Assign Resources / by Role / Roles / Activity Codes / Predecessors / Successors | Edit > Assign, Assign toolbar | Search/assign/remove/replace lists |
| Renumber Activity IDs | Edit menu | Prefix/suffix, increment, selected scope |
| User Preferences | Edit > User Preferences | Time/date/currency formats, email, startup, password |
| New Layout / Open Layout / Save Layout / Save As | View > Layout, Layout toolbar | Layout name, scope (user/project), import/export |
| Assign Baselines / Maintain Baselines | Project menu | Project, primary/secondary/tertiary baseline; create/copy/restore/delete |
| Schedule | Tools > Schedule (F9) | Data date, scheduling options, open/all projects |
| Level Resources | Tools > Level Resources (Shift+F9) | Leveling options, resources, priorities, float limits |
| Apply Actuals / Update Progress / Store Period Performance | Tools menu | Data date and scope, progress estimation, period selection |
| Global Change | Tools menu | Parameter-based bulk change |
| Monitor Thresholds / Issue Navigator | Tools menu | Threshold evaluation and issue list |
| Users / Security Profiles / Admin Preferences / Admin Categories / Currencies / Financial Period Calendars | Admin menu | Administration dictionaries and policies |
| Report dialogs (Run Report, Batch, Groups, Wizard, Preferences) | Tools > Reports, Reports toolbar | Report selection, batch, grouping, wizard steps |

Dialogs not yet described field-by-field by Oracle's published pages (Level Resources, Global Change, Store Period Performance) must be specified from their in-product fields before implementation; they are not guessed in this reference.

## View composition rules relevant to CUBI

1. Table and chart are synchronised: selecting a row highlights the corresponding bar/box; dragging a bar edits dates/duration.
2. Gantt supports activity bars, milestones, WBS summary bars, relationship lines, progress bars, baseline bars, data date line, progress line, critical path, timescale, zoom, horizontal scroll, bar labels/styles, background lines and legend.
3. Activity Network and Trace Logic are independent windows/views, not modal dialogs.
4. Layouts persist table columns, detail tabs, grouping, filters, Gantt settings and timescale. Layout scope can be user or project; layouts can be imported/exported.
5. Tracking layouts are a separate family from activity layouts.
