# CUBI Workspace Toolbar Inventory

Status: Phase 3 blueprint.
The reference product exposes 18 toolbars. CUBI does not need 18 visible strips at once. It uses **four persistent groups** plus optional toolbars that the user can show. Every button maps to a command in the command registry; no button is decorative.

## Persistent toolbar groups

### 1. Main (Standard + Project)

| Button | Command | Shortcut | Target | Status |
| --- | --- | --- | --- | --- |
| New project | `command:project.new` | Ctrl+N | Creation flow | Missing |
| Open project | `command:project.open` | Ctrl+O | Open Project dialog | Picker exists |
| Save layout + edits | `command:workspace.save` | Ctrl+S | Layout API | Partial (layout save) |
| Refresh | `command:workspace.refresh` | F5 | Workspace v2 read | Implemented |
| Activities | `command:window.activities` | — | Activities window | Implemented as module |
| WBS | `command:window.wbs` | — | WBS window | Partial |
| Resource assignments | `command:window.resource-assignments` | — | Assignments window | Partial |
| Documents | `command:window.documents` | — | Documents window | Partial |
| Expenses | `command:window.expenses` | — | Expenses window | Missing |
| Issues | `command:window.issues` | — | Issues window | Partial |
| Risks | `command:window.risks` | — | Risks window | Missing (API) |
| Baselines | `command:window.baselines` | — | Assign Baselines dialog | Missing |

### 2. Edit

| Button | Command | Shortcut | Target | Status |
| --- | --- | --- | --- | --- |
| Add | `command:edit.add` | Insert | Context add dialog | Partial |
| Delete | `command:edit.delete` | Delete | Delete selection | Partial |
| Cut / Copy / Paste | `command:edit.cut/copy/paste` | Ctrl+X/C/V | Table clipboard | Missing |
| Undo / Redo | `command:edit.undo/redo` | Ctrl+Z/Y | Layout and cell undo | Partial (layout) |
| Assign resources | `command:assign.resources` | — | Assign Resources dialog | Missing |
| Assign roles | `command:assign.roles` | — | Assign Roles dialog | Missing |
| Assign codes | `command:assign.codes` | — | Assign Codes dialog | Missing |
| Assign predecessors | `command:assign.predecessors` | — | Assign Predecessors dialog | Partial (logic panel) |
| Assign successors | `command:assign.successors` | — | Assign Successors dialog | Partial |
| Link / Unlink | `command:edit.link/unlink` | Ctrl+L | Relationship create/remove | Partial |
| Renumber IDs | `command:edit.renumber` | — | Renumber dialog | Missing |
| Fill down | `command:edit.fill-down` | Ctrl+D | Table | Missing |
| Find / Find next | `command:edit.find/find-next` | Ctrl+F / F3 | Find dialog | Missing |

### 3. Layout (active window)

| Button | Command | Target | Status |
| --- | --- | --- | --- |
| New layout | `command:layout.new` | New Layout dialog | Missing |
| Open layout | `command:layout.open` | Open Layout dialog | Partial (API) |
| Save layout | `command:layout.save` | Layout API | Implemented |
| Save as | `command:layout.save-as` | Save As dialog | Missing |
| Columns | `command:layout.columns` | Columns dialog | Partial (panel) |
| Filters | `command:layout.filters` | Filters dialog | Partial (text filter) |
| Group and sort | `command:layout.group-sort` | Group and Sort dialog | Partial |
| Timescale | `command:layout.timescale` | Timescale dialog | Partial (buttons) |
| Bars | `command:layout.bars` | Bars dialog | Missing |
| Line numbers | `command:layout.line-numbers` | Toggle | Missing |
| Table font and row | `command:layout.font-row` | Table Font and Row dialog | Missing |
| User preferences | `command:prefs.user` | User Preferences dialog | Missing |

### 4. Display and Gantt

| Button | Command | Target | Status |
| --- | --- | --- | --- |
| Zoom in / out / best fit | `command:view.zoom-*` | Gantt | Partial (scale buttons) |
| Expand all / collapse all | `command:view.expand/collapse` | Table | Missing |
| Progress line | `command:view.progress-line` | Toggle | Missing |
| Progress spotlight | `command:view.progress-spotlight` | Toggle | Missing |
| Relationship lines | `command:view.relationship-lines` | Toggle | Implemented |
| Windows: table + Gantt / Gantt / network | `command:view.top-layout` | Toggle | Partial |
| Bottom: details / profiles / trace logic / none | `command:view.bottom-layout` | Toggle | Missing |
| Tab group new horizontal / vertical / merge | `command:view.tab-group-*` | Tabs | Missing |

### 5. Schedule group (Tools)

| Button | Command | Shortcut | Target | Status |
| --- | --- | --- | --- | --- |
| Schedule | `command:tools.schedule` | F9 | Schedule dialog | Implemented |
| Level resources | `command:tools.level` | Shift+F9 | Level Resources dialog | Missing (backend adapter exists) |
| Apply actuals | `command:tools.apply-actuals` | — | Apply Actuals dialog | Missing |
| Update progress | `command:tools.update-progress` | — | Update Progress dialog | Missing |
| Reports | `command:tools.reports` | — | Reports window | Preview |
| Check schedule | `command:tools.check-schedule` | — | Check Schedule dialog | Missing |
| Summarize | `command:tools.summarize` | — | Action | Missing |

## Optional toolbars

| CUBI toolbar | Reference source | Buttons | Status |
| --- | --- | --- | --- |
| Enterprise | Enterprise toolbar | Projects, Resources, Reports, Tracking, Business Domains, Portfolios, Roles | Partial |
| Dictionaries | Dictionaries toolbar | Activity codes, resource codes, role codes, project codes, UDFs, calendars, shifts, step templates, cost accounts, funding, curves | Missing |
| Administration | Administrator toolbar | Users, security profiles, preferences, categories, currencies, financial periods | Missing |
| Assign | Assign toolbar | Resources, resources by role, roles, codes, predecessors, successors, step templates | Missing |
| Reports | Reports toolbar | Run report, run batch, modify, import, export, wizard, groups, batches | Missing |
| Find | Find toolbar | Find, find next, replace | Missing |
| Move | Move toolbar | Move up/down/left/right in hierarchy | Missing (WBS needs it) |
| Print | Print toolbar | Print, preview, page setup, print setup | Missing |
| Publish | Publish toolbar | Project site, activity layouts, tracking layouts | Disabled (no backend; local preview read-only) |
| Top layout | Top layout toolbar | Table, Gantt, network, relationship lines, chart view | Partial |
| Bottom layout | Bottom layout toolbar | Details, usage spreadsheet/profile, resource spreadsheet/profile, trace logic, none | Missing |

## Toolbar behaviour

1. Toolbars are positionable (top, left, right, bottom) and lockable; layout is per user.
2. Buttons show tooltip with label + shortcut; disabled buttons explain why.
3. Overflow collapses into a chevron menu; no horizontal page scrolling.
4. Customization: show/hide buttons and toolbars, reset to factory defaults.
5. Icons are CUBI-owned SVG, not Oracle artwork.

## Deliberately retired reference commands

| Command | Reason |
| --- | --- |
| Check in / check out | No multi-user checkout model in CUBI |
| Send project / email XER | No XER email workflow |
| Send to Unifier | No Unifier integration |
| Job services / job status | No server job scheduler exposed to the workspace |
| Visualizer | Replaced by CUBI Activity Network/Trace Logic views |
| Approvals > timesheets | Not part of the current product scope |
| Publish project web site | Local preview is read-only; no publishing service |
