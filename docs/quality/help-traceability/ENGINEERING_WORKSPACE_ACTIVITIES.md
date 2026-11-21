# Engineering — Workspace and Activities

Section 2 of the Help traceability workstream.
Verified: 2026-11-21 · Canonical rows: `docs/traceability/engineering-v26.json`
Help baseline: P6 Professional V26 HTML Help (`G48902-01`) and User Guide
(`G57529-01`). Every URL below returned HTTP 200 and is listed in the official
TOC (see `OFFICIAL_HELP_BASELINE.md`).

## 1. Scope

This section covers the Engineering workspace shell, the Activities window and
the Activity Table: columns, sorting, grouping, filtering, saved layouts,
selection, scope counts, quick search, export scopes, adding and editing.

It does **not** restate the Gantt, WBS, Activity Details or Resource surfaces;
those are Sections 3–4. Row IDs reuse `docs/traceability/engineering-v26.json`
where one exists.

Status semantics:

- **Doc status** — `DOCUMENTED`, `HELP_VERIFIED`, `TEST_SPECIFIED`.
- **Product status** — the observed implementation state in this repository:
  `IMPLEMENTED`, `PARTIAL`, `NOT_IMPLEMENTED`. It is never derived from the
  document. `FUNCTIONALLY_VERIFIED` requires an executed run and is not claimed
  in this section.

## 2. Traceability matrix

`Env` = **Engineering** · `Page / module` = **`/app/activities/`** plus the
workspace shell rows. Dependencies and expected results are stated once in §3;
every scenario below records its own expected result, negative, permission and
persistence outcome.

| Row ID | Functional item | Help topic · section | Direct Help URL | User Guide · URL | Expected behavior (from Help) | Inputs and validation | Scenario | Doc status | Product status · evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ENG-WS-SHELL | Open the project workspace and its windows | Using main windows · Opening windows; Project-specific data windows | https://docs.oracle.com/cd/G48902_01/client_help/en_US/using_main_windows.htm | Using main windows · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/usingmainwindows-20501a.html | A project window opens as a tab; the active window name is shown; windows can be opened and closed independently. | Requires an authorized project; no window opens without a project scope. | ENG-WS-ACT-01 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-desktop-shell.test.ts` |
| ENG-WS-ACTIVITY-TABLE | Activity table content | The Activity Table · Customizing Activity Layouts > Activity Table | https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_activity_table.htm | The Activity Table · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/theactivitytable-19431a.html | The table lists the open project's activities and their values; it can be customized, filtered, sorted and grouped. | Only activities in the authorized project scope are read. | ENG-WS-ACT-01 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-view.test.ts` |
| ENG-WS-ACTIVITY-TABLE | Define visible columns | Define Activity Table columns · Customizing Activity Layouts > Activity Table | https://docs.oracle.com/cd/G48902_01/client_help/en_US/define_activity_table_columns.htm | Define Activity Table columns · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/defineactivitytablecolumns-19061a.html | Available columns can be added, removed, and all can be added or removed; the selected order is the display order. | A column must exist in the field registry; unknown ids are rejected, not rendered. | ENG-WS-ACT-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/p6-columns-dialog.test.ts` |
| ENG-WS-ACTIVITY-TABLE | Column titles, width and alignment | Customize activity column titles · Customizing Activity Layouts > Activity Table | https://docs.oracle.com/cd/G48902_01/client_help/en_US/customize_activity_column_titles.htm | Define Activity Table columns · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/defineactivitytablecolumns-19061a.html | A column title may be renamed without changing the underlying field; width and alignment can be set. | Blank title is rejected; title is presentation only and never changes the field id. | ENG-WS-ACT-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/p6-columns-dialog.test.ts` (title, width 40–800, alignment start/center/end), `apps/web/src/p6-layout-persistence-adapter.test.ts` |
| ENG-WS-GROUPING | Sort the table | Sort activity information in the Activity Table · Customizing Activity Layouts > Activity Table | https://docs.oracle.com/cd/G48902_01/client_help/en_US/sort_activity_information_in_the_activity_table.htm | Sort activity information in the Activity Table · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/sortactivityinformationintheactivitytable-19707a.html | Clicking a column label sorts ascending, then descending; an arrow shows the direction. | Sorting requires a selected column; ties keep a deterministic order. | ENG-WS-ACT-03 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-view.test.ts` |
| ENG-WS-GROUPING | Group activities by field | Grouping activities by field · Grouping, Filtering, and Summarizing Data > Grouping and Sorting | https://docs.oracle.com/cd/G48902_01/client_help/en_US/grouping_activities_by_field.htm | Grouping activities by field · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/groupingactivitiesbyfield-19469a.html | One or more data items group the rows; grouping is combined with sorting to order rows inside each band. | Group fields come from the workspace group registry; clearing grouping restores the flat order. | ENG-WS-ACT-05 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-view.test.ts` |
| ENG-WS-FILTERS | Create a filter | Create a filter · Grouping, Filtering, and Summarizing Data > Filtering | https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_filter.htm | Filtering data · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/filteringdata-19459a.html | A filter has a name and one or more parameter/operator/value criteria; criteria can be added to narrow the result. | A criterion needs a known parameter, a supported operator and a value; an empty or unknown parameter is rejected. | ENG-WS-ACT-04 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-filters.test.ts` |
| ENG-WS-FILTERS | Apply a filter | Apply a filter · Grouping, Filtering, and Summarizing Data > Filtering | https://docs.oracle.com/cd/G48902_01/client_help/en_US/apply_a_filter.htm | Apply a filter · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/applyafilter-19457a.html | Checking a filter applies it to the layout; a preview is possible before committing. | Applying filters is presentation state and never edits activity data. | ENG-WS-ACT-04 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-filters.test.ts` |
| ENG-WS-FILTERS | Combine filters | Combine filters · Grouping, Filtering, and Summarizing Data > Filtering | https://docs.oracle.com/cd/G48902_01/client_help/en_US/combine_filters.htm | Combine filters · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/combinefilters-19665a.html | Several filters combine with `All` (intersection) or `Any` (union) to narrow the selection. | At least one filter must be active; mode is `all` or `any` only. | ENG-WS-ACT-04 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-filters.test.ts` |
| ENG-WS-LAYOUTS | Create a layout | Create a new activity layout · Customizing Activity Layouts > Overview | https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_new_activity_layout.htm | Create a new activity layout · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/createanewactivitylayout-19653a.html | A new layout is an existing layout saved under a new name, then modified and saved. | A layout name is required and unique within its scope. | ENG-WS-ACT-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/p6-layout-persistence-adapter.test.ts` |
| ENG-WS-LAYOUTS | Save a layout | Save a layout in the Activities window · Customizing Activity Layouts > Overview | https://docs.oracle.com/cd/G48902_01/client_help/en_US/save_a_layout_in_the_activities_or_rsrc_assignments_window.htm | Save a layout as a project layout · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/savealayoutasaprojectlayout-19659a.html | Saving persists the layout; saving as a project layout requires the project-layout right. | Saving needs the layout privilege; a stale base revision is rejected. | ENG-WS-ACT-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/p6-layout-persistence-adapter.test.ts` |
| ENG-WS-LAYOUTS | Open a layout | Open a layout · Customizing Activity Layouts > Overview | https://docs.oracle.com/cd/G48902_01/client_help/en_US/open_a_layout.htm | Open a layout · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/openalayout-19651a.html | Opening a layout prompts to save the current one; the list contains stored layouts only. | An unknown or deleted layout is not offered and never fabricated. | ENG-WS-ACT-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-layout-selector.test.ts` |
| ENG-WS-SELECTION | Multi-selection | Select multiple items · Getting Started > Workspace Basics | https://docs.oracle.com/cd/G48902_01/client_help/en_US/select_multiple_items.htm | Select multiple items · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/selectmultipleitems-21036a.html | Shift-click selects a contiguous group; Ctrl-click adds or removes individual rows. | A selection refers to read-model ids; a deleted activity is dropped from the selection. | ENG-WS-ACT-06 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-scope.test.ts` |
| ENG-WS-SELECTION | Select All scope | NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT (nearest: Select multiple items) | https://docs.oracle.com/cd/G48902_01/client_help/en_US/select_multiple_items.htm | Select multiple items · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/selectmultipleitems-21036a.html | CUBI defines Select All as the whole current filter + quick-search scope, including collapsed and grouped rows; it is never a DOM-only selection. | Disabled when the scope has zero rows. | ENG-WS-ACT-06 | `HELP_VERIFIED` (nearest), `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-scope.test.ts`, `apps/web/src/main.ts` |
| ENG-WS-ACTIVITY-TABLE | Scope counts (Total / Filter / Search / Visible / Selected / In scope) | NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT (nearest: Using the Status Bar and Layout Options bar, which does not list activity counts) | https://docs.oracle.com/cd/G48902_01/client_help/en_US/using_the_status_bar_and_display_layout_options_bar.htm | Using the Status Bar and Layout Options bar · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/usingthestatusbarandlayoutoptionsbar-21127a.html | CUBI shows six counts derived from the authoritative read model: total, filter match, search match, painted rows, selected, selected-in-scope. | Counts are read-only; each is recomputed after filter, search, grouping, collapse or selection. | ENG-WS-ACT-05 | `HELP_VERIFIED` (nearest), `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-scope.test.ts`, `apps/web/src/workspace-view.ts` |
| ENG-WS-ACTIVITY-TABLE | Quick search inside the table | Find Toolbar · Getting Started > Working with Toolbars and Menus > Menu, Toolbar, and Icon Reference | https://docs.oracle.com/cd/G48902_01/client_help/en_US/find_toolbar.htm | Find Toolbar (search/replace in the active window) — direct section URL `HELP REFERENCE NOT YET VERIFIED` | The official Find toolbar searches and replaces values in the active window. CUBI's quick search is a **scope filter** over ID, name, WBS and status, applied inside the active filter. | Case-insensitive; empty query restores the filter scope; no match shows an explicit empty state. | ENG-WS-ACT-07 | `HELP_VERIFIED` (topic), divergence documented | `IMPLEMENTED` · `apps/web/src/workspace-view.test.ts` |
| ENG-WS-ACTIVITY-TABLE | Export All / Filtered / Selected | NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT (P6 exports layouts and projects, not an activity-scope CSV) | https://docs.oracle.com/cd/G48902_01/client_help/en_US/export_a_tracking_layout.htm (nearest, different artifact) | Export a tracking layout · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/exportatrackinglayout-20193a.html | CUBI exports the chosen scope as RFC 4180 CSV using the current layout columns: all = read model, filtered = filter+search scope including collapsed rows, selected = in-memory selection in scope order. | Disabled when the scope is empty; hidden or collapsed rows are never lost. | ENG-WS-ACT-08 | `HELP_VERIFIED` (nearest), `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-scope.test.ts` |
| ENG-WS-ACTIVITY-TABLE | Edit a value in the table | Change activity information in the Activity Table · Customizing Activity Layouts > Activity Table | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_activity_information_in_the_activity_table.htm | Change activity information in the Activity Table · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/changeactivityinformationintheactivitytable-19697a.html | Double-clicking a value edits it in place; some values need security privileges. | Read-only fields reject editing; a stale `expected_revision` is rejected with a conflict, never overwritten. | ENG-WS-ACT-09 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-view.test.ts`, `tests/test_activity_master_repository.py` (`REVISION_CONFLICT`), `tests/test_p6_activity_master_http_routes.py` (`403`) |
| ENG-PUB-FEATURES-SCHEDULING | Add an activity | Add activities in the Activity Table · Developing Projects > Adding Activities to a Project | https://docs.oracle.com/cd/G48902_01/client_help/en_US/add_activities_in_the_activity_table.htm | Add activities in the Activity Table · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/addactivitiesintheactivitytable-19495a.html | A new activity is inserted into the selected group and placed by the current sort. | Activity ID and name are required; the WBS parent must exist; duration must be a positive value in a supported unit. | ENG-WS-ACT-11 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-view.test.ts` |

## 3. Page specification — Activities (`/app/activities/`)

- **Purpose** — read and edit the project's activity table, organize it for
  analysis, and export the current view scope.
- **Entry conditions** — authenticated session, an authorized project opened by
  the session, and a workspace read model that returned the project's
  activities, WBS and columns.
- **Permissions** — `viewer` reads and exports; `planner` and `project_admin`
  may add and edit. Write requests require a same-origin `Origin` and the
  session CSRF token.
- **Structure** — window tab; layout selector; activity toolbar (quick search,
  group, sort, sort direction, tree actions, Select All, Export…); scope-count
  strip; activity table with the layout's columns; optional bottom pane (Gantt
  or Details) owned by Sections 3–4.
- **Fields** — activity ID, code, name, WBS, status, type, duration, dates,
  percent complete and the layout's registered fields. The column set, order
  and titles come from the saved layout.
- **Commands** — add, edit, delete, select all, export, group, sort, collapse
  branch, save layout, save-as, open layout, import/export layout definition.
- **Filters** — quick search (ID, name, WBS, status) plus named criterion
  filters with `all`/`any` combination. Filters are presentation state.
- **Sorting and grouping** — one primary sort column with direction; grouping by
  a registered field, with WBS hierarchy support; both persist in the layout.
- **Dialogs** — Columns, Edit Column, Layout Open/Save, Export scope, Activity
  create/edit. Each validates before committing and has an explicit cancel.
- **Validation** — unknown column or group field rejected; empty filter
  parameter rejected; blank activity ID/name rejected; non-positive duration
  rejected; stale revision → `409 REVISION_CONFLICT`; missing CSRF → `403`;
  unauthorized role → `403`.
- **Save / cancel** — table edits commit per activity with the pinned revision;
  a cancel reverts the editor without writing. Layout saves create a revision;
  opening another layout prompts to save.
- **Dependencies** — workspace read v2, project lifecycle authorization, P6
  activity and WBS services, layout persistence, field registry, localization.
- **Expected results** — after a successful save a reload returns the stored
  value; after a layout save a reload offers the saved layout; after logout and
  a new session the same activity values and layout are read.
- **Error scenarios** — stale edit conflict, denied role, missing CSRF,
  cross-tenant project, empty required field, unknown column.
- **Help references** — rows above.
- **Acceptance criteria** — `ENG-WS-ACT-01` … `ENG-WS-ACT-11`.

## 4. Acceptance scenarios

### ENG-WS-ACT-01 — Open the Activities table from the read model

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` |
| Feature | Window open and table population |
| Preconditions | Planner session; project with at least 3 activities; WBS with one root |
| Test data | Activities `A-100`, `A-200`, `A-300`; names and statuses distinct |
| User action | Sign in → open the project → open Activities |
| Expected result | Table shows exactly the project's activities; each ID/name matches the read model; no row from another project |
| Negative | A session without project membership gets no project and no table |
| Permission | Viewer sees the same rows, read-only |
| Persistence | Reload and a new login show the same rows |
| Related Help | The Activity Table — https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_activity_table.htm |

### ENG-WS-ACT-02 — Column set and layout survive reload

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` |
| Feature | Columns dialog, layout save/open |
| Preconditions | Planner; a saved project layout exists |
| Test data | Add `activity_status`; remove `activity_code`; rename `activity_name` to `Task`; save as `Site layout` |
| User action | View → Columns → change set → OK → Layout → Save As → open another layout → reopen `Site layout` |
| Expected result | The table shows the configured columns in order, with the custom title; reopening restores it; revision increments once per save |
| Negative | Adding an unknown column id is rejected and changes nothing |
| Permission | Viewer cannot save a layout (`403`); the dialog is read-only |
| Persistence | Logout, new login, reopen `Site layout` → identical column set and order |
| Related Help | Define Activity Table columns — https://docs.oracle.com/cd/G48902_01/client_help/en_US/define_activity_table_columns.htm |

### ENG-WS-ACT-03 — Sort direction toggles and persists

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` |
| Feature | Sorting |
| Preconditions | At least 3 activities with distinct duration values |
| Test data | Durations 5, 2, 9 |
| User action | Click the Duration column label twice |
| Expected result | First click ascending (2, 5, 9) with an up arrow; second click descending (9, 5, 2) with a down arrow; equal values keep a stable order |
| Negative | Sorting by a column that is not displayed is not offered |
| Permission | Viewer can sort locally; sorting is not persisted for a viewer without layout rights |
| Persistence | A planner saves the layout; reload preserves the sort column and direction |
| Related Help | Sort activity information in the Activity Table — https://docs.oracle.com/cd/G48902_01/client_help/en_US/sort_activity_information_in_the_activity_table.htm |

### ENG-WS-ACT-04 — Filter criteria and All/Any combination

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` |
| Feature | Activity filters |
| Preconditions | Planner; 5 activities across two statuses and two WBS branches |
| Test data | Filter A: `status is In Progress`; Filter B: `wbs is Site works`; mode `all` then `any` |
| User action | Create A and B → apply both with `all` → switch to `any` → remove B |
| Expected result | `all` = intersection; `any` = union; removing B leaves A's rows; counts `Filter` and `Search` follow; no activity data changes |
| Negative | A criterion with an empty value or unknown parameter is rejected and the filter is not applied |
| Permission | Viewer can apply filters locally; filters do not grant access to unread rows |
| Persistence | Saved in the layout, reload restores the active filters and mode |
| Related Help | Combine filters — https://docs.oracle.com/cd/G48902_01/client_help/en_US/combine_filters.htm |

### ENG-WS-ACT-05 — Grouping, collapse and honest counts

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` |
| Feature | Grouping, collapse, scope counts |
| Preconditions | 6 activities in two WBS branches, one branch collapsed |
| Test data | Group by WBS; collapse the second branch |
| User action | Apply a filter that matches 4 rows, search for 3 of them, then collapse a branch |
| Expected result | `Total` = 6, `Filter` = 4, `Search` = 3, `Visible` = painted rows only, `Selected` = selected ids still present, `In scope` = selected ids inside filter+search. Collapsing changes only `Visible`. |
| Negative | With zero matches, the empty state is explicit and Select All is disabled |
| Permission | Counts are read-only for every role |
| Persistence | Group field and collapsed ids persist with the layout |
| Related Help | Grouping activities by field — https://docs.oracle.com/cd/G48902_01/client_help/en_US/grouping_activities_by_field.htm |

### ENG-WS-ACT-06 — Select All and export scope ordering

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` |
| Feature | Selection scope |
| Preconditions | 6 activities, one branch collapsed, 2 rows already selected |
| Test data | Filter matching 4 rows, one inside the collapsed branch |
| User action | Click Select All → export Selected |
| Expected result | All 4 in-scope activities are selected, including the collapsed one; `Selected` = 4 and `In scope` = 4; the CSV contains 4 rows in scope order |
| Negative | Select All is disabled when the scope has zero rows |
| Permission | Viewer may select and export; selection never mutates schedule data |
| Persistence | Selection is in-memory; a reload clears it and Select All re-derives from the scope |
| Related Help | Select multiple items — https://docs.oracle.com/cd/G48902_01/client_help/en_US/select_multiple_items.htm |

### ENG-WS-ACT-07 — Quick search narrows within the active filter

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` |
| Feature | Quick search |
| Preconditions | 6 activities; filter active with 4 matches |
| Test data | Query `pour` matches 2 of the 4; query `zzz` matches none |
| User action | Type `pour`, then `zzz`, then clear |
| Expected result | Search matches ID, name, WBS and status case-insensitively; the table shows 2, then an explicit empty state, then restores the 4 filtered rows |
| Negative | Search never expands beyond the active filter |
| Permission | Viewer may search within readable rows |
| Persistence | Search is presentation state and is not persisted across reload |
| Related Help | Find Toolbar — https://docs.oracle.com/cd/G48902_01/client_help/en_US/find_toolbar.htm (CUBI divergence: scope filter, not find/replace) |

### ENG-WS-ACT-08 — Export All, Filtered and Selected

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` |
| Feature | CSV export scopes |
| Preconditions | 6 activities; 4 match the filter; 2 selected |
| Test data | Column set including a value with a comma and a quote |
| User action | Export All, then Filtered, then Selected |
| Expected result | All = 6 rows; Filtered = 4 rows including collapsed; Selected = 2 rows in scope order; header uses the layout labels; RFC 4180 quoting; file names `<project>-activities-<scope>.csv` |
| Negative | Export is disabled when the scope is empty; no partial file is produced |
| Permission | Viewer may export readable rows; no cross-tenant row is ever included |
| Persistence | Export is a read; nothing is written to the project |
| Related Help | NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT |

### ENG-WS-ACT-09 — Edit with optimistic locking

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` |
| Feature | In-table edit and save |
| Preconditions | Planner; activity at revision 1 |
| Test data | Change name to `Pour slab`; second editor holds revision 1 |
| User action | Save from editor A → attempt save from editor B with `expected_revision: 1` |
| Expected result | A commits revision 2 and reload shows it; B receives `409 REVISION_CONFLICT`, no overwrite, and is offered a reload |
| Negative | Blank name is rejected before the request; unknown field is rejected |
| Permission | Viewer edit is rejected `403`; missing CSRF `403`; other tenant `403` |
| Persistence | New login reads `Pour slab` at revision 2 |
| Related Help | Change activity information in the Activity Table — https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_activity_information_in_the_activity_table.htm |

### ENG-WS-ACT-10 — Role, tenant and CSRF boundaries

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` |
| Feature | Authorization |
| Preconditions | Viewer in tenant A; outsider in tenant B; planner in tenant A |
| Test data | Attempt create, edit and export as each role |
| User action | Submit a write with a forged `X-Tenant-Id`, then without CSRF, then as viewer |
| Expected result | Forged tenant → `403 CROSS_SCOPE_ACCESS`; missing CSRF → `403 CSRF_TOKEN_INVALID`; viewer write → `403`; outsider sees no project |
| Negative | None of the attempts writes a row or leaks another tenant's activity |
| Permission | Documented per role |
| Persistence | No mutation survives a rejected request |
| Related Help | Change activity information in the Activity Table (security privileges) — https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_activity_information_in_the_activity_table.htm |

### ENG-WS-ACT-11 — Add an activity with validation

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` |
| Feature | Add activity |
| Preconditions | Planner; WBS root exists |
| Test data | Valid: `A-400`, `Cure concrete`, 5 working days, WBS root. Invalid: blank ID; duration 0; missing WBS |
| User action | Add the valid activity, then attempt each invalid case |
| Expected result | Valid row appears in the sorted position and survives reload; blank ID and zero duration are rejected with a field error; a missing WBS is rejected |
| Negative | A duplicate activity ID is rejected and does not overwrite the existing row |
| Permission | Viewer cannot open the create form; a direct POST is `403` |
| Persistence | Logout, new login, read `A-400` |
| Related Help | Add activities in the Activity Table — https://docs.oracle.com/cd/G48902_01/client_help/en_US/add_activities_in_the_activity_table.htm |

## 5. Documented divergences

| Divergence | Official Help | CUBI behavior | Reason |
| --- | --- | --- | --- |
| Quick search | Find toolbar searches/replaces values in the active window | Search narrows the current filter+search scope over ID, name, WBS and status | The table is a filtered workspace, not a modal find/replace |
| Scope counts | Status bar lists portfolio, data date, baseline, user, database; no activity counts | Six live counts from the read model | Needed to make filtered/selected scope explicit before export |
| Export scopes | P6 exports layouts and project files | CSV of all/filtered/selected activities with the layout columns | Server-neutral exchange without a P6 file format |
| Select All | Help documents Shift/Ctrl multi-select only | Select All selects the whole filter+search scope, including collapsed rows | Prevents a hidden row from escaping a bulk action |

No product defect was found while writing this section. The four divergences
are deliberate CUBI requirements and are recorded, not treated as defects.

## 6. Verification

| Item | Result |
| --- | --- |
| Help URLs opened, HTTP 200 and listed in the official TOC | 18/18 unique topics cited above (13 are new topics beyond the 84-row canonical index; 5 were already covered there) |
| User Guide URLs opened and title-matched | 16/16 unique URLs cited above |
| Link report | `evidence/section-02-activity-help-links.json` (this section); canonical index report `evidence/help-link-verification-2026-11-21.json` |
| Existing product tests cited | `workspace-activity-scope.test.ts`, `workspace-activity-filters.test.ts`, `workspace-desktop-shell.test.ts`, `p6-columns-dialog.test.ts`, `p6-layout-persistence-adapter.test.ts`, `workspace-layout-selector.test.ts`, `workspace-view.test.ts` |
| Executed acceptance | Not run by this workstream; scenarios are `TEST_SPECIFIED` |
