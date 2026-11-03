# CUBI Workspace Dialog Inventory

Status: Phase 3 blueprint.
Rule: a dialog may be built before its backend, but it must state its implementation state and must never show a fabricated success. Fields below are the minimum contract; additional fields may be added only with a data source.

## Project and file

| Dialog | Purpose | Minimum controls | Data / API | Status |
| --- | --- | --- | --- | --- |
| New Project — Step 1 Business Domain | Classify the project | Domain, portfolio and responsible organisation pickers | `sector`/`domain` on project create | Visual preview implemented; validation/API not connected |
| New Project — Step 2 Identity | Name and ID | Project name (2–120), editable suggested Project ID with tenant uniqueness check, description (≤2000) | `POST /api/projects` | Visual preview implemented; uniqueness/create not connected |
| New Project — Step 3 Configuration | Planning defaults | Start date (Gregorian/Jalali), target finish, date system, project calendar, responsible organisation, default activity duration type | Project create + calendars API | Visual preview implemented; validation/API not connected |
| New Project — Step 4 Development | Seed the plan | Blank/template WBS, authorized project copy, optional starter WBS/activities and resource/calendar templates | WBS/activity APIs | Visual preview implemented; creation/copy not connected |
| Open Project | Choose project | Search, domain filter, recent, role badge | `GET /api/projects`, `POST /open` | Implemented as picker, not dialog |
| Import / Export | Interchange | Format, project, mapping preview, conflict policy | Existing interchange API | Implemented (panel) |
| Print Preview / Print / Page Setup | Output | Layout, page, scale, margins, header/footer | Print profile API (not built) | Missing |
| Project Settings | Edit metadata | Name, description, start, date system, primary calendar, revision | `GET/PATCH /api/projects/{id}` | Implemented (modal) |

## Layout and data display

| Dialog | Controls | Behaviour | Status |
| --- | --- | --- | --- |
| Columns | Available/Selected lists; add/remove one/all; reorder; at least one visible; search/group/collapse available columns; edit title/width/alignment/visibility; Copy From; Default | Apply to active layout; save with layout | Visual preview implemented; layout persistence not connected |
| Filters | Default/Global/Layout/User-Defined categories; selected-filter All/Any; named filter; criteria All/Any; Parameter/Is/Value rows; comparison and range operators; add/delete/reorder/optimize/make-global | Apply to table/Gantt; show filter name in layout bar | Visual preview implemented; filter execution/persistence not connected |
| Group and Sort | Up to 20 grouping levels; hierarchical fields with To Level; multiple sort keys and ascending/descending/hierarchical order; Font & Color per band; indent/alphabetical bands; title/ID/code/name display; empty bands; page breaks; group/grand totals | WBS default; group before sort; persist per layout | Visual preview implemented; persistence not connected |
| Timescale | Two/Three lines; Timescale Start; Primary/Ordinal dates; date type and interval; ordinal start/interval; Day/Shift calendar; financial-period calendar; Font & Color/default font | Gantt/profile/spreadsheet time axis | Visual preview implemented; settings persistence not connected |
| Bars | Bar list, add/delete, style, label, filter, timescale, preview | Gantt bar rendering | Missing |
| Bar Chart Options | Relationship lines, background lines, legend, data date line, progress line | Gantt display | Partial (link toggle only) |
| Table Font and Row | Font scale, row height, colours | Table rendering | Missing |
| Bottom Layout Options / Customize Details | Tab list, visible, order | Activity Details tabs | Missing |
| Layout Manager (New/Open/Apply/Save/Save As/Delete/Import/Export) | Available-layout list; name, description, modified date, owner, scope (All Users / Another User / Current User / Project), target user/project, default-for-project flag, Apply preview, multi-select export, `.PLF` import/export, unsaved-current-layout prompt, privilege-aware actions | Persist presentation options only; never project data. Scope and destructive actions require explicit privilege checks. | Visual preview implemented; layout service, file interchange and privilege checks not connected |
| Collapse To | Group band | Collapse table to band | Missing |
| Find / Replace | Field scope, text, direction, match case | Highlight/next | Missing |
| Renumber Activity IDs | Prefix, start, increment, scope (selected/all) | Preview + apply; revision guard | Missing |

## Assignment and activity

| Dialog | Controls | Status |
| --- | --- | --- |
| Assign Resources | Resource list, search, assigned list, units/time, cost, curve | Missing |
| Assign Resources by Role | Role, candidates, units | Missing |
| Assign Roles | Role list, proficiency, assigned | Missing |
| Assign Activity Codes | Code dictionary, values, assigned | Missing |
| Assign Predecessors / Successors | Activity search, relationship type (FS/SS/FF/SF), lag | Partial (logic panel) |
| New/Edit Activity | ID, name, type, duration, calendar, WBS, dates, constraints | Partial (inline form) |
| New/Edit WBS | Code, name, parent, sequence, status | Implemented (forms) |
| New/Edit Relationship | Predecessor, successor, type, lag | Implemented (forms) |
| Dissolve Activity | Confirmation, resulting FS link preview | Missing |
| Activity Details > General/Status/Resources/... | See `workspace-window-inventory.md` | Missing |

## Tools

| Dialog | Controls | Status |
| --- | --- | --- |
| Schedule | Data date, project scope, options (existing schedule-cycle fields: leveling priority, level all, within float) | Implemented (options + run) |
| Level Resources | Leveling options, resources, priority, float limit, preview | Missing |
| Apply Actuals | Data date, project scope | Missing |
| Update Progress | Scope, percent/actual entry | Missing |
| Recalculate Assignment Costs | Scope, confirmation | Missing |
| Store Period Performance | Financial period, project | Missing |
| Global Change | Parameter rows, preview count, apply | Missing |
| Monitor Thresholds / Issue Navigator | Scope and results | Missing |
| Reports runner | Report, parameters, preview, export | Missing |

## Administration

| Dialog | Controls | Status |
| --- | --- | --- |
| Users | User list, roles, project access | Missing |
| Security Profiles | Profiles, privileges | Missing |
| Admin Preferences | Defaults, help location, numbering | Missing |
| Admin Categories | Category/value dictionaries | Missing |
| Currencies | Currency, symbol, decimals, base flag | Missing |
| Financial Period Calendars | Period calendar, start/end, generate periods | Missing |
| Business Domains / Portfolios | Tree/list, add/edit/delete | Missing |
| Calendars | Calendar list, workweek, shifts, holidays, exceptions | Partial (holidays only) |
| Codes (activity/resource/role/project) | Dictionary tree, values, colours | Missing |
| UDFs | Subject, data type, formula, values | Missing |
| Cost Accounts / Funding Sources | Dictionary trees | Missing |
| Resource Shifts / Curves | Shift windows, curve points | Missing |

## Cross-dialog rules

1. **Revision guard:** every mutation sends `expected_revision`; a `409` keeps the dialog open, shows the fresh revision and offers reload.
2. **Validation:** required fields are marked; inline errors; no submit until valid; server errors are mapped to fields where possible.
3. **Permission:** denied dialogs open in read-only or do not open, with a reason.
4. **Unsaved changes:** closing with changes asks to discard, save or cancel.
5. **No fake affordances:** buttons without a backend are disabled with a visible "Available after <capability>" note.
6. **Keyboard:** Enter submits, Esc cancels, Tab order follows visual order, focus returns to the invoking control.
7. **RTL:** dialog order mirrors, but numeric and ID fields remain LTR.
