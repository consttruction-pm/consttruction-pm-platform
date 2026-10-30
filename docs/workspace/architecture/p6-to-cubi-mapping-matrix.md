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

| Reference window | CUBI window key | CUBI title | Status |
| --- | --- | --- | --- |
| Projects | `projects` | Projects | Preview |
| WBS | `wbs` | Work Breakdown | Partial |
| Activities | `activities` | Activities | Partial |
| Resource Assignments | `resource-assignments` | Resource Assignments | Partial |
| Resources | `resources` | Resources | Missing |
| Calendars | `calendars` | Calendars | Partial |
| Reports | `reports` | Reports | Preview |
| Tracking | `tracking` | Tracking | Missing |
| WPs & Docs | `documents` | Documents | Partial |
| Project Expenses | `expenses` | Expenses | Preview |
| Project Thresholds | `thresholds` | Thresholds | Missing |
| Project Issues | `issues` | Issues | Partial |
| Risks | `risks` | Risks | Missing |
| Administration dialogs | `administration` | Administration | Missing |

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

## Parity status summary (2026-10-30)

| Area | Coverage | Evidence |
| --- | --- | --- |
| Menus | 0% UI (blueprint complete) | Audit: flat module bar only |
| Window tabs | 0% | No tablist in shell |
| Activities table | ~55% (grid, inline edit, WBS grouping, columns panel) | `workspace-view.ts`, `p6-field-chooser.ts` |
| Gantt | ~50% (bars, links, scales; no baseline/progress/critical styles) | `workspace-gantt.ts` |
| Activity Details | ~5% (selected id stub) | `workspace-view.ts:553` |
| Layouts | ~40% (API persistence, undo; no manager) | `p6-api.ts`, `main.ts` |
| Project creation | ~35% (name/description/start/date system) | `main.ts:1085-1290` |
| Resource assignments | ~25% (capacity only) | `p6-capacity-panel.ts` |
| Baselines | 0% UI, persistence exists | `P6_BASELINE_PERSISTENCE_V1.md` |
| Network / Trace Logic | 0% | — |
| Reports | ~5% (empty state) | `workspace-view.ts:567-608` |

Percentages are engineering estimates for planning, not acceptance claims.
