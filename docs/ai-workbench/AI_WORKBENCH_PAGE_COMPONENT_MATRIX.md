# AI Workbench — Page & Component Matrix

The Workbench has one shell and five studio documents. A studio is a full-size
surface, never a chat answer. No component below may be enabled without the
service named in its row.

| Studio | Page / region | Component | Service | Status |
|---|---|---|---|---|
| Shared | Header | Identity, active studio, project, project id, data date, source revision, analysis state, save state, locale, permissions, return to Engineering | session + project read | PLANNED |
| Shared | Command panel (300–360 px) | Command input, history, clarification, progress, warnings, proposal cards, structured response | `ai_workbench.plan_command` | PLANNED |
| Shared | Main workspace (≥65%) | Studio router viewport | studio service | PLANNED |
| Shared | Inspector | Dock/resize/hide/restore, selection-driven content | studio read model | PLANNED |
| Shared | Status bar | Calculation, scenario revision, source revision, validation, last updated, pending decisions, execution state | studio + audit | PLANNED |
| Import Staging | Tab 1 Source | File identity, format/version, size, checksum, security scan, parse state | project import contract (#1799) | BLOCKED |
| Import Staging | Tab 2 Inventory | Entity counts: EPS, projects, WBS, activities, relationships, calendars, codes, UDFs, resources, roles, assignments, expenses, baselines, constraints, documents | project import contract | BLOCKED |
| Import Staging | Tab 3 Mapping | Source→target field, rule, confidence, status, ambiguity choice | project import contract | BLOCKED |
| Import Staging | Tab 4 Validation | Blocking/warning/information/data-loss, row drill-through | project import contract | BLOCKED |
| Import Staging | Tab 5 Schedule Preview | WBS tree, Gantt, activity grid, details, source-vs-recalculated | staging snapshot + scheduling core | BLOCKED |
| Import Staging | Tab 6 Options | Create/update/merge, IDs, datasets, conflict policy, calendar, timezone, planned counts | project import contract | BLOCKED |
| Import Staging | Tab 7 Final Review | Counts, digest, target revision, permissions, confirmation, apply/verify | project import contract + audit | BLOCKED |
| Scenario Studio | Command Brief | Request, project, revision, data date, objective, constraints, assumptions, missing inputs | command layer | PLANNED |
| Scenario Studio | Scenario Selector | Baseline/current/A/B/C, create/duplicate/rename/archive/pin/recommend/compare | scenario service (#1989) | BLOCKED |
| Scenario Studio | Gantt Workspace | 4 visual bar styles, scales, overlays, float, critical, relationships, data date | scheduling core + scenario store | BLOCKED |
| Scenario Studio | Activity Grid | 22 columns, freeze, sort, filter, group, multi-select, context menu, keyboard | scenario read model | BLOCKED |
| Scenario Studio | Comparison | Side-by-side, overlay, variance table | scenario comparison service | BLOCKED |
| Scenario Studio | Inspector | 12 sections; dock/resize/hide | scenario read model | BLOCKED |
| Scenario Studio | Impact Dashboard | Finish, float, resources, cost, risk; each linked to evidence | scheduling core + scenario | BLOCKED |
| Scenario Studio | Controls | Run, recalculate, validate, compare, save draft, export, request approval, discard | scenario service | BLOCKED |
| Risk Studio | Overview/Register/Matrix/Quantitative/Response/History | Real risk register and matrix; quantitative only with valid inputs | risk API | WIRED_READ / WIRED_WRITE |
| Project Analysis | Executive/Schedule/Cost/Resource/Forecast | Read models and drill-down; EVM only when source data is valid | schedule/project read models | WIRED_READ |
| Decision Workspace | Inbox/Detail/Decision | Proposal list, before/after, validation, approve/reject/partial/defer | proposal service | PARTIAL (Enterprise approvals only) |

## Rules

- Chat is never the main canvas for Gantt, tables, matrices or comparisons.
- A blocked studio retains its route only as a disabled entry with the exact
  blocker text; it does not render sample data.
- Component IDs must be stable test IDs; no two studios may reuse one.
