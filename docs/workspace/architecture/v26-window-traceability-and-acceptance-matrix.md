# Version 26 to CUBI Window Traceability and Acceptance Matrix

- Parent epic: [#1722](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1722)
- Source register: [v26-source-register.md](../reference/v26-source-register.md)
- Complete target catalog: [v26-complete-window-component-catalog.md](v26-complete-window-component-catalog.md)
- Baseline commit used for initial documentation: 49201ddfbec83550e7147ce2fa3cc961e39eef55

## 1. Status vocabulary

Use one of these states for every requirement, after inspecting the exact branch and a real browser:

| Status | Meaning |
|---|---|
| NOT_AUDITED | No current source/browser evidence has been checked for this requirement. |
| MISSING | No implementation exists. |
| SHELL_ONLY | A label/icon/route/placeholder exists, but the required window or behavior does not. |
| WIRED_READ | Real authorized data is loaded and displayed, but one or more required writes/commands are absent. |
| WIRED_WRITE | Real persisted operations work, but some required visual states, interactions, or window details remain incomplete. |
| VERIFIED | Full requirement, permissions, persistence, errors, browser behavior and required evidence all pass. |
| BLOCKED_EXTERNAL | A named external dependency/licence/credential is necessary; blocker and safe fallback are documented. |
| NOT_APPLICABLE | Explicitly excluded with product-owner approval and rationale. |

A page or window can contain requirements in different states. Never assign one green status to an entire window when only some controls work.

## 2. Requirement traceability

The source-page column identifies the section or chapter in the Version 26 Help set. Use the detailed page/section references in the source PDF and record exact printed pages in the execution record when the requirement is implemented.

| ID | Requirement | Primary source section | CUBI surface/component | Required proof | Initial status |
|---|---|---|---|---|---|
| WS-001 | Single persistent authenticated workspace shell | Help: Getting Started / Workspace Basics | Canonical workspace shell | Login, direct-link, refresh and logout journey; only one authenticated shell | NOT_AUDITED |
| WS-002 | Menu bar with nested, active-window-aware commands | Help: Working with Toolbars and Menus | Global menu/command registry | Each command maps to stable ID, window, permission and action | NOT_AUDITED |
| WS-003 | Toolbar families, icons, tooltips and shortcut mappings | Help: Toolbar and Icon Reference | Main toolbar groups | Icon-to-command audit, tooltip, keyboard and disabled states | NOT_AUDITED |
| WS-004 | Window tabs, close, reorder, dirty state and lifecycle | Help: Using Main Windows | Window-tab manager | Duplicate-open, switch, close and unsaved-change tests | NOT_AUDITED |
| WS-005 | Context/shortcut menus on selected records and blank surfaces | Help: Use Shortcut Menus | Context-menu engine | Context matrix across all windows and hit targets | NOT_AUDITED |
| WS-006 | Multi-selection and keyboard selection behavior | Help: Select Multiple Items / Hot Keys | Selection manager | Mouse/keyboard selection, range, modifier and focus tests | NOT_AUDITED |
| WS-007 | Layout save/open, top/bottom view and restore | Help: Customizing Activity Layouts / Tracking Layouts | Layout manager | Save, reopen, refresh, revision conflict and reset tests | WIRED_WRITE (Activities only; see §2.1) |
| WS-008 | Full-screen and responsive workspace behavior | CUBI owner requirement | Workspace shell | 1280x720, 1366x768, 1920x1080 and landscape mobile evidence | NOT_AUDITED |
| WS-009 | RTL/LTR and eight-language coverage | CUBI owner requirement | Localization/layout engine | All windows, menus, dialogs, context menus and empty/error states | NOT_AUDITED |
| WS-010 | CUBI theme and state-color semantics | CUBI design system | Theme/token/icon registry | Light/dark contrast, status signal collision and consistency tests | NOT_AUDITED |
| ACT-001 | Full Activity Table with configurable field columns | Help: Activity Table | Activities / table | Complete field chooser, edit/read-only and persistence tests | NOT_AUDITED |
| ACT-002 | Multi-level group and sort including WBS hierarchy/path | Help: Grouping and Sorting | Activities / grouping engine | Multiple group and sort levels, stable order and saved layout | NOT_AUDITED |
| ACT-003 | Filters, compound conditions and saved filters | Help: Filtering | Activities / filter engine | Apply/combine/save/remove and full-project result count | NOT_AUDITED |
| ACT-004 | Group band fonts, colors and row styling | Help: Change Group Row Fonts and Colors | Activities / WBS group rows | Per-level styling, readability and semantic color separation | NOT_AUDITED |
| ACT-005 | Table font, color and row-height controls | Help: Change Activity Table Font, Color and Row Height | Activities / table preferences | Change, save, reload and reset | NOT_AUDITED |
| ACT-006 | WBS hierarchy plus/minus expand/collapse | Help: Grouping by Hierarchy; CUBI owner requirement | Activities / WBS tree rows | Collapse only selected branch, all depths and persisted state | NOT_AUDITED |
| ACT-007 | Collapsed WBS hides/restores matching Gantt rows/bars | CUBI owner requirement | Activities / synchronized table/Gantt view model | Row/bar identity and vertical alignment assertions | NOT_AUDITED |
| ACT-008 | Gantt timescale, pan, zoom and visible range | Help: Gantt Chart / Timescale | Activities / Gantt timeline | Unit/interval/range and refresh persistence tests | NOT_AUDITED |
| ACT-009 | Gantt bar types, shape, fill, outline, height and position | Help: Change Gantt Chart Bar Style/Settings | Activities / Bar Styles dialog | Per-type style preview and actual rendered geometry | NOT_AUDITED |
| ACT-010 | Gantt labels, filters, legend and background lines | Help: Gantt Chart options | Activities / Gantt options | Labels, legend, grid and per-bar filter tests | NOT_AUDITED |
| ACT-011 | Data Date, progress line, baseline and critical display | Help: Customize Data Date Line / Progress Line | Activities / Gantt overlays | Correct source date and overlay tests | NOT_AUDITED |
| ACT-012 | Relationship arrows and editing from Gantt | Help: View/Create/Edit Relationships in Gantt | Activities / Gantt connectors | FS/SS/FF/SF, lag, arrow context menu and persisted readback | NOT_AUDITED |
| ACT-013 | Activity Network view and node/edge layout | Help: Activity Network | Activities / Network | Node layout, edge details, selection synchronization | NOT_AUDITED |
| ACT-014 | Activity Details tabs and field completeness | Help: Customize Activity Details | Activities / Details | Tab inventory, field registry and selected-record binding | NOT_AUDITED |
| ACT-015 | Activity Usage Profile/Spreadsheet | Help: Activity Usage Profiles and Spreadsheets | Activities / bottom views | Time-phased values, bucket controls, totals and source binding | NOT_AUDITED |
| ACT-016 | Trace Logic view | Help: Trace Logic | Activities / bottom view | Predecessor/successor navigation and selection binding | NOT_AUDITED |
| ACT-017 | Right-click menu for WBS, activity, Gantt bar, arrow, blank table and blank chart | Help: Use Shortcut Menus; CUBI context matrix | Activities / context-menu engine | Every target has correct commands and enabled reasons | NOT_AUDITED |
| ACT-018 | Large-project grid/Gantt with no hard-coded 180-row cap | CUBI owner requirement | Workspace read, table, Gantt, query and export | 250+ and stress fixtures; no silent slice/truncation | NOT_AUDITED |
| ACT-019 | Hidden/filtered/collapsed activities remain in complete schedule input | CUBI owner requirement | Schedule input snapshot composer | Same snapshot/run result with different view filters/collapse states | NOT_AUDITED |
| ACT-020 | Full-project search, counts, selection and export scope | Help: Find / Select All / Filter / Export workflows | Activities / selection and export | Count reconciliation and all/filtered/selected scope tests | NOT_AUDITED |
| WBS-001 | Hierarchical WBS table and chart | Help: Defining WBS / WBS Chart and Table | WBS window | Same persisted nodes and ordering in both layouts | NOT_AUDITED |
| WBS-002 | WBS details, status and weighted milestones | Help: WBS Details / Status / Weighted Milestones | WBS Details | Field registry and roll-up tests | NOT_AUDITED |
| WBS-003 | WBS copy/cut/paste/delete protections | Help: WBS operations | WBS context menu and commands | Child/activity reference protection and undo/audit | NOT_AUDITED |
| PRJ-001 | Authorized project register and hierarchy | Help: Projects / EPS | Projects window | Authorization, tree, multi-project selection and filters | NOT_AUDITED |
| PRJ-002 | Project Details and defaults | Help: Project Details / Working with EPS | Projects Details | Field-by-field persistence and defaults application | NOT_AUDITED |
| PRJ-003 | Project open/close/switch and tab lifecycle | Help: Projects / Main Windows | Workspace and Projects | Project switch, dirty state, revisions and active tabs | NOT_AUDITED |
| REL-001 | Relationship create/edit/delete and predecessor/successor views | Help: Linking Activities with Relationships | Activity Details and relationship view | Endpoint, type, lag, calendar and revision tests | NOT_AUDITED |
| RES-001 | Resource hierarchy/register/details | Help: Defining Resources | Resources window | Resource types, hierarchy, codes and persistence | WIRED_WRITE (master, hierarchy and revision-guarded editor; see §2.1) |
| RES-002 | Roles, proficiency, price/unit rates and limits | Help: Roles | Roles window | Effective date/rate/limit and assignment tests | WIRED_WRITE (hierarchy, proficiency, effective-dated rates/limits; see §2.1) |
| RES-003 | Resource assignments grouped by resource | Help: Resource Assignments | Resource Assignments window | Grouping, assignment fields and drill-through | WIRED_WRITE (grouping, spreadsheet, profile and revision; see §2.1) |
| RES-004 | Resource Usage Profile/Spreadsheet | Help: Resource Usage Profiles and Spreadsheets | Resource window / assignments | Availability, limits, overallocation, overtime and bucket tests | NOT_AUDITED |
| RES-005 | Resource curves, shifts and rates over time | Help: Resource Curves / Shifts / Multiple Prices | Resources and assignments | Curve, shift and effective-date calculations | NOT_AUDITED |
| CAL-001 | Global/project/resource calendar dictionary | Help: Defining Calendars | Calendars window | Create/edit/copy/delete and scoped assignments | WIRED_WRITE (register, create-from-base, copy, usage list and assignment calendar reference; see §2.1) |
| CAL-002 | Workweek, daily hours, exceptions and holidays | Help: Project/Global/Resource Calendars | Calendar editor | Effective-calendar preview and scheduler parity | WIRED_WRITE (workweek, split shifts, exception add/remove, CPM parity, usage list; see §2.1) |
| CAL-003 | Calendar versioning and inheritance | CUBI core architecture | Calendar editor / shared core adapter | Version-bound read, inheritance and immutable snapshot tests | WIRED_WRITE (version-bound read and copied base facts; see §2.1) |
| SCH-001 | Schedule dialog, options and Data Date | Help: Scheduling Projects / Using the Data Date | Schedule window/dialog | Typed inputs, option persistence and exact snapshot binding | NOT_AUDITED |
| SCH-002 | CPM, float, critical path and multiple float paths | Help: Define Critical Activities / Multiple Float Paths | Shared calculation core / Schedule results | Full dataset tests and external Version 26 fixture comparison | NOT_AUDITED |
| SCH-003 | Constraints, open ends and relationship lag calendar | Help: Constraints / Relationship Lag Calendar | Schedule Options and Activity Details | Every supported type, units, calendar and diagnostics | NOT_AUDITED |
| SCH-004 | Schedule Check and diagnostics | Help: Checking Schedules | Schedule Check window | Rules, severity, counts and drill-through | NOT_AUDITED |
| SCH-005 | Resource leveling and leveling log | Help: Leveling Resources | Tools / Level Resources | Capacity, priority, float limits and final feasibility | NOT_AUDITED |
| SCH-006 | All persisted schedule-eligible activities included | CUBI owner requirement | Snapshot composer and evaluator | Compare stored activity count to snapshot and output count | NOT_AUDITED |
| BASE-001 | Baseline capture, copy, update and delete | Help: Creating Baselines | Baseline manager | Full activity-level snapshot and immutable identity | NOT_AUDITED |
| BASE-002 | Primary/secondary/tertiary assignment and comparison | Help: Assign Baselines / Compare Schedules | Baseline dialog and Gantt | Assignment, selected baseline and variance field tests | NOT_AUDITED |
| PRO-001 | Update progress for one/all/selected activities | Help: Updating Projects / Update Progress | Progress window and Activity Details | Explicit scope preview, validation, revision and readback | NOT_AUDITED |
| PRO-002 | Apply actuals and store period performance | Help: Apply Actuals / Store Period Performance | Progress and period tools | Unit/cost/date reconciliation and immutable period records | NOT_AUDITED |
| PRO-003 | Earned Value and cost analysis | Help: Earned Value / Analyze Costs | Cost/EVM window | PV/EV/AC/EAC/ETC/indices with missing-input behavior | NOT_AUDITED |
| TRK-001 | Tracking layout lifecycle and sharing | Help: Tracking Layouts | Tracking window | Save/open/share/import/export/delete tests | NOT_AUDITED |
| TRK-002 | Tracking top/bottom layout and profiles | Help: Tracking Layouts / Profiles | Tracking | Visibility, column, filter and Gantt/profile tests | NOT_AUDITED |
| DOC-001 | Document register, categories/status and assignments | Help: Work Products and Documents | Documents window | CRUD, linking, opening and authorization | WIRED_WRITE (register, filters, metadata CRUD, audited status graph and history; approval role-gated; binary upload absent; see §2.1) |
| COST-001 | Expenses, accrual categories and activity assignment | Help: Expenses | Expenses and Activity Details | Create/edit, accrual, category and activity linkage | WIRED_WRITE (create/edit/delete, accrual date, category enum and activity/WBS linkage; no approval or periodization; see §2.1) |
| COST-002 | Cost Account hierarchy and default | Help: Cost Accounts | Cost Accounts dictionary | Parent/child, default, edit/copy/delete | WIRED_WRITE (parent/child with cycle guard, single default, copy, edit/delete guards; see §2.1) |
| COST-003 | Budget, spending and funding sources | Help: Budgeting | Budget/Funding window | Periodized amounts, totals and variance | WIRED_WRITE (stored lines, pending/approved changes, funding and derived per-currency summary; actuals/variance and periodization absent; see §2.1) |
| ISSUE-001 | Issues, assignment, status, notification and history | Help: Issues | Issues window | CRUD, ownership, history and drill-through | WIRED_WRITE (register, validated status graph, comments and history; notifications absent; see §2.1) |
| THR-001 | Threshold definitions, monitoring and generated issues | Help: Thresholds | Thresholds window | Threshold engine, monitor run and issue linkage | WIRED_WRITE (definitions, immutable runs, level evaluation and one generated issue per issue transition; manual monitoring, three parameters; see §2.1) |
| RISK-001 | Risk register, categories, assignments and response | Help: Risks | Risks window | Exposure/response and project linkage | WIRED_WRITE (register, categories, scoring matrix, response strategy/owner and immutable history; activity/resource assignment and notifications absent; see §2.1) |
| RPT-001 | Report register, wizard/editor and batch runs | Reporting Guide / Help: Reports | Reports window | Create, validate, run, preview and output readback | WIRED_WRITE (three-subject register, validated column definitions, revision-guarded edit/delete, immutable stored runs and output readback; no batch/scheduled runs, aggregates, layout/print or file export; see §2.1) |
| ADM-001 | Users, security profiles and permission matrix | Administration Guide / Help: Admin | Administration | Role permission matrix and cross-scope denial tests | WIRED_READ (derived read-only roles × 14 permissions from the single policy; no stored users or profiles; see §2.1) |
| ADM-002 | System preferences and categories/dictionaries | Administration Guide | Admin Preferences and dictionaries | Values, defaults, scope and auditing | WIRED_WRITE (revision-guarded project preferences and five-code dictionary with idempotent creates, audited writes and server filters; preferences not yet consumed elsewhere; see §2.1) |
| ADM-003 | Currency, units and financial periods | Administration Guide | Organization/System settings | Precision, currency and period boundary tests | WIRED_WRITE (currency/unit/decimal/fiscal-start stored with validation; financial-period list and create over `p6-financial-periods`; no close/reopen or posting enforcement; see §2.1) |
| UTIL-001 | Global Change preview and apply | Help: Global Change | Tools / Global Change | Condition logic, preview count, before/after and audit | NOT_AUDITED |
| UTIL-002 | Search, import/export and data exchange | Help: Find / Import/Export / Remote Projects | Workspace tools | Full-field round-trip and validation/error tests | WIRED_WRITE (CSV export of activities/resources/risks, validated resource import, idempotent apply and run history; global search and remote-project exchange absent; see §2.1) |
| UTIL-003 | Full project and layout backup/recovery | CUBI owner requirements | Workspace Settings / Recovery | Backup, restore, authorization, integrity and audit | NOT_AUDITED |
| CUBI-001 | Form Builder and organization/project libraries | CUBI product requirements | Forms window/tool | Template publish/copy/version/assign/approve/export tests | NOT_AUDITED |
| CUBI-002 | Engineering Intelligence Assistant | CUBI AI requirements | On-page assistant | Propose → approve → execute → verify, permission and audit | NOT_AUDITED |
| CUBI-003 | Project compare/difference | CUBI product requirements | Comparisons window | Immutable runs, field variance, WBS grouping and source revision | NOT_AUDITED |

### 2.1 Status updates (evidence-backed, newest first)

| Date | ID | New status | Evidence |
|---|---|---|---|
| 2026-11-12 | UTIL-002 | WIRED_WRITE (import/export only) | PR [#1775](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1775), tested code `f7fdedc`, evidence commit `0edef46`, merged as `20f49d5b`. The Import / Export window (20th workspace menu) mounts three tabs over `p6-exchange-api.v1`: **Export** reads activities, resources and risks from their authoritative repositories with fixed contract columns and a CSV download; **Import** accepts a CSV for `resources` only, validates the header, row arity, ids, duplicates, parent existence, hierarchy cycles, calendars, type, email, units and active flag with row/field/code errors, and applies parents-first through `P6ResourceAPI.create` behind a required idempotency key (identical content replays the same `EXR-<dataset>-<n>` run, different content under a used key returns 409 `EXCHANGE_IDEMPOTENCY_KEY_REUSE`); **Import History** lists preview and apply runs. `activities`/`risks` imports return `EXCHANGE_DATASET_READ_ONLY`; reads require `PROJECT_READ`, imports `PROJECT_WRITE`, and a viewer sees disabled controls and receives 403 `EXCHANGE_PERMISSION_DENIED`. Previews never write and are capped at 20 returned rows. Remaining gap: no global search or “Find”, no remote-project exchange, no round-trip re-import of an edited export, no activity/relationship/WBS/cost/assignment import, no quoted/multiline CSV, JSON or XLSX, no dry-run diff, no history retry/download/delete, no Postgres mirror for run history, and new labels are inline English/Persian. Recorded in `docs/qa/CUBI_V26_EXECUTION_CHECKPOINT.md` (Stage F3). |
| 2026-11-12 | ADM-001, ADM-002, ADM-003 | WIRED_READ / WIRED_WRITE | PR [#1773](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1773), tested code `99f4a308`, evidence commit `aeed0efa`, merged as `0337a7ad`. The Administration window (19th workspace menu) mounts four tabs over `p6-administration-api.v1`. **ADM-002**: one revision-guarded project preference record (three-letter uppercase currency, unit of measure, `gregorian`/`jalali` date display, 0–4 decimal places, fiscal month `1..12`, defaults `USD/day/gregorian/2/1`) and a dictionary namespaced over five fixed codes (`cost_category`, `risk_category`, `issue_type`, `document_type`, `expense_category`) whose entries carry an id, label, sequence, active flag and revision; creates are idempotent with request-hash storage, duplicate ids and reused keys return 409, edit/delete require `expected_revision`, and every accepted write appends an immutable audit event readable per entry. Server-side code and search filters and the WSGI-carried `/administration` query string keep the list and route in step. **ADM-001**: the permission matrix is derived read-only from `default_role_permissions()` — three roles (viewer, planner, project_admin) × all 14 permissions — so the screen cannot drift from enforcement; reads require `PROJECT_READ`, writes `PROJECT_ADMIN`, cross-scope calls fail `CROSS_SCOPE_ACCESS`, an actor mismatch fails `ADMIN_ACTOR_MISMATCH`, and a viewer sees no write controls while direct writes receive 403 `ADMIN_PERMISSION_DENIED`. **ADM-003**: currency/unit/decimal/fiscal-start persist with validation, and the Financial Periods tab lists and creates `OPEN`/`CLOSED` periods through the existing `p6-financial-periods` contract. Remaining gap: preferences do not yet drive formatting, precision, Jalali rendering or fiscal calendars in other windows; there is no user directory, security-profile editor, role-to-user assignment, custom role or per-project grant override; the five dictionary codes are not yet consumed as pickers elsewhere and there is no bulk import/export or merge; financial periods have no close/reopen action, cross-period overlap check or posting enforcement; administration facts are SQLite-only (no Postgres mirror), deleted entries hide their audit trail from the API, and new labels are inline English/Persian. Recorded in `docs/qa/CUBI_V26_EXECUTION_CHECKPOINT.md` (Stage F2). |
| 2026-11-12 | RPT-001 | WIRED_WRITE | PR [#1771](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1771), tested code `bb30ec9`, evidence commit `861c69a`, merged as `09022f87`. The Reports window reads and writes a project-scoped `p6-report-api.v1` register over `SQLiteReportStore`: definitions select one of three authoritative subjects (`activities`, `resources`, `risks`) and an ordered, duplicate-free subset of its typed columns; idempotent creates, revision-guarded edit/delete, immutable audit history, server-side subject/search filters and WSGI-carried query strings. `POST /reports/{id}/run` materializes the selected columns from the authoritative activity repository, resource master and risk store at the current project revision and stores rows verbatim under `RUN-<report_id>-<n>`; run summaries and stored output are readable, and an edit never rewrites an earlier run. The window offers create/edit forms driven by the server catalogue, details with selected columns, run output with exact row count and meta, and run history. A stale write returns `REPORT_REVISION_CONFLICT` and reloads the authoritative record; planner/admin write, viewer runs and reads but receives server 403s on direct writes. Remaining gap: no batch/scheduled runs, parameters, grouping/subtotals/aggregates, charts, page layout/print pipeline or CSV/PDF/XLSX export; the catalogue is fixed to three subjects; no delta/portfolio runs or run deletion; deleting hides runs while the audit trail remains unreachable; report facts are SQLite-only (no Postgres mirror); new labels are inline English/Persian. Recorded in `docs/qa/CUBI_V26_EXECUTION_CHECKPOINT.md` (Stage F1). |
| 2026-11-12 | CAL-001, CAL-002 | WIRED_WRITE (extended) | PR [#1769](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1769), tested code `f714cf94`, evidence commit `8c3c17af`, merged as `cef505e9`. The Calendars window gains a read-only **Used By** tab backed by `p6-calendar-usage-api.v1`: `GET .../p6/calendars/{id}/{version}/uses` composes total, per-kind counts and one row per reference from the authoritative activity-calendar, relationship-lag, resource-master and resource-assignment repositories, matching explicit references on exact id+version (resource masters store only an id and report `calendar_version: null`). The payload parser fails closed on a drifted contract, calendar reference, row count or non-integer counts; unknown calendar/version is 404 and a malformed reference is 400. The Assignments register form offers stored calendars as exact `id\|version` values, persists `calendar_id`/`calendar_version` on create, rejects a half-filled reference (`INCOMPLETE_CALENDAR_REFERENCE`), shows the stored reference in its calendar column, and gates New/Revise to write roles. Remaining gap: usage is derived per read with no stored projection or Postgres mirror, activity/lag assignment UI is absent, no scoped assignment editor from Project Details/Resources, no calendar delete/replace, multi-view rendering and recurring exceptions stay absent, and labels are inline English/Persian. Recorded in `docs/qa/CUBI_V26_EXECUTION_CHECKPOINT.md` (Stage D3c). |
| 2026-11-12 | RISK-001 | WIRED_WRITE | PR [#1767](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1767), tested code `97826cd`, evidence commit `a6466b2`, merged as `1342b60a`. The Risks window reads and writes a project-scoped `p6-risk-api.v1` register over `SQLiteRiskStore`: title, description, nine categories, four statuses, integer probability/impact in `1..5`, derived score `p × i` and exposure band (low ≤4, medium ≤9, high ≤16, critical otherwise), five response strategies, owner, response owner/due date, responsible manager, identification date and closure note; idempotent creates, revision-guarded edit/delete, a validated status graph (`closed → open` only) and closure-note enforcement, plus an immutable `created/updated/status_changed/deleted` audit trail. The window shows five server-side filters, a 5×5 count matrix that outlines the selected risk, a register table, a create/edit form, details and history. A stale write returns `RISK_REVISION_CONFLICT` and reloads the authoritative record, viewer sees no write controls and receives server 403s, and WSGI carries the risk query strings through the real preview/production app. Remaining gap: risks are not assigned to activities, WBS nodes or resources and there is no response action plan, residual risk or risk-to-issue conversion; no notification, escalation, review cadence or report export; the matrix has no time dimension or history snapshots; deleting a risk hides its audit trail; risk facts are SQLite-only (no Postgres mirror); new labels are inline English/Persian. Recorded in `docs/qa/CUBI_V26_EXECUTION_CHECKPOINT.md` (Stage E5). |
| 2026-11-12 | THR-001 | WIRED_WRITE | PR [#1765](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1765), tested code `47ab370a`, evidence commit `a2ab8c2f`, merged as `a761b5be`. The Thresholds window reads and writes a project-scoped `p6-threshold-api.v1` register over `SQLiteThresholdStore`: definitions for a monitoring subject and parameter with optional lower/upper bounds (up to four decimals, bounds may be negative), warning and issue deviation levels (`issue > warning`), currency required only for monetary parameters, manager and active/inactive status; idempotent creates, revision-guarded edit/delete and immutable audit history. `POST /thresholds/{id}/monitor` reads authoritative metrics (`open_issue_count`, `expense_actual_total`, `budget_balance` from the issue, cost and budget stores), evaluates `normal\|warning\|issue`, records an immutable run with the observed value and raises exactly one generated P6 issue (`THR-<id>-R<sequence>`) only on a transition into `issue`, through the issue API so authorization and audit stay consistent. A competing write returns `THRESHOLD_REVISION_CONFLICT` and reloads the authoritative record, viewer sees no write controls and receives server 403s, and WSGI carries the threshold query strings through the real preview/production app. Remaining gap: only three monitoring parameters exist (other subjects store without a metric source), monitoring is manual with no scheduler/notification/escalation, generated issues link back only by id pattern, deleting a threshold leaves its audit trail but hides its runs, threshold facts are SQLite-only (no Postgres mirror), and new labels are inline English/Persian. Recorded in `docs/qa/CUBI_V26_EXECUTION_CHECKPOINT.md` (Stage E4). |
| 2026-11-12 | COST-001, COST-002 | WIRED_WRITE | PR [#1763](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1763), tested code `605678a8`, evidence commit `49a59396`, merged as `67b69adb`. The Expenses window reads and writes a project-scoped `p6-cost-api.v1` register over `SQLiteCostStore`: cost accounts with a parent hierarchy and ancestry-cycle guard, exactly one project default (clearing the previous default bumps its revision and writes a `default_cleared` audit event), server-side copy, and delete guards `COST_ACCOUNT_HAS_CHILDREN` / `COST_ACCOUNT_IN_USE`; expenses with a validated category enum, three-letter currency, activity/WBS/cost-account references, expense and accrual dates, planned/actual/remaining two-decimal money, revision-guarded create/edit/delete with `COST_REVISION_CONFLICT`, server-side filters/search and a per-currency summary. A competing write reloads the authoritative record instead of overwriting it, viewer sees no write controls and receives server 403s, and WSGI carries the account/expense query strings through the real preview/production app. Remaining gap: no expense approval workflow, periodization or derived variance (the summary is a direct roll-up), expenses do not link to budget lines yet, no account archive/merge or drag hierarchy editor, cost facts are SQLite-only (no Postgres mirror), and new labels are inline English/Persian. Recorded in `docs/qa/CUBI_V26_EXECUTION_CHECKPOINT.md` (Stage E3b). |
| 2026-11-12 | COST-003 | WIRED_WRITE | PR [#1761](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1761), tested code `32028937`, evidence commit `6fd72623`, merged as `9c11331b`. The Cost window mounts a project-scoped budget register over `p6-budget-api.v1`: stored original budget lines with a shared Decimal two-place money parser, revision-guarded edits, idempotent creates, currency locked once changes exist, `pending -> approved \| rejected` budget changes approved only by `project_admin`, funding sources with revision guards, immutable audit history and a server-derived per-currency summary (`current = original + approved`, pending tracked separately, `balance = current - funding`). WSGI carries line/funding filters, the preview runtime persists across restart, planner can write but not approve, and viewer is read-only. Remaining gap: no expenses, cost accounts, actual-cost engine, time-phased/variance calculation or bulk import/export; budget facts are SQLite-only (no Postgres mirror); funding is recorded but not reconciled; new labels are inline English/Persian. Recorded in `docs/qa/CUBI_V26_EXECUTION_CHECKPOINT.md` (Stage E3). |
| 2026-11-12 | DOC-001 | WIRED_WRITE | PR [#1759](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1759), tested code `b22c7955`, evidence commit `cbd783b2`, merged as `8f9b37a0`. The Documents window reads and writes a project-scoped `DocumentAPI` v1.0 register over `SQLiteDocumentStore` in preview and `PostgresDocumentStore` in production: validated `contract\|drawing\|correspondence\|rfi\|submittal\|delay_claim\|evidence` types and `draft\|submitted\|approved\|rejected\|superseded` statuses, an explicit `sha256:` content hash with bytes behind `storage_ref`, idempotent create, duplicate protection, revision-guarded metadata edits, server-side type/status/search filters, the documented transition graph with an audited reason, immutable history and role-gated approval (`project_admin`). A metadata write cannot change status (`DOCUMENT_STATUS_REQUIRES_TRANSITION`), a competing write returns `DOCUMENT_REVISION_CONFLICT` and reloads the authoritative record, and a viewer sees disabled create/edit/transition actions plus server 403s. Remaining gap: binary upload/download is absent (`GAP-DOC-02`), links are free-text references, there is no categories dictionary, multi-step workflow or notification, and the Postgres `list`/history path is not exercised by the default suite. Recorded in `docs/qa/CUBI_V26_EXECUTION_CHECKPOINT.md` (Stage E2). |
| 2026-11-12 | ISSUE-001 | WIRED_WRITE | PR TBD, tested code `f7ff537d`, evidence commit `545ed4a5`. The Issues window reads and writes a project-scoped `p6-issue-api.v1` register: validated type/status/priority enums, due-date ordering, resolution-note rules, the documented transition graph, revision-guarded update/delete/comment with 409 `ISSUE_REVISION_CONFLICT`, server-side filters/search, immutable audit events and a details pane with general, details, document-reference and history tabs. A competing write reloads the authoritative record instead of overwriting it, closed issues refuse edits and comments, and WSGI carries the issue query string so filters work through the real preview/production app. Remaining gap: no notification delivery, no user-directory assignment (owner is a free-text field), document references are stored as text rather than links to the document register, no attachments or bulk import/export, deleted records are not readable through the detail/history routes (the repository retains the event trail), and the Postgres mirror is not exercised by the default suite. Recorded in `docs/qa/CUBI_V26_EXECUTION_CHECKPOINT.md` (Stage E1). |
| 2026-11-12 | CAL-002, CAL-003 | WIRED_WRITE (extended) | PR [#1753](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1753), tested code `418425d3`, evidence commit `8e65ca20`, merged as `1ba5c9ef`. Calendars can be created from a base with a Jalali date system (`system` validated; a bare master cannot carry one) while the system is immutable on later edits. Jalali definitions accept typed Jalali exception dates, store the canonical ISO date and show both; stored exceptions are edited through a separate revision-guarded `PUT` that raises `record_revision` and rejects stale edits (`EXCEPTION_REVISION_CONFLICT`), missing rows and invalid revisions. Remaining gap: storage/scheduling remain Gregorian, no other calendar systems, one detailed interval per exception, no recurring exceptions, no scoped assignment editor, and no Postgres mirror for exception revision. Recorded in `docs/qa/CUBI_V26_EXECUTION_CHECKPOINT.md` (Stage D3b). |
| 2026-11-12 | CAL-001, CAL-002, CAL-003 | WIRED_WRITE | PR [#1751](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1751), tested code `c95c1cd5`, evidence commit `ec95b9ec`, merged as `03d61a39`. The Calendars window creates stored calendars from a base calendar and copies its snapshot, exceptions and all four work-hour kinds in one transaction; edits the workweek with revision-guarded standard and detailed rules (a new rule bumps the master revision), edits split shifts with strict non-overlapping `HH:MM-HH:MM` intervals and derived hours, and removes stored exceptions through a real `DELETE`. The preview registry applies persisted workweek rules through the shared resolver, registers working-time calendars and base references, and a Friday non-working rule changes the authoritative CPM finish and survives a restart. Remaining gap: day CPM does not consume per-day hours/split-shift capacity, dated detailed and total-hours rules fail closed, no calendar delete/replace/versioned copy-as, no scoped assignment editor from Project Details or Resources, recurring exceptions and exception editing are absent, Jalali browser evidence is pending, and the new labels are inline English/Persian. Recorded in `docs/qa/CUBI_V26_EXECUTION_CHECKPOINT.md` (Stage D3a). |
| 2026-11-11 | RES-002 | WIRED_WRITE | PR [#1749](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1749), tested code `adec57fe`, evidence commit `e06a69dc`, merged as `a9cdc362`. The Roles window reads the stored hierarchy in parents-first order, creates and edits with duplicate (409 `ROLE_ALREADY_EXISTS`), cycle (409 `ROLE_HIERARCHY_CYCLE`) and stale-revision (409 `REVISION_CONFLICT`) protection, assigns stored resources with five proficiency levels and exactly one primary role per resource (the previous primary is demoted), and writes effective-dated price/unit rates (at most five per date) and limits (one per date, units or percent) with edit revisions. Remaining gap: rate/limit/assignment facts are SQLite-only (no Postgres mirror), no role delete/copy/org chart, limits are not enforced by leveling, "Calculate Costs from Units" is not consumed by assignment cost, no bulk assignment, and the new labels are inline English/Persian. Recorded in `docs/qa/CUBI_V26_EXECUTION_CHECKPOINT.md` (Stage D2c). |
| 2026-11-11 | RES-003 | WIRED_WRITE | PR [#1747](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1747), tested code `de89d44c`, evidence commit `50e35112`. The Resource Assignments window reads stored assignment facts, creates real assignments with 409 duplicate protection, groups by resource/role/activity with exact decimal subtotals, sorts and filters without rewriting facts, persists column choices per project, writes time-phased periods from the Spreadsheet tab, derives the Profile from stored periods, and implements "Revise" as a real `-R2` create because stored facts are append-only. Remaining gap: in-place edit/delete, import/bulk create, drill-through from the Resources register, and translations of the new form. Recorded in `docs/qa/CUBI_V26_EXECUTION_CHECKPOINT.md` (Stage D2b). |
| 2026-11-11 | RES-001 | WIRED_WRITE | PR [#1745](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1745), tested code `4c3d0348`, evidence commit `825981fe`. The Resources window reads a stored `P6Resource` master (name, type, parent, calendar, active) and shows a parents-first hierarchy; create and edit write through `p6-resource-api.v1` with a required `expected_revision`, return the new revision, reject stale writes with `REVISION_CONFLICT`, reject duplicate ids with `RESOURCE_ALREADY_EXISTS` (409) instead of overwriting, and reject unknown parents or cycles. Remaining gap: delete/archive, organizational chart/table views, Move toolbar, drag reparenting, shifts/curves/codes, `calendar_id` validation against the calendar service, and translations of the new forms. Recorded in `docs/qa/CUBI_V26_EXECUTION_CHECKPOINT.md` (Stage D2a). |
| 2026-11-11 | WS-007 | WIRED_WRITE | PR [#1743](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1743), tested code `4a9ccc8b`, evidence commit `490c6464`. Activities reads both stored layout scopes from the layout service, previews/applies/cancels in the real table and Gantt, saves with revision conflict surfaced, Save As writes user scope, restores after reload and keeps projects isolated; switching leaves activities, relationships, WBS and dates untouched. Remaining gap: Resource Assignments and Tracking layouts, share/import/export/delete, reset-to-default, and layouts are scoped by layout scope rather than user identity. Recorded in `docs/qa/CUBI_V26_EXECUTION_CHECKPOINT.md` (Stage D1b). |

## 3. Window completion checklist

Apply this checklist independently to every window. A requirement is not VERIFIED until every applicable item passes.

### Structure and visual completeness
- [ ] Correct window-specific title, active tab and breadcrumb context.
- [ ] Complete top layout and all applicable alternate views.
- [ ] Required bottom Details tabs and optional bottom layouts.
- [ ] All menus, submenus, command bars, toolbar groups and icons.
- [ ] Window-specific dialogs, drawers, wizards and configuration panels.
- [ ] Table/chart/network fields, headers, data states and selection states.
- [ ] Correct hierarchy, indentation, color, typography, line weight, density and spacing.
- [ ] No duplicates, random empty rows, overflowing filters or misplaced controls.
- [ ] Empty, loading, error, permission-denied, read-only, dirty and conflict states.
- [ ] RTL/LTR, all approved locales, date display and full-screen behavior.

### Functional completeness
- [ ] Every visible command has a real action or truthful disabled reason.
- [ ] Mouse and keyboard interactions work, including multi-select and context menus.
- [ ] Every menu/toolbar/context command resolves to the same command ID.
- [ ] Selection and active record are consistent across all related views.
- [ ] Filters, grouping, sorting, collapse and layout changes do not mutate source records.
- [ ] Data read is scoped by tenant/project/revision and permission.
- [ ] Writes use revision guard, validation, audit and readback.
- [ ] Save/reopen/refresh preserves the supported layout and record state.
- [ ] Failure/timeout/conflict is visible and recoverable; no fake success.
- [ ] Data and calculations are from the authoritative service/shared core.

### Evidence requirements
- [ ] Unit/component tests.
- [ ] API/application/repository tests where data behavior is involved.
- [ ] Browser test for each primary user journey and context-menu target.
- [ ] Screenshots of initial, selected, expanded, collapsed, dialog, error and responsive states.
- [ ] Evidence records exact branch, commit SHA, environment, viewport and test identifiers.
- [ ] Independent reviewer verifies the evidence against the requirement, not just CI green.

## 4. Mandatory cross-window scenario tests

| Scenario | Expected result |
|---|---|
| Open every top-level window from menu, directory and context action | Same canonical window tab is activated; no duplicate shell |
| Change project while several project windows are open | Data re-scopes safely; unsaved edits are guarded; global windows remain valid |
| Create WBS, child WBS and activities | All hierarchy links persist, render and re-open correctly |
| Collapse a WBS branch in Activities | Its rows and Gantt bars disappear together; records remain in the schedule snapshot |
| Filter Activities to a small subset | View changes only; schedule still includes every eligible project activity |
| Hide a row using columns, grouping or virtualization | No schedule input or export scope is silently altered |
| Create relationship in table, Gantt and Network | Same authoritative relationship appears in all views after readback |
| Edit activity progress | Details, table, Gantt, progress page and schedule results stay consistent after reload |
| Change calendar, Data Date or constraints | New calculation snapshot uses exact revision-bound inputs |
| Capture and assign baseline | Baseline values persist and render as a separate Gantt layer |
| Assign resources and run leveling | Demand, capacity, calendars, priorities and dates reconcile |
| Deny a permission | Command is disabled/denied honestly and no mutation occurs |
| Simulate stale revision | 409/conflict is shown and authoritative state is reloaded without dropping the competing write |
| Run bulk change/import | Preview is accurate; approval precedes writes; failure is atomic or explicitly partial by contract |
| Export and re-import | Data round-trips with field/unit/calendar mapping and no silent omission |
| Refresh browser or restart preview runtime | Saved records, layout, selection and history restore according to their persistence contract |

## 5. High-volume Activities and schedule inclusion tests

These cases are mandatory because a display/render limit must never become a calculation limit.

1. Create a fixture with 250 schedule-eligible activities distributed across at least four WBS levels and multiple branches.
2. Ensure some branches are expanded and others collapsed; scroll so some rows are outside the rendered viewport.
3. Apply a filter that shows fewer than 20 records; then clear it.
4. Run Schedule in each display state and compare:
   - source project revision;
   - persisted schedule-eligible activity count;
   - input snapshot activity count;
   - evaluator output activity count;
   - number of returned facts;
   - project finish, critical path and float facts.
5. The schedule snapshot and calculated result must be identical for the same project revision and schedule options regardless of current UI filter, WBS collapsed state, scroll position, selected rows or virtualized DOM range.
6. Include a hidden activity that is the only predecessor chain controlling project finish and prove that its impact is present in output.
7. Include an activity hidden by a display filter but on the critical path and prove it remains in the critical result.
8. Include inactive/What-If/template status cases as separate fixtures; compare their treatment against the exact Version 26 semantics. Do not infer that a hidden row is inactive or that an inactive status always means excluded.
9. If a true scope selector intentionally schedules only a subset, require an explicit named scope and preview count. Never infer calculation scope from the display filter.
10. Verify exports and reports similarly state current view, filtered selection or full-project scope.

**Pass condition:** no arbitrary constant such as 180, 200 or another UI-rendering threshold truncates the stored dataset, query scope, schedule snapshot or exported records. Rendering optimization may limit only the DOM currently materialized.

## 6. Build order and stop/go gates

| Phase | Build focus | Gate before proceeding |
|---|---|---|
| 0 | Single shell, menus, toolbars, tabs, command registry, shared context-menu mechanism | All global shell tests and one real window lifecycle pass |
| 1 | Activities as the reference window: full table, WBS grouping, Gantt, Details, Network, usage/Trace Logic, context menus | Every ACT requirement has status VERIFIED or an approved BLOCKED_EXTERNAL/NOT_APPLICABLE disposition |
| 2 | WBS and Projects | Full structure, details, hierarchy operations and context menus verified |
| 3 | Resource Assignments, Resources, Roles and Calendars | Dictionary and assignment workflows reconcile to shared data/calculation services |
| 4 | Schedule, Progress, Baselines, EVM and Tracking | Calculation/input/output evidence and workflow tests pass |
| 5 | Documents, Expenses/Cost Accounts/Budget, Issues, Thresholds and Risks | Window-specific records, details, commands and persistence pass |
| 6 | Reports, Administration, import/export, backup/recovery and tools | Real end-to-end journeys and access controls pass |
| 7 | CUBI additions and cross-platform shells | Shared domain contract remains consistent across web/desktop/mobile |

Do not start another broad surface by adding only menu icons while the current phase has foundational gaps. A phase can continue with explicitly tracked sub-work, but its window must not be called complete until the gate passes.

## 7. Current repository evidence to refresh

Existing documents indicate that earlier audits found missing/partial window tabs, menu commands, Activity Details, WBS charting, report/tracking windows, resource dictionaries and resizable layouts. These were written on different branches and audit dates; they are not a current pass/fail report for the baseline commit in this PR.

Before the first implementation PR:
1. Re-open the actual target branch and exact current HEAD.
2. Re-run the current application using the documented preview runtime.
3. Update the existing window inventory and web traceability matrix from the actual code and browser.
4. Record real routes, modules, command IDs, service contracts and test names against each ID in this matrix.
5. Replace every NOT_AUDITED only after evidence exists.
6. Do not merge a catalog item to VERIFIED because a PR exists, CI is green, a menu label is visible or the developer reports completion.

## 8. Final review report template

For each completed window, attach:
- Window key and exact commit SHA.
- Version 26 source sections and printed page references.
- Requirements IDs in scope and their final status.
- Implemented files/components/command IDs/services.
- Screenshot set and viewport metadata.
- Test commands and results.
- Known gaps and disabled commands with reasons.
- Reviewer findings and resolution.
- Confirmation that no CUBI branding or product-vendor references leaked into customer UI.
