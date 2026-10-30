# CUBI Workspace Information Architecture

Status: Phase 3 blueprint. Implementation starts after this document set is merged.
Scope: the authenticated CUBI workspace only. Public marketing pages, pricing and site identity are out of scope and must not be changed by this programme.

## Product intent

CUBI's workspace is a professional project-controls environment, not a SaaS dashboard. It must feel like a desktop planning tool that happens to run in the browser: persistent menus, a dense activity table, a synchronised Gantt, configurable detail tabs, saved layouts and real data operations.

The structural reference is the P6 Professional desktop workspace (see `../reference/`). CUBI keeps the discipline of that model but uses its own vocabulary, its own calculation core and its own persistence. No Oracle or Primavera name may appear in the user interface.

## Objects

```
Business Domain (sector)
└── Portfolio (optional grouping)
    └── Project
        ├── WBS (hierarchy)
        │   └── Activity
        │       ├── Relationships (predecessor → successor)
        │       ├── Resource / Role assignments
        │       ├── Steps, Expenses, Documents, Risks, Issues, UDF values
        │       └── Baseline values
        ├── Calendars (project/global/resource)
        ├── Baselines (primary/secondary/tertiary)
        └── Layouts (user/project)
```

- **Business Domain** is the EPS-level classification used at project creation: Construction, Oil & Gas, Infrastructure, Industrial, Energy, Other.
- **Project** is the unit of open/close, revision control and permissions.
- **WBS** is the mandatory planning hierarchy; every activity belongs to one WBS element.
- **Activity** is the unit of scheduling, grouping and detail editing.
- **Layout** stores table columns, detail tabs, grouping, filters, Gantt settings and timescale for a window and scope.

## Regions of the workspace

| Region | Required content | Behaviour |
| --- | --- | --- |
| App status bar | Product mark, connection/sync state, language, calendar system, user | Always visible; never overlapped by menus |
| Menu bar | Workspace, Edit, View, Project, Organization, Tools, Administration, Help | Commands enable per active window/layout; keyboard mnemonics |
| Main toolbar | Standard + Project + Layout + Schedule groups | Compact, grouped, tooltips with shortcut |
| Breadcrumb/context bar | Business domain › portfolio › project, revision, data date | Shows current scope; project switch menu |
| Window tabs | One tab per open window; dirty indicator; close `X` | Idempotent open, drag order, keyboard cycling |
| Navigation panel | Collapsible tree: project windows, dictionaries, reports | Collapsible, width-persisted |
| Top layout | Table and/or Gantt/network | Splitter between table and chart |
| Bottom layout | Detail tabs, usage profiles, trace logic, none | Height-persisted; can be hidden |
| Layout bar | Layout name, filter name, layout menu | Opens columns/filter/group/timescale dialogs |
| Status bar | Project, data date, baseline, layout, filter, user/role, save state | Read-only except data date shortcut |

## Window model

CUBI windows are **views of data**, not pages:

- **Projects** — business-domain tree and project list.
- **Activities** — activity table + Gantt/network + details.
- **WBS** — WBS table/chart + element details.
- **Resource Assignments** — assignments grouped by resource.
- **Resources** — resource hierarchy and details.
- **Calendars** — calendar dictionary and working-time editor.
- **Reports** — report list and runner.
- **Tracking** — progress layouts against a data date.
- **Documents**, **Expenses**, **Thresholds**, **Issues**, **Risks** — project dictionaries.
- **Administration** — users, security profiles, preferences, categories, currencies, financial periods.

Opening a window:
1. If closed, open a tab and load its data.
2. If already open, activate the existing tab.
3. Project windows close when the last project closes; enterprise windows stay open.
4. Each window remembers its layout and splitter sizes per user.

## Command model

Every command declares:

```text
id, label, mnemonic, shortcut, icon, group,
enabled_when (window, layout, selection, permission, project state),
target (route | window | dialog | toggle),
effect (data operation or client state),
undoable,
audit_event
```

Rules:

- No command may exist only as a visual. If the backend is not ready, the command is disabled with a reason or opens a dialog that clearly states "not yet available in this build" — never a fake success.
- Destructive commands (delete WBS with activities, delete baseline, close with unsaved changes) require confirmation and show the affected count.
- Commands that change data show the revision guard (`expected_revision`) and surface `409` conflicts.
- Permission-denied commands stay visible but disabled with the reason (viewer/planner/admin).

## Navigation map

Top menus are the primary navigation. The left navigation tree is a secondary shortcut to the same windows. Both use the same window keys and routes. See `workspace-navigation-map.md`.

## Layouts and personalization

- Layouts belong to a window and a scope: **user** (private) or **project** (shared, revision-guarded).
- A layout stores: columns (order/width/visibility/alignment), detail tab order, grouping bands, sort levels, filters, Gantt bar styles/legend/data date line, timescale, row height/font scale, splitter sizes.
- Saving a project layout writes through the existing `/api/projects/{id}/p6/layouts/{scope}/{viewId}` API; user layouts use the same store with `scope=user`.
- Default layout for Activities: grouping = WBS, sort = WBS hierarchy order. This must hold on first entry, after refresh and after project switch unless the user explicitly changes it.

## Data and calculation boundary

The workspace never calculates schedule values. Dates, float, critical path, roll-ups and leveling come from the Shared Domain/Calculation Core through the API. The UI only presents, edits inputs and requests recalculation. Existing settings remain authoritative:

`{duration: working-day, calendar: jalali-gregorian, lag: working, constraints: hybrid, mode: both}`

## Localization

- English/LTR and Persian/RTL are equal first-class layouts, not translations of a fixed LTR shell.
- Calendar system (Gregorian/Jalali) is independent of language.
- Dates in tables honour the active calendar system; numeric columns use Latin digits in both languages unless the user chooses localized digits.
- Menu mnemonics are English-letter based; Persian labels still expose access keys through a documented mapping.
- Timescale, print and export respect direction, calendar and locale.

## Permissions

| Role | Workspace capabilities |
| --- | --- |
| Viewer | Read windows, layouts (user), reports preview; no mutations |
| Planner | Edit WBS/activities/relationships/calendars/layouts; schedule |
| Admin | Planner plus project settings, users/security, dictionaries |
| Newcomer | Read-only onboarding scope until invited to a project |

The command model consults the session roles and the project policy. Denied commands are disabled with an explanation, not hidden silently.

## Explicitly out of scope

- Public homepage, product marketing pages, pricing, SEO pages and brand redesign.
- Server/EPPM-only commands (check-in/out, job services, timesheets, web publishing) until a CUBI backend capability exists.
- Pixel copying of Oracle screenshots. Structural and behavioural parity is the target.

## Success criteria

1. A planner can open a project, see Activities grouped by WBS, edit activities, relationships, dates and resources, schedule, and read the Gantt without leaving the workspace.
2. Every visible menu command either works against real data or is disabled with a truthful reason.
3. Create Project follows Business Domain → Identity → Configuration → Development and ends in a usable WBS/activity workspace.
4. Layouts survive refresh and project switch; WBS grouping is the default.
5. Persian and English, Jalali and Gregorian, RTL and LTR all render the same workspace without layout breakage.
