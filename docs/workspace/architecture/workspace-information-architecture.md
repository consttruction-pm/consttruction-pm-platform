# CUBI Engineering Workspace Information Architecture

Status: Engineering environment blueprint.  
Scope: CUBI Engineering authenticated workspace only.  
Platform-level product entry and the two-environment model are governed by [CUBI_PRODUCT_SURFACE_ARCHITECTURE.md](../../product/CUBI_PRODUCT_SURFACE_ARCHITECTURE.md) and [CUBI_TWO_ENVIRONMENT_PRODUCT_ARCHITECTURE.md](../../architecture/CUBI_TWO_ENVIRONMENT_PRODUCT_ARCHITECTURE.md).

## Product intent

This document defines the interior of the **CUBI Engineering** Visual Workspace only. It does not define the CUBI Enterprise environment or the platform-level personal workbench / environment selector.

CUBI Engineering is the professional engineering and project-controls environment. It must retain its approved desktop-like workspace: persistent menus, dense activity table, synchronized Gantt, configurable detail tabs, saved layouts and real data operations. The two-environment platform decision does not authorize a redesign, replacement or regression of this shell.

The structural reference is the P6 Professional desktop workspace (see ../reference/). CUBI uses its own vocabulary, calculation core and persistence. No Oracle or Primavera name may appear in the user interface.

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

- **Business Domain** is the sector classification used at project creation.
- **Project** is the unit of open/close, revision control and permissions.
- **WBS** is the mandatory planning hierarchy; every activity belongs to one WBS element.
- **Activity** is the unit of scheduling, grouping and detail editing.
- **Layout** stores table columns, detail tabs, grouping, filters, Gantt settings and timescale for a window and scope.

## Regions of the Engineering workspace

| Region | Required content | Behaviour |
| --- | --- | --- |
| App status bar | Product mark, connection/sync state, language, calendar system, user | Always visible; never overlapped by menus |
| Menu bar | Workspace, Edit, View, Project, Organization, Tools, Administration, Help | Commands enable per active window/layout; keyboard mnemonics |
| Main toolbar | Standard + Project + Layout + Schedule groups | Compact, grouped, tooltips with shortcut |
| Breadcrumb/context bar | Business domain › portfolio › project, revision, data date | Shows current scope; project switch menu |
| Window tabs | One tab per open window; dirty indicator; close X | Idempotent open, drag order, keyboard cycling |
| Navigation panel | Engineering project windows, dictionaries and reports | Collapsible, width-persisted |
| Top layout | Table and/or Gantt/network | Splitter between table and chart |
| Bottom layout | Detail tabs, usage profiles, trace logic, none | Height-persisted; can be hidden |
| Layout bar | Layout name, filter name, layout menu | Opens columns/filter/group/timescale dialogs |
| Status bar | Project, data date, baseline, layout, filter, user/role, save state | Read-only except data date shortcut |

## Window model

Engineering windows are views of authoritative Engineering data, not a second application shell:
- Projects and project structure.
- Activities, WBS, relationships and schedule views.
- Resource assignments, resources and calendars.
- Engineering reports and tracking.
- Engineering documents, expenses, thresholds, issues and risks where owned by Engineering.
- Engineering administration and project security controls.

Opening a window activates an existing tab when already open; it must not create duplicate shells. Project windows close when the last project closes; persistent Engineering windows retain their own layouts per user.

## Command model

Every command declares its identity, label, shortcut, permission conditions, target, effect, undoability and audit event. No command may exist only as a visual. Unavailable commands must be disabled with a truthful explanation, never fake success.

Destructive operations require confirmation and affected-record counts. Mutations use revision guards and surface conflicts. Permission-denied commands remain visible but disabled with the reason where appropriate.

## Data and calculation boundary

The Engineering workspace does not independently calculate schedule values. Dates, float, critical path, roll-ups and leveling come from the authoritative Shared Domain/Calculation Core through the API. The UI presents data, edits permitted inputs and requests authoritative recalculation.

## Shared platform capabilities

Form Builder is available in both CUBI Engineering and CUBI Enterprise. Engineering uses it for engineering-owned records and workflows; Enterprise uses it for organizational/PMBOK-aligned processes. Shared form infrastructure must not change Engineering calculation ownership or couple the two environment release cycles.

## Localization and permissions

English/LTR and Persian/RTL are equal first-class layouts. Calendar system is independent of language. Commands consult authenticated/session roles and project policy; denied commands are disabled with an explanation, not silently hidden.

## Explicitly out of scope

- Public homepage, product marketing pages, pricing, SEO pages and brand redesign.
- The CUBI Enterprise environment and its organizational workflow modules.
- Platform-level personal workbench and environment selection.
- Any Enterprise feature that is not part of an approved Engineering-owned contract.

## Success criteria

1. Engineering project work continues inside the existing Visual Workspace.
2. Engineering tools and calculations remain authoritative and regression-free.
3. Every visible command works against real data or is disabled with a truthful reason.
4. Layouts, localization, project context and existing Engineering behavior remain stable.
5. Enterprise development and the platform entry flow do not block or regress Engineering completion.
