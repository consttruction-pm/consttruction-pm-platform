# CUBI Workspace — Visual Reference Audit

Mission: visual implementation order and Version 26 menu audit, 2026-11-02. This document records what was actually opened and seen before building the CUBI visual shell. It is an inspection log, not a design brief.

## Method and honesty notes

- Direct image URLs were fetched with `curl`/Node into a temporary folder outside the repository; the images were then opened at readable resolution and inspected one by one.
- Where a host refused the request, an image proxy (`images.weserv.nl`) was used and the result is marked below. That proxy re-encodes the image but does not change its content.
- Reference files are **not** copied into the application, not committed, and not shipped as CUBI assets. Only the observations and the source register are kept.
- Version caveat: only the Oracle Version 26 documentation is authoritative for feature inventory. The screenshots are older releases (8.3–18) and third-party captures; they are used for layout, density, colour and interaction patterns only.
- The latest official Version 26 documentation was re-opened and checked on 2026-11-02:
  - `https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/index.html` — loads; document G57529-01, release 26, publication October 2026; body is JavaScript-rendered, so structure was confirmed through the linked help pages.
  - `https://docs.oracle.com/cd/G48902_01/client_help/en_US/menu_bar.htm` — loads; confirms File, Edit, View, Project, Enterprise, Tools, Help and the conditional Admin menu (Admin appears only when connected to a Professional database).

## Latest official documentation audit — 2026-11-02

The current authoritative functional inventory is the latest official Version 26 help and user guide, not any legacy screenshot release. The menu bar was checked command-by-command against the current Help pages:

- Menu bar overview: `https://docs.oracle.com/cd/G48902_01/client_help/en_US/menu_bar.htm`
- File menu: `https://docs.oracle.com/cd/G48902_01/client_help/en_US/49093.htm`
- Edit menu: `https://docs.oracle.com/cd/G48902_01/client_help/en_US/49094.htm`
- View menu: `https://docs.oracle.com/cd/G48902_01/client_help/en_US/49095.htm`
- Project menu: `https://docs.oracle.com/cd/G48902_01/client_help/en_US/49096.htm`
- Enterprise / organization menu: `https://docs.oracle.com/cd/G48902_01/client_help/en_US/49097.htm`
- Tools menu: `https://docs.oracle.com/cd/G48902_01/client_help/en_US/49098.htm`
- Administration menu: `https://docs.oracle.com/cd/G48902_01/client_help/en_US/49099.htm`
- Help menu: `https://docs.oracle.com/cd/G48902_01/client_help/en_US/49100.htm`
- Version 26 user guide, October 2026: `https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/index.html`

### Menu-by-menu acceptance inventory

| CUBI menu | Required Version 26 command families | CUBI presentation / audit status |
| --- | --- | --- |
| Workspace | New, Open, Close All, Page Setup, Print Setup, Print Preview, Print, Import, Export, Send Project, Exchange Data, Check In/Out, Select Project Portfolio, Commit Changes, Refresh Data, Recent Projects, Exit | Inventory present; save, backup/restore and package workflows are CUBI additions. Most commands remain disabled until their real owner workflow is connected. |
| Edit | Undo, Cut, Copy, Paste, Add, Delete, Dissolve, Assign Resources / Resources by Role / Roles / Activity Codes / Predecessors / Successors, Link/Unlink, Renumber Activity IDs, Fill Down, Select All, Find/Find Next, Replace, Spell Check, User Preferences | Inventory present; command activation remains context- and service-dependent. |
| View | Layout, Show on Top/Bottom, Bottom Layout Options, Bars, Bar Chart Options, Columns, Timescale, Filter By, Group and Sort By, Progress Line/Spotlight, Attachments, Line Numbers, Activity Critical Path, Check Schedule, Table Font and Row, Activity Network, Arrange/Align Children, Chart Box Template, Chart Font and Colors, Launch, Hint Help, Zoom, Expand/Collapse/Collapse To, Toolbars, Reset/Lock Toolbars, Tab Groups | Inventory present. Columns, Filter By, Group and Sort By, Timescale, Bars, Bar Chart Options and Bottom Layout Options have live routes in the activity workspace. Other commands remain visibly disabled until the corresponding view or behavior exists. |
| Project | Activities, Additional Activities View, Resource Assignments, WBS, Assign/Maintain Baselines, Expenses, Work Products and Documents, Thresholds, Issues, Risks (conditional), Set Default Project | Inventory present, with CUBI project-detail and project-default additions. Several secondary windows remain preview/partial. |
| Organization | Projects, EPS, Tracking, Portfolios, Resources, Roles, OBS, Project/Activity/Resource/Role Codes, User Defined Fields, Calendars, Resource Shifts, Activity Step Templates, Cost Accounts, Funding Sources, Stored Images, Resource Curves, External Applications | Inventory present in CUBI wording; organization-wide records must come from authorized services, never fabricated demo rows. |
| Tools | Schedule, Level Resources, Apply Actuals, Update Progress, Recalculate Assignment Costs, Summarize, Job Services/Job Status (conditional), Store Period Performance, Auto-Reorganization, Global Change, Monitor Thresholds, Issue Navigator, Timesheets/Approvals, Reports/Groups/Batches/Preferences, Report Wizard, Publish layouts/site, Schedule Visualization, Project Comparison | Inventory present, plus CUBI Form Builder, Smart Guide and Assistant. A visible menu entry is not proof that a command is implemented. |
| Administration | Users, Security Profiles, Admin Preferences, Admin Categories, Currencies, Financial Period Calendars | CUBI team, permissions, audit and system-default controls are additional product-specific commands; access must be role-authorized. |
| Help | Local Help, Online Help, About, What's New, Share Feedback | CUBI guide, context help, shortcuts and documentation library are additional help destinations. |

The Edit menu's Add Activity, Add WBS, Add Relationship and Link Activities entries now route to the existing creation/relationship workflows; Find focuses the activity filter. These commands reuse the owning form and API callback rather than duplicating write logic.

### Main-window submenu routing audit — 2026-11-02

Module submenus are not allowed to remain decorative labels when the destination already exists. The current navigation surface now routes supported submenus into their real module stage, detail tab, calendar editor tab or tracking-layout selector:

| Workspace window | Live submenu routes | Explicitly unavailable submenu |
| --- | --- | --- |
| Project | Project/WBS, Details, Import/Export | — |
| WBS | WBS Register, WBS Details tab | WBS Chart until a real hierarchy chart renderer exists |
| Schedule | Activity Grid, Gantt, relationship/calendar/resource/progress reference groups, schedule options, run, formula and documentation sections | Any future view not rendered by the shared schedule workspace |
| Progress | Data-backed Activity Progress Register with entered progress/actual dates, selectable activity details, Site Daily Logs, Timecards, Equipment Reports and Field Issues routes | Update Progress, period close and progress calculations remain unavailable until authoritative scheduling/progress services expose them |
| Resources | Resource Register, Max Units/Time, Assignments, Codes, Roles detail tabs; capacity tool | Resource utilization and assignment calculations until backed by authoritative resource/assignment data |
| Resource Assignments | Assignment register, General details tab | Resource Usage chart/profile |
| Roles | Role register, Rates and Assignments detail tabs | — |
| Calendars | Calendar register, Workweek, Exceptions, Assignments tabs | Create/Edit/Delete while calendar persistence is not connected |
| Expenses | Expense register, General details tab | Cost Accounts until the account register is connected |
| Cost | Procurement/Change/Claim metrics plus Cost Accounts, Budget, Actuals, Forecast, Cash Flow, Earned Value, Financial Periods and Funding tabs | Account and financial registers remain empty until authoritative services return records; no client-side financial calculations |
| Documents | Data-backed document register, selectable rows, General/Links/Integrity/Revisions/UDF detail tabs, Evidence type filter | Upload/write operations and revision history remain unavailable until the document service exposes them |
| Reports | Report Library, Layouts, Batch Reports, Print Preview, Page Setup, Export and Custom Reports tabs | Template catalog, query, generate, print and export services remain disabled until connected |
| Tracking | Project Table, Bar Chart, Gantt/Profile and Resource Analysis layout selector | Data selection, summarization, chart rendering and saved layouts |
| Issues | Issue register, Details tab | Create/Edit/Delete until the issue service is connected |
| Risks | Risk register, Details tab | Risk analysis until the scoring/response renderer is connected |
| Thresholds | Threshold register, Monitoring and Details tabs | Create/Edit/Delete until the threshold service is connected |
| Control | Quality, Inspections, Safety, Field Issues, Punch List, Changes/Claims and Forms detail tabs with live category counts | Register rows remain empty where the authoritative control record is not loaded; no synthesized control or earned-value data |
| Settings | Project settings and workspace settings | Unsupported preferences are not exposed as active controls |

For a submenu implemented as a detail-tab action, activation must reuse the module's existing tab event path. It must not maintain a second, divergent tab state. Tracking layout choices may change the selected layout type, but they must not claim that the underlying tracking data or chart is available.

### Docking and splitter parity — 2026-11-02

- The Activities window now places Activity Details below the activity table/Gantt region, with a horizontal splitter. The splitter supports pointer drag, Arrow Up/Down, Home/End, double-click reset, ARIA range values and browser-local height persistence.
- The Projects window now places Project Details below the upper Project Structure / Project Register region, with the same accessible and persistent horizontal splitter behavior.
- The Projects upper region places Project Structure in a leading 190–340 px rail (240 px default) and Project Register in the remaining width; the rail supports pointer and keyboard resizing, persists locally, RTL mirrors the leading edge, and narrow screens stack the two regions.
- View → Show on Bottom → Activity Details routes to the docked details pane. View → Bottom Layout Options opens the available/displayed Activity Details tab selector.
- View → Show on Top → Table and Gantt Chart are connected to the real workspace layout state. Activity Network and usage/profile layouts remain disabled until their renderers and data contracts exist.
- Pane sizes are visual preferences only. They are stored locally and do not alter project data, schedule calculations or permissions.

### Columns window parity — 2026-11-02

View → Columns opens a dedicated modal window around the existing authoritative field-registry chooser. The chooser retains add/remove, visible/hidden, order, width, alignment, pin/freeze and layout-history controls. If the field registry is not loaded, the dialog explicitly reports that state instead of rendering fabricated fields. The rail Tools action continues to open the full field chooser drawer.

The Progress navigation now exposes read-only Update Progress and Store Period Performance dialogs with Current/New Data Date, Progress Spotlight/selected-activity scope, timesheet actuals, remaining-duration recalculation choices, out-of-sequence policy, project Data Date scope and financial-period controls. The controls remain disabled until the authoritative update and period-performance services are available; no progress values are computed or written by the visual layer.

### Activity Details tab customization parity — 2026-11-02

The Activity Details customization dialog now uses separate Available Tabs and Display Tabs listboxes. It includes Add, Add All, Remove, Remove All, Move Up, Move Down, Default, Cancel, Apply and OK controls. The displayed order is preserved when applied and used by the Activity Details tab strip; it is not merely a checked/unchecked list. The selected tab order is stored as a browser-local layout preference, separate from project schedule data. Help remains disabled until a contextual help target is connected.

### Dialog and window audit gates

- A menu command must open its named dialog/window or be disabled with a truthful explanation; it must never be an inert enabled button.
- Dialogs must use a title/header, labelled group boxes, correctly typed inputs, selection lists, and a right-side action column where the reference pattern calls for it. OK, Cancel, Apply and Help are individually wired or visibly disabled.
- Options are enabled only when their rendering, persistence and domain contract exist. A visual placeholder must not imply a working calculation or saved change.
- Activity Details customization must support moving available tabs into the displayed tab set, ordering them, restoring defaults and applying the result; an empty or decorative tab is not acceptable.
- Timescale controls must preserve two/three-line format, primary/ordinal dates, date interval, shift calendar and font settings only after their renderer and persistence are implemented. Current live controls are the display interval and relationship-line visibility; the remaining fields are intentionally disabled and documented as gaps.
- Every major window is checked for table, chart, detail pane, navigation, empty state, selection, context actions, resize/scroll behavior, keyboard focus, RTL/LTR and mobile-width overflow.
- No source-vendor product name, logo or URL may appear in CUBI workspace chrome or user-facing help.

## Source register and inspection status

| # | Image | Direct URL | Source page | Version | Screen / dialog | Inspection status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Complete Activities workspace | `https://www.oracle.com/webfolder/technetwork/tutorials/primavera/CoursePreviews/P6PROFUN8.3PREV/Publishing%20Content/P6PROFUN8.3PREV/data/tpc/ff3bbbdb-0b90-4191-9c10-a38965c54855/images/Overview%201a1.png` | Oracle tutorial `.../ff3bbbdb-.../index.html` | 8.3 | Activities workspace with Edit menu | **Failed.** Oracle returned HTTP 403 (Akamai "Oracle Export Error") for both the image and its page, directly and through an image proxy; no Wayback snapshot exists. Not inspected. Equivalent regions were inspected in images 2, 3, 8, 9 and 10. |
| 2 | Activities table and Gantt | `https://ead.verano.com.br/cursos/demo-en/howto/edelivery12.png` | same host | 18.x (title reads "Primavera P6 Professional 18") | Activities, Classic Schedule Layout | Inspected, 1155×766 |
| 3 | WBS window | `https://www.taradigm.com/wp-content/uploads/2021/07/primavera-p6-pro-wbs.png` | `taradigm.com/how-to-display-the-wbs-on-the-activities-screen-in-primavera-p6/` | 8.x (title "Primavera P6 Professional 18: 1542-1.00") | WBS tab in the Activities window | Inspected via proxy (direct host failed TLS), 660×510 |
| 4 | Activity Details tab customization | `https://nebula.wsimg.com/7f26da7f435ace284fa7221db0ece09d?AccessKeyId=71A0B2080A851A84BB51&alloworigin=1&disposition=0` | `melaniecalverley.com/the-best-of-primavera-p6-activity-layouts.html` | 8.x | Activity Details dialog | Inspected, 614×391 |
| 5 | Group and Sort dialog | `https://i0.wp.com/consultleopard.com/wp-content/uploads/2025/07/Arrange-Order-of-Sort-Fields.jpg?resize=800%2C535&ssl=1` | `consultleopard.com/oracle-primavera-p6-22-12-...` | 22.12 | Group and Sort with nested Sort dialog | Inspected via direct `consultleopard.com` URL (i0.wp.com unreachable), 800×535 |
| 6 | Timescale dialog | `https://nebula.wsimg.com/12fa0a2409a2c253ea5134d9726398c6?AccessKeyId=71A0B2080A851A84BB51&alloworigin=1&disposition=0` | `melaniecalverley.com/primavera-p6-visual-appeal-and-formatting.html` | 8.x | Timescale dialog | Inspected, 511×404 |
| 7 | Calendar editor | `https://www.proove.eu/images/uploads/knowledge/20180518_MWA_afbeelding_02.png` | `proove.eu/knowledge/project-calendars-over-global-calendars` | 8.x | Project Calendar dialog | Inspected, 727×611 |
| 8 | Resource assignments | `https://doduykhuong.files.wordpress.com/2017/03/how-to-assign-resource-resource-loading-make-resource-plan-in-primavera-p6-9.png` | `planningplanet.com/blog/how-assign-resource-...` | 16.2 | Resource Assignments layout | Inspected via proxy, 1366×728 |
| 9 | Activity Network / Trace Logic | `https://www.emerald-associates.com/images/stories/Blog/P6_Trace_Logic/P6_Trace_Logic_Options.png` | `emerald-associates.com/item/chasing-down-logic-in-p6-trace-logic-to-the-rescue.html` | 17.x | Activity Network layout with Trace Logic below | Inspected, 1862×733 |
| 10 | Toolbar and navigation arrangement | `https://3.bp.blogspot.com/-K-brtMpWrMA/WDLA7twZUSI/AAAAAAAAMwQ/SiKgrGEmqi8gXtTVy5AO5IZk1jAk0GoWQCLcB/s1600/getting%2BStarted-7.png` | `.../getting Started-7.png` (blogger) | 15.x | Annotated Activities window: title bar, menu bar, quick access toolbar, directory, command bar | Inspected via proxy, 1255×639 |

## Observations by image

### Image 2 — Activities table and Gantt

- Window chrome: light Windows 7 title bar, application icon at the far left, project name in the title (`… 18: EC00515 (City Center Office Building Addition)`), minimise/maximise/close at the right.
- Menu bar directly under the title bar: File, Edit, View, Project, Enterprise, Tools, Admin, Help. Text is small (≈8 pt), sentence case.
- Two command rows: a standard toolbar of ~30 small colourful icons with separators, then a layout toolbar with columns, filter, group, sort, layout picker, print and search icons.
- A narrow view/directory strip on the left edge (≈44 px) and a command-bar strip on the right edge (≈30 px), both with small monochrome/colour icons.
- Activity table occupies roughly 47 % of the width; Gantt 53 %.
- Table header: beveled grey gradient, 1 px dark bottom border, 22 px tall. Columns: Activity ID, Activity Name, Original Duration, Remaining Duration, Sc… (scrolls).
- Group band: saturated blue (`#1f4f9f`-ish) with white bold text, collapse box at the left, full-width.
- Summary rows: solid green (`#67b52f`-ish) with white text, bold.
- Detail rows: white, 17–18 px tall, thin grey grid lines; WBS indentation of ≈16 px per level with a small expansion box.
- Selection: light blue fill with a thin focus rectangle (not visible in this frame); the group band carries the deepest blue.
- Gantt: two time bands (quarter labels row, month labels row) plus a day-number row; light grey header, weekend days shaded very lightly.
- Bars: summary as black bracket ends with a thin black line; normal activities as blue rounded rectangles; critical as red rectangles; milestones as black diamonds; relationship lines thin black with arrowheads; a red vertical data-date line crosses the chart.
- Activity names printed to the right of bars in black; bar labels can be longer than the bar.
- Activity Details: tab strip General | Status | Resources | Predecessors | Successors (active tab raised white, inactive grey); a record navigator row with up/down arrows, an activity selector, `Activity ID`, and `Project`; two field rows with beveled grey comboboxes and `...` pickers; field labels above the inputs, left aligned.
- Status bar: six sunken panes: Portfolio / Access Mode / Data Date / Baseline / User / DB.
- Colour notes: window `#f0f0f0`, header `#e6e6e6`–`#f6f6f6`, grid `#c8c8c8`, blue `#1f4f9f`, green `#67b52f`, critical red `#d93a3a`, Gantt background `#ffffff`.

### Image 3 — WBS window

- The Activities and WBS windows are tabs inside one window frame (`Activities` and `WBS`), active tab underlined.
- WBS layout bar: `Layout: WBS` plus a filter field.
- Columns: WBS Code, WBS Name, Total Activities (right aligned).
- The first row is selected: solid blue fill, white text.
- Tree: expand/collapse boxes with blue `+`/`−`; indentation ≈16 px per level; WBS codes repeat the parent path (`1542-1.00.2.3.2`).
- Icons: small blue/purple tree-node glyphs before each name; root level uses a distinct glyph.
- Gantt pane still visible at the right (January 2007 columns), empty for the WBS rows.
- Toolbar and directory strips identical to image 2.

### Image 4 — Activity Details tab customization

- Dialog 614×391, light chrome, title `Activity Details`.
- Two list boxes side by side with sunken borders and small caps headings: `Available Tabs` (Codes, Discussion, Expenses, Feedback, Notebook, Relationships, Risks, Steps, Summary, WPs & Docs) and `Display Tabs` (General, Status, Resources, Predecessors, Successors).
- Between the lists: four square arrow buttons stacked (`→`, `⇉`, `←`, `⇇`) with grey faces and blue arrow glyphs.
- Right side: vertical stack of full-width buttons with icons: OK (green tick), Cancel (red cross), Apply (green plus), Default (green flag), Help (yellow question mark). Buttons ≈90×24 px, 6 px gaps.
- Lists have white background, 1 px border, rows ≈16 px, no zebra striping. Nothing is selected in either list.

### Image 5 — Group and Sort

- Main dialog, 800×535 (screenshot includes a nested Sort dialog overlaying the right half).
- Left column `Display Options`: Show Group Totals (checked), Show Grand Total, Show Summaries, Shrink vertical groups.
- `Group By` list: WBS level 1 selected (blue), WBS level 2–5 below, scrollbar; radio/selection is expressed by highlight.
- `Group By Options`: Hide if empty; Sort bands alpha…; Show: Title (checked), ID / Code, Name / Description (checked).
- Right command column: OK, Cancel, Apply, Delete, then Add (+), Delete (×), Move Up, Move Down (disabled), Sort…, Default, Help. Icons are colour glyphs on small buttons.
- Nested `Sort` dialog: `Field Name` combo showing `Activity ID`; `Sort Order` list with `Ascending` selected in blue and `Descending` below; OK/Cancel.
- Font and Color entry is available in the full dialog (below the fold in this capture).
- Overall: dense, 8 pt text, no card styling; every command is a button with an icon.

### Image 6 — Timescale

- Dialog 511×404, title `Timescale`.
- `Timescale Format` group: Two Lines (selected) / Three Lines radios.
- `Timescale Start`: text field with value `PS` and a `...` browse button.
- `Font & Color`: a preview button showing `AaBbYyZz`; separate `Default Font` button.
- `Date Format` group: `Show Primary Dates` radio (selected), `Type` combo (`Calendar`), `Date Interval` (highlighted yellow because focused) with an open list: Quarter/Month, Month/Week, Week/Day 1, Week/Day 2, Day/Shift, **Day/Hour (selected)**, Year/Financial Period, Quarter/Financial Period.
- `Shift Calendar` field; `Show Ordinal Dates` section with `Ordinal Start` and `Ordinal Date Interval`.
- Buttons on the right: OK, Cancel, Apply, Help, vertically stacked, same icon language as image 4.

### Image 7 — Project Calendar

- Red title bar in this capture (`Project Calendar: GBL Project-Normal Calendar`) — a themed/third-party skin; not treated as a CUBI colour requirement.
- Top radios: Total work hours/day, Detailed work hours/day (selected).
- Month navigation `< August 2017 >`; weekday header band in blue-grey; dates in a 7-column grid; Saturday/Sunday tinted blue (nonworking); day 14 has a black focus outline.
- Right panel `Work hours`: two sub-columns 00–30 and 30–60, rows 1–24, working rows striped blue.
- Command buttons: OK, Cancel, Help; then Work (green +), Nonwork (red ×), Standard (disabled); Workweek…, Time Periods… buttons with small calendar icons.
- Legend: Standard (white swatch), Nonwork (blue swatch), Exception (white swatch).
- `Inherit holidays and exceptions from Global Calendar` with a combo defaulting to `GLB Project-Normal Site Calendar`.

### Image 8 — Resource Assignments

- Same shell as image 2; window tabs `Activities` and `Resource Assignments` (active underlined).
- Layout bar: `Layout: P11-Demo-Quantity Plan`; right pane header `Display`.
- Table: Activity ID, Activity Name, Budgeted Units, Unit of Measure. Group bands bright blue; summary rows green; selected activity row pale blue with a blue left edge.
- Time-phased grid: month band (December 2016 … March 2017), weekly columns labelled with day numbers (12, 19, 26, 02, 09…), light grey empty cells, green band on group rows, black right-aligned numeric values, vertical scrollbar.
- Left directory and right command strips identical to image 2.
- Status bar identical panes.

### Image 9 — Activity Network and Trace Logic

- Layout `Activity Network`, filter `All Activities`.
- Upper area: table left (Activity ID, Activity Name, Original Duration, Remaining Duration, Duration %, Start, Finish) and Gantt right; group band blue, summary bars green, normal bars red (critical), milestones as diamonds.
- Selected activity row pale blue with a left blue edge.
- Lower area: Trace Logic diagram on a white canvas. Each node is a yellow box with a thin dark border, ID label in small text at the top-left, activity name at the bottom-left; the selected node has a thick purple border; relationship lines are red orthogonal connectors with arrowheads; predecessor nodes can sit above the successor row (Begin Building Construction) with a longer routed line.
- No toolbar inside the lower pane; the diagram is part of the window layout.

### Image 10 — Toolbar and navigation arrangement

- Annotated callouts: title bar, menu bar, Quick Access toolbar, Directory (left), Command Bar (right).
- Quick Access toolbar: two rows — the first with file/print/edit icons and two search fields, the second with view/layout icons.
- Directory: a vertical panel with text labels under small icons (Projects, Resources, Reports, Tracking, WBS, Activities, Assignments, WPs & Docs, Expenses, Thresholds, Issues, Risks).
- Command bar: vertical icon strip, grouped by separators, containing view icons at the top, then column/filter/group/layout icons, then move/reorder arrows at the bottom.
- Table: yellow rows for WBS summary levels, green group bands, blue selected row (`(New Project)`), normal white rows; Gantt light with year band and monthly columns.
- Activity Details tabs: General, Status, Resources, Relationships, Codes; a resource assignment table with columns Resource ID/Name, Curve, Cost Account, Units/Time, Price/Unit, Budgeted Units, Actual This Period Units, Actual Units, Remaining Units, At Completion Units; command buttons Add Resource, Add Role, Assign by Role, Remove.
- Bottom window edge has a horizontal scrollbar and a resize grip.

## Colour token inventory (approximate, sampled visually)

These are observations of the reference screenshots, not authoritative Oracle values. CUBI tokens below are the values actually used by the implementation.

| Role | Reference observation | CUBI token |
| --- | --- | --- |
| Window / app background | `#f0f0f0` light grey | `--cp-ui-window` `#eef1f5` |
| Panel / table background | `#ffffff` | `--cp-ui-surface` `#ffffff` |
| Toolbar / header band | `#e8e8e8` gradient | `--cp-ui-chrome` `#f4f6f9` |
| Border / grid line | `#b8b8b8` / `#cfcfcf` | `--cp-ui-border` `#c3ccd8`, `--cp-ui-grid` `#dfe5ec` |
| Primary / selection blue | `#1f4f9f` | `--cp-ui-primary` `#1c4f8f` |
| Group band blue | `#2456a4` | `--cp-ui-band` `#1c4f8f` |
| Selection row | `#b9d8f5` | `--cp-ui-selected` `#cfe3f7` |
| Summary green | `#67b52f` | `--cp-ui-summary` `#4f9a3c` |
| Critical red | `#d93a3a` | `--cp-ui-critical` `#c0392b` |
| Normal bar blue | `#2f5fa8` | `--cp-ui-bar` `#2f5fa8` |
| Nonworking / weekend | `#e8eef7` pale blue | `--cp-ui-nonwork` `#eef2f7` |
| Milestone | black diamond | `--cp-ui-milestone` `#1f2937` |
| Yellow trace node | `#fff200` | `--cp-ui-node` `#fff3b0` |
| Status bar text | dark grey on light grey | `--cp-ui-status` `#2b3440` |

## Typography

- Reference UI text is small Windows UI type (Tahoma / Segoe UI, ~8–9 pt ≈ 11–12 px); table rows ≈17 px; headers bold 11 px.
- CUBI uses Inter for Latin and Vazirmatn for Persian, 12 px base, 11 px table, 12 px menu, 13 px dialog titles. Numbers are tabular in tables.
- The reference never uses large marketing headings inside the workspace; CUBI keeps workspace headings compact (13–15 px).

## Geometry and density

- Menu bar 22 px, toolbar rows 26 px, layout bar 22 px, status bar 22 px in the reference.
- CUBI: menu bar 30 px, toolbar 36 px, layout bar 32 px, status bar 28 px — larger for pointer and touch, same density ordering.
- Table header 28 px, row 26 px (reference 17 px is below current accessibility guidance; CUBI keeps professional density but readable).
- Dialog buttons 92×26 px; list rows 24 px; group boxes with 1 px border and 8 px padding.

## Visual comparison checklist

For each built surface, compare against the observations above:

- [ ] Eight menu groups, order and labels: Workspace, Edit, View, Project, Organization, Tools, Administration, Help.
- [ ] Menu popups are grouped with separators; shortcuts right aligned; disabled items visibly disabled.
- [ ] Toolbar buttons have icon, tooltip, hover, pressed and disabled states; overflow scrolls, never clips.
- [ ] Window tabs show active state and close affordance; opening a window activates its tab.
- [ ] Activities table: WBS indentation, group band, summary rows, selected row and cell, grid lines, frozen ID/Name.
- [ ] Gantt: multi-line timescale, nonworking shading, critical red, summary brackets, milestones, relationship arrows, data date line.
- [ ] Activity Details: tab strip, navigator, field grid; no blank tab.
- [ ] Dialogs: title bar, group boxes, labelled inputs, right-hand command column, OK/Cancel/Apply/Help.
- [ ] Status bar: project, data date, baseline, user, database.
- [ ] RTL mirroring: menus, table order, splitter direction, arrows.
- [ ] No Oracle, Primavera or P6 string or logo anywhere in the workspace chrome.
- [ ] Demo data is labelled as preview data, never presented as calculated or saved.

## Known gaps in the evidence

1. Image 1 could not be retrieved (HTTP 403 from Oracle, no archive). The "complete Activities workspace with the Edit menu open" therefore relies on the remaining screenshots and the Version 26 help pages.
2. Images 2–10 are not Version 26. Features that exist only in newer releases were taken from the official help pages, not from screenshots.
3. The reference screenshots are raster captures at 96 dpi on Windows 7/10; exact font metrics cannot be reproduced, only the hierarchy and density.


### Desktop Professional edition tab correction — 2026-11-03

The Version 26 desktop Professional Help index distinguishes desktop Activity Details from EPPM-only detail tabs. The visual shell previously exposed the **Tasks** tab in Activity Details and **Planning Resources** in Project Details, both explicitly marked EPPM-only by the official Details Windows index. These were removed from the desktop workspace tab inventories. This prevents the Professional desktop shell from presenting server-edition-only tabs as native desktop features. The Professional-only Activity Details > Risks tab remains in scope. Verification is covered by the Activity Details tab inventory test and the Project Details tab inventory test.

Official reference: https://docs.oracle.com/cd/G48902_01/client_help/en_US/detailswindows-postdropdowns.htm

The Version 26 Activity Details page lists **Summary** as a native tab, and the Details Windows index separately lists **Update History**. The prior audit incorrectly classified Summary as a CUBI extension; its origin is corrected to `desktop-reference`. Update History is retained as a native tab. The EPPM-only Tasks tab remains excluded.



## Activity-window filter command parity — 2026-11-03

- Version 26 desktop reference: the View menu exposes **Filter By**, which opens the Filters dialog; the Edit menu's **Find** action is a separate text-search command. The Activities window documentation also distinguishes filtering from Find/search and exposes filter selection alongside layout, grouping, sorting, columns, and timescale controls.
- CUBI correction: the desktop View > Filters command and the Layout toolbar Filters command now dispatch the dedicated filter-dialog action instead of the Find/search action. Edit > Find remains a separate command and retains its Ctrl+F behavior.
- The filter dialog remains honest about current implementation boundaries: it applies the connected text criterion, while saved filter definitions and multi-condition criteria remain explicitly unavailable rather than being represented as working controls.
- Regression coverage asserts that both the View menu and toolbar Filters entries target the dedicated filter-dialog command.
- Reference pages: https://docs.oracle.com/cd/G48902_01/client_help/en_US/activities_window.htm and https://docs.oracle.com/cd/G48902_01/client_help/en_US/49095.htm.

## WBS window — table/chart presentation — 2026-11-03

- Version 26 desktop WBS window supports a WBS table and WBS chart in the top layout, WBS Details in the bottom layout, and hierarchy operations including expand/collapse and move controls.
- CUBI correction: the WBS module's previously disabled Chart View control is now an active presentation toggle. It reuses the same ordered project WBS hierarchy and selected-node state, presenting the hierarchy as connected cards; Table View restores the hierarchy-list presentation. Selecting a node remains the same action in both views.
- This is a visual presentation of current WBS records only; it does not invent missing WBS attributes, alter hierarchy data, or claim the full desktop WBS chart editing/formatting toolset is complete.
- Regression coverage added for both view controls and chart-mode dispatch.
- Reference: https://docs.oracle.com/cd/G48902_01/client_help/en_US/wbs_window.htm.
## Tracking window pane parity — 2026-11-03

- Version 26 desktop Tracking is not a single chart card. Its documented workspace includes the Project Explorer at upper left and the active Top Layout at upper right; supported layouts may add the Resource Explorer at lower left and Bottom Layout at lower right. Pane display options control the top, bottom, and left columns.
- CUBI correction: the Tracking window now renders a real multi-pane frame with Project Explorer, Top Layout, Resource Explorer, and Bottom Layout. Project Table and Project Bar Chart use the upper explorer/top-layout arrangement; Project Gantt/Profile and Resource Analysis expose the lower explorer and lower layout panes. The layout selector changes the visible surface and persists its selection through re-render within the window.
- The four layout surfaces are intentionally empty-state shells until the project/tracking data services are available. No project values, charts, profiles, or resource analysis results are fabricated; Refresh and Save remain unavailable.
- Regression assertions cover the four-pane inventory and the default hidden state of lower panes and inactive chart surfaces.
- Reference: https://docs.oracle.com/cd/G48902_01/client_help/en_US/tracking_window.htm.

- Follow-up correction: added a dedicated Display Options group with independent show/hide controls for Project Explorer, Top Layout, Resource Explorer, and Bottom Layout. The controls expose their state through `aria-pressed`, update the pane frame immediately, and preserve visibility choices when the workspace re-renders. The Resource Explorer and Bottom Layout remain available only for the two split-pane layout types, matching the documented layout behavior.
- The pane frame now uses an explicit two-column/two-row arrangement for split layouts and a full-height top layout for Project Table and Project Bar Chart; hidden panes no longer retain visible grid space. Narrow viewports can wrap the display controls without forcing a wide toolbar.
- Regression coverage verifies that pane visibility changes are dispatched, reflected in the rendered state, and retained across a subsequent render.
- Scope remains honest: project/resource selection, summarized data, live charts, and persistent saved layouts remain unavailable until their authoritative services exist.
- Additional reference: https://docs.oracle.com/cd/G48902_01/client_help/en_US/49095.htm (View Menu: Show on Top, Show on Bottom, and Tracking layout display options).

## Calendar editor visual parity — 2026-11-03

- Version 26 Professional calendar dialog separates the calendar pool (Global, Project, Resource), standard workweek, dated exceptions, and Hours per Time Period; calendar editing also exposes month navigation, Work / Nonwork / Standard, Workweek, Time Periods, inheritance from a global calendar where applicable, and Used By assignments.
- CUBI visual correction: the calendar register now distinguishes the five detail areas (General, Workweek, Exceptions, Time Periods, Assignments). The standard workweek table visibly supports two daily work intervals rather than a single start/finish pair. The exceptions area has date-range and exception-record columns; Time Periods has separate Hour, Day, Week, Month and Year conversion rows. Calendar record selection and detail-tab selection are preserved within the open workspace window.
- A default-tab visibility defect was corrected: General is visible on first open, while all other detail panels are hidden; selecting another tab updates ARIA selection and panel visibility, and the selected tab survives a re-render.
- No work hours, holiday dates, inheritance, assignments or conversion factors are fabricated. Write controls remain disabled until the authoritative calendar service is connected. This is a visual-shell completion, not a claim that calendar CRUD is operational.
- Regression coverage checks the five-tab inventory, split work intervals, time-period panel, initial panel visibility, and selected-tab persistence.
- References: https://docs.oracle.com/cd/G48902_01/client_help/en_US/calendar_dialog_box.htm and https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/globalcalendars.htm.

## Calendar register selection — 2026-11-03

- Version 26 Professional Help documents distinct Global, Project, and Resource calendar pools, their creation/edit/delete workflows, default calendar settings, and calendar assignment lookup. The current CUBI calendar read contract exposes only calendar ID, name, type, kind, version, and record revision.
- CUBI correction: calendar register rows are now selectable. Selection is retained for the lifetime of the open workspace window and drives the Calendar Details heading plus a read-only identity summary using only fields present in the authoritative calendar catalogue. No working hours, shift patterns, exception dates, or assignments are inferred from the calendar name or type.
- New/Edit/Delete and the calendar editor's editable controls remain disabled until a calendar write contract supplies the complete versioned calendar definition and save lifecycle. This is intentional and avoids presenting non-persisting controls as operational.
- Regression coverage verifies selection, selected-row state, and the identity summary.
- Reference: Oracle P6 Professional Help Version 26, Table of Contents → Defining Calendars → Project Calendars / Global Calendars / Resource Calendars: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm.
## Resource Assignments window — usage spreadsheet surface — 2026-11-03

- Version 26 desktop reference requires the Resource Assignments window to support assignment-table customization, grouping/sorting/filtering, timescale selection, Resource Usage Spreadsheet, and Assignment Details.
- CUBI correction: replaced the generic register-only presentation with a dedicated Assignment Analysis strip and a user-toggleable Resource Usage Spreadsheet surface. The spreadsheet exposes time scale and data-field selectors for budgeted, actual, remaining units and costs, plus period columns; no assignment rows or period values are invented.
- The assignment details tabs remain General, Planning, Costs, Units & Prices and UDFs. The usage spreadsheet can be shown/hidden without losing the selected presentation during a rerender.
- Editing, fill-down/across, field customization and persistence remain disabled until the authoritative assignment service supplies editable assignment and period-bucket records.
- Regression coverage added for toggle behavior and the empty-data contract.
- Reference: https://docs.oracle.com/cd/G48902_01/client_help/en_US/resource_assignments_window.htm.

## Tracking window — layout management commands — 2026-11-03

- Version 26 desktop reference defines four tracking layout types: Project Table, Project Bar Chart, Project Gantt/Profile and Resource Analysis. The Tracking window is pane-based, with Project Explorer and Top Layout always represented, and optional Resource Explorer and Bottom Layout panes.
- CUBI already exposed the four layout types and display-pane toggles. This pass adds the visible layout-management command group: New Layout, Open Layout, Save As, Import, Export and Delete Layout, each explicitly disabled with a reason while the tracking-layout store is unavailable. This avoids implying that a click has persisted a layout.
- Reference: https://docs.oracle.com/cd/G48902_01/client_help/en_US/tracking_window.htm; https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/types_of_tracking_layouts.htm; https://docs.oracle.com/cd/G48902_01/client_help/en_US/layout_toolbar.htm.

## E2E submenu count correction — 2026-11-03

- Updated the preview E2E submenu inventory selector to count actionable submenu buttons as well as links and disabled submenu entries. The prior selector excluded functional buttons and falsely failed the Control navigation inventory despite the menu exposing its actions.

## WBS Details — native inventory vs CUBI extension — 2026-11-03

- The Version 26 Professional WBS Details inventory contains General, Notebook, Budget Log, Spending Plan, Budget Summary, WBS Milestones, WPs & Docs, Earned Value and User Defined Fields. Planning Resources is EPPM-only; there is no native WBS Details Activities tab.
- CUBI retains the useful linked-activities view as an explicitly marked **Related Activities (CUBI extension)** tab, appended after all native WBS Details tabs. Its origin is encoded in tab metadata and its tooltip.
- Reference: https://docs.oracle.com/cd/G48902_01/client_help/en_US/wbs_details.htm.

## Calendar window — read-only month canvas — 2026-11-03

- Added a dedicated Calendar tab alongside General, Workweek, Exceptions, Time Periods, and Assignments.
- The month canvas generates actual date labels using the workspace-selected calendar mode: Gregorian weeks begin Sunday; Jalali weeks begin Saturday. Previous, Today, and Next navigate by calendar month, including correct month boundaries.
- The calendar legend is present for Standard, Exception, and Nonworking classifications, but the dates remain visually unclassified and explicitly say that working status is not loaded. No workday, holiday, exception, or hours data is fabricated.
- Editing remains disabled until the authoritative calendar service is connected. This is a visual/navigation completion, not a claim that calendar editing or scheduling integration is complete.
- Regression coverage checks the six detail tabs, 42-cell month canvas, navigation controls, and honest unknown-status state.
- Reference: Version 26 Professional User Guide, “Edit a global calendar” and “Edit a project calendar”: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/edit_a_global_calendar.htm. The calendar dialog's month navigation, Work/Nonwork/Standard, Workweek, and Time Periods controls are also documented here: https://docs.oracle.com/cd/F51303_01/client_help/en_US/calendar_dialog_box.htm.


## Project and Activity Details — native and additive tab provenance — 2026-11-03

- Contract Management is a CUBI addition to Project Details and is not part of the Version 26 native tab inventory. Summary is a native Activity Details tab and must not be classified as a CUBI extension.
- CUBI correction: Contract Management is visibly labeled as a CUBI extension, appended after the native Project Details tabs, and carries `data-detail-origin="cubi-extension"` metadata and an explanatory tooltip. Activity Summary carries `data-detail-origin="desktop-reference"`.
- References: https://docs.oracle.com/cd/G48902_01/client_help/en_US/detailswindows-postdropdowns.htm; https://docs.oracle.com/cd/G48902_01/client_help/en_US/wbs_details.htm.

## WBS top-layout parity refinement — 2026-11-03

- The Version 26 desktop WBS window supports three distinct top-layout surfaces: WBS Table, WBS Chart, and Gantt Chart; WBS Details is a separate bottom layout. The desktop WBS Details inventory includes General, Notebook, Budget Log, Spending Plan, Budget Summary, WBS Milestones, WPs & Docs, Earned Value and UDFs. Planning Resources is EPPM-only and remains excluded.
- CUBI correction: Table View is now a true hierarchy-aware grid with only fields present in the loaded WBS model (local code, name, parent and sequence). Chart View remains the hierarchy-card view. Gantt Chart is exposed as a separate top-layout choice, but its timeline remains an explicit empty state because the current WBS records do not contain WBS start/finish dates; no dates or bars are invented. The selected top layout persists across re-renders.
- The Related Activities detail is retained as a clearly marked CUBI extension, not a native WBS Details tab.
- Remaining WBS parity work: chart formatting and layout templates, chart arrangement/alignment, expand/collapse and move toolbar controls, WPs & Docs assignment actions, and richer detail panels once their corresponding records are available.
- References: https://docs.oracle.com/cd/G48902_01/client_help/en_US/wbs_window.htm and https://docs.oracle.com/cd/G48902_01/client_help/en_US/wbs_details.htm.

## Calendar register — pool filtering and lookup commands — 2026-11-03

- Version 26 desktop Calendars dialog distinguishes Global, Project and Resource pools; its Display Options bar supports searching calendars, and Resource calendars support Shared/Personal filtering. Calendar actions include Add, Delete, Modify, Used By, and calendar-pool conversions where applicable.
- CUBI correction: added live client-side search over the loaded calendar identity fields. Search filters only loaded rows and shows an explicit no-match row; it does not create or infer calendar data. Existing Global/Project/Resource pool buttons remain separate.
- CUBI's visible Used By and To Global / To Shared / To Personal actions are now represented in the register toolbar but remain disabled with the current unavailable-service boundary; Add/Edit/Delete are also disabled until calendar persistence is connected.
- Regression coverage added for search behavior, pool controls, and the disabled management actions.
- Reference: https://docs.oracle.com/cd/G48902_01/client_help/en_US/calendars_dialog_box.htm; https://docs.oracle.com/cd/G48902_01/client_help/en_US/calendars_dialog_box.htm.
## Resource Assignments — Usage Spreadsheet display controls — 2026-11-03

- Version 26 Resource Assignments supports a right-pane Resource Usage Spreadsheet, with time-phased quantity or cost fields, configurable timescale, spreadsheet field selection, and Assignment Details. Its values are editable only under the documented security, preference, and timescale conditions.
- CUBI correction: the assignment workspace now exposes active Timescale and Data selectors plus a Spreadsheet Fields dialog. The selected presentation preferences persist across re-renders within the open window, and the field chooser requires at least one selected field. The grid remains an honest empty state until time-phased assignment records are supplied; no periods or quantities are fabricated as data.
- Editing and fill-down/across remain unavailable until authoritative assignment period-bucket data and permission checks are connected.
- Regression coverage verifies opening/applying the field chooser and changing timescale.
- Reference: https://docs.oracle.com/cd/G48902_01/client_help/en_US/resource_assignments_window.htm; https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/the_resource_usage_spreadsheet.htm.
## Calendar month dialog controls and dual calendar display — 2026-11-03

- The calendar's Calendar tab now renders a 42-cell month grid using the selected Jalali or Gregorian display mode, localized month/year and weekday labels, and previous / Today / next navigation. The grid deliberately labels each date's working status as not loaded; its legend is informational only and does not color dates as working or nonworking without authoritative calendar data.
- The visual toolbar now includes the documented Total work hours/day and Detailed work hours/day display modes, Work / Nonwork / Standard commands, and direct navigation to Workweek and Time Periods. Date classification and write actions remain disabled until calendar records and permissions are supplied. The General panel includes the global-calendar inheritance selector, also disabled until authoritative values are loaded.
- Regression tests cover month navigation, both calendar display modes, the 42-day grid, explicit unknown work-status state, the documented work-hour controls and navigation.
- Reference: https://docs.oracle.com/cd/G48902_01/client_help/en_US/calendar_dialog_box.htm.

## Resource Details and navigation inventory — 2026-11-03

- The Professional desktop Resource Details inventory is General, Codes, Details, Units & Prices, Roles, Notes and UDFs. Progress Reporter is explicitly EPPM-only and is excluded from the desktop resource window.
- CUBI correction: the Resource register now uses the desktop detail-tab inventory, removes duplicate Rates (covered by Units & Prices) and non-native Assignments / Calendars tabs from Resource Details, adds the missing Details and Unit of Measure fields, and aligns the resource submenu actions with the seven desktop tabs. Resource Assignments remains a separate window.
- Resource records and hierarchy are not yet supplied by the resource service, so the register stays an honest empty state and all write/move operations remain unavailable. The visual shell does not invent resource IDs, rates, availability, or hierarchy nodes.
- Remaining parity work: resource hierarchy/list switch, move toolbar, full Details and Units & Prices forms, rate history, resource shifts and resource calendar assignments after authoritative records are available.
- Reference: https://docs.oracle.com/cd/F74771_01/client_help/en_US/resource_details.htm and Version 26 Professional User Guide, Resources chapter: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/resources.htm.

## Resource Assignments top-layout pane parity — 2026-11-03

- Version 26 Professional documents the Resource Assignments window as an assignment register with a Resource Usage Spreadsheet in the right pane and Assignment Details in the bottom layout. The spreadsheet exposes time-phased quantity/cost fields, timescale selection, spreadsheet field customization, and grouping/sorting/filtering controls.
- CUBI correction: the Resource Assignments workspace now opens with the assignment register and Resource Usage Spreadsheet side by side; Assignment Details remains below. The spreadsheet can be collapsed to give the register the full width. Its timescale and field chooser remain interactive presentation preferences.
- No resource assignment or time-phased values are loaded, so the spreadsheet uses a truthful empty state and does not invent period values. Manual planning/editing remains unavailable until authoritative assignment records and permissions are connected.
- References: https://docs.oracle.com/cd/E90748_01/client_help/en_US/resource_assignments_window.htm and https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/resourceusagespreadsheet.htm.

## WBS Chart Display Options — 2026-11-03

- Version 26 WBS chart display includes Chart Box Template and Chart Font and Colors commands. The documented controls include choosing the information shown in WBS boxes, font, background color, and WBS box color.
- CUBI correction: added chart-only display controls for Code + Name / Name only / Code only, font family, font size, canvas background, and WBS node color. Changes apply immediately to the chart presentation and remain local to the open workspace window; they do not modify WBS records.
- The View menu now exposes Chart Box Template and Chart Font and Colors entries when the WBS window is active; both route to the same contextual display-options surface. The controls remain disabled outside the WBS window.
- Remaining parity: chart arrange/alignment, zoom-to-fit, full box templates, and matching Project/Resource chart settings.
- Reference: https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_the_work_breakdown_structure_chart_display.htm; https://docs.oracle.com/cd/G48902_01/client_help/en_US/wbs_window.htm.
## Project Expenses register and details parity — 2026-11-03

- The desktop Project Expenses window provides an expense register and a separate Project Expense Details pane. The documented detail areas are General, Activity and Costs; the current Help also includes Description. Expense-specific fields include category, vendor, cost account, document number, activity/WBS assignment, accrual type, price/unit and budgeted, actual and remaining cost.
- CUBI correction: the Expenses register now exposes the desktop detail inventory (General, Activity, Costs, Description), removes unrelated Documents and UDFs tabs, adds missing expense category, document number, unit price and remaining cost columns, and routes the matching navigation submenu actions to those detail tabs.
- Expense records are not currently loaded; create/edit/delete remain disabled and no expense values are fabricated.
- References: https://docs.oracle.com/cd/F25600_01/client_help/en_US/project_expenses_window.htm and https://docs.oracle.com/cd/E75426_01/client_help/en_US/project_expense_details.htm.

## Work Products and Documents detail parity — 2026-11-03

- The desktop WPs & Docs window supports document records in a hierarchy, move controls in outline view, a bottom WP & Doc Details pane, file location references, and assignments to activities and WBS elements. Native detail areas include General, Files and Assignments; CUBI retains UDFs plus its own Links, Integrity and Revisions views.
- CUBI correction: Files and Assignments are now first-class detail tabs. Files exposes private/public location and Launch/Browse controls (disabled while the document service is unavailable). Assignments exposes the WBS/activity association table and Work Product flag (empty until assignment data is loaded). The CUBI-specific tabs are explicitly labeled as extensions, and navigation routes to each native or extension tab.
- No document file paths, assignment rows or work-product flags are fabricated. Create, upload, launch, assign and remove operations remain disabled until the document service and permission checks are connected.
- References: https://docs.oracle.com/cd/F51303_01/client_help/en_US/wps_and_docs_window.htm and Version 26 User Guide, Work Products and Documents: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/p6_pro_user.pdf.

## Projects window — top-layout surfaces — 2026-11-03

- Version 26 Projects window supports Project Table, project chart view and Project Gantt Chart in the top layout, with Project Details as a separate bottom layout. The window is also scoped by the currently selected portfolio and supports EPS hierarchy navigation.
- CUBI correction: added explicit Project Table, Project Chart and Gantt Chart top-layout switching. The chart view shows only the single authorized project record and its loaded WBS/activity counts. The Gantt view remains an honest empty state because the current session record does not expose project start/finish dates. The page continues to state that portfolio and sibling EPS/project records are not loaded, rather than fabricating them.
- Remaining parity: portfolio selector and EPS tree when those records are supplied; project table columns, project-chart box formatting, Gantt timescale/bars, project context menu and full top/bottom layout options.
- Reference: https://docs.oracle.com/cd/G48902_01/client_help/en_US/projects_window.htm.
## Resources window — resource type filter parity — 2026-11-03

- Version 26 Professional resource records distinguish Labor, Nonlabor and Material resource types. The Resources window includes a resource register and Resource Details tabs General, Codes, Details, Units & Prices, Roles, Notes and UDFs; Progress Reporter is EPPM-only.
- CUBI correction: added All Types, Labor, Nonlabor and Material filter controls with selected-state behavior. The current project API does not return resource rows, so the filter state is reflected without creating sample labor, equipment or material records. Resource creation, hierarchy changes, pricing and assignment calculations remain unavailable until the authoritative resource service is connected.
- Reference: Version 26 Professional Help, Table of Contents → Defining Resources and Roles → Resources; Details Windows index: https://docs.oracle.com/cd/G48902_01/client_help/en_US/detailswindows-postdropdowns.htm.
## Activity Details record navigator — 2026-11-03

- Version 26 Activity Details provides Previous and Next navigation plus Activity ID, Activity Name and Project fields above the tab strip. The Summary tab is part of the native desktop inventory; it is no longer labeled or tagged as a CUBI extension.
- CUBI correction: added Previous/Next navigation across the currently loaded activity order and read-only Activity ID, Activity Name and Project fields. Navigation calls the existing activity-selection callback; identity fields remain read-only until the authorized activity update workflow is available.
- Regression coverage verifies adjacent-record navigation, displayed identity values and native Summary provenance.
- Reference: https://docs.oracle.com/cd/G48902_01/client_help/en_US/activity_details.htm.