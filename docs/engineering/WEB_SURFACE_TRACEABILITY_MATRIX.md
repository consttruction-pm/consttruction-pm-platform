# CUBI Web Surface Traceability Matrix

Audit date: 2026-11-03
Branch: `codex/jalal/resource-dependent-core-20261102`
Audited head: `beeb856a` (latest code head `a0823f4c`)
Reference baseline: Primavera P6 Professional Version 26 official documentation
(see `CORE_COMPLETION_EXECUTION_LEDGER.md` for the calculation-core matrix).

This document is the Stage 1 page audit for the CUBI web product. It records what
each navigation surface actually renders, which authoritative data it reads, which
core/HTTP capability already exists, what the user can really do today, and which
gaps remain. It is derived from source inspection of:

- `apps/web/src/workspace-navigation.ts` (menus, submenus, declared status)
- `apps/web/src/workspace-view.ts` (`renderP6ModuleStage`, register shells)
- `apps/web/src/workspace-read-api.ts` (loaded workspace state)
- `apps/web/src/schedule-cycle.ts`, `workspace-gantt.ts`,
  `workspace-activity-details.ts`, `p6-capacity-panel.ts`, `calendar-holidays.ts`
- `src/construction_pm/http/project_lifecycle_routes.py` (real HTTP routes)
- `src/construction_pm/p6_*_api.py`, `reporting.py` (core/API contracts)
- the existing web unit/E2E tests

Status legend (surface-level, not calculation parity):

| Status | Meaning |
|---|---|
| `WIRED` | Every exposed control performs a real, persisted operation through the shared core or its HTTP boundary. |
| `WIRED-READ` | Real persisted data is read and selectable; write actions are absent rather than decorative. |
| `SHELL` | The visual structure exists but data and/or actions are not connected. |
| `GAP-CORE` | No authoritative core or HTTP capability exists yet; must not be faked in the UI. |

`SHELL` and `GAP-CORE` surfaces are honest current-state labels. They are not
completion claims. No surface is marked complete until it is `WIRED`, covered by a
test that exercises the real path, and verified in a browser.

## 1. Page-level audit

| Key | Page | Nav status | Renderer / code path | Current data source | Existing authoritative capability | Controls that really work | Missing or non-working controls | Surface status | Gaps | Primary tests |
|---|---|---|---|---|---|---|---|---|---|---|
| `project` | Project | partial | `workspace-view.ts` `renderP6ModuleStage` `case "project"` | Workspace state: context, WBS, activities, relationships, documents | Project lifecycle and workspace read HTTP; project settings POST | Open WBS, Import/Export tool panel, project settings dialog, live WBS/structure summary | No create/open/close/archive project from this page; single authorized project only; no EPS hierarchy | `WIRED-READ` | GAP-PRJ-01, GAP-PRJ-02 | `project-bootstrap.test.ts`, `workspace-read-api.test.ts`, `workspace-view.test.ts` |
| `wbs` | WBS | partial | `renderWbsTree` + `renderWbsDetails` | Workspace state `wbsNodes`, selected node | `/p6/wbs` read/write API (`p6_wbs_master_api`), workspace read | Select node, add WBS via rail action, delete selected node, detail tabs | Chart View disabled; contract/management fields not all editable; no reorder/move | `WIRED-READ` | GAP-WBS-01 | `workspace-view.test.ts`, `p6-activity-wbs-grid.test.ts` |
| `schedule` | Schedule | implemented | `schedule-cycle.ts`, `workspace-gantt.ts`, `workspace-activity-details.ts`, `p6-*` clients | `/p6/activities`, `/p6/relationships`, `/p6/schedule`, `/p6/baselines`, `/p6/earned-value`, layouts, fields, formulas, interchange | Full shared CPM/calendar/resource/cost/baseline/EVM core plus HTTP routes | Activity grid, Gantt, relationships, calendars/work time, schedule options and Data Date, resources/leveling, progress/baselines, run schedule, formula editor, code reference, layout persistence, import/export, EVM read model | Numeric parity against a licensed V26 reference run is not proven; long-tail dialogs remain to be audited | `WIRED` | GAP-V26-01, GAP-SCH-01 | `schedule-cycle.test.ts`, `workspace-gantt.test.ts`, `workspace-activity-details.test.ts`, `shared-scheduling-adapter.test.ts`, `p6-*.test.ts` |
| `progress` | Progress | preview | `case "progress"` metrics | Field records already loaded in state | Field operations/application APIs; `/p6/activity-period-actuals` exists for schedule progress | Open field-record tools | Page itself shows only counts; no progress update grid, out-of-sequence handling or update log | `SHELL` | GAP-PRG-01 | `workspace-view.test.ts` |
| `resources` | Resources | partial | `case "resources"` + `p6-capacity-panel.ts` | Workspace state counts; capacity panel via `/p6/resource-capacities` | Resource read/write, capacity read/write/resolve, rate read/write, spreads | Open capacity panel, open assignments page | No resource dictionary register (labor/nonlabor/material/roles) on this page | `WIRED-READ` | GAP-RES-01 | `p6-capacity-panel.test.ts`, `p6-capacity-api.test.ts` |
| `assignments` | Resource Assignments | preview | `renderRegisterWindow` shell | Static empty table | `/p6/resource-assignments` GET/POST, assignment periods/spreads, baseline assignments | None | Whole register, tabs, New/Edit/Delete/Filter are decorative | `SHELL` | GAP-ASN-01 | `workspace-view.test.ts` |
| `roles` | Roles | preview | `case "roles"` static register | Static empty table | `/p6/roles` create/update/list (`p6_role_api`) | None | New/Edit/Delete disabled; details tabs are text placeholders | `SHELL` | GAP-ROL-01 | `workspace-view.test.ts` |
| `calendars` | Calendars | partial | `workspace-calendars.ts` mounted on `[data-calendar-page]` (static shell replaced on render) | `/p6/calendars` catalogue, `/p6/calendars/{id}/{version}/snapshot` and `/exceptions` | Calendar catalogue/snapshot/exceptions/work-hours GET+POST, create/update/delete/copy/replace | Select a catalogue row, read persisted snapshot factors/workweek/holidays, edit name/type with expected revision, save, copy to a new reference, delete with confirmation, add all four exception modes (Gregorian or Jalali date conversion) | No blank-calendar creation (no snapshot-create HTTP route), workweek writes go through the copy contract, and no exception delete route exists yet | `WIRED` | GAP-CAL-01 (resolved) | `workspace-calendars.test.ts`, `workspace-surface-matrix.test.ts` |
| `cost` | Cost | preview | `case "cost"` metrics | Procurement/change/claim counts | `/p6/expenses`, `/p6/cost-accounts`, `/p6/financial-periods`, `/p6/earned-value` | Open cost-record tools | Cost page shows unrelated counts; no cost accounts, expense ledger, cash flow, EVM summary, variance or forecast | `SHELL` | GAP-COST-01 | `workspace-view.test.ts`, `p6-formula-grid-binding.test.ts` |
| `expenses` | Expenses | preview | `renderRegisterWindow` shell | Static empty table | `/p6/expenses` create/list (`p6_expense_api`), `/p6/cost-accounts` | None | Whole register and New/Edit/Delete/Filter are decorative | `SHELL` | GAP-EXP-01 | `workspace-view.test.ts` |
| `documents` | Documents | partial | `case "documents"` real list | `state.documents` from workspace read | Document API in core; workspace read model | View loaded document records | No create/edit/link/upload/delete from this page | `WIRED-READ` | GAP-DOC-01 | `workspace-view.test.ts`, `workspace-document.test.ts` |
| `reports` | Reports | preview | `case "reports"` placeholder | None | `reporting.py` typed dataset core; no HTTP route yet; `/p6/layouts` for saved layouts | Open reports/print tools | No report selection, columns, filters, grouping, layout save, print/export | `SHELL` | GAP-RPT-01, GAP-RPT-02 | `workspace-view.test.ts`, `p6-report-print-field-selection.test.ts` |
| `tracking` | Tracking | preview | `case "tracking"` static layout | Static text | No tracking read model; layouts API exists | Layout type selector changes only the local label | Refresh Data and Save Layout disabled; no project set, chart, profile or resource analysis | `SHELL` | GAP-TRK-01 | `workspace-view.test.ts` |
| `issues` | Issues | preview | `renderRegisterWindow` shell | Static empty table | Field issues exist in field-operations domain; no P6-style issue register API | None | Whole register is decorative; loaded field issues are not shown here | `SHELL` | GAP-ISS-01 | `workspace-view.test.ts` |
| `risks` | Risks | preview | `renderRegisterWindow` shell | Static empty table | None | None | Whole register is decorative | `GAP-CORE` | GAP-RSK-01 | `workspace-view.test.ts` |
| `thresholds` | Thresholds | preview | `renderRegisterWindow` shell | Static empty table | None | None | Whole register is decorative | `GAP-CORE` | GAP-THR-01 | `workspace-view.test.ts` |
| `control` | Control | partial | `case "control"` metrics | Field assurance/quality/safety/punch counts | Form builder and field-operations APIs | Open forms and workflows, open control records | Control summary is count-only; changes/claims page is separate rail surface | `WIRED-READ` | GAP-CTL-01 | `workspace-view.test.ts`, `workspace-control-intelligence.test.ts` |
| `settings` | Settings | partial | `case "settings"` | Locale and preferences | Project settings HTTP; locale registry (8 locales, en/fa authored strings) | Project settings dialog, language/workspace preferences | No per-surface layout administration; translated-string coverage for de/zh/ar/fr/ja/ko depends on activated language packs and is not audited | `WIRED-READ` | GAP-I18N-01, GAP-ADM-01 | `workspace-preferences.test.ts`, `workspace-localization.test.ts` |

## 2. Submenu inventory (58 entries)

Every navigation submenu is listed with the surface that currently backs it. The
submenu labels are the authoritative `WORKSPACE_NAVIGATION` labels; this table is
kept in sync by `apps/web/src/workspace-surface-matrix.test.ts`.

| Page | # | Submenu | Backing surface | Status |
|---|---|---|---|---|
| project | 1 | Project / WBS | Project page + WBS page | WIRED-READ |
| project | 2 | Details | Project register and structure summary | WIRED-READ |
| project | 3 | Import / Export | Interchange panel (`p6-interchange-panel.ts`) | WIRED |
| wbs | 1 | WBS Register | WBS hierarchy tree | WIRED-READ |
| wbs | 2 | WBS Details | WBS detail tabs | WIRED-READ |
| wbs | 3 | WBS Chart | Not connected (Chart View disabled) | SHELL |
| schedule | 1 | Activity Grid | `schedule-cycle.ts` grid | WIRED |
| schedule | 2 | Gantt Chart | `workspace-gantt.ts` | WIRED |
| schedule | 3 | Relationships & lag | Relationship editor | WIRED |
| schedule | 4 | Calendars & work time | Schedule options calendar editor + holidays | WIRED |
| schedule | 5 | Schedule options & Data Date | Schedule settings form | WIRED |
| schedule | 6 | Resources & leveling | Capacity/leveling panels | WIRED |
| schedule | 7 | Progress & baselines | Progress/baseline panels | WIRED |
| schedule | 8 | Run Schedule | Schedule execution command | WIRED |
| schedule | 9 | Formula editor | `p6-formula-editor.ts` | WIRED |
| schedule | 10 | Code Reference | `workspace-scheduling-reference.ts` | WIRED-READ |
| schedule | 11 | Option catalogue | Generated reference catalogue | WIRED-READ |
| schedule | 12 | Formula contracts | Formula contract view | WIRED-READ |
| schedule | 13 | Documentation review | Documentation review view | WIRED-READ |
| progress | 1 | Progress Overview | Count metrics | SHELL |
| progress | 2 | Progress Detail | Count metrics | SHELL |
| resources | 1 | Max units / time | `p6-capacity-panel.ts` | WIRED |
| resources | 2 | Assignments | Links to assignments page | SHELL |
| assignments | 1 | Assignment Register | Empty register shell | SHELL |
| assignments | 2 | Resource Usage | Empty register shell | SHELL |
| assignments | 3 | Assignment Details | Placeholder tabs | SHELL |
| roles | 1 | Role Register | Static empty table | SHELL |
| roles | 2 | Rates & Limits | Placeholder tab | SHELL |
| roles | 3 | Assignments | Placeholder tab | SHELL |
| calendars | 1 | Calendar Register | Real catalogue | WIRED-READ |
| calendars | 2 | Workweek & Shifts | Disabled editor | SHELL |
| calendars | 3 | Exceptions & Holidays | Disabled editor (holiday editor exists only in schedule options) | SHELL |
| calendars | 4 | Assignments | Empty panel | SHELL |
| cost | 1 | Cost Overview | Count metrics | SHELL |
| cost | 2 | Cost Detail | Count metrics | SHELL |
| expenses | 1 | Expense Register | Empty register shell | SHELL |
| expenses | 2 | Cost Accounts | Empty register shell | SHELL |
| expenses | 3 | Expense Details | Placeholder tabs | SHELL |
| documents | 1 | Documents | Real document list | WIRED-READ |
| documents | 2 | Evidence | Workspace tools | WIRED-READ |
| reports | 1 | Reports | Placeholder | SHELL |
| reports | 2 | Print | Tool button only | SHELL |
| tracking | 1 | Project Table | Static layout | SHELL |
| tracking | 2 | Project Bar Chart | Static layout | SHELL |
| tracking | 3 | Project Gantt / Profile | Static layout | SHELL |
| tracking | 4 | Resource Analysis | Static layout | SHELL |
| issues | 1 | Issue Register | Empty register shell | SHELL |
| issues | 2 | Issue Details | Placeholder tabs | SHELL |
| risks | 1 | Risk Register | Empty register shell | GAP-CORE |
| risks | 2 | Risk Analysis | Empty register shell | GAP-CORE |
| risks | 3 | Risk Details | Placeholder tabs | GAP-CORE |
| thresholds | 1 | Threshold Register | Empty register shell | GAP-CORE |
| thresholds | 2 | Monitoring Rules | Empty register shell | GAP-CORE |
| thresholds | 3 | Threshold Details | Placeholder tabs | GAP-CORE |
| control | 1 | Control Summary | Count metrics | WIRED-READ |
| control | 2 | Changes & Claims | Change/claim rail surface | WIRED |
| settings | 1 | Language | Locale selector (8 registered locales) | WIRED |
| settings | 2 | Workspace | Project settings and preferences | WIRED-READ |

## 3. Gap register

Wiring gaps are fixable against the existing shared core and HTTP boundary without
changing calculation architecture. Core gaps are recorded here and must not be
faked in the UI.

| ID | Class | Gap | Evidence | Required change | Blocking |
|---|---|---|---|---|---|
| GAP-CAL-01 | Wiring | Calendar page editor disconnected from calendar core — resolved 2026-11-04 | Replaced by `workspace-calendars.ts`: catalogue selection, snapshot read, revision-checked update, copy, delete and exception writes. Browser-verified against the real preview WSGI/SQLite runtime (select, workweek, holidays, save revision 1→2, copy, delete, nonwork exception); unit tests cover fail-closed parsing and all write payloads. Remaining sub-gaps: no blank-calendar creation route, workweek writes only through copy, no exception delete route | — | No |
| GAP-RES-01 | Wiring | No resource dictionary register for labor/nonlabor/material/roles | `case "resources"` shows capacity and counts; `p6_resource_read_api.py`/`p6_resource_write_api.py` and `/p6/resource-*` routes exist | Load the resource dictionary and bind register/details after the calendar page | No |
| GAP-ASN-01 | Wiring | Assignment register is a static shell | `renderRegisterWindow`; `/p6/resource-assignments` GET/POST and period/spread read models exist | Load assignments for the project and bind register/details; use existing schedule commands for writes | No |
| GAP-ROL-01 | Wiring | Role register is a static shell | `p6_role_api.py` create/update/list; `/p6/roles` routed | Load roles, bind details, create/update with revision | No |
| GAP-EXP-01 | Wiring | Expense register is a static shell | `p6_expense_api.py` create/list; `/p6/expenses` routed | Load expenses, bind register/details, create with cost account and activity references | No |
| GAP-COST-01 | Wiring | Cost page shows unrelated counts | `case "cost"`; cost accounts/financial periods/EVM routes exist | Build cost overview from expenses, cost accounts, financial periods and the EVM read model; never compute finance in the browser | No |
| GAP-PRG-01 | Wiring | Progress page does not expose progress updating | `case "progress"` counts; `/p6/activity-period-actuals` and schedule progress write paths exist | Bind activity progress/actuals/remaining work to authoritative endpoints and reuse schedule recalculation | No |
| GAP-RPT-01 | Core | Reporting core has no HTTP exposure | `reporting.py` defines typed datasets only; no report route in `project_lifecycle_routes.py` | Add a versioned report read API that produces datasets from authoritative queries, then bind the Reports page | Yes (server) |
| GAP-RPT-02 | Wiring | Reports page is a placeholder | `case "reports"` | Bind report selection, columns, filters, grouping, saved layouts, print/export after GAP-RPT-01 | Blocked by GAP-RPT-01 |
| GAP-TRK-01 | Core | No tracking read model | `case "tracking"` static; no tracking API | Define project table/bar/Gantt-profile/resource-analysis read models from authoritative schedule and cost data | Yes (server) |
| GAP-RSK-01 | Core | No risk register domain | No risk module in `src/construction_pm` | Define risk register contract and persistence; then bind UI | Yes (server) |
| GAP-THR-01 | Core | No threshold domain | No threshold module | Define threshold/monitoring contract and persistence; then bind UI | Yes (server) |
| GAP-ISS-01 | Wiring | Issues page ignores loaded field issues and has no issue API | `state.fieldIssues` exists; P6-style issue register API absent | Decide the authoritative issue home (field-operations or project issues), expose it, and bind the register | Partly server |
| GAP-WBS-01 | Wiring | WBS chart and full detail fields absent | `case "wbs"` disabled Chart View | Render the WBS chart from the WBS tree; complete detail fields against `/p6/wbs` | No |
| GAP-DOC-01 | Wiring | Documents are read-only | `case "documents"` list only | Bind document create/link/upload/delete to the document API with permissions | No |
| GAP-PRJ-01 | Wiring | Only the session-authorized project is visible | `case "project"` note | Add EPS/portfolio navigation once a multi-project read API is exposed; do not invent projects | Partly server |
| GAP-PRJ-02 | Wiring | Project lifecycle actions absent from the page | `case "project"` | Expose open/close/archive operations already supported by the lifecycle service | No |
| GAP-SCH-01 | Audit | Long-tail schedule dialogs not yet line-by-line audited | This matrix | Complete page/dialog audit for schedule submenus 1-13 against V26 Help | No |
| GAP-I18N-01 | Audit | Eight locales registered, but translated-string coverage is not verified per page | `workspace-localization.ts` registry; `sync-runtime.language-pack.test.ts` | Audit each page in de/zh/ar/fr/ja/ko with activated packs; fix mixed-language and width breakage | No |
| GAP-ADM-01 | Wiring | No per-surface layout administration | Settings page | Bind layout save/restore administration to the layouts API | No |
| GAP-CTL-01 | Wiring | Control summary is count-only | `case "control"` | Bind control summary metrics to the control-intelligence read API | No |
| GAP-V26-01 | Evidence | No licensed Version 26 reference run available in this environment | `CORE_COMPLETION_EXECUTION_LEDGER.md` | Obtain an authorized reference dataset and run numeric parity; until then no row is `IMPLEMENTED_AND_PARITY_TESTED` | Yes (external) |

## 4. Order of completion

1. `GAP-CAL-01` — Calendars page (core and HTTP already complete). **Resolved 2026-11-04.**
2. `GAP-ROL-01`, `GAP-ASN-01`, `GAP-EXP-01` — resource/cost registers.
3. `GAP-PRG-01` — progress updating bound to the schedule core.
4. `GAP-COST-01` — cost overview from authoritative reads.
5. `GAP-WBS-01`, `GAP-DOC-01`, `GAP-PRJ-02`, `GAP-CTL-01`, `GAP-ADM-01` — remaining wiring.
6. `GAP-RPT-01`, `GAP-TRK-01`, `GAP-RSK-01`, `GAP-THR-01`, `GAP-ISS-01` — server-side contracts.
7. `GAP-SCH-01`, `GAP-I18N-01` — audits and fixes.
8. `GAP-V26-01` — numeric parity once an authorized reference run exists.

Ordering is dependency-based, not a completion claim. Each item is closed only by
merged code, a test that exercises the real path, and browser evidence.
