# CUBI Workspace Dialog Inventory

Status: Phase 3 blueprint.
Rule: a dialog may be built before its backend, but it must state its implementation state and must never show a fabricated success. Fields below are the minimum contract; additional fields may be added only with a data source.

## Project and file

| Dialog | Purpose | Minimum controls | Data / API | Status |
| --- | --- | --- | --- | --- |
| New Project — Step 1 Business Domain | Classify the project | Domain cards: Construction, Oil & Gas, Infrastructure, Industrial, Energy, Other; organisation (optional) | `sector`/`domain` on project create | Missing |
| New Project — Step 2 Identity | Name and ID | Project name (2–120), Project ID (auto from name, editable, unique check), description (≤2000) | `POST /api/projects` | Partial (name/description exist; no ID/domain) |
| New Project — Step 3 Configuration | Planning defaults | Start date (Gregorian/Jalali), finish target, calendar, responsible organisation, date system, default activity duration type, default calendar | Project create + calendars API | Partial (start/date system only) |
| New Project — Step 4 Development | Seed the plan | WBS template or blank, activity template, copy from project, create sample activities | WBS/activity APIs | Missing |
| Open Project | Choose project | Search, domain filter, recent, role badge | `GET /api/projects`, `POST /open` | Implemented as picker, not dialog |
| Import / Export | Interchange | Format, project, mapping preview, conflict policy | Existing interchange API | Implemented (panel) |
| Print Preview / Print / Page Setup | Output | Layout, page, scale, margins, header/footer | Print profile API (not built) | Missing |
| Project Settings | Edit metadata | Name, description, start, date system, primary calendar, revision | `GET/PATCH /api/projects/{id}` | Implemented (modal) |

## Layout and data display

| Dialog | Controls | Behaviour | Status |
| --- | --- | --- | --- |
| Columns | Available/selected lists, add/remove, up/down, width, title, alignment, visibility | Apply to active layout; save with layout | Partial (field chooser panel, no modal) |
| Filters | Any/All rows; field; operator; value; add/delete/order; named filters | Apply to table/Gantt; show filter name in layout bar | Partial (free-text filter only) |
| Group and Sort | Group bands (up to 10), sort levels (up to 10), ascending/descending, summary options | WBS default; persist per layout | Partial (one group + one sort) |
| Timescale | Scale (day/week/month/quarter/year), range, date format, fiscal options | Gantt ticks and labels | Partial (five scale buttons) |
| Bars | Bar list, add/delete, style, label, filter, timescale, preview | Gantt bar rendering | Missing |
| Bar Chart Options | Relationship lines, background lines, legend, data date line, progress line | Gantt display | Partial (link toggle only) |
| Table Font and Row | Font scale, row height, colours | Table rendering | Missing |
| Bottom Layout Options / Customize Details | Tab list, visible, order | Activity Details tabs | Missing |
| Layout Manager (New/Open/Save As/Delete/Import/Export) | Name, scope (user/project), default flag, duplicate | Persist through layout API | Partial (API + undo, no manager) |
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
