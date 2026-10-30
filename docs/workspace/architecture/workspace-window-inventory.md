# CUBI Workspace Window Inventory

Status: Phase 3 audit of the current client (`apps/web/src`, branch `main` at 2026-10-30) against the target architecture.
Status values: **Implemented** = usable with real data; **Partial** = some real capability, missing structure or controls; **Preview** = placeholder/empty state; **Missing** = no window.

## Shell

| Element | Current | Status | Target |
| --- | --- | --- | --- |
| App shell | `.cp-app-shell` with `.cp-app-status` + `#workspace` (`main.ts:411`) | Partial | Keep; add menu bar, toolbars, tabs inside `#workspace` |
| Menu bar | None; `nav.cp-menu` has 9 flat buttons `[data-menu]` (`workspace-view.ts:476-478`) | Missing | 8 menus with dropdowns and command registry |
| Main toolbar | None | Missing | Standard + Project + Layout + Schedule groups |
| Window tabs | None (`role=tab` absent) | Missing | Tab strip with dirty state, close, reorder |
| Navigation tree | Flat module bar and `.cp-navigation-surface` links | Partial | Collapsible project/organization tree |
| Splitter panels | CSS grid only; no drag splitters | Missing | Drag handles with persisted sizes |
| Status bar | Language + calendar toggles and "Web shell" label (`main.ts:419-450`) | Partial | Project, data date, baseline, layout, filter, user, sync |
| Layout bar | None | Missing | Layout name, filter name, layout menu |
| Breadcrumb | Header shows project id and revision (`workspace-view.ts:470-475`) | Partial | Domain › portfolio › project + revision + data date |

## Windows

| CUBI window | Current implementation | Status | Gap to target |
| --- | --- | --- | --- |
| Projects / Business Domains | Project picker in `main.ts:1306-1344`; `GET /api/projects`, `POST /api/projects/{id}/open` | Preview | No window, no business-domain tree, no EPS/portfolio grouping |
| Activities | Activity grid `#cp-activity-grid` (`workspace-view.ts:518`), Gantt `#cp-gantt` (`:544`), filter/group/sort (`:1159-1180`), P6 field chooser (`:1183-1240`) | Partial | No window tabs, no Activity Details tabs, no menu commands, no resizable layouts |
| WBS | `#cp-project-wbs` aside (`:489`), create/edit forms (`:492-515`) | Partial | No WBS window, chart view or element details |
| Resource Assignments | Capacity panel `#cp-resource-capacity` (`:551`) | Partial | No assignments window grouped by resource; assignment editing UI incomplete |
| Resources | Capacity ceilings only | Missing | Resource hierarchy, details, rates, calendars |
| Calendars | Project calendar holidays in schedule options (`schedule-cycle.ts`, `#cp-calendar`) | Partial | No calendar dictionary window, no working-hours editor |
| Reports | `renderModuleEmptyState` for `reports` (`workspace-view.ts:567-608`) | Preview | Report list, profiles, runner |
| Tracking | None | Missing | Tracking layouts against data date |
| Documents | `#cp-documents` (`:1073`) | Partial | Document register exists; needs window and launch/open actions |
| Expenses | Cost module is a preview | Preview | Expense register per activity |
| Thresholds | None | Missing | Threshold dictionary and monitor |
| Issues | Field/site issues `#cp-field-operations` (`:909`), quality/safety panels | Partial | Project issue register with history/notify |
| Risks | None | Missing | Risk register and exposure |
| Administration | None | Missing | Users, profiles, preferences, categories, currencies, periods |

## Activities window composition (target)

| Region | Current | Target |
| --- | --- | --- |
| Activity Table | `role=grid` table, editable cells, WBS grouping, single filter, one sort level, column chooser | P6-style table with multi-level group/sort, saved filters, column manager, line numbers, fill down, renumber |
| Gantt | SVG bars, dependency arrows, five timescales, link toggle | Bars/milestones/summary bars, baseline bars, data date line, progress line, critical path, bar styles, legend, drag editing |
| Activity Details | Stub showing selected activity id (`:553`, `:394-398`) | Tabs below with real fields and persistence |
| Bottom views | None | Details default; usage profile/spreadsheet and Trace Logic options |
| Activity Network | None | Separate top-layout view and window |
| Trace Logic | None | Bottom view with predecessor/successor navigation |

## Activity Details tabs

| Tab | Status | Notes |
| --- | --- | --- |
| General | Missing | Activity inline edit exists but not tabbed detail |
| Status | Missing | Percent/actuals fields exist in the model; no tab |
| Resources | Missing | Assignments API exists; no detail tab |
| Predecessors | Partial | Grid shows predecessors text; logic panel `#cp-logic` edits relationships |
| Successors | Partial | Derived via relationships; no tab |
| Codes | Missing | Activity code dictionaries not implemented in UI |
| Notebook | Missing | No notebook model |
| Steps | Missing | Backend `p6_activity_step_repository` exists |
| Documents | Missing | Document register exists; no per-activity tab |
| Expenses | Missing | Backend expense persistence exists |
| Summary | Missing | Roll-ups available from read model |
| Relationships | Partial | Logic panel only |
| Risks | Missing | No risk model/API |
| UDFs | Missing | UDF definitions not implemented |
| Update History | Missing | Revision history exists at project level only |
| Discussion / Feedback / Tasks | Not planned | Discussion/Feedback are not desktop-Professional differentiators for CUBI v1; Tasks is EPPM-only. Decision recorded here, revisit later. |

## Preserved existing capabilities (must not regress)

- WBS-bound activity creation, including assistant-proposed `activity.create` with approval/execution and fresh read-back.
- Activity edit with revision guard, relationship create/delete, delete activity.
- Schedule options (data date, leveling priority, level-all/within-float), run schedule, result table, Gantt refresh.
- Calendar holiday editing consumed by the scheduler.
- Import/export interchange panel.
- Formula/field layout persistence and capacity panels.
- Persian/English, Jalali/Gregorian, RTL/LTR.
- Assistant launcher and AI action panel.

## Evidence used

- `apps/web/src/workspace-view.ts`, `workspace-model.ts`, `workspace-navigation.ts`, `workspace-preferences.ts`, `workspace-filter-sort.ts`, `schedule-cycle.ts`, `main.ts`.
- `apps/web/styles.css` grid definitions.
- Read-only audit on 2026-10-30 (file/line references above reflect that revision).
