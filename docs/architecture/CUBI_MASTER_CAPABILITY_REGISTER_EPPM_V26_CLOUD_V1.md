# CUBI Master Capability Register — EPPM V26 / Primavera Cloud / Environment Ownership

**Status:** Product-owner scope baseline; architecture register, not an implementation-completion claim.  
**Execution priority:** Engineering P1 (Qoder implementation); Enterprise P2 (architecture and delivery planning coordinated here); shared boundary prerequisites P0 only where required.  
**Applies to:** all existing parity work and all new capabilities across Engineering, Enterprise and Workbench.

## 1. Binding decisions

1. P6 EPPM Version 26 HTML Help is the primary parity authority for every capability. For capabilities absent from EPPM Help, Primavera Cloud HTML Help is the functional source for the new extension.
2. Where both contain related behavior, reconcile without duplicating menus, APIs, persistence, data ownership, workflows or calculations. P6 Team Member V26 Help is a separate normative contributor surface. P6 Professional V26 Help is supplementary only and cannot establish EPPM parity.
3. Engineering owns project execution truth: project/EPS/WBS, activities, relationships, CPM, calendars, baselines, project resource assignments/leveling, cost, progress, EVM, project risk calculations and schedule-linked field execution.
4. Enterprise owns organizational and cross-project truth: people, teams, memberships, entitlements, portfolio lifecycle, strategic prioritization, enterprise capacity, workflow definitions/approval evidence, external portal grants, integration governance and cross-project aggregation.
5. Workbench is a shared entry, navigation, personal action and notification projection. It owns no duplicate business records or calculations.
6. Engineering is P1; Enterprise is P2 and must not block or introduce release dependencies into Engineering. Existing independent Enterprise work may continue only without destabilizing P1 contracts.
7. No top-level menu for every Cloud app. Extend existing CUBI specialist contexts. No parallel shell, duplicate route, second schedule engine or competing edit surface.
8. No row is complete from a roadmap, mock, schema, API alone or stale CI. Progression is: discovered → source-traced → ownership decided → feasibility accepted → contract approved → implemented → exact-head tests/runtime evidence → released.
9. Do not alter Jalal 5 weights or earned progress without explicit evidence and approval. CUBI UI/help/branding remains CUBI-native; Oracle references are research sources only.

## 2. Required source crosswalk for every capability

Every implementation slice must record: exact P6 EPPM V26 HTML topic(s) and canonical URL or NOT PRESENT after searching TOC, relevant guide and applicable API/data dictionary; exact P6 Team Member V26 topic(s) or NOT APPLICABLE; exact Primavera Cloud HTML topic(s) and URL or NOT APPLICABLE; classification (EPPM parity, Cloud-origin extension, shared/reconciled, CUBI-native, open/source verification); behavior differences and chosen CUBI resolution; authoritative environment, record/calculation owner, menu/context placement, API and persistence boundary; dependencies, migrations, authorization, audit, concurrency/idempotency and negative-security tests; acceptance journeys and evidence tied to exact commit SHA. Unavailable/ambiguous references remain MISSING / VERIFY.

## 3. Master capability register

Status below is a planning disposition, not a claim of full implementation. Existing foundations must be re-audited at the actual implementation head before extension.

| ID | Capability / outcome | Owner / priority | Help crosswalk to complete | CUBI placement and single-owner rule | Feasibility / delivery direction | Current disposition |
|---|---|---|---|---|---|---|
| ENG-01 | Project, EPS, WBS and lifecycle | Engineering P1 | EPPM Projects/EPS/WBS; Cloud Scope/Project only for gaps | Engineering project directory; Enterprise reads governed portfolio summaries | Extend existing project/WBS services, no second project master | Foundation; full parity audit |
| ENG-02 | Activity Master, codes, steps, relationships, constraints | Engineering P1 | EPPM Activities/Details/Steps/Relationships/Constraints/Codes | Canonical Activities/Schedule workspace | Extend authoritative Activity APIs and scheduler inputs | Active parity work |
| ENG-03 | CPM, calendars, critical path, float, schedule publication | Engineering P1 | EPPM Scheduling/Calendars/Critical Path/Float; Cloud Schedule Management | Existing Schedule context and Shared Scheduling Core | One calculation engine; versioned runs; timezone and Jalali-Gregorian semantics | Strong foundation; edge parity remains |
| ENG-04 | Baselines, schedule comparison, what-if and scenario lifecycle | Engineering P1 | EPPM Baselines/Schedule/What-if where applicable; Cloud schedule scenarios/compare/merge | Schedule > Baselines / Scenarios / Compare | Immutable source snapshots/runs; guarded promotion; do not confuse portfolio what-if with project scenarios | Contract drafted; live service unproven |
| ENG-05 | Schedule health and diagnostics | Engineering P1 | EPPM schedule/constraint/float/report topics; Cloud Schedule Health Score | Schedule > Health/diagnostics | Explainable findings from authoritative schedule runs | Six-rule foundation reported; crosswalk/expansion |
| ENG-06 | Project resources, roles, assignments, rates, units, spreads, leveling | Engineering P1 | EPPM Resources/Roles/Assignments/Leveling; Cloud resource-loaded schedule | Project Resources and Activity > Assignments | Reuse assignment and leveling core; Enterprise does not recalculate project assignments | Existing foundation; parity in progress |
| ENG-07 | Project cost, expenses, budgets, actuals, progress and EVM | Engineering P1 | EPPM Costs/Expenses/Progress/Earned Value/Financial Periods | Project Cost & Progress | One authoritative project cost/progress/EVM calculation; Enterprise consumes snapshots | Existing foundation; verify workflows |
| ENG-08 | Project risk register, issues, responses and actions | Engineering P1 | EPPM Risks/Issues/Activity Risks/Thresholds; Cloud Risk Management | Project Risk area | Extend risk lifecycle and typed links to schedule/cost | Foundation; lifecycle gaps |
| ENG-09 | Quantitative risk / Monte Carlo / confidence and contingency | Engineering P1 | EPPM risk topics to verify; Cloud Risk Analysis prerequisites and Run Risk Analysis | Project Risk > Quantitative Analysis | New reproducible simulation from pinned schedule/cost; async immutable runs | Major new capability; feasibility required |
| ENG-10 | Field Work Plan / Last Planner: lookahead, weekly commitments, constraints, huddles, PPC | Engineering P1 | EPPM Activities/Progress/Steps/Constraints; Cloud Task Management Work Plan | Existing Field Operations / Field Assurance | Schedule-linked work packages; generic Enterprise tasks are not field commitments | Foundations; full workflow gap |
| ENG-11 | Activity-centric Team Member updates | Engineering P1 | Separate P6 Team Member Web Help V26 plus EPPM activity semantics | Activity Details > Team Update / assigned My Activities | Assigned activity scope, permitted fields, predecessor context, submit/withdraw/review | Distinct parity gap; not generic tasks |
| ENG-12 | Project timesheets and actual labor posting | Engineering data owner P1 | P6 Team Member timesheets and EPPM actual units/periods; Cloud Timesheets | Contributor My Work and Engineering Resources/Progress | One time-entry record; approved actuals post through Engineering APIs | Attendance is not timesheets parity |
| ENG-13 | Project documents and structured attachments | Engineering for engineering links P1 | EPPM Documents/Activity/WBS/Project attachments; Cloud docs where needed | Contextual project/WBS/activity/risk attachments | Engineering owns structured links; Enterprise governs external sharing/retention | Foundation; lifecycle verify |
| ENG-14 | Project layouts, filters, grouping, columns, print/export and reports | Engineering P1 | EPPM Activity Views/layouts/filters/reports/print/export/data dictionary | Canonical workspace and project Reports | Native complete workflows, saved layouts, formulas/columns and exports | High-priority workspace parity |
| ENT-01 | Organization, users, teams, memberships, OBS, roles, security profiles, audit | Enterprise P2; auth boundary P0 | EPPM Administration/OBS/Security Profiles/Privileges; Cloud Administration/Security | Enterprise > Organization & Access | One tenant authorization authority; immediate revocation across APIs | Partial; open PRs need exact-head verification |
| ENT-02 | Portfolio lifecycle, ideas/intake, strategy, prioritization, funding decisions | Enterprise P2 | EPPM Portfolios/Portfolio Analysis/Projects; Cloud Ideas/Portfolio Management | Enterprise > Portfolio & Executive | CRUD/lifecycle/scorecards/decisions; project calculations remain Engineering-owned | Read/decision foundation; lifecycle gap |
| ENT-03 | Enterprise resource pool, skills, qualifications, availability and capacity | Enterprise P2 | EPPM Resources/Roles/hierarchy; Cloud Portfolio Resource Planning | Organization & Access > Resources & Skills; Portfolio > Capacity | Enterprise owns workforce/capacity; Engineering owns project assignments/leveling | No complete central lifecycle proven |
| ENT-04 | Portfolio resource scenarios and cross-project allocation | Enterprise P2 | EPPM Portfolio/Resources/Approvals; Cloud Resource Planning Scenarios/Scenario Comparison | Portfolio detail > Resource Plan | Enterprise allocates envelopes; Engineering calculates project outcomes | Planned; depends on ENG-06/ENT-03 |
| ENT-05 | Portfolio risk appetite, exposure and cross-project escalation | Enterprise P2 | EPPM Portfolio/Risk/Threshold; Cloud Portfolio/Risk | Portfolio & Executive > Risk | Governance and roll-up only; consume Engineering snapshots | Governance gap |
| ENT-06 | Role-based dashboards, portlets and executive KPIs | Enterprise P2 | EPPM Dashboards/Portlets/Reports; Cloud dashboards only as extension | Enterprise Home > Dashboards | Configurable role/user layouts; authorized read models | Foundation; full designer unproven |
| ENT-07 | Generic organizational tasks and collaboration | Enterprise P2 | EPPM collaboration topics; Team Member is not equivalent; Cloud Task Management | Enterprise > Team & Task Center; Workbench inbox projection | Enterprise task owner; typed links to Engineering; never duplicate Activity/Field Plan | Task API/UI partial |
| ENT-08 | Workflow Studio, delegation, escalation, approvals and review history | Enterprise P2 | EPPM Approvals/Timesheet/Activity Status review; Cloud Workflow Design | Workflow Studio / Approvals; embedded requests in owner domain | Enterprise defines workflow; owning domain validates and commits mutations | Partial foundations |
| ENT-09 | Project Portal, external stakeholders, document grants and retention | Enterprise P2 | EPPM Project Information/Documents/security; Cloud document APIs | Enterprise > Project Portal | One document identity/access policy; Engineering retains structured attachments | Partial foundations |
| ENT-10 | Enterprise reports and cross-project analytics/publication | Enterprise P2 | EPPM Reports/Reporting Guide/schema; Cloud API/Data Services | Enterprise > Reports and portfolio dashboards | Governed read-only aggregation with units, currency, data date, source revision and freshness | Read-model foundation; full UX unproven |
| ENT-11 | Integration Hub, APIs, webhooks, import/export, credentials, replay, audit | Enterprise P2 | EPPM Integration/API/Import-Export guides; Cloud API/Integration/Data Services | Enterprise > Integration Hub / Operations & Jobs | Enterprise governs credentials/tenant scope/replay; adapters call owner APIs | Varying foundations; governance gap |
| ENT-12 | Benefits/value realization, PMO knowledge and strategic measures | Enterprise P2 | EPPM Portfolio/Project/Reports where present; Cloud Portfolio/Ideas; else CUBI-native | Portfolio & Executive > Benefits / Knowledge | Enterprise owns benefits; Engineering owns actual progress/cost/schedule | New CUBI-native/Cloud-informed feasibility |
| SH-01 | Workbench home, navigation, recent projects and environment switching | Workbench P0 | EPPM workspace/navigation; Cloud common navigation as comparative | One shared Workbench entry; specialist shells remain canonical | No business-data ownership; deep links only | Shell decision exists; verify single route |
| SH-02 | Personal inbox and notifications | Workbench projection P0 | EPPM notifications/approvals where present; Cloud workflow/task notifications | Workbench > My Work / Notifications | Project source-owned action state; Workbench projects typed links/unread state | Contract needed |
| SH-03 | Permission-filtered global search | Workbench P0 | EPPM search/navigation; Cloud search/API where documented | Workbench global search | Federated index; source rechecks access on open; no copied authoritative record | Feasibility required |
| SH-04 | Tenant, identity, entitlement, session and cross-environment authorization | Shared platform P0 | EPPM Administration/security; Cloud Administration/Security | Shared identity contract | Server-derived actor/tenant; fail-closed authorization and revocation | Partial foundations; security verification |
| SH-05 | Audit, event contracts, idempotency, concurrency and background jobs | Shared platform P0 | EPPM audit/security/integration; Cloud API/workflow/job semantics | Shared technical primitives; domain owns business events | Versioned contracts, optimistic revisions, idempotency and auditable jobs | Varying foundations |
| SH-06 | Multilingual UI, RTL/LTR, timezone and Jalali-Gregorian semantics | Shared platform P0 | EPPM calendar/date/time/locale; Cloud locale/timezone | Shared localization/date services | One date/time semantic contract; conversion provenance; full language matrix | FA/EN partial; other locales/tests remain |
| SH-07 | Storage, backups, retention and subscription entitlements | Shared platform P0 | EPPM Administration/data management; Cloud Administration/licensing; CUBI pricing rules | Account/tenant settings and project storage controls | Server backup/restore vs user export; enforce Free/Pro limits server-side | Decisions recorded; implementation verify |
| SH-08 | Offline-capable desktop/mobile core and synchronization | Shared core + Engineering data P1 | EPPM data/import/export/API semantics; Cloud mobile docs; CUBI-native requirement | Reusable core for web, Flutter and Windows | Web need not be offline; native clients need local persistence, conflict resolution, queued commands and deterministic calculations | Architecture/feasibility needed |
| SH-09 | Forms/Form Builder, organization library and project forms | Enterprise platform P2; domain owns submissions | EPPM UDF/forms/customization; Cloud forms/workflow | Shared Form Builder entry; org and project library scopes | Template/schema owner distinct from submitted domain record | Foundation; permissions/version/publish verify |
| SH-10 | Super-admin site content, branding assets and account administration | Enterprise platform P2 | EPPM Administration where analogous; otherwise CUBI-native | Restricted Super Admin console, separate from normal workspace | Dimension-validated asset/content replacement, audit and role-scoped controls | Requirements recorded; implementation verify |

## 4. No-duplication and cross-environment contract rules

- Engineering is authoritative for project, EPS/WBS, activity, relationship, calendar, baseline, CPM, project assignment/leveling, cost, progress, EVM, project risk calculations, field commitments and actuals.
- Enterprise is authoritative for organization/person/team/skills, memberships/entitlements, workflow definitions/approval evidence, portfolio lifecycle/strategy, enterprise capacity envelopes, external portal grants, integration credentials and enterprise aggregation.
- Workbench only projects inbox, notifications, navigation, recent projects and federated search. Every open/write is re-authorized by the source owner.
- Enterprise must never reimplement CPM, project leveling, EVM, project risk or Monte Carlo. It aggregates immutable Engineering results with source revision/model version/freshness metadata.
- Generic tasks, Engineering Field Work Plan commitments, Team Member assigned activities and timesheets remain distinct typed concepts.
- Cross-environment commands require server-derived tenant/actor, typed source reference, explicit scope, source revision, optimistic concurrency, idempotency, audit and stable forbidden/not-found/stale/conflict/unavailable errors.

## 5. Execution sequence

### Gate 0 — inventory and collision control (immediate)
1. Refresh main, every open PR head, changed paths, CI and active code ownership.
2. Inspect root and nested AGENTS.md in the canonical checkout; do not infer absence from a failed GitHub path lookup.
3. Complete dual-source topic crosswalk for every register row.
4. Compare the register with existing issues, active PRs, canonical workspace, Jalal 5 baseline and repository state. Deduplicate work.
5. Record owner, dependencies, acceptance criteria and executable Qoder handoff per row.

### P1 — Engineering (Qoder implementation)
A. Continue active EPPM V26 Activity/Schedule/Resource/Cost/Progress/Calendar parity without disrupting active PR ownership.  
B. Complete project resource, progress, cost and EVM workflows using existing core.  
C. Complete project risk lifecycle; separately feasibility-test Monte Carlo.  
D. Build schedule-linked Field Work Plan/Last Planner.  
E. Implement Team Member activity updates and timesheets against separate V26 Help.  
F. Implement scenario lifecycle after pinned source/run contract and scheduler collision review.  
G. Close project reporting/layout/print/export and documents gaps.  
Each slice must be coded, tested and evidenced on exact head.

### P2 — Enterprise (architecture and coordinated implementation)
A. Finish Organization & Access/security parity and immediate revocation.  
B. Complete Portfolio lifecycle, intake, scorecards, decisions and history.  
C. Build enterprise resource pool/skills/availability and portfolio capacity on Engineering demand contracts.  
D. Complete Workflow Studio/Approvals, dashboards/portlets and reports.  
E. Complete Project Portal/documents, Integration Hub/Operations and benefits/knowledge.  
F. Connect Workbench inbox/search/notifications after source event and authorization contracts stabilize.

### P0 — shared boundary prerequisites
Tenant/actor/auth, audit/idempotency/concurrency, source-revision metadata, locale/timezone/calendar semantics and permission-filtered navigation/search. Keep these minimal; do not use them as a reason for a global shell rewrite.

### Definition of done per row
Source crosswalk independently reviewed; ownership/no-duplication boundary explicit; feasibility covers code reuse, persistence/migration, API, UI placement, authorization, concurrency, offline implications and jobs; tests cover positive/negative authorization, tenant isolation, stale revisions, idempotency, persistence adapters, localization/RTL and browser journeys; runtime evidence tied to exact commit; release only after exact-head gates and product approval. A provider build-rate-limit is not a pass.

## 6. Canonical HTML Help source set

### P6 EPPM Version 26 — primary parity authority
- Help HTML TOC: https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm
- User Guides index: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/user.html
- All Guides index (Admin, API, import/export, integration, schema): https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/books.html
- What's New V26: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-wn26/index.html
- Team Member Web Help V26 TOC: https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/toc.htm

### Primavera Cloud — functional source for new capabilities absent from EPPM
- Documentation index: https://docs.oracle.com/cd/E80480_01/toc.htm
- User Guides index: https://docs.oracle.com/cd/E80480_01/87731.htm
- Help system: https://docs.oracle.com/cd/E80480_01/help/en/user/173189.htm
- Application Administration: https://docs.oracle.com/cd/E80480_01/English/admin/app_admin_guide/index.html
- API Documentation: https://docs.oracle.com/cd/E80480_01/87749.htm
- Ideas: https://docs.oracle.com/cd/E80480_01/English/user_guides/ideas_user_guide/index.html
- Portfolio Management: https://docs.oracle.com/cd/E80480_01/English/user_guides/portfolio_management_user_guide/index.html
- Risk Management: https://docs.oracle.com/cd/E80480_01/English/user_guides/risk_management_user_guide/index.html
- Schedule Management: https://docs.oracle.com/cd/E80480_01/English/user_guides/schedule_management_user_guide/index.html
- Scope Management: https://docs.oracle.com/cd/E80480_01/English/user_guides/scope_management_user_guide/index.html
- Task Management / Work Plan: https://docs.oracle.com/cd/E80480_01/English/user_guides/task_management_user_guide/index.html
- Timesheets: https://docs.oracle.com/cd/E80480_01/English/user_guides/timesheets_user_guide/index.html
- Workflow Design: https://docs.oracle.com/cd/E80480_01/English/user_guides/workflow_design_guide/index.html

Cloud topic URLs must be verified against the live HTML index at implementation time. P6 Professional V26 is supplementary only. Any unavailable topic remains MISSING / VERIFY.
