# CUBI Complete Window and Component Build Catalog

- Parent epic: [#1722](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1722)
- Source register: [v26-source-register.md](../reference/v26-source-register.md)
- Baseline inspected: main commit 49201ddfbec83550e7147ce2fa3cc961e39eef55
- Product rule: one canonical CUBI Visual Workspace; no second authenticated shell or competing dashboard.
- Scope: complete window-by-window UI specification and behavior inventory. This is a build contract, not a claim that every item already exists.

## 1. Non-negotiable product and implementation rules

1. A window is a complete professional work surface, not an icon, route name, generic list, dashboard card, static mock or placeholder.
2. Each window must own its layout, selection context, columns, view modes, details tabs, menus, context menus, keyboard behavior, empty/loading/error states, permission rules and saved preferences.
3. A window is complete only when all required structures and controls are implemented and browser-tested. A visually accurate but inert control is not complete.
4. Every visible command must either perform its advertised action or be disabled with a truthful explanation. Never return simulated success, fabricated rows, estimated values presented as authoritative, or pretend persistence.
5. The menu bar, navigation tree, toolbar, window tabs and shortcut menus must address the same command registry and canonical window identities. Opening an already-open window activates its existing tab; it must not create duplicate shells.
6. The same data model and command behavior must be used whether a window is opened from a menu, navigation tree, toolbar, context menu or deep link.
7. No artificial project-activity cap is allowed in the UI, grid, Gantt, filtering, selection, export or schedule engine. Rendering optimization may virtualize rows, but it cannot truncate the underlying project data or calculation set.
8. Filtering, sorting, collapsing WBS, changing layout, hiding rows, using a different top/bottom view or virtualizing the DOM must never mutate project records or alter the schedule input population.
9. Every persisted edit uses authenticated scope, permission checks, revision/concurrency controls, audit where applicable and a visible result/error. Destructive actions confirm affected records and dependencies.
10. Customer-visible CUBI labels, help, URLs, icons and branding are independent of the reference product. Reference product names and logos are allowed only in internal source notes where needed to identify the standard.
11. Preserve the CUBI logo and brand identity, but do not constrain workspace presentation to the brand palette. Support coordinated light/dark themes, configurable window/panel/grid/Gantt backgrounds, user-selected colors and distinct WBS level treatments. Maintain readable contrast and independent visual signals for WBS level, status, criticality and selection. Do not copy third-party branded artwork or proprietary screenshots.
12. Preserve the user's approved proportions and existing working behavior. Do not invent a new ratio file or change the timeline scale merely to accommodate a different monitor. Resizable regions need bounded, persisted user settings.

## 2. Global workspace shell

The shell must be persistent across every authenticated workspace window.

### 2.1 Required regions

| Region | Required contents | Required behavior |
|---|---|---|
| Product/status strip | CUBI mark, current project, project revision, current user/role, connection/sync state, language, date-calendar display and theme | Compact, persistent, no overlapping controls; connection and save state are truthful |
| Main menu bar | Workspace, Edit, View, Project, Organization, Tools, Administration, Help | Nested dropdowns, keyboard mnemonics, selection-aware enablement, tooltips and separators |
| Main toolbar | Standard, Project, Layout, Schedule, Selection/Navigation and CUBI tools | Small grouped icons, consistent sizing, tooltips, accessible names, keyboard focus and command registry binding |
| Breadcrumb/context | Business Domain, optional portfolio, project, active window, revision and Data Date | Shows active scope; project switching is explicit and permission-aware |
| Window tabs | One tab per open window, active marker, dirty marker, close, reorder and keyboard cycling | Project windows close when last project closes; global windows follow their own lifecycle; duplicate open requests activate existing tab |
| Navigation/directory strip | Compact icon rail for windows/tools, overflow or scroll when necessary | Collapsible, keyboard accessible, state persisted; it is not a second menu implementation |
| Main work area | Window-specific top layout and content | Window owns its layout; no generic empty panel masquerading as a window |
| Bottom layout / Details | Window-specific tabs, usage views, spreadsheets or trace logic | Optional, resizable, context bound to the current window and selection |
| Layout options bar | Current layout/filter, view, columns, group/sort, timescale and bar settings as applicable | Contextual controls; no duplicated rows of identical controls |
| Status bar | Project scope, Data Date, baseline, layout, filter, selected/total count, user/role, save/sync state | Read-only status except for explicit shortcuts; no fabricated data |

### 2.2 Global interaction and window lifecycle

- Menu keyboard access: Alt/mnemonic access, arrows, Enter, Escape and documented shortcuts.
- Tab behavior: activate, close, reorder, keyboard cycle, dirty-state warning, restore after refresh where approved.
- Panel behavior: mouse and keyboard splitter movement; min/max bounds; saved per user/window/project; reset to default.
- Full-screen behavior: enter full-screen and return to main view without losing selection, active window or unsaved edits.
- Mobile: authenticated workspace opens in landscape mode where supported; menus and panels remain navigable without hiding controls.
- Localization: Persian, English, German, Chinese, Arabic, French, Japanese and Korean; RTL/LTR for every shell and window. Date calendar mode is independent of UI language.
- Context help: field hints and keyboard shortcuts must be discoverable; Help opens CUBI documentation, not the source product's help or a third-party brand page.

### 2.3 Shared command contract

Each command definition must contain:
- Stable CUBI command ID and translated label.
- Menu path, toolbar group, icon and keyboard shortcut if assigned.
- Supported window keys and supported view/layout keys.
- Required selection cardinality and selection types.
- Required project state and user permission.
- Enabled/disabled reason and visibility rule.
- Target type: window, dialog, drawer, inline action, toggle or data operation.
- Input contract and validation.
- Expected state transition or persisted effect.
- Undo/redo support where safe, revision behavior and audit event.
- Success and failure feedback, including conflict handling.
- Test ID and evidence reference.

The command registry must be the single source for menu entries, toolbar icons, context menus and keyboard shortcuts. Do not create separate, inconsistent action maps per screen.

## 3. Menu, toolbar and context-menu inventory

### 3.1 Workspace menu

Required command families:
- Project lifecycle: create, open, switch, close current, close all, recent projects.
- Data exchange: import, export, mapping/review, validation, backup and restore.
- Output: print preview, page setup, print and PDF/export actions.
- Recovery: session recovery, unsaved changes, restore layout and supported project restore.
- Account/session: preferences, profile, sign out.
- Any command not backed by an available service must be disabled with a reason.

### 3.2 Edit menu

Required command families:
- Undo, redo, edit history where the affected operation is truly reversible.
- Cut, copy, paste, paste special, fill down and fill across where data type permits.
- Add, edit, duplicate and delete for the selected entity type.
- Add/edit relationships; link/unlink selected activities.
- Assign resources, roles, activity codes, predecessor/successor links and documents.
- Renumber activity IDs with preview and collision validation.
- Find, replace, select all and selection navigation.
- Bulk edit / Global Change only through preview, explicit affected-row count and approval before execution.
- Destructive operations must report the affected selection and dependent records.

### 3.3 View menu

Required command families:
- Window layouts: new, open, save, save as, delete, import/export where supported.
- Top layouts: table, Gantt, network, chart, usage profile and usage spreadsheet as applicable.
- Bottom layouts: Details, activity/resource profile, spreadsheet, Trace Logic or none as applicable.
- Layout and bottom-view options.
- Columns: choose fields, order, visibility, width, alignment, pin/freeze and reset.
- Filters: predefined, custom, compound conditions, save/apply/remove.
- Group and Sort: hierarchy, field/path groupings, multiple group levels, multiple sort levels, band formatting, totals and expand/collapse.
- Timescale: unit, interval, visible range, date headers and zoom.
- Gantt bars: data, styles, shapes, colors, labels, positions, filters, legend and dependencies.
- Progress line/spotlight, Data Date line, relationship line, baseline display, nonworking shading and background grid.
- Font, color, row height, chart font/color, zoom, best fit and expand/collapse.
- Toolbars, toolbar reset/lock/customization and tab groups.
- Hint help/context hints and full-screen control.
- Workspace theme selection, including complete light/dark palettes, window/panel background customization and user-defined color presets. Brand logo colors remain unchanged; workspace colors are not limited to brand tokens.

### 3.4 Project menu

Required window launchers and project-scoped tools:
- Activities and an independently saved additional Activity view where supported.
- WBS.
- Resource Assignments.
- Baseline assignment and maintenance.
- Project Expenses.
- Documents/work products.
- Project Issues, Thresholds and Risks.
- Project Details, codes, defaults, notebook, calendars and custom fields.
- Menu entries must open the real window/dialog and must not land on an empty generic module page.

### 3.5 Organization menu

Required organization/global dictionaries:
- Business Domains and project/portfolio register.
- Responsibility structure / organizational hierarchy.
- Resources, roles, resource codes and activity/project codes.
- Global, project and resource calendars; work hours, shifts, holidays and exceptions.
- Resource curves and price/rate dictionaries.
- Cost accounts, funding sources, currencies and financial periods.
- UDF/custom-field dictionary.
- Each dictionary has its own register, Details panel, create/edit/delete/copy behavior, validation, filters, columns and permission rules as applicable.

### 3.6 Tools menu

Required tool families:
- Schedule and Schedule Options.
- Schedule Check / diagnostics.
- Resource Leveling and leveling log.
- Progress/actuals application and calculation-safe update tools.
- Assignment cost recalculation.
- Summarization and stored-period performance.
- Global Change.
- Reports, report groups/batches, designer/editor, preview and distribution.
- Import/export validation and mapping.
- CUBI Engineering Assistant, Smart Guide, Form Builder and approved CUBI tools.
- External or future features are clearly marked unavailable until the service, permission and workflow exist.

### 3.7 Administration menu

Required administration surfaces:
- Users and invitations.
- Security/access profiles and permissions.
- Role and project membership administration.
- Organization/system defaults.
- Baseline, expense, document, risk, WBS and other approved category dictionaries.
- Currency, unit-of-measure and financial period administration.
- Audit log, data retention, backup/recovery and access history.
- System-level controls must not appear to ordinary project users without appropriate permission.

### 3.8 Help menu

Required:
- CUBI workspace guide and context help.
- Keyboard shortcut reference.
- Help for the active window, current selection and current dialog.
- Documentation library, release notes and About CUBI.
- No source-product name, URL, logo, trademark, screenshot or external product link in customer-facing Help.

### 3.9 Toolbar families

Implement toolbar groups by purpose, not by random icon placement:
- Standard / file and output.
- Edit and selection.
- Project navigation.
- Organization/dictionary navigation.
- Layout and display.
- Top layout and bottom layout.
- Assignments.
- Move/reorder/arrange.
- Find/search.
- Schedule and resource leveling.
- Reports and publishing/export.
- CUBI tools and assistant.
Each icon needs an exact command mapping, a tooltip, a disabled reason where relevant, a consistent icon glyph, pressed/selected state and keyboard support.

### 3.10 Context (right-click) menus

Right-click on a record, chart object or empty region must use the context object and active window to build the correct menu. A single universal context menu is not acceptable.

Required context targets:
- Window tab.
- Navigation tree node.
- Project/EPS node.
- WBS node/group band.
- Activity row.
- Gantt bar, milestone, summary bar, baseline bar and relationship arrow.
- Resource, role and assignment row.
- Column header and selected cells.
- Chart/network node and connection.
- Spreadsheet cell/heading.
- Empty space in table, Gantt, chart, details pane and register.
- Dialog field/list item where relevant.

Every context command has the same permission, dirty-state, validation, revision and execution rules as its menu/toolbar counterpart. Right-clicking blank space must offer view/layout actions; right-clicking a record must offer record actions; right-clicking a visual object must offer the actions valid for that object.

## 4. Window specifications

## 4.1 Projects / Business Domain / Portfolio

**Purpose:** manage the authorized project register and the hierarchy that organizes projects.

**Main layouts**
- Business Domain / portfolio / project tree.
- Project register table.
- Project chart or Gantt where applicable.
- Optional summary view for selected projects.

**Table and hierarchy fields**
- Project ID, project name, short name, domain, portfolio, status, priority, project type, start/finish, responsible manager, project owner, currency, date system, calendar, revision and modified metadata.
- Configurable columns, widths, order, visibility, sorting, filters, grouping and hierarchy order.
- Search/find and multi-select, with commands enabled only when selection cardinality and permission permit.

**Project Details target tabs**
- General, Dates, Defaults, Resources, Settings, Codes, Notebook, Budget Log, Spending Plan, Budget Summary, Funding, Baselines, Documents, History and UDFs.

**Interactions and context commands**
- Expand/collapse hierarchy; add child domain/portfolio/project where service permits.
- Open, close, switch, copy, archive/status change and delete only where supported.
- Context menu differs for domain, portfolio, project and blank register area.
- Project selection updates project scope and breadcrumb; switching project closes or scopes project windows safely and preserves authorized global windows.
- Project defaults must be applied to newly created activities, calendars and assignments only through explicit persisted settings.

**Acceptance**
- Multi-project/organization tree is backed by authorized server records, not invented hierarchy.
- Project status/permissions and open state are explicit.
- Project switch retains user window state but reloads correct project data and revision.

## 4.2 Activities — highest-priority reference window

**Purpose:** the primary planning workbench that synchronizes WBS, activities, relationships, Gantt, details and all activity-level tools.

**Required top layouts**
1. Activity Table.
2. Gantt Chart.
3. Activity Network.
4. Approved chart/usage layouts where applicable.

**Required bottom layouts**
1. Activity Details.
2. Activity Usage Profile.
3. Activity Usage Spreadsheet.
4. Trace Logic.
5. None.

**Activity Table**
- Dense, fixed-layout grid with column chooser, display titles, ordering, width, visibility, pin/freeze, alignment, sorting, multiple selections and row/cell keyboard navigation.
- Full activity field catalog through the column manager; default columns are a user layout, not a data limitation.
- Editable cells only when the field is writable and the user has permission; clear validation and revision conflict feedback.
- WBS hierarchy/grouping must be readable through indentation, hierarchy labels, group bands, level styling, row icons and collapse controls.
- Grouping supports hierarchy, WBS path and selected fields; multiple levels, sorting within groups, group summaries, total bands and group-specific font/color.
- Table presentation includes font, color, row height, selected-row, active-cell, invalid-cell and read-only states.
- Multi-select and fill-down must preserve field validation and never apply an invalid value silently.
- Find, filter, saved filter, compound filter, clear filter, selection count and total project count.
- Row-number display, renumber IDs, copy/paste, cut/paste and fill-down where supported.
- Column and filter state persist per user/window/project layout.

**WBS hierarchy behavior inside Activities**
- WBS summary/group rows must be visually distinct from activity rows.
- Each WBS level has a coherent level-specific visual treatment: independently configurable background color/tint, font weight, indentation, label, icon and separator hierarchy. WBS colors may be chosen from the active workspace theme or user palette and must remain legible in both light and dark themes.
- WBS level styling is separate from status, criticality, selection and activity-type styling. These signals must not overwrite one another.
- Every expandable WBS node has a clear plus/minus affordance.
- Clicking minus collapses only that node's descendant rows. Clicking plus restores only that node's descendants.
- Collapse/expand works at every hierarchy depth, retains selection safely, and does not alter activity records, relationships, dates, schedule calculations or project counts.
- Collapse/expand state is part of the saved layout and survives refresh/reopen.
- A group header must show enough identity/context to know which WBS branch is collapsed.

**Mandatory synchronized table/Gantt contract**
- Table and Gantt must consume the same canonical ordered row/view model and the same activity identities.
- When a WBS branch is collapsed, all activity rows and all corresponding Gantt bars, labels, baseline bars and row-level relationship segments under that branch disappear together from the visible viewport.
- Expanding the branch restores those rows and their visual counterparts at the correct vertical positions.
- Scroll position and row geometry are synchronized vertically; time-axis pan/zoom is synchronized horizontally with the shared date scale.
- A hidden row caused by filtering/collapse/scroll virtualization remains part of project data and the authoritative schedule input. Visibility is never an inclusion/exclusion rule for CPM.
- Group summaries are computed from authoritative data and are not substitutes for underlying child activities.

**Gantt Chart**
- Shared time axis with selectable scale and interval: day, week, month, quarter, year and any finer/coarser unit supported by the time model.
- Header shows year/period hierarchy, current visible range, working/nonworking periods and clear date ticks.
- Draw activity bars with visually calibrated thickness, cap/shape, start/finish geometry, fill, border, progress segment and label placement. Rows, bars and table must line up pixel-consistently.
- Different visual semantics for normal task, critical task, completed task, in-progress task, not-started task, start/finish milestone, WBS Summary, Level of Effort, baseline and actual/remaining work.
- Bar Styles editor: bar type, filter/condition, shape at start/end, center fill, outline, color, pattern, height, position, label and label position.
- Relationship lines: FS, SS, FF and SF, with lag/lead representation, endpoint routing, arrowheads and overlap handling.
- Display controls: relationship lines, critical path, multiple float path, legend, grid/background lines, nonworking time shading, Data Date line, progress line, baseline, actual/remaining, summary bars and bar labels.
- Pan/scroll, zoom in/out, best fit, jump to activity, change visible timescale and retain row/axis alignment.
- Edit start/finish/duration by drag only where domain validation allows it; all drag edits must commit through the real mutation path and handle revision conflicts.
- Hover/selection tooltip shows real activity identity and supported dates/duration/float/progress; it must not derive or invent calculated data.
- A bar's right-click menu is specific to the bar kind and available commands. A dependency arrow has its own menu; empty chart area has view commands.
- No default arbitrary bar thickness; use measured, consistent engineering density. Bars must not overlap row boundaries or cover labels and relationships.

**Activity Details target tabs**
- General: activity identity, name, short name, type, WBS, calendar, duration type, percent-complete type, constraints and approved defaults.
- Status: status, status code, percent complete, actual start/finish, remaining start/duration, suspend/resume and update state.
- Resources: resource/role assignments, units/time, budgeted/actual/remaining units and costs, driving/non-driving behavior, curves, rate source and calendars.
- Predecessors: incoming links, relationship type, lag/unit/calendar, predecessor dates and link creation/removal.
- Successors: outgoing links, relationship type, lag/unit/calendar, successor dates and link creation/removal.
- Relationships: complete linked-record register and relationship editing.
- Codes: assigned activity codes and values.
- Notebook: notes/topics and history.
- Steps: ordered activity steps, descriptions, weights and completion where supported.
- Work Products & Documents: linked documents, category/status, reference/open action and assignment.
- Expenses: expense rows, category, accrual type, cost and assignment.
- Issues: linked issues, status, owner and history.
- Risks: linked risks, category, response and exposure where supported.
- Summary: calculated summary values and links to source records.
- UDFs: typed custom fields with validation.
- Update History: dated change records, actor, old/new values and source; do not present nonpersisted history as real.

**Activity Network**
- Activity nodes, identifiers, node field selection, node template, node size, layout direction, spacing, alignment/arrange, zoom/fit and selection.
- Relationship connectors show FS/SS/FF/SF and lag information.
- Node and connector context menus.
- Selecting a node synchronizes the selected activity in grid, Gantt and Details.
- Editing or linking in the network uses the same relationship/record services and validation as the table/Gantt.

**Activity Usage Profile and Spreadsheet**
- Time-phased units/cost/remaining/actual values, bucket period, cumulative/noncumulative, histogram/curve/stacking, legend and background lines.
- Spreadsheet field selection, column arrangement, period columns, totals and copy/export.
- Profile selection may filter/highlight the related activities without limiting scheduling input.
- Read-only periods and unsupported data must be explicit.

**Trace Logic**
- Show predecessor/successor chain around selected activity, connection type, lag and relationship direction.
- Layout preferences, spacing, navigation and link highlight.
- Navigation updates the selected activity consistently in all Activity views.

**Activities right-click menu matrix**

| Right-click target | Minimum command families |
|---|---|
| WBS group row | Expand/collapse this branch; expand/collapse descendants; add child WBS; open WBS details; group/filter/sort; branch-specific layout commands; authorized WBS edit/delete |
| Activity table row | Open/edit activity; add above/below or in selected WBS; copy/cut/paste/duplicate; delete with dependency warning; dissolve where supported; assign resources/roles/codes/documents; add predecessor/successor; link/unlink; renumber; select related activities; show in Gantt/network; view Details |
| Selected cells/column header | Copy, fill down where valid, filter by field/value, sort, pin/freeze, hide/show, resize, align and choose columns |
| Gantt task bar | Open activity; edit dates/duration where allowed; add/edit relationship; show predecessors/successors; bar style/label; select related; open details; baseline/progress display commands |
| Milestone/summary/baseline bar | Type-specific details, visibility/style/label and selection commands; no task-only duration mutation on zero-duration milestones |
| Relationship arrow | Edit/delete relationship, change type/lag/calendar, show endpoints and selection of predecessor/successor |
| Empty table area | Columns, filters, group/sort, layout, selection reset, paste if valid, import/export where allowed |
| Empty Gantt area | Timescale, zoom, gridlines, nonworking shading, legend, bar styles, progress/Data Date/baseline display and layout |
| Network node/edge | Node details, select/open activity, edit relationship, arrange, zoom/fit and view settings |
| Details pane/tab | Configure tabs, reset/order tabs, copy field value, open linked record where supported |

**Activity scale/performance rules**
- The project may contain any volume permitted by the product's documented commercial/resource constraints; there is no hard-coded display cap such as 180 rows.
- Rendering may virtualize DOM rows/bars or progressively render viewport segments, but the API/read model must make the full authorized dataset queryable.
- Filtering/grouping/collapse/paging is a view projection only. All schedule and CPM operations work against the complete authoritative project snapshot.
- Selection totals must distinguish visible, selected, filtered and total project activity counts where useful.
- Exports and bulk operations must clearly state whether their scope is current visible selection, current filter or entire project.
- Tests must include at least 250 activities and a larger stress fixture; verify no silent truncation or omission.
- A schedule result must expose the calculation's activity count and snapshot identity. Tests compare the count to the authoritative stored project population after applying only documented semantic exclusions (never UI visibility).

**Activities acceptance gates**
- WBS level color bands are coherent and distinguish group rows from activity rows.
- Expand/collapse of one WBS node hides/restores the corresponding grid rows and every matching Gantt visual at once.
- Table/Gantt scroll alignment is stable after expand/collapse, filter, sort, zoom and resize.
- Context menus are correct for all listed hit targets and command availability matches permissions/selection.
- 250+ fixture is fully visible through scrolling/search/filter; no 180 cap or silent slice.
- Run Schedule computes all persisted schedule-eligible activities whether visible, filtered or collapsed.
- Network, Details, profile and spreadsheet remain synchronized to the same selected activity.
- All layout states persist and restore with revision safety.
- Browser evidence is captured at 1280x720, 1366x768 and 1920x1080, including high density and collapsed WBS cases.

## 4.3 WBS window

**Main layouts**
- Hierarchical WBS table.
- WBS chart/tree view with box layout templates.
- Optional WBS-linked summary/Gantt view where backed by data.

**Required fields and details**
- WBS code, full hierarchical code, name, parent, sequence/order, status, responsible manager/OBS, dates, progress/earned-value settings, category/code values, notebook, UDF and audit/history data where supported.
- Details tabs: General, Status, Resources, Earned Value, Work Products & Documents, Notebook, Issues, Risks, UDFs and History.

**Operations**
- Add child/sibling, edit, copy, cut/paste, reorder/move, delete with child/activity protection, expand/collapse and chart navigation.
- Color/format by hierarchy depth and configured status/category; no mixed semantic color meanings.
- WBS selected in WBS window does not silently change an unrelated project-level details context.

**Acceptance**
- WBS chart and table use the same persisted hierarchy and order.
- Activity-to-WBS assignment is validated and cannot reference another project/revision.
- Parent/child relationships remain consistent after copy, move, reorder and refresh.
- Expand/collapse behavior is consistent with Activities WBS grouping.

## 4.4 Resource Assignments window

**Main layouts**
- Assignment table grouped by resource, with optional grouping by project, WBS or activity.
- Time-phased usage profile and spreadsheet.
- Details panel for selected assignment.

**Fields**
- Resource/role, activity, project, WBS, assignment type, units, units/time, budgeted/actual/remaining units and costs, rate type/source, calendar, curve, driving flag, dates, periods and status.

**Operations**
- Assign/remove/replace resource or role; edit rate type/source; recalculate costs; set units and period values; inspect allocation and capacity.
- Group/sort/filter, column manager, timescale, spreadsheet field selection, profile chart and export.
- Context menus for resource, role, assignment, activity, period cell and blank region.
- Resource and assignment calendars must remain distinct; unit conversions must use explicit units and periods.

**Acceptance**
- Resource assignments are grouped correctly and reconcile to activities and resource dictionaries.
- Capacity and demand views use matching units, calendars and time periods.
- Assignment create/edit/delete semantics reflect actual service capabilities. Unsupported operations are disabled, not simulated.
- Profile and spreadsheet read the same assignment data.

## 4.5 Resources window

**Main layouts**
- Resource hierarchy/table.
- Resource chart/usage profile.
- Resource Details.

**Fields and Details tabs**
- Resource ID/name, resource type (labor/nonlabor/material), parent/hierarchy, unit of measure, status, calendar, shifts, limits/capacity, price/rate history, roles, codes, comments, curves and UDFs.
- Details tabs: General, Details, Units & Prices, Roles, Codes, Calendars, Shifts, Curves, Capacity/Availability and UDFs.

**Operations**
- Add resource/wizard, edit, copy, cut/paste, delete with assignment warning, assign shared/personal calendar, define shifts, rate changes over time, comments and discussion.
- Resource analysis across projects only within permitted scope.
- Context menu differs for resource group, resource, rate row and chart/blank area.

**Acceptance**
- Labor, nonlabor and material resources have type-specific fields and validation.
- Effective-dated rates and capacity resolve at the correct date.
- Resource hierarchy, role assignment and calendar changes persist and are auditable.

## 4.6 Roles window

- Role hierarchy/table and role Details.
- Fields: role ID/name, description, proficiency, limits, price/unit rates over time, codes, UDFs and assignments.
- Operations: add/edit/copy/delete (where supported), assign role to activity/resource, set proficiency, limits and effective-date rate.
- Context menus and Details tabs must distinguish role dictionary from a resource's assigned role.
- Verify rate effective dates, assignment unit conversion and role-limit calculations.

## 4.7 Calendars window

**Calendar kinds**
- Global, project and resource calendars.
- Shared and personal resource calendars where the CUBI product model supports these scopes.
- Effective dated calendar versions and derived/inherited rules.

**Views and fields**
- Calendar register/tree, calendar details, workweek/day pattern, daily work intervals, exceptions, holidays, shifts, base-calendar reference, hours per time period and assignments.
- Calendar Details tabs: General, Workweek, Work Hours, Exceptions/Holidays, Assignments, Base/Inheritance, History.

**Operations**
- Create, copy, edit, replace, delete with reference checks, set defaults, add/edit exceptions, inspect assignments, change working hours and validate time-period basis.
- Persian/Jalali and Gregorian date entry/display must share canonical date values with scheduling and exports.
- Calendar version must be pinned in schedule inputs; no calculation may read a mutable latest calendar during an immutable run.

**Acceptance**
- UI workweek/holiday preview matches the effective calendar used by CPM.
- Activity, resource and relationship-lag calendars remain distinct.
- Editing a calendar version does not mutate old schedule snapshots.

## 4.8 Dictionaries and reusable definitions

### Project, activity, resource, role and WBS codes
- Register and value list with scope, hierarchy and ordering.
- Add/edit/delete values, assign values to records, show code colors and support global/project/domain scope where applicable.
- Activity-code value color is a visual category signal and must not collide with critical path or progress colors.
- Security and scope control which users may see/edit each code.

### User-defined fields
- Dictionary for field name, entity type, data type, width/scale, lookup values, formula or indicator behavior where supported.
- Validate type, requiredness, uniqueness, scope and field visibility.
- Display the same UDF consistently in the correct register, Details tab, filters, columns and reports.

### Resource curves and shifts
- Curve dictionary, points/shape, period basis, assignment relation and effective rules.
- Shift dictionary/calendar and application to resource availability.
- Profile chart and spreadsheet must display the same curve/shift calculations as the resource calculation core.

### Cost accounts, funding and currencies
- Hierarchical cost-account register, defaults, funding source register/assignment, currency definitions and conversion policy.
- Financial data must store explicit currency and exact decimal precision; no silent inferred currency.

### Notebooks and activity step templates
- Notebook topic dictionary and notes/history linked to project/WBS/activity/resource as permitted.
- Activity steps: sequence, name/description, weights, status, planned/actual dates and template reuse.
- Templates are dictionaries; assigned steps remain activity-scoped records.

## 4.9 Schedule and Schedule Options

**Schedule execution surface**
- Run Schedule command and dialog with project scope, Data Date, calculation mode/options, calendar context, log/diagnostics, warnings and run identity.
- Schedule Check with condition list, severity, scope, result count and drill-through to affected activity/relationship/constraint.
- Activity Critical Path and multiple-float-path tools with path selector and selection drill-through.
- Schedule result readback must bind to the exact published input snapshot and calculation context.

**Required concepts and settings**
- Data Date, project start/finish, project calendar, activity calendars, relationship-lag calendar, expected-finish behavior, out-of-sequence behavior, critical path definition, total/free float method, multiple float paths, open ends, constraints and resource-leveling options.
- Every setting needs help text, input constraints, units, supported values and an explicit implementation disposition.
- Unsupported option combinations must fail explicitly and must never be quietly ignored.
- CUBI scheduling must not calculate only the currently visible or selected page of activities.

**Acceptance**
- Run creates an immutable project-revision-bound snapshot.
- The snapshot includes all persisted schedule-eligible activities, relationships, constraints, effective calendar versions and relevant resource facts.
- The output's activity count matches the snapshot input count, with all exceptions explicitly diagnosed.
- Results are fresh-read from the published snapshot; no browser calculation substitutes for the shared core.
- Re-run after Data Date, actuals, relationships, constraints or calendars changes produces a new calculation identity.

## 4.10 Baselines and schedule comparison

- Baseline register with type, name, source project/revision, capture date, status, assignment as primary/secondary/tertiary or user-selected.
- Baseline creation/copy/update/modify/delete with explicit confirmation and immutable version/history.
- Baseline comparison by activity and WBS: original/current start/finish/duration, variance, baseline cost/units, progress and selected field differences.
- Gantt can display multiple approved baseline bar layers with distinct styles and legend.
- No baseline page may be called complete if it only persists baseline metadata but not activity-level baseline values.
- Schedule comparison results must state incompatible units/calendars/fields and never fabricate equivalence.

## 4.11 Progress, actuals and earned value

**Progress update surface**
- Activity selection, Data Date, activity status, percent-complete type/value, actual start/finish, remaining duration/start and suspension/resumption where supported.
- Update all activities, selected activities or filtered activities only with an explicit scope preview and approval.
- Apply Actuals must preview the impact on assignments, units/cost, actual dates and remaining work before commit.
- Show changed and unchanged counts; store actor, timestamp and before/after values in update history.

**Earned Value**
- PV, EV, AC, BAC, EAC, ETC, VAC, CPI, SPI and selected methods/assumptions, currency, period and source baseline.
- EVM values must be read from the authoritative model with explicit unavailable reasons when inputs are missing.
- Activity/WBS/project roll-ups, historical period data and baseline variance drill-through.
- CUBI report/chart controls must not label an estimate as actual or show a zero as a substitute for missing data.

## 4.12 Tracking window

- Tracking layout register with open/new/save/save-as/share/import/export/delete.
- Top/bottom layout control, table, Gantt, spreadsheet and profiles.
- Show/hide top/bottom regions and columns, filter, group/sort, expand/collapse, row font/color/height, chart bar style and timescale.
- Track progress against Data Date and selected baseline; allow selection/drill-through to project/activity/resource.
- Layout state is separate per user and project where the scope requires it.
- Tracking window must be usable as an independent professional view, not an image or report card.

## 4.13 Activity and Resource Usage Profiles / Spreadsheets

- Activity Usage Profile: units/cost over time, curve, histogram, cumulative/noncumulative, time period, filters, legend and display.
- Resource Usage Profile: regular/stacked histogram, units/cost, availability, limits, over-allocation, overtime and past-period actuals.
- Activity Usage Spreadsheet: configurable time-phased fields and periods.
- Resource Usage Spreadsheet: select resources/roles, view by project/all projects subject to permission, customize columns, period values, totals, group/sort and resize panes.
- All profile/spreadsheet values come from the same authoritative assignment/time-phased data source. Empty, unavailable or unsupported buckets must be visible as such.

## 4.14 Documents / Work Products

- Document register and assignment register; type/category/status, name, ID, revision, location/reference, owner, project/WBS/activity linkage, dates and history.
- Details: General, Status, Category, Location/Reference, Assignments, Notes and History.
- Add/edit/delete, open/download, assign/remove, category/status change and filter/search.
- Context menu differs for document record, assignment row and empty register.
- Document access is permission-checked; unavailable external locations must not be represented as successfully opened.

## 4.15 Expenses, Cost Accounts, Budget and Funding

- Expense register with activity assignment, category, accrual type, description, planned/budgeted/actual cost and currency.
- Expenses can be created and assigned from the Expenses window or supported Activity Details context.
- Expense categories and accrual rules are dictionaries; expense rows are persisted project records.
- Cost Account hierarchy register with parent/child, code, description and project default; copy/cut/edit/delete where supported.
- Budget and Funding views: budget setup, changes, funding sources, monthly spending, planned/actual totals and variance.
- Details and history show source records and revision.
- Decimal precision, units and currency are explicit; no float rounding or inferred units.

## 4.16 Issues, Thresholds and Risks

### Issues
- Register/list, status, severity/priority, description, responsible person/OBS, project/WBS/activity/resource link, duration, tracking layout and history.
- Add/edit/status update/assign/notify/history and delete where supported.
- Issue navigator and drill-through.

### Thresholds
- Threshold definition, parameter/metric, limit values, responsible person, monitoring status, generated issue link, enable/disable and history.
- Monitor against authoritative project data and show when the last monitor ran.
- No threshold-generated item may be fabricated by the UI.

### Risks
- Risk register, category, probability, impact, response/mitigation, owner, activity/project linkage, exposure and history.
- Create/assign/respond/modify/remove assignment/delete where permitted.
- Mark risk calculation scope and data provenance; distinguish Professional-only features from common product behavior.

## 4.17 Reports

- Report register, groups, batches, wizard, advanced designer/editor, preview, run status, output format, schedule, distribution and report preferences.
- Create/modify/import/export/duplicate/delete as authorized.
- Report definition and execution are separate states; a saved report is not proof it can run successfully.
- Report datasets must identify source fields, scope, date/time, baseline, Data Date, currency and filter.
- Preview, validation errors, empty result, job progress and download states are real.
- Reporting guide is the specialized visual/functional reference.

## 4.18 Global Change / bulk operations

- Condition builder with AND/OR and typed field operators.
- IF / THEN / ELSE structure, expression editor, rearrange, copy/paste, validation and function/operator reference.
- Preview affected records, show before/after, counts and unsupported expressions before apply.
- Apply requires explicit approval; operation records actor, revision, timestamp and audit identity.
- Undo only where the operation is transactionally reversible; otherwise show an immutable change record and supported restore path.

## 4.19 Administration and system preferences

- User register, invitations, enabled/disabled access, security/access profiles, global/project profiles, permission matrix and membership.
- Role-based project access and resource-level access with visible reasons.
- System settings: default work hours/time periods, week start, default activity duration/type, hierarchy/code/ID constraints, baseline count and field length limits, default earned-value settings, summarization and upload restrictions.
- Category dictionaries: baseline types, expense categories, WBS categories, document categories/statuses, risk categories, notebook topics and units of measure.
- Currencies and financial period calendars/records.
- Audit, export/download access, backup/restore and retention.
- All user and system admin actions require strong authorization and audit evidence.

## 4.20 Import, export, multi-project and offline operations

- Import/export wizard and mapping/review step, validation, field mapping, preview, warnings, error rows, commit/rollback and post-import readback.
- Export scope clearly identifies all project data versus selected/filtered records.
- XML/MSP/Excel/PDF or any other format is shown only when a real codec and test exists.
- Multi-project operations state which projects are open, selected and authorized.
- Offline operations must record local state, sync conflicts, stale revisions and recovery. Do not present unsynced data as server-saved.
- No import/export function is complete from a file picker or downloaded header-only document; prove round-trip integrity.

## 4.21 Companion visualization and reporting tools

- Advanced schedule visualization and time-scaled logic diagrams are catalogued separately from the core Gantt layout.
- Report design/creation and batch processing are catalogued separately from report viewing.
- If CUBI folds these into Tools windows, preserve the supported input/output and workflow; do not claim parity based on a launcher icon alone.

## 5. CUBI-only approved additions

These extend the source model and must be labelled as CUBI capabilities in UI and documentation:
- Persian/Jalali date input and display alongside Gregorian storage, preserving time zone and calendar semantics.
- CUBI Engineering Intelligence Assistant with typed/speech/files, proposal-before-write, user approval, permission-aware execution and verified results.
- Organization Form Library and project-specific Form Library with template inheritance, field types, approvals and history.
- Project comparison/difference with immutable comparison runs and field-level changes.
- Construction-specific field workflows (daily logs, inspections, quality, safety, procurement, claims and progress evidence).
- Offline desktop/mobile architecture while sharing the same domain and calculation core.

These additions must not weaken or omit the baseline window behaviors above.

## 6. Related existing repository references

- [Workspace window inventory](workspace-window-inventory.md)
- [Visual shell master audit](workspace-visual-shell-master-audit.md)
- [Workspace information architecture](workspace-information-architecture.md)
- [Window reference](../reference/oracle-p6-window-reference.md)
- [Menu reference](../reference/oracle-p6-menu-reference.md)
- [Visual reference audit](../visual-reference-audit.md)
- [Web surface traceability matrix](../../../engineering/WEB_SURFACE_TRACEABILITY_MATRIX.md)
- [CUBI V1 acceptance matrix](../../../governance/CUBI_V1_ACCEPTANCE_MATRIX.md)

The existing audit documents describe known implementation gaps at their audit dates. They must be refreshed against the actual branch and browser before assigning a current implementation status.
