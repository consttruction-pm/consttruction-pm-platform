# Reference-to-CUBI Mapping Matrix

Status: Phase 3 blueprint.
Rule: the left column exists only for traceability. **No Oracle or Primavera name may appear in the CUBI interface, help text, tooltips or URLs.** CUBI labels are canonical and translatable.

## Menus

| Reference | CUBI menu | Notes |
| --- | --- | --- |
| File | Workspace | Project lifecycle and output |
| Edit | Edit | Editing and assignment |
| View | View | Layout and display |
| Project | Project | Project windows |
| Enterprise | Organization | Enterprise dictionaries and structure |
| Tools | Tools | Scheduling, leveling, reporting |
| Admin | Administration | Users/security/preferences |
| Help | Help | Guide, shortcuts, about |

Submenu mappings:

| Reference item | CUBI label |
| --- | --- |
| Enterprise Project Structure | Business Domains |
| OBS | Responsibility Structure |
| WPs & Docs | Documents |
| Assign Baselines / Maintain Baselines | Baselines → Assign / Manage |
| User Preferences | Preferences |
| Admin Preferences | Organization Preferences |
| Tab Groups | Tab Groups (unchanged) |

## Windows

Status vocabulary here describes the current renderer only; it is **not** a Version 26 parity or verification claim. Every surface remains subject to page-level source comparison, interaction review and screenshot evidence.

| CUBI window | Current renderer | Version 26 parity status |
| --- | --- | --- |
| Projects | Shared register/table renderer | Implemented preview; page audit pending |
| WBS | WBS-specific renderer | Implemented preview; page audit pending |
| Activities | Activity table/Gantt/details renderer | Implemented preview; detailed parity audit pending |
| Resource Assignments | Assignment-specific renderer | Implemented preview; page audit pending |
| Resources | Dedicated resource register renderer | Implemented preview; page audit pending |
| Roles | Dedicated role register renderer | Implemented preview; page audit pending |
| Calendars | Dedicated calendar/workweek renderer | Implemented preview; page audit pending |
| Reports | Report library/runner surfaces | Implemented preview; report-family audit pending |
| Tracking | Dedicated four-family renderer: Project Table, Project Bar Chart, Project Gantt/Profile, Resource Analysis | Implemented preview; exact-head tests and runtime/screenshot audit pending |
| Documents | Shared register/table renderer | Implemented preview; page audit pending |
| Expenses | Shared register/table renderer | Implemented preview; page audit pending |
| Thresholds | Shared register/table renderer + monitor dialog | Implemented preview; page audit pending |
| Issues | Shared register/table renderer | Implemented preview; page audit pending |
| Risks | Shared register/table renderer | Implemented preview; page audit pending |
| Administration | Dedicated administration sections | Implemented preview; page audit pending |
| Activity Network | Dedicated network renderer/options | Implemented preview; page audit pending |
| Trace Logic | Dedicated trace renderer/options | Implemented preview; page audit pending |
| Timeline | Dedicated timeline renderer/options | Implemented preview; page audit pending |
| Activity Usage Profile | Dedicated profile renderer/options | Implemented preview; page audit pending |
| Resource Usage Profile | Dedicated profile renderer/options | Implemented preview; page audit pending |
| Activity Usage Spreadsheet | Dedicated spreadsheet renderer/options | Implemented preview; page audit pending |
| Resource Usage Spreadsheet | Dedicated spreadsheet renderer/options | Implemented preview; page audit pending |
| Cost & Financial Control | Dedicated CUBI module preview | Additive CUBI surface; baseline mapping and audit pending |
| Progress & Field Control | Dedicated CUBI module preview | Additive CUBI surface; baseline mapping and audit pending |
| Procurement & Materials | Dedicated CUBI module preview | Additive CUBI surface; baseline mapping and audit pending |
| Changes & Claims | Dedicated CUBI module preview | Additive CUBI surface; baseline mapping and audit pending |
| Form Builder | Dedicated CUBI form-builder renderer | Additive CUBI surface; audit pending |
| Organization | Dedicated organization renderer | Additive CUBI surface; baseline mapping and audit pending |
| Smart Guide | Dedicated CUBI renderer | Additive CUBI surface; audit pending |
| Engineering Assistant | Dedicated CUBI renderer | Additive CUBI surface; audit pending |
| Global Search | Dedicated CUBI renderer | Additive CUBI surface; audit pending |
| Comments & Notebook | Dedicated CUBI renderer | Additive CUBI surface; baseline mapping and audit pending |

## Concepts

| Reference concept | CUBI concept | Storage / API today |
| --- | --- | --- |
| EPS | Business Domain tree | Project `sector` intent exists in assistant tooling; API field pending |
| Portfolio | Portfolio | Not implemented |
| Project | Project | `projects` table, `/api/projects`, revision |
| WBS | WBS | `wbs_master`, WBS APIs |
| Activity | Activity | Activity master + typed field registry |
| Relationship | Relationship | `relationships`, FS/SS/FF/SF + lag |
| Resource / Role | Resource / Role | Resource and capacity APIs; role dictionary partial |
| Calendar | Calendar | Project calendar + holidays; global calendars partial |
| Baseline | Baseline | Persistence: `docs/architecture/P6_BASELINE_PERSISTENCE_V1.md`; UI missing |
| Layout | Layout | `/api/projects/{id}/p6/layouts/{scope}/{viewId}` |
| Activity code | Activity code | Code persistence exists (`P6_CODE_SCOPE_PERSISTENCE_V1.md`); UI missing |
| UDF | Custom field | Not implemented |
| Expense | Expense | `P6_EXPENSE_PERSISTENCE_V1.md` |
| Step | Step | `P6_ACTIVITY_STEP_PERSISTENCE_V1.md` |
| Data date | Data date | Schedule options + workspace read |
| Critical path | Critical path | Computed by the core; Gantt display partial |
| Progress line | Progress line | Not implemented |
| Timescale | Timescale | Five scales in Gantt; dialog missing |

## Activity Details tabs

| Reference tab | CUBI tab | Decision |
| --- | --- | --- |
| General | General | Build |
| Status | Status | Build |
| Resources | Resources | Build |
| Predecessors | Predecessors | Build (logic panel data exists) |
| Successors | Successors | Build |
| Codes | Codes | Build after code UI |
| Tasks | — | Retired: EPPM-only |
| Discussion | — | Deferred: not a desktop differentiator; revisit with collaboration model |
| Notebook | Notebook | Build after notebook model |
| Steps | Steps | Build (persistence exists) |
| Feedback | — | Deferred |
| WPs & Docs | Documents | Build |
| Expenses | Expenses | Build |
| Summary | Summary | Build |
| Relationships | Relationships | Build |
| Risks | Risks | Build after risk API |
| UDFs | Custom Fields | Build after UDF model |
| Update History | History | Build after activity audit trail |

## Commands retired from CUBI

| Reference command | Decision |
| --- | --- |
| Check In / Check Out | Retired: no checkout model |
| Send Project (XER email) | Retired |
| Send to Unifier | Retired |
| Job Services / Job Status | Retired from workspace |
| Visualizer | Replaced by Activity Network + Trace Logic |
| Approvals > Timesheets | Out of scope |
| Publish Project Web Site | Disabled: local preview is read-only and no publishing service exists |
| Tasks / EPPM-only fields | Retired by edition boundary |

## Naming rules

1. Product name is **CUBI**; "P6", "Primavera", "Oracle", "EPS", "OBS", "WPs & Docs" never appear in the UI.
2. "Business Domain" replaces EPS; "Responsibility Structure" replaces OBS; "Documents" replaces WPs & Docs.
3. Persian labels are authored natively, not transliterated: e.g. Activities = فعالیت‌ها, WBS = ساختار شکست کار, Resources = منابع, Calendars = تقویم‌ها, Reports = گزارش‌ها, Administration = مدیریت سیستم.
4. URLs use CUBI keys (`window=activities`, `dialog=columns`), never reference-product names.
5. Code identifiers may keep historical names (e.g. `p6_layouts` API path) for compatibility, but user-visible text must not.

## Parity status summary (refreshed 2026-11-03)

The percentage table from 2026-10-30 described the pre-demo application and is superseded. The current visual demo contains 32 window destinations and dedicated renderers for several major workspaces, but this is **not evidence of Version 26 parity**. Page-by-page audits, runtime interactions and screenshot comparisons remain outstanding. Use the per-window status table above and the governing audit record; do not reuse the old percentages.

## Mandatory page-level audit gate

Every mapping row and every mapped window/component must link to a page-specific audit record governed by [`../reference/visual-audit-governing-principles.md`](../reference/visual-audit-governing-principles.md). A mapping is not complete merely because a CUBI label or route exists. Record the complete page hierarchy, fields, states, menus, submenus, appearance, documented colour controls, defaults, interactions, implementation paths, tests and screenshots. Gantt and chart colour/style configuration must be implemented and verified in this phase; only final global theme harmonization is deferred.


## Tracking layout-family implementation — 2026-11-03

The Tracking window now exposes four distinct selectable layout families rather than a generic Activity register:

| Family | Visible structure | Reference-backed scope | Current boundary |
|---|---|---|---|
| Project Table | Project/activity analysis table | Tabular project data | Preview data; filter/group dialogs are visual only |
| Project Bar Chart | Horizontal progress/allocation bars | Project data in horizontal bar-chart form | Illustrative values; configuration is not persisted |
| Project Gantt/Profile | Upper Gantt timeline + lower profile/spreadsheet region | Project columns and Gantt above, time-distributed data below | Illustrative; no schedule calculations |
| Resource Analysis | Resource register/columns + time-distributed usage profile | Resource allocation analysis with Gantt, profile and spreadsheet presentations | Illustrative; no leveling or capacity calculation |

English/Persian RTL rendering assertions cover family visibility and representative family-specific content. The four families are not yet Verified: exact-head CI, browser interaction review and screenshots remain required.
