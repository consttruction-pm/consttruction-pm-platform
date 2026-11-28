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
| ENG-WS-MENUS | Application menu bar and commands | Menu bar · Menu, Toolbar, and Icon Reference | https://docs.oracle.com/cd/G48902_01/client_help/en_US/menu_bar.htm | — | The window has one application menu bar in the professional order (File, Edit, View, Project, Enterprise, Tools, Admin, Help in V26); every command carries an icon and a shortcut or an explicit unavailable reason, and a checked item does not shift its label. | The Admin menu appears only for an administrator; commands that need a selection or a missing service are disabled with a real reason, never a silent no-op. | ENG-WS-ACT-15 | `HELP_VERIFIED` (environment divergence documented) | `PARTIAL` · seven menus measured in the browser 2026-11-27 at `fc513c255`; merged #2168 removed the in-workspace Enterprise menu (environment selection lives in the Personal Workbench) and open PR #2175 restores the position as a project-scoped Organization menu · `apps/web/src/workspace-desktop-shell.test.ts`, `apps/web/e2e/toolbars-v26.mjs` (six cells; records the absent reference menu with its owner) |
| ENG-WS-TOOLBARS | Command toolbar, chart controls and icon rails | Layout Toolbar · Menu, Toolbar, and Icon Reference | https://docs.oracle.com/cd/G48902_01/client_help/en_US/layout_toolbar.htm | — | Each window has one icon toolbar whose commands are grouped in the reference order; the chart board keeps only chart-local controls; the vertical tool rails stay readable and mirror in RTL. | A command with no service path is disabled with a stated reason; hiding a toolbar family is a browser-local preference and never removes the command from the menus. | ENG-WS-ACT-15 | `HELP_VERIFIED` | `PARTIAL` · 10 visible families and 57 command buttons measured 2026-11-27 (46 enabled, 11 disabled with a reason; one surface, 57/57 overflow mirror, rails 48/40px); V26 Standard Commit and a separate New Layout entry remain documented gaps · `apps/web/src/workspace-toolbars.test.ts`, `apps/web/e2e/toolbars-v26.mjs` (six cells) |
| ENG-WS-ACTIVITY-TABLE | Activity table content | The Activity Table · Customizing Activity Layouts > Activity Table | https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_activity_table.htm | The Activity Table · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/theactivitytable-19431a.html | The table lists the open project's activities and their values; it can be customized, filtered, sorted and grouped. | Only activities in the authorized project scope are read. | ENG-WS-ACT-01 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-view.test.ts` |
| ENG-WS-ACTIVITY-TABLE | Define visible columns | Define Activity Table columns · Customizing Activity Layouts > Activity Table | https://docs.oracle.com/cd/G48902_01/client_help/en_US/define_activity_table_columns.htm | Define Activity Table columns · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/defineactivitytablecolumns-19061a.html | Available columns can be added, removed, and all can be added or removed; the selected order is the display order. | A column must exist in the field registry; unknown ids are rejected, not rendered. | ENG-WS-ACT-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/p6-columns-dialog.test.ts` |
| ENG-WS-ACTIVITY-TABLE | Column titles, width and alignment | Customize activity column titles · Customizing Activity Layouts > Activity Table | https://docs.oracle.com/cd/G48902_01/client_help/en_US/customize_activity_column_titles.htm | Define Activity Table columns · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/defineactivitytablecolumns-19061a.html | A column title may be renamed without changing the underlying field; width and alignment can be set. | Blank title is rejected; title is presentation only and never changes the field id. | ENG-WS-ACT-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/p6-columns-dialog.test.ts` (title, width 40–800, alignment start/center/end), `apps/web/src/p6-layout-persistence-adapter.test.ts`, `apps/web/e2e/activity-columns-v26.mjs` (2026-11-27: 11 scenarios; scenario 03 edits title/width/alignment and reloads) |
| ENG-WS-GROUPING | Sort the table | Sort activity information in the Activity Table · Customizing Activity Layouts > Activity Table | https://docs.oracle.com/cd/G48902_01/client_help/en_US/sort_activity_information_in_the_activity_table.htm | Sort activity information in the Activity Table · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/sortactivityinformationintheactivitytable-19707a.html | Clicking a column label sorts ascending, then descending; an arrow shows the direction. | Sorting requires a selected column; ties keep a deterministic order. | ENG-WS-ACT-03 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-view.test.ts` |
| ENG-WS-GROUPING | Group activities by field | Grouping activities by field · Grouping, Filtering, and Summarizing Data > Grouping and Sorting | https://docs.oracle.com/cd/G48902_01/client_help/en_US/grouping_activities_by_field.htm | Grouping activities by field · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/groupingactivitiesbyfield-19469a.html | One or more data items group the rows; grouping is combined with sorting to order rows inside each band. Help allows adding grouping levels (up to 20) by repeating the field step. | Group fields come from the workspace group registry; CUBI supports three group levels, each with its own ascending/descending direction; clearing grouping restores the flat order. | ENG-WS-ACT-05 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-view.test.ts`, `apps/web/src/workspace-wbs-display.test.ts` (three-level nesting), `apps/web/e2e/activity-group-sort-v26.mjs` (2026-11-26: 13 scenarios) |
| ENG-WS-GROUPING | Sort activities in the Group and Sort dialog | Sort activities · Grouping, Filtering, and Summarizing Data > Grouping and Sorting | https://docs.oracle.com/cd/G48902_01/client_help/en_US/sort_activities.htm | — | One or more sort criteria apply in order; each criterion is ascending or descending, and grouping is applied before sorting. | CUBI applies up to three sort levels inside the innermost band, skips a field that already groups, keeps blanks last and breaks ties by Activity ID. | ENG-WS-ACT-05 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-filter-sort.test.ts`, `apps/web/e2e/activity-group-sort-v26.mjs` |
| ENG-WS-FILTERS | Create a filter | Create a filter · Grouping, Filtering, and Summarizing Data > Filtering | https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_filter.htm | Filtering data · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/filteringdata-19459a.html | A filter has a name and one or more parameter/operator/value criteria; criteria can be added to narrow the result. | A criterion needs a known parameter, a supported operator and a value; an empty or unknown parameter is rejected. | ENG-WS-ACT-04 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-filters.test.ts` |
| ENG-WS-FILTERS | Apply a filter | Apply a filter · Grouping, Filtering, and Summarizing Data > Filtering | https://docs.oracle.com/cd/G48902_01/client_help/en_US/apply_a_filter.htm | Apply a filter · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/applyafilter-19457a.html | Checking a filter applies it to the layout; a preview is possible before committing. | Applying filters is presentation state and never edits activity data. | ENG-WS-ACT-04 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-filters.test.ts`, `apps/web/e2e/activity-filters-v26.mjs` (2026-11-27: 14 scenarios; replace and highlight apply modes) |
| ENG-WS-FILTERS | Combine filters | Combine filters · Grouping, Filtering, and Summarizing Data > Filtering | https://docs.oracle.com/cd/G48902_01/client_help/en_US/combine_filters.htm | Combine filters · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/combinefilters-19665a.html | Several filters combine with `All` (intersection) or `Any` (union) to narrow the selection. | At least one filter must be active; mode is `all` or `any` only. | ENG-WS-ACT-04 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-filters.test.ts`, `apps/web/e2e/activity-filters-v26.mjs` (2026-11-27: Any+Highlight keeps the row set, All Activities clears it) |
| ENG-WS-LAYOUTS | Create a layout | Create a new activity layout · Customizing Activity Layouts > Overview | https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_new_activity_layout.htm | Create a new activity layout · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/createanewactivitylayout-19653a.html | A new layout is an existing layout saved under a new name, then modified and saved. | A layout name is required and unique within its scope. | ENG-WS-ACT-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/p6-layout-persistence-adapter.test.ts` |
| ENG-WS-LAYOUTS | Save a layout | Save a layout in the Activities window · Customizing Activity Layouts > Overview | https://docs.oracle.com/cd/G48902_01/client_help/en_US/save_a_layout_in_the_activities_or_rsrc_assignments_window.htm | Save a layout as a project layout · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/savealayoutasaprojectlayout-19659a.html | Saving persists the layout; saving as a project layout requires the project-layout right. | Saving needs the layout privilege; a stale base revision is rejected. | ENG-WS-ACT-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/p6-layout-persistence-adapter.test.ts` |
| ENG-WS-LAYOUTS | Open a layout | Open a layout · Customizing Activity Layouts > Overview | https://docs.oracle.com/cd/G48902_01/client_help/en_US/open_a_layout.htm | Open a layout · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/openalayout-19651a.html | Opening a layout prompts to save the current one; the list contains stored layouts only. | An unknown or deleted layout is not offered and never fabricated. | ENG-WS-ACT-02 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-layout-selector.test.ts` |
| ENG-WS-LAYOUTS | Undo or redo a layout change | NO DIRECT P6 HELP TOPIC — CUBI EXTENSION (nearest: Using Undo, which covers data edits in the Activity Details tabs only and says layout changes do not clear that history) | https://docs.oracle.com/cd/G48902_01/client_help/en_US/using_undo.htm | — | Help's Edit → Undo restores modified data values in General, Status, Resources and Relationships; scheduling, leveling, layout changes and opening a layout do not clear it. It does not define layout undo. | CUBI keeps an append-only revision history per layout scope/view. Undo saves the previous revision as a new head revision, Redo saves the undone one, and both run from the history bar, Edit → Undo/Redo and Ctrl+Z/Ctrl+Y; a new edit clears the redo stack. | ENG-WS-ACT-12 | `HELP_VERIFIED` (nearest), divergence documented | `IMPLEMENTED` · `apps/web/e2e/layout-undo-redo-v26.mjs` (2026-11-26: 9 scenarios) |
| ENG-WS-LAYOUTS | Restore an earlier layout revision | NO DIRECT P6 HELP TOPIC — CUBI EXTENSION (nearest: Open a layout) | https://docs.oracle.com/cd/G48902_01/client_help/en_US/open_a_layout.htm | Open a layout · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/openalayout-19651a.html | Opening a stored layout restores its definition. | Older revisions of the current scope/view are listed newest-first with their column count; Restore writes the chosen revision as a new head, never deletes history, and clears redo. A revision with no group/sort metadata renders the canonical WBS plan it predates. | ENG-WS-ACT-12 | `HELP_VERIFIED` (nearest), divergence documented | `IMPLEMENTED` · `apps/web/e2e/layout-undo-redo-v26.mjs`, `apps/web/src/main.ts` (`hydrateGroupSortFromLayout`) |
| ENG-WS-LAYOUTS | Show line numbers | Add line numbers · Customizing Activity Layouts > Overview | https://docs.oracle.com/cd/G48902_01/client_help/en_US/51388.htm | — | View → Line Numbers numbers each visible row in a separate column at the far left, starting at 1, headed `#` (not customisable, not movable); rows renumber when rows are added or removed and when groups are expanded or collapsed; the option applies to every applicable grid in the Activities view. | The Activities table is the one applicable grid in CUBI. | ENG-WS-ACT-13 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/e2e/table-layout-line-numbers-prefs-v26.mjs` (2026-11-27: scenarios 01–03) |
| ENG-WS-LAYOUTS | Table Font and Row | Change Activity Table font, color, and row height · Customizing Activity Layouts > Activity Table | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_activity_table_font_color_and_row_height.htm | — | View → Table Font and Row sets the table font and the background colour; in the Row Height area Keep Current keeps the heights already set, Optimize by content sizes rows to the cell text (optionally capped at X lines), and Select height for all rows applies one numeric height; Show Icons adds the row symbols. | The height field applies only to Select height for all rows. | ENG-WS-ACT-13 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/e2e/table-layout-line-numbers-prefs-v26.mjs` (2026-11-27: scenario 04) |
| ENG-WS-LAYOUTS | User Preferences | Define user preferences · Getting Started > Setting User Preferences | https://docs.oracle.com/cd/G48902_01/client_help/en_US/define_user_preferences.htm | Setting User Preferences · https://docs.oracle.com/cd/G48902_01/client_help/en_US/settinguserpreferences.htm | Edit → User Preferences keeps display preferences per user: time units, dates, currency, email, wizards, application startup, password, resource analysis, calculations, startup filters and personal information. | — | ENG-WS-ACT-13 | `HELP_VERIFIED` (scope divergence documented), `TEST_SPECIFIED` | `PARTIAL` · CUBI User Preferences carries the table presentation, line numbers and WBS band format (the layout preferences of this web runtime); the account-level tabs are recorded as a divergence, not implemented here · `apps/web/e2e/table-layout-line-numbers-prefs-v26.mjs` (2026-11-27: scenario 05) |
| ENG-WS-SELECTION | Multi-selection | Select multiple items · Getting Started > Workspace Basics | https://docs.oracle.com/cd/G48902_01/client_help/en_US/select_multiple_items.htm | Select multiple items · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/selectmultipleitems-21036a.html | Shift-click selects a contiguous group; Ctrl-click adds or removes individual rows. | A selection refers to read-model ids; a deleted activity is dropped from the selection. | ENG-WS-ACT-06 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-scope.test.ts` |
| ENG-WS-SELECTION | Select All scope | NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT (nearest: Select multiple items) | https://docs.oracle.com/cd/G48902_01/client_help/en_US/select_multiple_items.htm | Select multiple items · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/selectmultipleitems-21036a.html | CUBI defines Select All as the whole current filter + quick-search scope, including collapsed and grouped rows; it is never a DOM-only selection. | Disabled when the scope has zero rows. | ENG-WS-ACT-06 | `HELP_VERIFIED` (nearest), `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-scope.test.ts`, `apps/web/src/main.ts` |
| ENG-WS-ACTIVITY-TABLE | Scope counts (Total / Filter / Search / Visible / Selected / In scope) | NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT (nearest: Using the Status Bar and Layout Options bar, which does not list activity counts) | https://docs.oracle.com/cd/G48902_01/client_help/en_US/using_the_status_bar_and_display_layout_options_bar.htm | Using the Status Bar and Layout Options bar · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/usingthestatusbarandlayoutoptionsbar-21127a.html | CUBI shows six counts derived from the authoritative read model: total, filter match, search match, painted rows, selected, selected-in-scope. | Counts are read-only; each is recomputed after filter, search, grouping, collapse or selection. | ENG-WS-ACT-05 | `HELP_VERIFIED` (nearest), `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-scope.test.ts`, `apps/web/src/workspace-view.ts` |
| ENG-WS-ACTIVITY-TABLE | Quick search inside the table | Find Toolbar · Getting Started > Working with Toolbars and Menus > Menu, Toolbar, and Icon Reference | https://docs.oracle.com/cd/G48902_01/client_help/en_US/find_toolbar.htm | Find Toolbar (search/replace in the active window) — direct section URL `HELP REFERENCE NOT YET VERIFIED` | The official Find toolbar searches and replaces values in the active window. CUBI's quick search is a **scope filter** over ID, name, WBS and status, applied inside the active filter. | Case-insensitive; empty query restores the filter scope; no match shows an explicit empty state. | ENG-WS-ACT-07 | `HELP_VERIFIED` (topic), divergence documented | `IMPLEMENTED` · `apps/web/src/workspace-view.test.ts` |
| ENG-WS-ACTIVITY-TABLE | Export All / Filtered / Selected | NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT (P6 exports layouts and projects, not an activity-scope CSV) | https://docs.oracle.com/cd/G48902_01/client_help/en_US/export_a_tracking_layout.htm (nearest, different artifact) | Export a tracking layout · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/exportatrackinglayout-20193a.html | CUBI exports the chosen scope as RFC 4180 CSV using the current layout columns: all = read model, filtered = filter+search scope including collapsed rows, selected = in-memory selection in scope order. | Disabled when the scope is empty; hidden or collapsed rows are never lost. | ENG-WS-ACT-08 | `HELP_VERIFIED` (nearest), `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-activity-scope.test.ts` |
| ENG-WS-ACTIVITY-TABLE | Edit a value in the table | Change activity information in the Activity Table · Customizing Activity Layouts > Activity Table | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_activity_information_in_the_activity_table.htm | Change activity information in the Activity Table · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/changeactivityinformationintheactivitytable-19697a.html | Double-clicking a value edits it in place; some values need security privileges. | Read-only fields reject editing; a stale `expected_revision` is rejected with a conflict, never overwritten. | ENG-WS-ACT-09 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-view.test.ts`, `tests/test_activity_master_repository.py` (`REVISION_CONFLICT`), `tests/test_p6_activity_master_http_routes.py` (`403`); browser-verified 2026-11-27: `apps/web/e2e/activity-add-edit-v26.mjs` scenarios 04–07 |
| ENG-PUB-FEATURES-SCHEDULING | Add an activity | Add activities in the Activity Table · Developing Projects > Adding Activities to a Project | https://docs.oracle.com/cd/G48902_01/client_help/en_US/add_activities_in_the_activity_table.htm | Add activities in the Activity Table · https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/addactivitiesintheactivitytable-19495a.html | A new activity is inserted into the selected group and placed by the current sort. | Activity ID and name are required; the WBS parent must exist; duration must be a positive value in a supported unit. | ENG-WS-ACT-11 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `IMPLEMENTED` · `apps/web/src/workspace-view.test.ts`; browser-verified 2026-11-27: `apps/web/e2e/activity-add-edit-v26.mjs` scenarios 01–03 |
| ENG-WS-SHORTCUTS | Keyboard shortcut catalogue and rebinding | Using Shortcut Keys · Getting Started > Working with Toolbars and Menus | https://docs.oracle.com/cd/G48902_01/client_help/en_US/63783.htm | — | Help lists the P6 shortcut keys (22 command rows in v26). CUBI's F1 shortcut dialog lists the catalogue with the active chord per row, a reason for every unavailable command and an optional Help link; a person can record a new chord for a row, and it is rejected when the chord is already taken or is not a usable chord. | Every row must carry a chord; a row whose command has no execution path is shown disabled with its real reason; a chord must contain a non-modifier key, must not collide with another binding, and `Escape` while recording cancels; overrides persist per browser profile and Reset returns the default. | ENG-WS-ACT-14 | `HELP_VERIFIED` (divergences documented) | `IMPLEMENTED` · `apps/web/e2e/activity-shortcuts-v26.mjs` (2026-11-27: 8 scenarios) |

### Activity Usage Spreadsheet and Profile (`/app/activities/`, bottom layout)

| Row ID | Functional item | Help topic · section | Direct Help URL | User Guide · URL | Expected behavior (from Help) | Inputs and validation | Scenario | Doc status | Product status · evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ENG-WS-USAGE | Activity Usage Spreadsheet | The Activity Usage Spreadsheet · Customizing Activity Layouts > Activity Usage and Resource Usage Spreadsheets | https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_activity_usage_spreadsheet.htm | No verified direct section URL | The spreadsheet is split into two panes: the left pane is the Activity Table with its columns, grouping, sorting and filtering, and the right pane shows timescaled data for each activity; it is read-only and can sit in the top or bottom layout. | Only stored period values are shown; a project with no stored periods exposes no fabricated row. | ENG-USAGE-01 | `HELP_VERIFIED` (divergence documented) | `IMPLEMENTED` as a bottom-layout view with one activity pane; CUBI has no separate left Activity Table pane · browser-verified 2026-11-27: `apps/web/e2e/activity-usage-v26.mjs` scenarios 01–05, 07, 08 |
| ENG-WS-USAGE | Metric and scope for the usage views | The Activity Usage Profile · Customizing Activity Layouts > Activity Usage and Resource Usage Profiles | https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_activity_usage_profile.htm | No verified direct section URL | The profile shows cost or unit values over a timescale for all activities or only the selected ones; filters on the Activity Table also apply to the profile. | Units and cost come from the stored assignment periods; switching metric or scope is presentation only and writes nothing. | ENG-USAGE-01 | `HELP_VERIFIED` | `IMPLEMENTED` · units/cost metric and all/selected scope persisted per project profile · `apps/web/e2e/activity-usage-v26.mjs` scenarios 03–05, 11 |
| ENG-WS-USAGE | Activity Usage Profile histogram | The Activity Usage Profile · Customizing Activity Layouts > Activity Usage and Resource Usage Profiles | https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_activity_usage_profile.htm | No verified direct section URL | Each period is a vertical bar for the allocated units or cost, with optional value labels; cumulative curves may also be charted. | Peak and total are derived from the same stored periods that feed the spreadsheet. | ENG-USAGE-02 | `HELP_VERIFIED` (partial divergence) | `PARTIAL` · labelled bars with peak and total; no cumulative curves or timescale/bar customisation · `apps/web/e2e/activity-usage-v26.mjs` scenarios 06, 09, 10 |
| ENG-WS-USAGE | Customize spreadsheet columns and fields | Customize Activity Usage Spreadsheet columns · Select Activity Usage Spreadsheet fields · Customizing Activity Layouts > Activity Usage and Resource Usage Spreadsheets | https://docs.oracle.com/cd/G48902_01/client_help/en_US/customize_activity_usage_spreadsheet_columns.htm | No verified direct section URL | View > Columns adds, removes and reorders the left-pane columns with Default/Apply/OK; Spreadsheet Fields, Customize selects the right-pane data fields. | At least one column must stay displayed; the changes are presentation only. | ENG-USAGE-03 | `HELP_VERIFIED`, `TEST_SPECIFIED` | `NOT_IMPLEMENTED` · fixed columns (activity, label, periods, total) and a fixed metric/scope switch |

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
- **Acceptance criteria** — `ENG-WS-ACT-01` … `ENG-WS-ACT-12` for the table, layout and activity write paths; `ENG-WS-ACT-13`–`ENG-WS-ACT-15` for table typography/preferences, the shortcut catalogue and the menu/toolbar chrome.

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

### ENG-WS-ACT-05 — Multi-level grouping, sort plan, collapse and honest counts

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` |
| Feature | Three-level grouping, three-level sort, collapse, scope counts |
| Preconditions | 14 activities across the persisted WBS tree; one branch collapsed |
| Test data | Group by WBS (asc) > Activity Status (desc) > Critical (asc); sort by Total Float (asc), Activity Name (desc), Early Finish (asc) |
| User action | Apply a filter that matches 4 rows, search for 3 of them, then collapse a branch |
| Expected result | Bands nest in the configured order with each level's direction; sibling WBS bands follow sequenceNumber then localCode; `No value` stays last; rows inside the innermost band follow the three sort levels; `Total` = 14, `Filter` = 4, `Search` = 3, `Visible` = painted rows only, `Selected` = selected ids still present, `In scope` = selected ids inside filter+search. Collapsing changes only `Visible`, and the Gantt follows the same row order. |
| Negative | With zero matches, the empty state is explicit and Select All is disabled; an unknown or duplicate group field is dropped by normalization instead of inventing a band |
| Permission | Counts are read-only for every role; grouping and sorting are presentation only |
| Persistence | All three group levels and all three sort levels plus collapsed ids persist in `metadata.groupSort`; a reload — and a refresh of the WBS order — restores the same plan |
| Related Help | Grouping activities by field — https://docs.oracle.com/cd/G48902_01/client_help/en_US/grouping_activities_by_field.htm and Sort activities — https://docs.oracle.com/cd/G48902_01/client_help/en_US/sort_activities.htm |

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

### ENG-WS-ACT-12 — Layout revision history: undo, redo and restore

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` |
| Feature | Layout history bar (Settings), Edit → Undo/Redo, Ctrl+Z/Ctrl+Y |
| Preconditions | Fresh project layout at R1 with no earlier revision; planner |
| Test data | Widen Activity ID 20px, then undo; redo; reload; restore R1; save a Group & Sort plan (Activity Status) and undo it |
| User action | Use the history bar, the keyboard chords and the revision list |
| Expected result | Undo with no history reports `No earlier layout revision is available.` and changes nothing; each undo/redo/restore appends exactly one revision and leaves older revisions recoverable; the rendered column width and Group & Sort bands match the revision that becomes head, including a pre-group-sort revision that renders the canonical WBS plan; a new edit clears redo; after reload undo still works from the server list while redo is honestly empty |
| Negative | Undo never deletes a revision or overwrites a newer head; a revision outside the offered list is rejected |
| Permission | Viewer sees the history bar read-only; saving an undo/redo/restore needs the layout write right (`403` without it) |
| Persistence | The new head revision survives logout; a fresh login reads the same columns, presentation and group/sort plan |
| Related Help | Using Undo (data edits only; layout changes do not clear it) — https://docs.oracle.com/cd/G48902_01/client_help/en_US/using_undo.htm · Open a layout (nearest for restore) — https://docs.oracle.com/cd/G48902_01/client_help/en_US/open_a_layout.htm |

### ENG-WS-ACT-13 — Line numbers, Table Font and Row and User Preferences

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` |
| Feature | View → Line Numbers, View → Table Font and Row, Edit → User Preferences, grid context menu and Layout toolbar |
| Preconditions | Planner; project layout at its default table presentation; WBS grouping on |
| Test data | 14 activity rows under 7 WBS bands; row height 18→30px; font 11→13px; line numbers on and off |
| User action | Toggle line numbers from the View menu, the row context menu and the toolbar; collapse and expand the root band; reopen Table Font and Row in Keep Current, Optimize by content and Fixed height; open User Preferences, change the font and line numbers, then use Reset band format |
| Expected result | The `#` column is the first column, has no column id and no resize handle, numbers visible activity rows 1..n sequentially and renumbers after a collapse, an expand and after a reload that clears `localStorage`; Keep Current and Optimize by content lock the height field and never change the saved height (even when the disabled attribute is removed and a value is submitted), Fixed height for all rows unlocks it and applies 30px; Cancel writes nothing; User Preferences shows the same table block plus line numbers; Reset band format resets the band and leaves the table fieldset untouched |
| Negative | A height typed while another mode is selected never reaches the table; Cancel never bumps a value; the line-number column cannot be resized, dragged or given a custom heading |
| Permission | Viewer can see line numbers and open both dialogs read-only; saving needs the layout write right |
| Persistence | After `localStorage.clear()` and a reload the line numbers, row height, font size and row mode come back from the saved layout |
| Related Help | Add line numbers — https://docs.oracle.com/cd/G48902_01/client_help/en_US/51388.htm · Change Activity Table font, color, and row height — https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_activity_table_font_color_and_row_height.htm · Define user preferences — https://docs.oracle.com/cd/G48902_01/client_help/en_US/define_user_preferences.htm |

### ENG-WS-ACT-14 — Shortcut catalogue, rebinding, conflict refusal and RTL

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` |
| Feature | F1 shortcut dialog: catalogue, search, Change/Reset, Reset all, Help links |
| Preconditions | Planner; default shortcut overrides (empty `localStorage`); project open |
| Test data | 27 rendered rows (25 static entries plus `Alt+1…9` window rows); new chord `Ctrl+Alt+K` for `shortcut.about`; duplicate attempt `Ctrl+F`; unusable chord `k` |
| User action | Press F1; type in the search field and clear it; press Ctrl+A, Ctrl+S, F5 and Insert from the shell; open Change for About, record `Ctrl+Alt+K`, reload and press the new chord, then Reset; try `Ctrl+F` and `k`; press Escape during recording; switch to fa/RTL at 1280×720 and en/LTR at 1920×1080 |
| Expected result | The dialog lists the whole catalogue with a visible chord on every row, a real reason on every disabled row and a Help link on every documented command; search narrows and clearing restores every row; Ctrl+A selects the whole scope and Ctrl+S appends one layout revision; F5 re-reads the project without changing the row count and Insert opens the Add Activity form focused on `activity_id` without writing; the new chord persists across reload and runs its command; Reset restores `Shift+F12` and clears storage; a duplicate chord or a bare character is refused with an error tone and never stored; Escape cancels recording; the dialog localises in fa/RTL without horizontal overflow and fits en/LTR at 1920×1080 |
| Negative | A refused chord is neither stored nor applied; a disabled row's chording never executes an unsupported command; recording never swallows the browser's own reload chord |
| Permission | Any signed-in role may open the catalogue and rebind personal shortcuts; the overrides are personal, not project data |
| Persistence | Overrides survive a reload through the per-profile storage key prefix; Reset removes the override and returns the default chord |
| Related Help | Using Shortcut Keys — https://docs.oracle.com/cd/G48902_01/client_help/en_US/63783.htm |

### ENG-WS-ACT-15 — Menu bar, command toolbar, icons and RTL chrome

| Field | Content |
| --- | --- |
| Environment | Engineering |
| Page | `/app/activities/` |
| Feature | Application menu bar, command toolbar, chart controls, navigation and context rails, icon set |
| Preconditions | Administrator session (so the role-gated Admin menu is part of the bar); project `preview-rps-01` open; Classic Schedule Layout |
| Test data | 1280×720, 1366×768 and 1920×1080 in en/LTR and fa/RTL; seven rendered menus; 57 toolbar command buttons; four executed menu commands (Select All, Link, Unlink, Collapse To) |
| User action | Open every menu and measure its popup, icons and target height; open View and inspect the Windows flyout; run Select All, Link (A100→A110), Unlink and Collapse To from the menu; apply the Classic Schedule Layout and reload; measure the toolbar families, button inventory, overflow mirror and both rails in all six cells |
| Expected result | The menu bar matches the approved eight- or seven-menu shape exactly and records any absent reference menu with a named owner; every popup opens inside the viewport with an icon on every command and a reserved check column; menu targets are ≥22px at ≥11px font; there is one toolbar with the ten Activities families, no iconless button, no duplicate command, a complete overflow mirror and a ≥20×20 smallest target; the chart keeps five scale presets and one relationship toggle; the rails are ≥46px/≥38px with ≥16px icons and mirror in RTL; Select All selects 14/14 rows and focuses the grid, Link preselects A100→A110, Unlink removes exactly one relationship after confirmation, Collapse To opens the branch dialog; the Classic Schedule Layout survives reload; zero exceptions, console errors and 5xx |
| Negative | Any menu combination other than the approved eight or seven fails the run; an absent reference menu without a named owner fails the run; a disabled toolbar command never executes |
| Permission | Any signed-in role sees the seven shared menus; the Admin menu is limited to `project_admin`; commands are gated per item |
| Persistence | Toolbar family visibility is per-user browser storage and never removes a command from the menus; the applied layout survives reload |
| Related Help | Menu bar — https://docs.oracle.com/cd/G48902_01/client_help/en_US/menu_bar.htm · Layout Toolbar — https://docs.oracle.com/cd/G48902_01/client_help/en_US/layout_toolbar.htm |

## 5. Documented divergences

| Divergence | Official Help | CUBI behavior | Reason |
| --- | --- | --- | --- |
| Quick search | Find toolbar searches/replaces values in the active window | Search narrows the current filter+search scope over ID, name, WBS and status | The table is a filtered workspace, not a modal find/replace |
| Scope counts | Status bar lists portfolio, data date, baseline, user, database; no activity counts | Six live counts from the read model | Needed to make filtered/selected scope explicit before export |
| Export scopes | P6 exports layouts and project files | CSV of all/filtered/selected activities with the layout columns | Server-neutral exchange without a P6 file format |
| Select All | Help documents Shift/Ctrl multi-select only | Select All selects the whole filter+search scope, including collapsed rows | Prevents a hidden row from escaping a bulk action |
| Layout undo/redo and restore | Help's only Undo (Edit → Undo) restores data values in Activity Details tabs and explicitly says layout changes do not clear that history; no layout undo/redo or revision restore topic exists | The history bar, Edit → Undo/Redo and Ctrl+Z/Ctrl+Y undo/redo/restore persisted layout revisions; data-value undo is not provided | Layout history is a CUBI extension built on the append-only layout revision contract; it is recorded as an extension, never as a P6 command |

| Line numbering of grouping bands | Help numbers "each row" that is visible and does not say how grouping bands are numbered | Activity rows are numbered 1..n; a grouping band row shows an empty number cell | Keeps the running count tied to activities, so a collapsed band never consumes a number |
| Row line limit | Optimize by content offers an optional "Do not exceed X lines per row" cap | Optimize by content lets a row grow to its cell text without a cap | Documented remaining gap; the cap is not implemented in this runtime |
| User Preferences scope | Help's User Preferences carries time units, dates, currency, email, wizards, application, password, resource analysis, calculations, startup filters and personal information | CUBI User Preferences carries the table presentation, line numbers and WBS band format; account-level formats live outside the Activities window | The web runtime has no desktop email/LDAP/password tabs; the layout preferences are the ones this window owns |
| Table text colour | Help documents the table font and background colour | CUBI also exposes a text colour | Small CUBI extension so a dark background stays readable |
| F7 shortcut | Using Shortcut Keys maps F7 to Spell Check | CUBI maps F7 to resource levelling and lists Spell Check as unavailable with its reason | The table has no spell-check surface in this runtime; the binding follows the levelling command, and the mapping is left to the catalogue-owning branch rather than changed in a display slice |
| Shift+F9 shortcut | Using Shortcut Keys maps Shift+F9 to Level Resources | CUBI maps Shift+F9 to Schedule Options | Levelling is exposed from the row context menu; Schedule Options is the command bound to that chord here |
| Shift+F12 shortcut | Using Shortcut Keys maps Shift+F12 to Disable Auto-Reorganization | CUBI maps Shift+F12 to About CUBI | Auto-reorganization has no CUBI counterpart; About is the useful command on that chord |
| Ctrl+R and the F1 Help family | Using Shortcut Keys lists `Ctrl+R` and `Alt+F1`/`Ctrl+F1`/`Ctrl+Alt+F1` (Hint, Local Help, Online Help) | `Ctrl+R` is deliberately unavailable with a browser-reload reason and only `F1` opens Help | The browser owns `Ctrl+R`; the three context-help variants are not implemented in this web runtime and are recorded rather than faked |
| Organization / Enterprise menu | The V26 menu bar includes an Enterprise menu in position five | The Engineering workspace currently renders seven menus; #2168 moved environment selection to the Personal Workbench and open PR #2175 restores the position as a project-scoped Organization menu | Environment choice is not a project-window destination; the project-scoped Organization menu is the approved replacement, so the row stays PARTIAL until #2175 lands |

One product defect was found while writing this section and fixed: Keep Current and
Optimize by content both applied the numeric height field, so "Keep Current" changed the
row heights it promised to keep. The height is now read only in Fixed height mode and the
field is locked in the other two. The remaining divergences are deliberate CUBI choices.

## 6. Verification

| Item | Result |
| --- | --- |
| Help URLs opened, HTTP 200 and listed in the official TOC | 19/19 unique topics cited above (14 are new topics beyond the 84-row canonical index; 5 were already covered there) |
| User Guide URLs opened and title-matched | 16/16 unique URLs cited above |
| Link report | `evidence/section-02-activity-help-links.json` (this section); canonical index report `evidence/help-link-verification-2026-11-21.json` |
| Existing product tests cited | `workspace-activity-scope.test.ts`, `workspace-activity-filters.test.ts`, `workspace-desktop-shell.test.ts`, `workspace-dialogs.test.ts`, `p6-columns-dialog.test.ts`, `p6-layout-persistence-adapter.test.ts`, `workspace-layout-selector.test.ts`, `workspace-view.test.ts`, `apps/web/e2e/layout-undo-redo-v26.mjs`, `apps/web/e2e/table-layout-line-numbers-prefs-v26.mjs`, `apps/web/e2e/activity-columns-v26.mjs`, `apps/web/e2e/activity-filters-v26.mjs`, `apps/web/e2e/activity-shortcuts-v26.mjs`, `workspace-activity-usage.test.ts`, `apps/web/e2e/activity-usage-v26.mjs`, `apps/web/e2e/activity-add-edit-v26.mjs` |
| Executed acceptance (2026-11-27) | `apps/web/e2e/table-layout-line-numbers-prefs-v26.mjs` on the local full-stack runtime: **7/7 scenarios PASS**, 10 screenshots, 0 exceptions/console errors/5xx. Evidence: `docs/workspace/evidence/table-layout-line-numbers-prefs-v26-2026-11-27/`. The remaining scenarios above stay `TEST_SPECIFIED` |
| Executed acceptance (2026-11-27, columns and filters) | `apps/web/e2e/activity-columns-v26.mjs` **11/11 PASS** with 12 screenshots and `apps/web/e2e/activity-filters-v26.mjs` **14/14 PASS** with 13 screenshots on the local full-stack runtime, 0 exceptions/console errors/5xx at code `e734b0b85`; the Columns run proves the Edit Column title/width/alignment edit and its reload, and the Filters run proves Any+Highlight keeps rows while All Activities clears the highlight. Evidence: `docs/workspace/evidence/activity-columns-v26-2026-11-27/` and `docs/workspace/evidence/activity-filters-v26-2026-11-27/` |
| Executed acceptance (2026-11-27, shortcuts) | `apps/web/e2e/activity-shortcuts-v26.mjs` (contract `cubi-activity-shortcuts-v26.v1`) **8/8 PASS** with 7 screenshots on the local full-stack runtime, 0 exceptions/console errors/5xx at code `e734b0b85`: the catalogue renders 27 rows with a chord on every row, 14 rows link a Help topic and 9 rows are disabled with a real reason; search narrows and restores; Ctrl+A/Ctrl+S/F5/Insert behave; a rebound `Ctrl+Alt+K` survives reload and runs, Reset restores `Shift+F12`; a duplicate and a bare character are refused and not stored; fa/RTL 1280×720 and en/LTR 1920×1080 fit. Evidence: `docs/workspace/evidence/activity-shortcuts-v26-2026-11-27/` |
| Executed acceptance (2026-11-27, Activity Usage) | `apps/web/e2e/activity-usage-v26.mjs` (contract `cubi-activity-usage-v26.v1`) **11/11 scenarios PASS** with 11 screenshots at code `eb82b00aa`: both views stay disabled until stored periods exist, the spreadsheet matches the read-API period values with row and grand totals, the cost metric and the selected scope persist, the profile draws one labelled bar per period with peak and total, a refresh reads a newly stored period, an activity without periods shows an explicit empty state, fa/RTL 1280×720 and en/LTR 1920×1080 fit, and using the views issues no schedule/activity/relationship or assignment write. Evidence: `docs/workspace/evidence/activity-usage-v26-2026-11-27/` |
| Executed acceptance (2026-11-27, add and edit activity) | `apps/web/e2e/activity-add-edit-v26.mjs` (contract `cubi-activity-add-edit-v26.v1`) **9/9 scenarios PASS** with 9 screenshots at code `bad3f3290`: the Add command opens the Tools drawer on the create form with a suggested activity ID and the project's WBS options and writes nothing; submitting creates the activity through the real `p6-activity-master-api` POST and the grid row and a fresh read agree on ID, name, duration and WBS; a duplicate ID is refused with a visible error, keeps one row and leaves the stored record unchanged; the row Edit command prefills the stored name, duration, unit and WBS; saving PATCHes with the stored revision and the grid and read API agree with a bumped revision; a form opened before a concurrent write is refused with `REVISION_CONFLICT` and never overwrites the newer value; changing the WBS moves the activity; fa/RTL 1280×720 and en/LTR 1920×1080 fit; zero exceptions, zero unexpected console errors (the one designed duplicate rejection is classified) and zero 5xx. Evidence: `docs/workspace/evidence/activity-add-edit-v26-2026-11-27/` |
| Executed acceptance (2026-11-27, menus, toolbar and icons) | `apps/web/e2e/toolbars-v26.mjs` (contract `cubi-toolbars-v26.v1`) **6/6 cells PASS** with 9 screenshots at code `fc513c255`: the approved seven-menu shape (File, Edit, View, Project, Tools, Admin, Help) in en/fa with every menu open, iconised and inside the viewport and the absent reference Organization menu recorded with its owner (PR #2175); one toolbar with ten families, 57 commands (46 enabled, 11 disabled with a reason), no iconless or duplicate command and a 57/57 overflow mirror; rails 48/40px mirrored in RTL; Select All 14/14, Link A100→A110, Unlink 15→14, Collapse To and the Classic Schedule Layout after reload; zero exceptions/console errors/5xx. The official Preview alias returned `DEPLOYMENT_NOT_FOUND`; evidence is from the local full-stack runtime. Evidence: `docs/workspace/evidence/toolbars-v26-2026-11-27/` |
