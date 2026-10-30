# CUBI Workspace — Visual Reference Audit

Mission: visual implementation order, 2026-10-30. This document records what was actually opened and seen before building the CUBI visual shell. It is an inspection log, not a design brief.

## Method and honesty notes

- Direct image URLs were fetched with `curl`/Node into a temporary folder outside the repository; the images were then opened at readable resolution and inspected one by one.
- Where a host refused the request, an image proxy (`images.weserv.nl`) was used and the result is marked below. That proxy re-encodes the image but does not change its content.
- Reference files are **not** copied into the application, not committed, and not shipped as CUBI assets. Only the observations and the source register are kept.
- Version caveat: only the Oracle Version 26 documentation is authoritative for feature inventory. The screenshots are older releases (8.3–18) and third-party captures; they are used for layout, density, colour and interaction patterns only.
- Oracle Version 26 documentation was re-opened on 2026-10-30:
  - `https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/index.html` — loads; document G57529-01, release 26, publication October 2026; body is JavaScript-rendered, so structure was confirmed through the linked help pages.
  - `https://docs.oracle.com/cd/G48902_01/client_help/en_US/menu_bar.htm` — loads; confirms File, Edit, View, Project, Enterprise, Tools, Help and the conditional Admin menu (Admin appears only when connected to a Professional database).

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
