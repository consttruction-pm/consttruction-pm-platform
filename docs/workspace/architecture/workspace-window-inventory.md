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
| Projects / Business Domains | Projects module shell with current-project register, loaded WBS structure summary and bottom Project Details; project picker still uses project list/open APIs | Partial | Organization-wide register/tree, multi-project list context, full tab data and persistent project defaults still require service contracts |
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

## Projects window composition (current shell and target)

| Region | Current | Target |
| --- | --- | --- |
| Project Register | Current authorized/open project facts and loaded WBS summary | Full authorized project list with domain/portfolio tree, table columns, grouping, sorting and filters |
| Project Details | Bottom-docked tab surface; project-scoped tabs | General, Dates, Defaults, Resources, Settings, Codes, Notebook, budget/funding, Baselines, Documents, History and UDFs |
| Project metadata edit | Existing metadata dialog/API | Editing for every field with service contract, revision guard and audit |

See the Projects Window and Project Details specification for field inventory, choices and acceptance gates.

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


## Master visual-shell audit status (2026-11-02)

The full target inventory is documented in [workspace-visual-shell-master-audit.md](./workspace-visual-shell-master-audit.md). Current UI remains substantially incomplete relative to that target:

- The global menu/toolbar catalogue is rendered as a visual-only shell; command entries are intentionally not wired to APIs or actions.
- The existing left rail is still not the complete hierarchical navigation tree.
- Most listed windows remain partial, preview, or missing; they are not independently navigable as real window tabs.
- Page-specific Details inventories are specified, but only partial Project Details/Activity Details surfaces are rendered; other page-specific detail tabs are not complete.
- Contextual command bars for each window are not complete. The right-side CUBI Add (+) command bar remains a separately tracked requirement.
- Layout dialogs for network/chart/profile/spreadsheet, advanced filters, multi-level group/sort, bar styles, tab groups, and per-window layouts remain visual work.
- Form Builder is additive and must coexist with all baseline windows; its organization and project libraries remain distinct.

Do not mark the visual shell complete based on this catalogue or disabled menu labels. Completion requires running-app acceptance evidence listed in the master audit. This inventory is visual-only and makes no statement about API readiness.


## Detailed desktop visual parity gate (2026-11-02)

The master audit now contains the full visual composition rule, window/mode matrix, layout dialogs, calendar editor, object-property dialogs and menu/command presentation requirements. This is the normative design inventory for the skin-only phase.

**Critical layout rule:** the application must not become one wide page containing every control. It must render as a desktop workbench with independent window tabs, a collapsible/resizable left navigation tree, a compact global menu and toolbar, a page-specific horizontal command bar, a central top-layout surface (table/tree synchronized with Gantt/network/chart where relevant), and a docked page-specific bottom Details pane. The right-edge CUBI Add (+) rail remains a separate narrow strip. Panes and splitters are independently adjustable. Responsive mode may reflow these regions but must preserve their identity and interaction.

**Visual parity inventory includes:**
- Projects, Activities, WBS, Resource Assignments, Resources, Roles, Calendars, Documents, Expenses, Thresholds, Issues, Risks, Reports and Tracking windows.
- CUBI-only Form Builder, Cost & Financial Control, Progress & Field Control, Procurement, Changes & Claims and Engineering Intelligence surfaces.
- Grid/table, Gantt, project bar chart, network diagram, usage spreadsheet, resource profile/histogram and tracking profile modes.
- Layout open/save/import/export, columns, advanced filters, multi-level grouping/sorting, timescale, bars/labels/legend, Gantt/network/profile options, tab configuration and font/row/color dialogs.
- Calendar register, workweek and split-shift editor, recurring and one-off exceptions, holidays, calendar preview and assignment dialogs.
- Project/activity/WBS/resource/role properties, relationships, baselines, schedule, resource leveling, import/export, print/page setup, preferences, security, search, global change and recovery dialogs.

**Status:** this is a completed target inventory only. It does not mean those visual surfaces have all been implemented. The running application remains partial until each window, pane, menu, submenu, dialog and layout mode exists and is proven in browser interaction and screenshots. Do not merge or mark skin complete based on the written catalogue.

## Mandatory visual audit rule

This inventory is a checklist, not proof of parity. Each window and each of its subcomponents must receive an individual GitHub audit record under [`../reference/visual-audit-governing-principles.md`](../reference/visual-audit-governing-principles.md). Verify actual rendered geometry, controls, tabs, menu/context-menu hierarchy, typography, colours, visual states and interactions against the exact Version 26 desktop reference. Gantt and every chart family require complete colour/style controls and rendered-result verification now; do not defer them to the later theme phase. Only a page whose subcomponents pass evidence, tests and screenshot review may be marked Verified.
