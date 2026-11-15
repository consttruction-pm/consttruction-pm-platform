# CUBI Primavera Cloud + P6 EPPM V26 — Implementation Feasibility, Priority, Navigation & Integration Blueprint

**Status:** Reviewed architecture and implementation blueprint; documentation only.
**Parent decision:** PR #1988 — capability ownership and environment boundaries.
**Baseline main SHA reviewed:** `376af9e2751ea1260ea3b4ed9be050eb1722afbf` (2026-11-15).
**Mandatory product priority:** Engineering = Priority 1; Enterprise = Priority 2. Enterprise must not block, slow, or introduce release dependencies into Engineering.
**Normative parity source:** Oracle Primavera P6 EPPM Help Version 26 English HTML and separate P6 Team Member Help Version 26 English HTML. Primavera Cloud Help is a comparative capability source, not a substitute for P6 EPPM parity.

## 1. Executive decision

Build one CUBI product with:
1. **Engineering** — authoritative project execution environment.
2. **Enterprise** — authoritative organization, governance and portfolio environment.
3. **Workbench** — shared entry and coordination experience, not a third business-data owner.

Do not copy every Primavera Cloud app into a new top-level CUBI menu. Integrate features into the existing specialist workspace and its contextual menus. The same record must never have two edit surfaces with separate persistence or calculations.

**Engineering-first delivery is a sequencing rule, not a transfer of Enterprise-owned features into Engineering.** Implement Engineering-owned capabilities first. Then implement Enterprise-owned capabilities using stable Engineering read contracts. Continue the already-active P6 EPPM V26 parity work in Engineering without waiting for Enterprise.

## 2. Source set — canonical HTML Help addresses

### 2.1 Oracle P6 EPPM Version 26 — normative parity set

- P6 EPPM V26 Help HTML table of contents: https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm
- P6 EPPM V26 User Guides index: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/user.html
- P6 EPPM V26 All Guides index (administration, user, import/export, integration and schema guides): https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/books.html
- P6 Team Member Web Help V26 HTML table of contents: https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/toc.htm
- P6 EPPM V26 What's New: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-wn26/index.html
- P6 EPPM V26 Data Dictionary / field reference is available from the User Guides index and must be used for field-level parity.
- P6 EPPM V26 REST/API, Integration API, XER/XLSX import/export and schema references are available from All Guides. Use the guide matching the exact exchange surface; do not infer semantics from UI labels.

Relevant P6 topic families to trace per feature:
- Activities, Activity Views, WBS, Gantt, relationships, constraints, float, critical path, resource leveling, baselines, scheduling, activity progress, steps, resources, roles, risks, issues, documents, expenses, earned value and milestones.
- Team Member assigned activities, activity status updates, steps, timesheets, submit/withdraw, approval and review.
- Dashboards and portlets, Portfolios/Portfolio Analysis, Projects/EPS, Resources, Approvals, Reports, Administration, security profiles, OBS and privileges.
- Reporting Guide / publication and reporting schema where reports need persisted and time-distributed values.

The current V26 Help parity contract already recorded in `docs/enterprise/CUBI_ENTERPRISE_PRIMAVERA_P6_EPPM_HELP_PARITY_V26.md` is controlling. This blueprint extends its placement and delivery plan; it does not replace it.

### 2.2 Oracle Primavera Cloud — comparative/extension HTML Help set

Canonical documentation index: https://docs.oracle.com/cd/E80480_01/toc.htm
User Guides index: https://docs.oracle.com/cd/E80480_01/87731.htm
Help system: https://docs.oracle.com/cd/E80480_01/help/en/user/173189.htm
Application Administration Guide: https://docs.oracle.com/cd/E80480_01/English/admin/app_admin_guide/index.html
Security Guide: https://docs.oracle.com/cd/E80480_01/English/admin/security_guide/index.html
API Documentation index: https://docs.oracle.com/cd/E80480_01/87749.htm
Integration Overview: https://docs.oracle.com/cd/E80480_01/English/Integration/overview/index.html
Data Service Reference Guide: https://docs.oracle.com/cd/E80480_01/English/Integration/data_service/index.html
Mobile app documentation is linked from the canonical documentation index.

Direct HTML guide entry points:
- Ideas: https://docs.oracle.com/cd/E80480_01/English/user_guides/ideas_user_guide/index.html
- Portfolio Management: https://docs.oracle.com/cd/E80480_01/English/user_guides/portfolio_management_user_guide/index.html
- Progress: https://docs.oracle.com/cd/E80480_01/English/user_guides/progress_user_guide/index.html
- Risk Management: https://docs.oracle.com/cd/E80480_01/English/user_guides/risk_management_user_guide/index.html
- Schedule Management: https://docs.oracle.com/cd/E80480_01/English/user_guides/schedule_management_user_guide/index.html
- Scope Management: https://docs.oracle.com/cd/E80480_01/English/user_guides/scope_management_user_guide/index.html
- Task Management: https://docs.oracle.com/cd/E80480_01/English/user_guides/task_management_user_guide/index.html
- Timesheets: https://docs.oracle.com/cd/E80480_01/English/user_guides/timesheets_user_guide/index.html
- Workflow Design: https://docs.oracle.com/cd/E80480_01/English/user_guides/workflow_design_guide/index.html

Important direct topics used for this feasibility:
- Schedule overview / what-if / baseline / histograms / leveling / Schedule Health Score: https://docs.oracle.com/cd/E80480_01/English/user_guides/schedule_management_user_guide/90786.htm
- Resource-loaded scheduling: https://docs.oracle.com/cd/E80480_01/English/user_guides/schedule_management_user_guide/221709.htm
- Risk process: https://docs.oracle.com/cd/E80480_01/English/user_guides/risk_management_user_guide/142216.htm
- Risk analysis prerequisites: https://docs.oracle.com/cd/E80480_01/English/user_guides/risk_management_user_guide/93538.htm
- Run risk analysis (Monte Carlo): https://docs.oracle.com/cd/E80480_01/English/user_guides/risk_management_user_guide/88298.htm
- Work Plan tasks, hand-offs, constraints, commitments and completion: https://docs.oracle.com/cd/E80480_01/English/user_guides/task_management_user_guide/102799.htm
- Portfolio resource planning: https://docs.oracle.com/cd/E80480_01/English/user_guides/portfolio_management_user_guide/109147.htm
- Resource planning scenarios: https://docs.oracle.com/cd/E80480_01/English/user_guides/portfolio_management_user_guide/109149.htm
- Scenario comparison: https://docs.oracle.com/cd/E80480_01/English/user_guides/portfolio_management_user_guide/86887.htm
- Timesheets guide: https://docs.oracle.com/cd/E80480_01/English/user_guides/timesheets_user_guide/index.html
- Workflow/forms: https://docs.oracle.com/cd/E80480_01/English/user_guides/workflow_design_guide/index.html
- Primavera Cloud licensing is feature/app dependent; use the license guide as a scope/packaging reference, not as a CUBI implementation requirement: https://docs.oracle.com/cd/E80480_01/English/admin/app_admin_guide/154358.htm

**Source handling:** Oracle HTML URLs and topic names must be checked again at implementation time. If Oracle moves a page, update the traceability record with the new canonical HTML topic. PDFs may help research but are not accepted as the normative implementation reference where the HTML topic exists.

## 3. What the repository currently proves — and what it does not

| Area | Evidence in reviewed main | Feasibility conclusion |
|---|---|---|
| Engineering schedule, CPM, WBS, activity, calendar and baseline foundations | Mature active implementation; V26 activity/calendar/WBS work and browser evidence visible in recent commits | Extend in place; do not create a second schedule engine or separate Cloud-style Schedule app |
| Project resources, cost, progress and EVM | Existing Engineering domain foundations | Reuse existing authoritative calculations; validate each feature's UI/API acceptance before parity claim |
| Project risk | Deterministic risk foundation exists; `risk_engine.py` is explicitly not a CPM solver or Monte Carlo simulation | Keep project risk in Engineering; Monte Carlo is a new calculation capability, not a relabelled score |
| Field Operations / Field Assurance | Existing roadmap and domain foundations | Extend into schedule-linked work planning; do not equate attendance/inspection with full Last Planner |
| Portfolio | `portfolio_query.py`, Stage 34.2.9 read model and Stage 34.2.10 approval boundary | Strong foundation only: Stage 34.2.9 explicitly excludes Portfolio CRUD and cross-project financial calculations; Stage 34.2.10 does not mutate projects |
| Enterprise Tasks | Task API and Task Center foundations | Generic tasks are not schedule activities, P6 Team Member or Timesheets |
| Organization/access | Tenant-scoped team/membership and audit foundation has started | Complete administration, role grants, resolver and revocation tests before enabling cross-environment assignment |
| Workflow, dashboards, Integration Hub, enterprise capacity | Plans/contracts/foundations vary | Feasibility and runtime proof required; do not call a planned item implemented |

**Important implementation caution:** the exact current Engineering menu and shell composition must be inspected at the target commit before a code change. This document specifies the target insertion points by existing domain context, not permission to replace `apps/web/src/main.ts`, change the global shell, or add duplicate routes blindly.

## 4. Capability ownership, priority and placement matrix

Priority:
- **P1 — Engineering first:** build or complete in the Engineering environment.
- **P2 — Enterprise second:** build after its source contracts and the P1 foundations it consumes are stable. Existing independent Enterprise foundations may continue only without blocking P1.
- **P0 — boundary prerequisite:** architecture/security contract needed before cross-environment integration; minimal, isolated, no shell refactor.

| Priority | Capability / user job | Owner | Exact proposed placement in host environment | Entry/access pattern | P6 EPPM V26 trace | Cloud reference / feasibility |
|---|---|---|---|---|---|---|
| P1 | Schedule What-if scenarios | Engineering | Existing project > Activities/Schedule workspace; add a contextual **Scenarios** tab beside current Schedule/Baselines, plus Schedule toolbar action | Project-scoped; create/duplicate/compare/retire scenario; scenario never changes live schedule until an explicit validated apply | Activities, Scheduling Projects, Baselines, Schedule Comparison | Cloud Schedule Guide 90786; feasible by extending existing schedule domain |
| P1 | Schedule comparison and health diagnostics | Engineering | Existing Schedule workspace > **Compare** and **Health** sub-tabs or right-side analysis panel; no new global top-level app | Pin source schedule revision and baseline; show explainable checks, trend and exceptions | Schedule, Baselines, Float, Critical Path, Resource Leveling | Cloud Schedule Overview; build on scheduler outputs, not a separate formula service |
| P1 | Project Risk Register and response lifecycle | Engineering | Existing project **Risk** area; add Register, Assessment, Response, Analysis, History tabs | Risk records linked to WBS/activity/cost/resource and project revision | Risks, Issues, Activity Risks, Documents, Earned Value as applicable | Cloud Risk process 142216; existing foundation; lifecycle gaps to close |
| P1 | Quantitative project risk / Monte Carlo | Engineering | Project > Risk > **Quantitative Analysis**; launch from risk register and schedule assurance; results as immutable analysis runs | Require current schedule run, data date, risk factors and uncertainty inputs; show P-values, finish/cost distributions, tornado/scatter, pre/post response | Risks, Scheduling, Activity Duration, Costs, Baselines, Reports | Cloud 93538 + 88298; major engineering complexity; async job and reproducible model required |
| P1 | Project resource-loaded plan and leveling | Engineering | Existing project > **Resources** area and Activity > Assignments detail; add Usage/Histogram/Leveling views inside existing resource context | Project resource assignments, units/costs, role/resource histograms and controlled leveling | Resources, Roles, Configuring Activity Resources, Resource Leveling | Cloud 221709; reuse existing assignment and scheduler authority |
| P1 | Field Work Plan / Last Planner | Engineering | Existing project **Field Operations** area; add **Work Plan** tab with weekly/lookahead board, daily huddle, constraints, handoffs, commitments, PPC and missed-reason analysis | Tasks must be typed and linked to project/WBS/activity; planning board can filter by crew, subcontractor, location and week | Activities, Activity Progress, Steps, Team Collaboration, Constraints, Resources | Cloud Task Guide 102799; build as schedule-linked field execution, not Enterprise generic Task |
| P1 | Activity-centric Team Member updates | Engineering | Existing Activity detail > **Team Update** panel and contributor **My Activities** view in Engineering/Workbench | Only assigned activity updates; permitted fields, step progress, predecessor context, submit/withdraw and review; scheduler owns resulting schedule mutation | Separate P6 Team Member V26 Help | P6 Team Member Help is normative; do not use generic Task API |
| P1 | Project time entry and actuals integration | Engineering domain owns project charging/actual-unit effect | Contributor My Work > Timesheets opens a dedicated time-entry experience; project manager can enter via project Resources/Progress context | One time-entry record; map to project/resource/activity/period; submit/approve then post actuals through Engineering domain | Team Member timesheets, actual units, timesheet approval and Application Settings | Cloud Timesheets guide; implement only after project assignment and period semantics are validated |
| P2 | Role-based dashboards and portlets | Enterprise | Enterprise Home > **Dashboards**; dashboard designer in Enterprise > Configuration > Dashboards | Cards/portlets consume authorized Engineering snapshots and Enterprise data; role/user layouts | Dashboards, Portlets, Reports | Cloud licensing docs note app/feature availability; reuse existing reporting/read models |
| P2 | Portfolio lifecycle, intake and analysis | Enterprise | Enterprise > **Portfolio & Executive** > Portfolios; portfolio detail tabs: Overview, Projects, Scorecards, Strategy, Risks, Decisions, Scenarios, History | Portfolio CRUD, membership, intake, strategic criteria, weighted score, compare and human-approved decisions | Portfolios, Portfolio Analysis, Projects/EPS, Resources | Cloud Portfolio guide 109147 / scenario comparison 86887; CRUD/lifecycle absent from current read-model stage |
| P2 | Enterprise resource pool, skills and availability | Enterprise | Enterprise > **Organization & Access** > Resources & Skills; separate **Capacity Planning** workspace under Portfolio & Executive | Central person/role/skill/qualification/location/availability; versioned time-phased capacity; read Engineering demand | Resources, Roles, resource hierarchy, assignments, OBS/security | Cloud Portfolio 109147; Enterprise owns capacity policy, Engineering owns assignment math |
| P2 | Portfolio resource scenarios and prioritization | Enterprise | Portfolio detail > **Resource Plan** tab; scenario compare/review/propose/approve lifecycle | Demand from Engineering, scenario assumptions, time-phased role capacity, budget/priority optimization and approval; committed allocation returned to Engineering | Portfolios, Resources, Portfolio Analysis, Approvals | Cloud 109149 / 86887; existing Stage 34.2.9/10 are foundations, not this full feature |
| P2 | Enterprise generic tasks and collaboration | Enterprise | Enterprise > **Team & Task Center**; also global Workbench > My Work | Cross-project organizational tasks, decisions, requests and follow-up; typed links to Engineering records | P6 Team Member is separate; use P6 task/communication topics only where relevant | Cloud Task Guide is comparative; do not duplicate Field Work Plan |
| P2 | Workflow Studio and Approval Center | Enterprise | Enterprise > **Workflow Studio** for definitions; Enterprise > **Approvals** for inbox/history; embedded request buttons in owning domain | Definition and approval policy in Enterprise; owning domain validates revision and executes final mutation | Approvals, Timesheets, Activity Status Review, Administration/security | Cloud Workflow Design guide; separate approval evidence from domain mutation |
| P2 | Enterprise reporting, documents and portal | Enterprise | Enterprise > **Project Portal** and **Reports**; Portfolio dashboards deep-link to project owner views | External stakeholder access, document grants, reports and portfolio rollups; Engineering retains structured attachments/technical records | Reports, Documents, Project information, security | P6 Reporting Guide and Cloud APIs/Data Services |
| P2 | Ideas and strategic intake | Enterprise | Portfolio & Executive > **Ideas & Intake**; convert approved idea into project proposal through controlled lifecycle | Ideas are not projects until approval; project creation delegates to project/portfolio owner service | Portfolio/project lifecycle, custom fields, workflow | Cloud Ideas Guide; verify user need and product fit before build |
| P2 | Scope / work packages | Engineering for project execution scope; Enterprise for cross-project scope intake/governance | Engineering Project > **Scope & Work Packages**; Enterprise Portfolio > Scope Summary read view | One authoritative project scope item; Enterprise aggregates, never edits a duplicate | WBS, Activities, Documents, Issues, Project controls | Cloud Scope guide; detailed parity/feasibility required |
| P0/P2 | Shared identity, grants and cross-environment reference resolver | Enterprise identity/access service; enforced by every domain API | No user-facing duplicate menu; exposed through session, permission and deep-link services | Tenant, actor, role, project grant, resource membership and object permission checked server-side on every request | Administration, OBS, security profiles, Team Member access | Cloud Security + P6 Application Administration |
| P0/P2 | Shared notifications, jobs and integration contracts | Platform service; Enterprise governance, owner-domain adapters | Workbench Notifications; Enterprise Integration Hub / Operations & Jobs | Outbox/event, idempotent consumer, source revision, retry/dead-letter and audit | Reports, Admin, Integration and service docs | Cloud API/Data Services and integration docs |

## 5. Engineering menu integration — avoid collision and preserve its unified workspace

Engineering is already a cohesive, specialist interface. Do **not** add a new top-level navigation item for every Cloud app, and do not create a second schedule/risk/resource shell.

Use the existing project context and existing module entry points:

### 5.1 Project-level contextual map

- **Activities / Schedule** (existing): retain current list, Gantt, filters, columns, WBS and detail tabs. Add Scenarios, Compare and Health as tabs/actions within this context. The current Activity window must remain the authoritative editor for activities and relationships.
- **Resources** (existing): retain resource dictionary, roles, assignments and rates. Add project Usage/Histogram/Leveling views here. Enterprise capacity is only surfaced as a read-only allocation envelope or link; do not add enterprise portfolio scenario editing here.
- **Risk** (existing or current project risk entry): add Register, Assessment, Response, Quantitative Analysis and History within the same project risk context. Risk analysis runs must capture schedule revision, data date, calendar set, cost model version and simulation settings.
- **Field Operations** (existing): add Work Plan, Lookahead, Constraints, Daily Huddle, Commitments and PPC as tabs in the current field module. Field cards reference schedule activities; they do not create shadow activities.
- **Progress / Cost** (existing): timesheet approvals and actuals may be reviewed here, but time-entry record creation remains a single contributor workflow, not a second form hidden in each module.
- **Activity detail** (existing): add a Team Update panel for the P6 Team Member-like activity status workflow. Do not put this in generic Enterprise Task Center.

### 5.2 Keep the top-level Engineering menu stable

Only add a top-level entry if a user research and route audit proves the capability cannot be discovered contextually. Preferred structure is:
- Projects / project selector
- Activities / Schedule
- WBS
- Resources
- Cost & Progress
- Risk
- Field Operations
- Reports / existing tools

Do not add separate top-level entries named What-if, Monte Carlo, Last Planner, Weekly Plan, Team Member, PPC, Histograms or Schedule Health. These are sub-capabilities of existing project modules.

### 5.3 Reuse existing UI primitives

Before adding a component, inspect current Engineering implementations for:
- tabs, split panels, data grids, filters, saved views and context menus;
- Gantt/activity detail and toolbar action patterns;
- modal/dialog lifecycle, confirmation, validation and unsaved-change guards;
- project context selector and route state;
- calendar/date/locale utilities, Jalali display and canonical ISO storage;
- permissions/disabled states and error/conflict banners;
- current browser E2E harness and screenshot evidence.

Do not replace an existing grid, Gantt, shell, calendar, or navigation framework merely to make the new feature look like Primavera Cloud. Extend the current host patterns and prove no regressions.

## 6. Enterprise menu integration — preserve a distinct organizational workspace

Enterprise remains its own specialist environment, not a clone of Engineering.

Proposed navigation:
1. **Home & Dashboards**
2. **Organization & Access** — People, Teams, Memberships, Roles, Skills, Entitlements, Audit
3. **Team & Task Center** — generic organizational tasks, collaboration and cross-project actions
4. **Portfolio & Executive** — Portfolios, Ideas & Intake, Scorecards, Resource Plans, Decisions, Benefits
5. **Workflow Studio**
6. **Approvals**
7. **Project Portal & Documents**
8. **Reports**
9. **Integration Hub**
10. **Operations & Jobs**
11. **Administration**

Project Portal is a cross-environment bridge: it displays project metadata and approved summaries, but activity/WBS/schedule mutations open Engineering. Enterprise must not expose a second editor for Engineering-owned objects.

## 7. End-to-end user journeys — one product, one source of truth

### Journey A — portfolio selection and resource commitment
1. Portfolio manager opens Enterprise > Portfolio & Executive > Resource Plans.
2. Enterprise loads approved project demand snapshots from Engineering, including project id, source revision, role, time bucket, units, currency and data date.
3. Enterprise creates one or more portfolio scenarios, selects projects, compares constraints, strategic score and budget.
4. Scenario goes through review/proposal/approval. Decision boundary stores approver, evidence, snapshot revision and decision.
5. After approval, Enterprise publishes a versioned allocation envelope to each affected project.
6. Engineering validates current project revision, role/resource mapping and capacity; project manager accepts/commits assignment in Engineering.
7. Engineering calculates project assignments/leveling. Enterprise refreshes its portfolio snapshot and shows committed vs requested vs stale allocations.
8. If the source revision changed or permission was revoked, the apply step fails closed and requires refresh/re-approval.

### Journey B — schedule scenario and risk simulation
1. Scheduler opens Engineering > Project > Activities/Schedule > Scenarios.
2. Creates a fork from a named schedule revision and records scenario assumptions.
3. Runs scheduler against the fork; baseline and live schedule remain unchanged.
4. Opens Compare/Health to review date, float, critical path, resource and health changes.
5. Opens Risk > Quantitative Analysis; selects risk factors, activity uncertainty, weather impacts, cost settings and simulation profile.
6. A tracked background job runs Monte Carlo against the pinned scenario revision; result is immutable and records engine/model version, seed, iterations and input hashes.
7. User compares pre-response/post-response outcomes; only a separate explicit approved command can apply a selected schedule change to live project state.
8. Enterprise consumes a risk/health snapshot for portfolio reporting, never recalculates CPM or Monte Carlo.

### Journey C — weekly field work and PPC
1. Superintendent opens Engineering > Field Operations > Work Plan.
2. Chooses week and crew/subcontractor; imports or links candidate work from scheduled activities/WBS.
3. Adds hand-offs and constraints, assigns responsible team and records readiness.
4. Daily huddle records commitment/recommitment; completed tasks update field progress and, subject to rules, propose activity progress.
5. Scheduler reviews/accepts the activity update in Engineering; schedule recalculates under the project settings.
6. PPC and missed-commitment reason analysis derive from committed tasks and verified completion states.
7. Enterprise can show company-level rollups and escalations but cannot create a parallel copy of a field task or mutate schedule progress.

### Journey D — contributor timesheet
1. Contributor enters Workbench > My Work > Timesheets (single entry point).
2. Selects period and authorized project/activity/resource assignments.
3. System validates assignment, calendar, period, actual units, duplicate time and submission rules.
4. Submit creates a revisioned timesheet; Enterprise Approval Center may route approval according to organizational policy.
5. Approved command returns to Engineering actuals service, which applies actual units and recalculates dependent project data according to P6 semantics.
6. Rejected/withdrawn/stale submissions do not silently alter actuals. Audit records submitter, approver, period, activity and posted revision.

### Journey E — generic Enterprise task linked to Engineering
1. A PMO manager creates a cross-project follow-up in Enterprise Task Center.
2. Task stores typed link to Engineering activity/project and the source revision, not copied activity fields.
3. Opening the link navigates to Engineering. Engineering checks current actor and project access.
4. Task completion remains Enterprise-owned; activity status remains Engineering-owned.
5. No task permission can grant activity access.

## 8. Integration contracts and anti-conflict rules

### 8.1 Single-writer ownership
- Project schedule/CPM/activity/WBS/calendar/baseline/scenario calculations: Engineering only.
- Project resource assignments, cost, progress, EVM, project risk and quantitative simulation: Engineering only.
- Portfolio lifecycle, strategic score, enterprise capacity policy, workflow definitions, approvals evidence and organization membership: Enterprise only.
- Workbench: no authoritative business writes except personal preferences/read state where explicitly defined.

### 8.2 Typed references and read models
Every cross-environment reference carries:
- tenant id and actor derived from authenticated server context;
- source environment, domain, object type, opaque object id;
- source revision / ETag and timestamp;
- data date, calendar, unit/currency and model version where relevant;
- allowed operation scopes, purpose and freshness/expiry;
- idempotency key for commands;
- audit correlation id.

A link/reference is not a grant. Target domain re-authorizes every open/read/write. Read models are snapshots, not source-of-truth stores.

### 8.3 Avoid domain duplication and circular dependencies
- Enterprise may depend on published Engineering contracts, not import Engineering internal modules.
- Engineering may consume Enterprise-issued identity, grants and approved allocation envelopes through stable contracts, not query Enterprise tables directly.
- No circular imports, cross-database joins, shared ORM entities or synchronous UI-to-UI coupling.
- Use API/application-service boundaries and event/outbox delivery for long-running or cross-service operations.
- Never recompute CPM, EVM, resource leveling or Monte Carlo in Enterprise dashboards.
- No two systems independently transition the same timesheet, task, risk or approval state.

### 8.4 Conflict and stale-data behavior
- Use optimistic concurrency (expected revision) on every mutation.
- Show source age and revision in portfolio snapshots.
- Reject stale allocation application, schedule update or approval with a conflict state; refresh and re-evaluate.
- Idempotent retries must return the original result, not create duplicate tasks, postings or decisions.
- Use transactional outbox/inbox and dead-letter observability for asynchronous events.
- Immediate membership/role revocation must invalidate access across both environments.
- Never resolve conflicts with silent last-write-wins for schedule, actuals, timesheets, approvals or allocations.

## 9. Feasibility, complexity and risk

Effort estimates are relative T-shirt sizing for planning, not commitments. Actual sizing requires code-level discovery and acceptance decomposition.

| Capability | Owner | Feasibility | Relative effort | Main risk / dependency | Gate |
|---|---|---|---|---|---|
| Schedule scenarios / compare / health | Engineering | High–Medium | L–XL | scheduler fork isolation, immutable revision, large project performance | no live schedule mutation until explicit apply; compare regression |
| Project risk lifecycle | Engineering | High | M–L | links to schedule/cost and risk taxonomy | full risk register/response audit |
| Monte Carlo | Engineering | Medium | XL | statistical model validation, runtime cost, deterministic reproducibility, schedule engine integration | independent model tests, benchmarks and P50/P80/P90 accuracy |
| Project resource histograms/leveling | Engineering | High–Medium | L | existing resource engine semantics and calendar consistency | no duplicate assignment engine |
| Last Planner / Work Plan / PPC | Engineering | Medium–High | L–XL | typed task vs activity distinction, crew membership, mobile/field usability | full weekly-to-daily E2E and PPC audit |
| Activity Team Member updates | Engineering | High–Medium | L | permitted fields, schedule status semantics, reviewer and out-of-sequence rules | separate P6 Team Member traceability |
| Timesheets / actual posting | Engineering + Enterprise workflow | Medium | XL | periods, labor/resource mapping, approval and financial posting semantics | end-to-end duplicate/stale/withdraw/approve tests |
| Enterprise portfolio CRUD and dashboards | Enterprise | High–Medium | L | tenant scope, portfolio lifecycle, reporting permissions | portfolio persistence + role-filtered UI |
| Enterprise capacity and portfolio scenarios | Enterprise | Medium | XL | cross-project role demand, time-phased capacity, optimization, negotiations | source revision and approval/commit lifecycle |
| Workflow Studio / Approval Center | Enterprise | Medium–High | L–XL | generic workflow vs domain-specific state transition | owning-domain mutation adapter and audit |
| Ideas / Scope / Benefits | Enterprise + Engineering scope owner | Medium | M–L each | product boundary and duplicate project objects | feasibility spike and explicit scope decision |
| Integration Hub | Enterprise | High for first-party contracts | L | credential security, replay, retries, observability | tenant-scoped secret and event security tests |

Complexity rating is not implementation authorization. No estimate is a promise of schedule or staffing.

## 10. Delivery sequence — enforce Engineering Priority 1, Enterprise Priority 2

### P0 — architecture guardrails (small, isolated, parallel only if no P1 contention)
- Freeze the domain ownership map and typed cross-environment reference contract.
- Confirm exact current routes, shell composition, data contracts, authorization and active PR collisions.
- Add no shared shell or database migration in this phase.
- Maintain current Engineering work queue and regression suite.

### P1-A — Engineering foundation and no-regression
- Finish in-flight P6 EPPM V26 Engineering work (Activity, WBS, calendars, relationships, schedule checks, resource/cost/progress semantics).
- Establish immutable project/schedule revision snapshots required by scenarios and risk.
- Verify existing resource, progress, risk and field operations services before extending them.
- Maintain exact-head test/browser evidence; no Enterprise dependency.

### P1-B — Engineering high-value Cloud gaps
1. Schedule Scenarios + Compare (first, because it reuses the current scheduler and schedule UI).
2. Schedule Health diagnostics (after stable calculation outputs).
3. Project Risk Register lifecycle and response actions.
4. Project resource histograms/usage/leveling improvements.
5. Field Work Plan / Lookahead / constraints / hand-offs / commitments / PPC.
6. Activity-centric Team Member status/steps workflow.
7. Quantitative Monte Carlo after the schedule revision and risk model are stable.
8. Timesheets and actual posting after activity/resource/period and approval contracts are proven.

P1 feature order may be adjusted by dependencies, but no Enterprise extension should delay active Engineering V26 acceptance work.

### P2-A — Enterprise EPPM baseline
Deliver the mandatory P6 EPPM V26 Enterprise functional baseline in the already-established order:
1. Dashboards and portlets.
2. Portfolio management.
3. Project overview and EPS / Project Portal.
4. Resource administration and enterprise capacity views (read Engineering-owned project assignments).
5. Team Member / activity status / approval integrations (not generic-task substitution).
6. Risk and issue portfolio views (read Engineering-owned project risk).
7. Reports and performance status.
8. Administration, organization, roles and security.
9. Documents and project information.

Use `docs/enterprise/CUBI_ENTERPRISE_PRIMAVERA_P6_EPPM_HELP_PARITY_V26.md` as the acceptance source. Do not mark a row done from a route, model, API schema or mock alone.

### P2-B — Enterprise Cloud extensions
1. Portfolio intake / Ideas and lifecycle.
2. Enterprise resource pool, skills, qualifications and availability.
3. Portfolio resource planning scenarios, comparison and optimization.
4. Portfolio risk appetite, cross-project exposure and strategic prioritization.
5. Workflow Studio, Approval Center and delegations.
6. Enterprise dashboards, portlets, reports and stakeholder portal.
7. Integration Hub and operations.
8. Benefits/value realization and PMO knowledge if product value is validated.

### P3 — integrated product experience
- Workbench global search, My Work, notifications and deep links.
- Cross-environment action inbox with typed references and permission checks.
- Unified terminology, breadcrumb, user identity and help discovery.
- Visual convergence only after representative screens pass RTL/LTR, accessibility, responsive and regression checks.

## 11. Test and acceptance plan

Every feature must have a trace row:
`Oracle HTML topic → user goal → CUBI host menu and route → owning domain → API/contract → persistence → permission → audit → test → runtime evidence`.

Mandatory test dimensions:
- unit/domain calculations and boundary values;
- API schema, authentication, tenant isolation, project grants and immediate revocation;
- PostgreSQL round-trip, migration forward/backward safety and concurrent revision conflict;
- idempotency/retry and transactional atomicity;
- schedule determinism, calendar/date/timezone and Jalali display with canonical ISO storage;
- scenario fork isolation and no mutation of live schedule;
- Monte Carlo distribution sanity, seeded reproducibility, statistical validation and performance limits;
- resource capacity/time-bucket/unit/currency correctness;
- timesheet duplicate, withdraw, rejection, approval and posting semantics;
- Work Plan task-to-activity identity and PPC formula traceability;
- keyboard, responsive, RTL Persian and LTR English;
- browser E2E for complete journeys, not just component rendering;
- exact candidate SHA, screenshots, API traces, logs and zero unexpected 5xx/console errors.

No production deployment or main merge is authorized by this blueprint.

## 12. Engineering UI collision assessment and mitigations

Potential collisions and required prevention:
1. **Duplicate top-level apps:** avoid by contextual sub-tabs in Activities, Resources, Risk and Field Operations.
2. **Activity vs Task identity:** separate typed objects and APIs; Field Work Plan tasks may reference but never replace Activities.
3. **Scenario vs live schedule:** immutable fork and explicit apply command with revision guard.
4. **Risk score vs Monte Carlo:** label deterministic indicator separately from probabilistic simulation; never imply current risk engine is Monte Carlo.
5. **Project resources vs enterprise capacity:** Engineering owns assignment calculation; Enterprise owns cross-project capacity and allocation policy.
6. **Timesheet vs attendance/timecard:** time entry must post to project/resource/activity and period; attendance is not automatically billable/project actual time.
7. **Approval vs mutation:** Enterprise approval records authorization/evidence; owning domain executes mutation.
8. **Shared shell regression:** no route or global navigation refactor in P1; integrate through current module context.
9. **RTL and dense grids:** reuse current table/Gantt conventions and test Persian RTL; do not fork date or number storage semantics.
10. **Performance:** long-running simulations and portfolio optimizations run as jobs with progress, cancellation, resource limits and immutable results.

## 13. Explicit implementation gates

Before a code PR:
- re-read latest main SHA and open PRs; do not rely on the baseline SHA in this document;
- identify the current UI route/menu and owner service from code, not assumptions;
- verify no active Engineering agent owns the same files;
- define the smallest feature slice and its V26/Cloud source topics;
- define data contract, migration, authorization and audit behavior;
- add negative tests and runtime acceptance;
- keep Enterprise work isolated from Engineering release paths.

A feature is **Implemented & Verified** only after exact-head tests and real persistence/runtime evidence. Other states must be explicit: Partial, Backend Only, UI Missing, Planned, Missing, Not Applicable.

## 14. Related CUBI source documents

- `docs/enterprise/CUBI_ENTERPRISE_PRIMAVERA_P6_EPPM_HELP_PARITY_V26.md`
- `docs/enterprise/CUBI_ENTERPRISE_FOUNDATION_V1.md`
- `docs/enterprise/CUBI_ENTERPRISE_IMPLEMENTATION_PLAN.md`
- `docs/architecture/CUBI_PRIMAVERA_CLOUD_CAPABILITY_GAP_AND_ENVIRONMENT_OWNERSHIP_V1.md`
- `docs/roadmap/STAGE_34_2_9_PORTFOLIO_CONTROL_READ_MODEL.md`
- `docs/roadmap/STAGE_34_2_10_PORTFOLIO_DECISION_BOUNDARY.md`
- `docs/architecture/P6_26_4_PARITY_AND_NO_OMISSION.md`
- `docs/workspace/architecture/v26-traceability-and-acceptance-matrix.md`

## 15. Final architecture rule

**Engineering first for project execution depth; Enterprise second for organization and portfolio breadth; Workbench for unified access.** The product is integrated by shared identity, typed references, revision-aware contracts, notifications and navigation—not by duplicating screens, calculations, records or databases. Preserve the existing Engineering interface and add each capability where the user already performs that kind of work.
