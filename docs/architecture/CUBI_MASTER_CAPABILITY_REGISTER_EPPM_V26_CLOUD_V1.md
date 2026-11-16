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



## 2A. Mandatory Cloud Help UI/visual parity and Professional non-interference gate (binding)

This gate applies to **every Cloud-origin or Cloud-informed user-facing capability**, including existing and newly proposed capabilities. A feature is not accepted merely because its data model, API, calculation or basic screen exists.

### A. Source-first visual and interaction inventory

Before implementation, inspect the exact feature-specific Primavera Cloud HTML Help topics (not only the general TOC or guide landing page). Record each canonical topic URL, Help revision/version, prerequisites, roles/privileges, workflow states and every user-visible surface. Extract a complete inventory of:

- every page, workspace, panel, tab, subtab, dialog, wizard, popover, context menu, toolbar/menu item, empty/error/loading state and navigation/return path;
- visual hierarchy, layout, spacing, alignment, density, field order, labels, icon meaning/shape, button type/state, badges, status indicators, colors and semantic color rules;
- every form field, control type, default, required/optional rule, validation, read-only/disabled/hidden condition, dependent field, value format, unit, date/time behavior and save/cancel/reset behavior;
- every user-selectable option, dropdown value, toggle, checkbox, radio group, multi-select, filter, grouping, sort, view/layout setting, personalization choice, permission-dependent choice and its default/impact;
- every chart and graph type, series, axes, scales, legends, labels, units, thresholds, colors, markers, tooltips, drill-through, zoom/filter behavior and export/print form;
- every report, table, grid and list: columns, order, widths, row height, grouping bands, totals/subtotals, sorting/filtering, pagination/virtualization, selection, row actions, export/print and empty/overflow behavior;
- sizing and responsive behavior: page/dialog/panel dimensions, split ratios, min/max sizes, resize behavior, scroll regions, density and supported viewport breakpoints;
- interaction semantics and state transitions, including create/edit/duplicate/open/close/submit/approve/reject/reopen/archive/delete, undo/cancel, confirmation and failure handling.

If Help screenshots or diagrams are available, preserve them as source evidence and record the corresponding Help topic/page. Where Help is silent on a visual detail, mark it **NOT SPECIFIED** and verify through the official Cloud application/reference evidence; do not invent a purported Help rule.

### B. CUBI implementation parity requirement

Implement the complete documented functional and visual behavior for the Cloud-derived scope, not a reduced mock. Reproduce the information architecture, control inventory, form semantics, table/report/chart configuration, selectable options, state transitions and meaningful visual language faithfully. Translate labels and use CUBI's approved identity (Deep Navy / Engineering Blue / Copper Orange / Brushed Titanium; Inter + Vazirmatn); do **not** copy Oracle/Primavera names, logos, proprietary branding or external product chrome into CUBI. A CUBI skin is allowed; omission or simplification of documented controls, chart/report content, form fields, choices or workflows is not.

For each slice attach: source-to-CUBI component mapping; source screenshots/Help references; CUBI screenshots at equivalent states; field/option inventory; chart/report/table schema mapping; visual-diff review; interaction/browser tests; and exact tested commit SHA. Test all supported CUBI locales and RTL/LTR where the surface is localized. Any documented item not implemented must be listed as an explicit gap and blocks claiming full parity.

### C. Mandatory P6 Professional V26 and EPPM collision audit

Before designing or merging a Cloud-derived feature, search the full applicable **P6 Professional V26 HTML Help** (including the supplied 815-page reference only as supplementary desktop evidence) and **P6 EPPM V26 HTML Help**, plus Team Member Help where contributor behavior is involved. Compare semantics, UI surfaces, icons, forms, fields, options, charts, reports, tables, permissions, lifecycle, calculations, keyboard/context-menu actions and data ownership. Record exact topic URLs or **NOT PRESENT after TOC + guide search** for each source.

Classify every behavior as (1) existing Professional/EPPM parity, (2) genuinely Cloud-origin extension, (3) shared behavior requiring one reconciled implementation, or (4) CUBI-native. If Professional/EPPM already provides the behavior, CUBI must implement/complete it in the existing canonical Engineering/Enterprise context; do not create a second Cloud-looking menu, window, route, form, table, report, calculation engine or record store. Where Cloud has extra fields/options/workflow, extend the single existing CUBI capability with clearly scoped additions and preserve backward compatibility. Never let a Cloud extension change the established Professional V26-aligned Activity/Schedule behavior or duplicate its controls.

### D. Release gate / evidence

A Cloud-derived slice is **NOT ACCEPTED** until the PR contains: exact Cloud Help topic crosswalk; exact Professional V26 + EPPM V26 overlap matrix; source-to-CUBI visual inventory; screenshot comparison for all major states; complete forms/options/chart/report/table inventory; responsive sizing evidence; interaction and permission tests; duplicate-route/menu/data-owner scan; regression evidence proving existing Professional V26-aligned workflows remain unchanged; and exact-head CI plus a fresh Vercel Preview for the same SHA. Stale previews, API-only tests or a green build alone do not satisfy this gate. If a source or environment cannot be inspected, mark **MISSING / VERIFY** and keep the feature blocked from full-parity acceptance.

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


## 7. Initial topic-level source crosswalk — verified HTML pages (2026-11-15)

This is the first source-verified tranche, not yet the complete crosswalk for every row. These pages were retrieved from the official HTML Help domains. Where a topic family is listed but its exact page is not yet confirmed, the full TOC remains the index and the row stays OPEN for topic-level verification.

| Register rows | P6 EPPM V26 HTML evidence | Primavera Cloud HTML evidence | Disposition / implementation consequence |
|---|---|---|---|
| ENG-02, ENG-03, ENG-06, ENG-07, ENG-14 | Activities section TOC: https://docs.oracle.com/cd/G48897_01/p6help/en/44475.htm. It explicitly lists Activity Views, Activity Codes, Gantt Charts, WBS, Baselines, Scheduling Projects, Float, Critical Path Activities, Resource Leveling, Activity Progress, Resources, Roles, Documents, Expenses, Constraints, Relationships, Risks, Steps, Budgets and Earned Value. | Cloud Schedule Management guide index and overview: https://docs.oracle.com/cd/E80480_01/English/user_guides/schedule_management_user_guide/90786.htm | Shared parity family: retain the existing Engineering schedule/activity/resource/cost authorities; Cloud-only extensions must not create another schedule engine. |
| ENG-03 | Scheduling Projects: https://docs.oracle.com/cd/G48897_01/p6help/en/7878.htm | Schedule Scenarios Overview: https://docs.oracle.com/cd/E80480_01/English/user_guides/schedule_management_user_guide/107323.htm | EPPM scheduling is baseline behavior. Cloud scenario lifecycle is a distinct extension and must be isolated from the current schedule until guarded promotion. |
| ENG-04 | EPPM Activities TOC includes About Baselines and About Scheduling Projects; EPPM global TOC includes Portfolio Views > About What-if Analysis. The latter is not proof of project schedule scenario lifecycle. | Schedule Scenarios Overview: https://docs.oracle.com/cd/E80480_01/English/user_guides/schedule_management_user_guide/107323.htm; Manage a Scenario: https://docs.oracle.com/cd/E80480_01/English/user_guides/schedule_management_user_guide/107330.htm | Cloud-origin project schedule scenario extension. Verify add/duplicate/close/retire/source/current-schedule semantics and immutable CUBI provenance before implementation. |
| ENG-05 | EPPM Activities TOC includes constraints, float, critical path and scheduling; exact combined schedule-health-score topic not yet verified in EPPM Help. | Cloud Help TOC contains Schedule Health Score Reference and View Schedule Health Score Results under Schedule Management: https://docs.oracle.com/cd/E80480_01/help/en/user/toc.htm | Do not claim a matching EPPM health score. CUBI diagnostics may be CUBI-native/Cloud-informed, derived from authoritative Engineering runs. |
| ENG-08, ENG-09 | EPPM Activities TOC includes Risks and Issues; EPPM risk register/issue semantics require their individual topic crosswalk before parity claims. | Risk Analysis Prerequisites: https://docs.oracle.com/cd/E80480_01/English/user_guides/risk_management_user_guide/93538.htm; Run a Risk Analysis: https://docs.oracle.com/cd/E80480_01/English/user_guides/risk_management_user_guide/88298.htm; View Risk Iteration Analysis Results: https://docs.oracle.com/cd/E80480_01/English/user_guides/risk_management_user_guide/236375.htm | Monte Carlo is a major Cloud-origin quantitative extension. It must consume a current scheduler result, support reproducibility metadata/seed and immutable runs; Enterprise only aggregates outputs. |
| ENG-10 | EPPM Activities TOC includes Activity Progress, Steps, Constraints, Relationships, Activity Owners and Team Collaboration on an Activity. | Work Plan Overview: https://docs.oracle.com/cd/E80480_01/English/user_guides/task_management_user_guide/101909.htm; Manage Tasks on Work Plan: https://docs.oracle.com/cd/E80480_01/English/user_guides/task_management_user_guide/102799.htm; Pull Plan: https://docs.oracle.com/cd/E80480_01/English/user_guides/task_management_user_guide/294155.htm | Cloud Work Plan/hand-off/commitment concepts are a project-execution extension. Keep typed and linked to Engineering activity/WBS; do not substitute generic Enterprise tasks. |
| ENG-11, ENG-12 | EPPM Team Member interfaces and Timesheets are listed in V26 TOC: https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm; Timesheets Page: https://docs.oracle.com/cd/G48897_01/p6help/en/5972.htm; About Timesheets: https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/6610.htm | Cloud Timesheets guide index: https://docs.oracle.com/cd/E80480_01/English/user_guides/timesheets_user_guide/index.html | EPPM Team Member is normative and separate from generic task management. Confirm the exact Team Member Web Help pages for assigned activities, status update submission/review and timesheet entry before building. |
| ENG-13 | Assigning Documents to Activities: https://docs.oracle.com/cd/G48897_01/p6help/en/41625.htm | Cloud API/Data Services and document guide topics still require exact source verification. | Shared structured attachment/link behavior; external sharing, retention and portal grants may be Enterprise-owned. |
| ENT-02 | EPPM V26 TOC includes Portfolios, Portfolio Analysis, portfolio views/scorecards/charts, About What-if Analysis and Capacity Planning. Creating Portfolios: https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/7858.htm | Portfolio Management guide index: https://docs.oracle.com/cd/E80480_01/English/user_guides/portfolio_management_user_guide/index.html | Existing EPPM portfolio parity first; Cloud additions only after exact semantic comparison. |
| ENT-03, ENT-04 | EPPM V26 TOC includes Capacity Planning; Resource Planning/roles and committed allocations require detailed topic verification. | Resource Planning Overview: https://docs.oracle.com/cd/E80480_01/English/user_guides/portfolio_management_user_guide/109148.htm; Add a Resource Planning Scenario: https://docs.oracle.com/cd/E80480_01/English/user_guides/portfolio_management_user_guide/109149.htm | Enterprise owns portfolio capacity envelopes/scenarios; Engineering retains project assignments, leveling and schedule calculation. |
| ENT-06 | EPPM V26 TOC includes Dashboards, Dashboard Access/Filters/Layout, Project Performance Metrics and Portlets. | Cloud dashboards/portfolio guide topics need exact crosswalk where CUBI extends EPPM. | EPPM parity is primary; Enterprise consumes permission-checked Engineering read models. |
| ENT-08, SH-02 | EPPM V26 TOC includes Approvals, Timesheets, email notifications and Team Member update/review topics. | Workflow Design Editor: https://docs.oracle.com/cd/E80480_01/English/user_guides/workflow_design_guide/81785.htm; Workflow task inbox: https://docs.oracle.com/cd/E80480_01/English/user_guides/workflow_design_guide/82285.htm | Enterprise owns workflow definitions and approval evidence; source domain validates and performs final business mutation. Workbench inbox is a projection only. |
| ENT-07, ENG-10 | EPPM activity collaboration and Team Member topics are distinct from Cloud Task Management. | Tasks Overview: https://docs.oracle.com/cd/E80480_01/English/user_guides/task_management_user_guide/101908.htm; Work Plan Overview: https://docs.oracle.com/cd/E80480_01/English/user_guides/task_management_user_guide/101909.htm | Separate generic organizational tasks from schedule-linked Field Work Plan and assigned Team Member activities. |
| ENT-01, SH-04 | EPPM V26 TOC contains About User Access, OBS, Security Profiles, module access, resource access, UI Views and audit topics: https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm | Cloud Administration/Security guide indexes are listed in §6; exact privilege/topic pages still need row-level extraction. | One shared authorization authority; every environment enforces server-side access and immediate revocation. |

### Confirmed source facts that affect feasibility

- The EPPM V26 Activities topic explicitly groups activity views, Gantt, WBS, baselines, scheduling, float, critical path, resource leveling, progress, resources, roles, documents, expenses, constraints, relationships, risks, steps, budgets and earned value. This strongly supports extending the existing Engineering Activities/Schedule context rather than creating Cloud-app clones.
- EPPM V26 global TOC explicitly includes Dashboards/Portlets, Portfolios/Portfolio Analysis, Capacity Planning, Timesheets, User Access, OBS, Security Profiles, module/resource access and audit. These are EPPM parity work, not Cloud-only features.
- Cloud Schedule Scenarios explicitly isolate scenario data from current schedule/other scenarios/baselines until a user makes a scenario current. CUBI should preserve stronger immutable provenance and guarded promotion while reusing the same Engineering scheduler.
- Cloud Monte Carlo requires current schedule inputs, risk/uncertainty distributions, iterations, convergence controls, reproducibility seed, distributions and sensitivity/tornado outputs. It is not equivalent to a deterministic risk score.
- Cloud Work Plan includes task planning boards, hand-offs, constraints, commitments, due-date proposals and missed-commitment history. CUBI should link these to Engineering activity/WBS without turning them into schedule activities or Enterprise generic tasks.
- Cloud portfolio resource planning is time-phased, scenario-based and includes review/negotiation/approval before committing role allocations. CUBI must keep that portfolio envelope in Enterprise and let Engineering own project assignment/leveling calculations.


## 8. Existing repository workstream cross-reference — deduplication checkpoint (2026-11-15)

This is an initial issue/PR collision map from the current open GitHub search. It is not proof that every referenced item is complete or that its latest files do not overlap. Before any source edit, refresh each issue/PR head, changed paths, review state and exact-head checks.

| Register area | Existing issue / PR references | Required handling |
|---|---|---|
| Full EPPM V26 feature-difference/source audit | Issues #1925; PR #1926 | Reuse as source inventory. Reconcile EPPM vs Professional distinctions and do not duplicate the audit. Feed confirmed EPPM V26 topics into this register. |
| Canonical Activity/Schedule visual workspace and parity | Issue #1691; PR #1716 and other active workspace PRs | Continue the canonical workspace only. Refresh exact path ownership before changes to Activity/Gantt/shell files. |
| Scenario lifecycle | Issue #1989; architecture PR #1988 | #1989 is one ENG-04 child slice, not the whole CUBI roadmap. |
| Engineering Intelligence and knowledge | Issue #1706; Issue #1540; PRs #1724 and #1729 | Preserve the CUBI-owned/model-free assistant principles and knowledge privacy boundaries; deduplicate learning-memory and knowledge-base work. |
| Organization, security, identity and OBS | Issue #1984; PRs #1971, #1974, #1980, #1983 | These are existing Enterprise/security workstreams. Audit each exact head and merge/CI status; do not create another identity, team, profile or OBS model. |
| Enterprise organization and collaboration | Issue #1928; PR #1929 | Use as the Enterprise parent workstream; generic tasks remain separate from Engineering activities and Field Work Plan. |
| Workflow, approval and shared Form Builder | Issue #1927 | Treat as the design gate for ENT-08/SH-09; do not create a second form/workflow engine. |
| Subscription, payment and owner CMS | Issue #1605; Issue #1888; PR #1887 | Reuse approved Free/Pro/Team/Enterprise requirements and owner-controlled payment/CMS decisions; verify current plan decisions before implementation. |
| Offline Flutter/Windows clients | Issue #1670 | Use as the architecture gate for SH-08; shared core and local persistence are required without forcing web offline. |
| Localization | Issue #1531 | Reuse extensible localization resources; complete the agreed language/RTL/timezone matrix rather than add one-off maps. |
| Takeoff, estimating, resource/equipment planning and risk mitigation | Issue #1617 | Reconcile this broad engineering backlog against ENG-06/08/09 and existing core before splitting work. |
| Personal dashboard hidden reporting menu | Issue #1924 | Keep this future personal-dashboard scope separate from the current canonical Engineering workspace; no duplicate visible menu in the Activity shell. |

### Current open PRs with likely ownership relevance (must refresh before code edits)

- #1974 — Organization & Access team management.
- #1983 and #1980 — OBS/WBS responsible access.
- #1971 — CUBI-ID and team invitation lifecycle.
- #1929 — Enterprise Team & Task domain foundation.
- #1926 — EPPM vs Professional V26 difference audit.
- #1887 — subscription/payment/owner CMS requirements.
- #1988 — architecture and master register documentation package.

The open-PR search also returned unrelated public-site and legacy workspace PRs; do not assume they are safe to merge or edit from title/body alone. Exact changed-path and exact-head CI inspection is a mandatory precondition.

### Dedupe decisions

1. #1990 is the program-level parent issue. Existing issues above remain their own bounded workstreams; do not replace or close them.
2. #1989 remains the Scenario Lab child issue.
3. #1925/#1926 provide source-difference evidence; #1988/master register organizes CUBI ownership and implementation sequencing.
4. #1928/#1929 and #1927 own the Enterprise task/workflow/form design track. CUBI should reuse one Enterprise identity, task and workflow foundation.
5. Product requirements in #1605/#1888/#1887 and the client architecture gate #1670 must be reconciled before those shared/platform rows are treated as implementation-ready.


## 9. Full-program feasibility blueprint

The row-by-row delivery feasibility, dependency graph, single-owner technical boundaries, persistence/API/UI/security/offline/job considerations and implementation acceptance gates for **all ENG-01–14, ENT-01–12 and SH-01–10** are maintained in:

`docs/architecture/CUBI_MASTER_PROGRAM_FEASIBILITY_AND_EXECUTION_BLUEPRINT_V1.md`

This blueprint is subordinate to this register and Issue #1990. It is a feasibility/planning artifact only; it grants no implementation credit and does not replace exact topic-level EPPM V26 / Team Member / Primavera Cloud source verification or exact-head implementation evidence.


## 2B. Strict one-to-one, topic-by-topic Cloud Help conformity (explicit product-owner requirement)

**The Cloud Help is the specification, and CUBI's Cloud-derived implementation must match it item by item.** This is a strict one-to-one conformity requirement, not a general inspiration, approximate resemblance, selective feature adoption or "similar workflow" target.

For every applicable Cloud capability, work through the complete feature-specific HTML Help **topic by topic, page by page, section by section, and procedure/step by procedure/step**. Build a traceability matrix with one row for every Help requirement and visible/interactive element. At minimum, each row must identify: exact Help topic URL and heading; Help page/section/procedure; source step and expected result; screen/surface; control/icon/field/option; default and available values; validation and permission conditions; state transition; table/report/chart output; corresponding CUBI component; implementation status; and test/evidence reference.

The required comparison is exhaustive and bidirectional:
1. **Help → CUBI:** every documented page, screen, menu item, icon, button, tab, dialog, field, option, default, validation, chart, report, table, column, color meaning, size, layout, interaction, procedure step and resulting behavior must have a corresponding CUBI implementation or an explicitly justified NOT APPLICABLE / NOT PRESENT disposition. Nothing may silently be omitted, simplified, replaced by a placeholder or deferred while claiming parity.
2. **CUBI → Help:** every proposed Cloud-derived CUBI control, choice, workflow, report, visualization and behavior must be traceable to its Cloud Help source, or explicitly classified as a CUBI-native enhancement rather than Cloud parity. Do not falsely attribute undocumented behavior to Cloud Help.
3. **Procedure replay:** reproduce every documented user procedure in order, including prerequisites, role/permission, input values, selections, intermediate screens, confirmation, resulting state and expected output. Test both successful and documented failure/validation paths wherever Help describes them.
4. **Visual equivalence:** compare equivalent Help/application states side by side. Match information architecture, component hierarchy, control type, icon intent, field order, option inventory, chart/report/table structure, semantic color, density, sizing, spacing, alignment, responsive/resizing behavior and interaction affordances. Use screenshots and a visual-diff checklist for each surface/state. CUBI brand tokens and translated labels remain CUBI-native; this branding adaptation does not permit changing or omitting the Help-defined functional/UI structure.
5. **Complete selectable-choice parity:** enumerate every option/value in dropdowns, selectors, menus, filters, radio/checkbox/multi-select groups, layout/display settings, personalization and permission-dependent choices, including defaults, dependencies, disabled/hidden rules and effects. A matching control with missing values is a parity failure.
6. **Complete output parity:** enumerate and compare every chart/graph/report/table including type, data meaning, columns/series, ordering, dimensions, grouping, totals, axes, legends, labels, units, colors, filters, drill-down, sorting, export/print and empty/error states. A generic or approximate chart/report is not a substitute.
7. **Professional non-interference:** after the one-to-one Cloud comparison, map every item against P6 Professional V26 and EPPM V26 Help. Where an equivalent CUBI capability already exists, extend that single canonical CUBI surface and preserve its Professional-aligned behavior; do not add duplicate windows, menus, icons, forms, controls, reports, tables, routes, records or calculation engines. Cloud-only additions must be additive and isolated so they cannot regress or alter Professional-aligned Activity/Schedule behavior.

**Acceptance rule:** 100% of applicable Help requirements must be dispositioned and implemented, with every documented procedure replayed and evidenced, before a Cloud-derived capability may be marked parity-complete or released as such. Any unresolved row is MISSING / VERIFY (or an explicit, approved NOT APPLICABLE with rationale) and blocks the parity-complete claim. No percentage estimate, passing smoke test, generic screenshot, green build or API-only implementation can replace the row-by-row evidence. This is a binding gate for all Cloud-origin and Cloud-informed capabilities, not an optional QA recommendation.


## 2C. Non-subtractive Cloud capability preservation and dual-environment uplift (binding product-owner decision)

**Do not reduce, remove, weaken, simplify or discard any Cloud functionality when bringing it into CUBI.** The complete documented Cloud capability is to be added to CUBI. Cloud Help is not a feature-minimization checklist and Professional parity is not a reason to cut Cloud functionality down to the Professional common denominator.

For each Cloud-derived capability:
- Preserve the full Cloud Help-defined functional scope, workflows, fields, selectable values, permissions, reports, charts, tables, outputs and documented behaviors. Any Cloud capability that is not present in Professional/EPPM must remain available as a genuine additive CUBI capability; it must not be omitted merely because Professional lacks it.
- Upgrade **both CUBI environments** through the same coherent product capability: shared/common improvements should strengthen the canonical capability in both the Professional-aligned and Cloud-aligned environments. Cloud-specific extensions must remain fully available in the Cloud-aligned environment and be integrated into the Professional-aligned environment wherever semantically applicable, without forcing incompatible Cloud-only workflow or controls into a Professional context.
- Treat Professional and Cloud as complementary source environments, not competing feature ceilings. Reconcile shared semantics once; retain the union/superset of their valid capabilities in CUBI, with clear context-aware presentation and permissions. No source environment may be used to subtract functionality from the other.
- Preserve source-specific workflows and distinctions when they are materially different. Use explicit context adapters, capability flags or role/permission-aware presentation over canonical CUBI domain services where appropriate; do not create duplicate business records, calculation engines or conflicting ownership.
- When the same capability exists in both Help systems, compare differences and implement the complete reconciled behavior, including Cloud additions and Professional behavior. Record any genuine incompatibility and its resolution; never silently drop one source's behavior.
- Run regression and acceptance tests in **both environments**. A Cloud enhancement must not break Professional-aligned workflows; a Professional-aligned improvement must not strip or regress Cloud-aligned workflows.

**Acceptance gate:** a capability is not complete until its full Cloud Help scope is retained in CUBI, all applicable shared improvements are demonstrated in both environments, Cloud-only additions remain usable in the Cloud-aligned environment, and tests prove no destructive cross-environment regression. "Parity" means faithful preservation plus additive CUBI integration and dual-environment uplift—not reduction to the smaller feature set.


## 10. Enterprise layered ownership refinement — 2026-11-16

The detailed layered Enterprise architecture and Cloud-to-environment deduplication matrix are maintained in `docs/enterprise/CUBI_ENTERPRISE_LAYERED_CAPABILITY_ARCHITECTURE_V1.md`.

Binding interpretation for this register:
- Enterprise is organized into layers: shared platform foundations (reuse only), organization/governance, portfolio/strategy/executive oversight, enterprise coordination/stakeholder services, and contextual shared tools.
- The earlier flat 12-heading Enterprise sketch is reconciled into the canonical eight-module architecture in `CUBI_TWO_ENVIRONMENT_PRODUCT_ARCHITECTURE.md`; it is not a license to create 12 new modules or duplicate existing product contexts.
- Cloud schedule scenarios, Monte Carlo project risk, Field Work Plan/Last Planner, Team Member activity updates, project timesheets, project resource assignments/leveling, project risk registers, structured project attachments and schedule diagnostics remain Engineering-owned (ENG-04..ENG-13 as applicable). Enterprise may consume authorized summaries or coordinate generic actions but must not implement competing records or calculations.
- Enterprise owns portfolio lifecycle/decisions, enterprise resource pool and portfolio capacity envelopes/scenarios, portfolio risk governance, workflow definitions/approval evidence, generic organizational tasks, executive read models, stakeholder grants, integration governance, benefits and organizational knowledge (ENT-01..ENT-12), subject to source crosswalk and evidence.
- Form Builder remains the explicitly shared cross-environment capability; platform primitives are reused services, not duplicate Enterprise modules.
- Enterprise Executive Portfolio Decision Scenario is a proposal only and remains **OPEN — PRODUCT-OWNER DECISION REQUIRED**. It is distinct from Engineering project schedule scenarios and the already-listed ENT-04 portfolio resource-planning scenarios. No implementation or menu is authorized until explicit approval.
- Quality & Safety Center and Unifier-informed Contract/Commercial Management are not approved additions; obtain a separate product-owner decision after source/ownership analysis.
- This refinement is architecture/documentation only. It does not claim any capability is implemented, tested, parity-complete or released.


## 11. Source inheritance, traceability and build-time gates — binding

Every capability row in this register must link to its exact software Help source(s), applicable standards and implementation crosswalk. Apply the source hierarchy and mandatory inheritance packet defined in `docs/enterprise/CUBI_ENTERPRISE_LAYERED_CAPABILITY_ARCHITECTURE_V1.md` §§8–9.

Minimum rule:
- P6 EPPM V26 Help for inherited EPPM behavior.
- Primavera Cloud Help for Cloud-only/additive behavior, preserving the complete Cloud scope.
- Primavera Unifier Help for contract/commercial/procurement/cost-BP/SOV/payment lifecycle behavior.
- PMI and domain standards for theory/control only, never as a substitute for software Help.
- Machine-readable source manifest, formula register, lifecycle/state model, permissions, UI/procedure crosswalk and mapped tests required before implementation acceptance.
- CI validation is a required follow-on implementation task; this document does not claim the validator exists.

## 12. New Enterprise capability family — ENT-13 Contract & Commercial Management

**Status:** Added to Enterprise target scope by product-owner direction on 2026-11-16.  
**Canonical source family:** Primavera Unifier Help, with PMI procurement/contract and cost-management practices; applicable law/policy is jurisdiction-configured.  
**Lifecycle:** sourcing strategy → solicitation/tender → evaluation → award → contract formation/execution → administration/obligations → SOV/progress/payment applications/certification → variations/change orders → claims/disputes/notices → forecast/cash flow → suspension/termination → final account/closeout/archive.  
**Ownership:** Enterprise owns contract/commercial records and governance; Engineering owns schedule, activity, project cost/EVM and resource calculations. Approved commercial events integrate through revision-pinned domain APIs. Shared forms/workflows/audit/storage/jobs are reused. No duplicate cost sheet, EVM, schedule or payment execution ledger.  
**Required source anchors:** Unifier Contracts BP, Cost Type BP, Change Orders, Payment Applications, Cost Manager/SOV and Cost Management Levels Help; see the Enterprise architecture §9 for official URLs, field/lifecycle expectations and formula gates.  
**Evidence status:** Initial official topic anchors identified; exhaustive current-release topic-by-topic crosswalk remains MISSING / VERIFY. No implementation or parity-complete claim.

**Register cardinality:** 37 capability families (ENG-01..14, ENT-01..13, SH-01..10). Existing IDs are unchanged.
