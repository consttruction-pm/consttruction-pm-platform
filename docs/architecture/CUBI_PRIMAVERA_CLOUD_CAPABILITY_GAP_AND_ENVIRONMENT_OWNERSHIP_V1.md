# CUBI vs Primavera Cloud — Capability Gap & Environment Ownership V1

**Status:** Product architecture proposal; recorded on an isolated documentation branch, not yet merged or implemented.
**Baseline:** `main` at `376af9e2751ea1260ea3b4ed9be050eb1722afbf` (2026-11-15).
**Purpose:** Define where each Primavera Cloud-inspired capability belongs so CUBI remains one coherent product without duplicating domain authority or weakening specialist workflows.

## 1. Product decision

CUBI is one product with two specialist environments and one shared entry/coordination experience:

- **CUBI Engineering** is the system of record for project execution and engineering truth: projects, EPS/WBS, activities, relationships, CPM, calendars, baselines, schedule updates, project resource assignments/levelling, cost, progress, EVM, project risk calculations and field production controls that directly change or explain the executable project plan.
- **CUBI Enterprise** is the system of record for organizational and cross-project governance: organizations, people, teams, memberships, entitlements, portfolio lifecycle, strategic prioritization, enterprise capacity allocation, cross-project decisions, workflow/approvals, stakeholder access, collaboration, consolidated reporting and integrations.
- **CUBI Workbench** is the shared entry, navigation, personal action and notification surface. It is not a third domain and owns no duplicate business records or calculations.

The rule is **one capability, one authoritative owner; many role-appropriate views**. A capability may be discoverable from both environments, but only its owning domain may create or mutate its authoritative records. The non-owning environment consumes versioned, permission-checked, revision-pinned contracts and links users to the owner for authoritative actions.

This proposal complements, and does not override, the mandatory Oracle Primavera P6 EPPM Help V26 HTML parity baseline. P6 EPPM parity remains the first Enterprise functional baseline; Primavera Cloud capabilities are an additional comparison and extension backlog, not a substitute for P6 EPPM Help.

## 2. Capability ownership and gap matrix

Status values describe current repository evidence, not product marketing claims:
- **Foundation / partial:** some contracts, models or domain behavior exist; end-to-end product capability is not proven.
- **Backend / read model:** service or contract exists without complete production lifecycle and user experience.
- **Planned / gap:** no sufficient end-to-end evidence was found in the reviewed baseline.
- **Verify:** repository evidence must be checked against runtime and acceptance tests before claiming completion.

| Capability | Authoritative environment | Supporting environment / integration | Current CUBI evidence and gap | Recommended delivery |
|---|---|---|---|---|
| Project schedule, CPM, activities, WBS, relationships, calendars, baselines | Engineering | Enterprise Project Portal and Portfolio read views | Strong Engineering foundation; continue P6 EPPM V26 parity work | Engineering only owns schedule truth and calculations |
| Project-level schedule what-if and schedule comparison | Engineering | Enterprise consumes approved scenario summaries | Scenario/what-if end-to-end parity requires verification; do not confuse API contracts with usable scenario workflow | Build in Engineering beside schedule/baseline workflows; preserve immutable scenario inputs/results |
| Schedule health score, project schedule diagnostics | Engineering | Enterprise aggregates health indicators | No complete Cloud-equivalent evidence established | Engineering computes explainable indicators; Enterprise aggregates, filters and escalates |
| Project resource assignments, rates, units, spreads and project levelling | Engineering | Enterprise provides people/skills/availability context | Resource/capacity foundations exist in Engineering | Engineering owns assignment math and project-level levelling |
| Enterprise resource pool, skills, qualifications, availability and cross-project demand/capacity | Enterprise | Engineering provides demand/assignment facts and receives approved allocation envelopes | No complete centralized enterprise capacity-planning lifecycle established | Enterprise owns people/skill/availability master and portfolio allocation; never duplicates project assignment calculations |
| Project risk register and project risk/issue actions | Engineering | Enterprise cross-project risk oversight and escalation | Engineering risk foundations exist; full lifecycle and Cloud quantitative depth remain gaps | Engineering owns project risk records tied to project execution and schedule/cost impact |
| Quantitative schedule/cost risk analysis (Monte Carlo, confidence levels, contingency) | Engineering | Enterprise aggregates portfolio exposure and funding/contingency requests | Current deterministic risk engine is not Monte Carlo; probabilistic analysis is a major gap | Implement simulation in Engineering using authoritative schedule/cost inputs; expose reproducible, versioned result distributions to Enterprise |
| Portfolio risk appetite, exposure thresholds and cross-project risk governance | Enterprise | Engineering publishes project risk snapshots | Portfolio-level governance not yet complete | Enterprise owns policy, thresholds, escalation and portfolio decisions; no duplicate risk calculations |
| Field production schedule, work packages tied to activities, daily execution status | Engineering | Enterprise team directory, assignment authority and collaboration | Field Operations / Assurance foundations exist; Last Planner workflow gaps remain | Engineering owns schedule-linked field work and production facts |
| Weekly work plans, lookahead, constraints, commitments, daily huddles, PPC and missed-commitment reasons | Engineering (execution truth) | Enterprise supplies team/company membership, permissions and cross-project commitment views | Field Operations is not yet equivalent to Primavera Cloud Task Management / Last Planner | Build execution workflow in Engineering; Enterprise may show company-wide rollups and manage organizational escalation |
| Generic organizational tasks, team collaboration and cross-project actions | Enterprise | Engineering links to relevant project/activity context | Enterprise Task API/UI is a partial foundation; generic tasks are not P6 activities | Keep generic tasks in Enterprise; use typed, permission-checked links to Engineering records |
| Portfolio lifecycle, intake, grouping, strategic scorecards, prioritization and funding decisions | Enterprise | Engineering provides project estimates, schedule/resource/cost/risk evidence | Portfolio read model and decision boundary exist; Portfolio CRUD/lifecycle and complete UX are gaps | Complete Enterprise Portfolio & Executive Center using existing read/decision foundations; no duplicate project calculations |
| Portfolio and capital planning scenarios | Enterprise | Engineering calculates project-level scenario outcomes | Cross-project financial/capacity scenario lifecycle is not complete | Enterprise orchestrates portfolio scenarios; delegate each project schedule/cost/resource calculation to Engineering; store assumptions and source revisions |
| Dashboards, portlets, executive KPIs and cross-project reporting | Enterprise | Engineering provides detailed project dashboards and domain reports | Reporting/read-model foundations exist; full configurable role-based dashboards are not proven | Enterprise owns portfolio dashboards and portlet catalog; Engineering owns dense project-control dashboards; shared navigation links, not shared data ownership |
| Timesheets / actual labor time entry | Engineering owns project charging and actual-unit effects; Enterprise owns workforce policy and consolidated administration | Shared contributor experience through Workbench; Enterprise approves organization-wide policy | Attendance/timecards foundations must not be represented as full P6 Timesheets parity | Time entry must map to project/resource/activity and feed Engineering actuals through a controlled API; Enterprise handles policy, periods and cross-project oversight. One time-entry record, one workflow state |
| P6 Team Member activity updates, steps, predecessor context and activity status approval | Engineering | Enterprise identity, membership, delegation and approval routing | Generic Enterprise Task is not an activity; Team Member V26 parity remains a distinct gap | Put activity-centric contributor workflow in Engineering; Enterprise may provide identity and reusable workflow/approval infrastructure |
| Workflow definitions, delegation, escalation and approval policy | Enterprise platform service | Owning domain executes approved mutation | Workflow Studio and Feedback & Approval foundations are planned/partial | Enterprise owns workflow definitions and approval records; final mutation is executed by Engineering/other owning domain after authorization, revision check and idempotency |
| Organization, teams, memberships, roles, project grants and audit | Enterprise | Engineering consumes authorized identity/team/project grants | Organization/access persistence foundation has begun; full administration still requires verification | One tenant-aware authorization authority; revocation must apply immediately in every environment |
| Project documents and stakeholder portal | Enterprise owns external sharing, grants, retention and portal lifecycle; domain owners own structured engineering attachments/links | Engineering links project records to governed documents | Existing document/storage foundations; full portal parity remains partial | One document identity and access policy; no copies with divergent permissions |
| Integrations, APIs, webhooks, import/export and operational jobs | Enterprise | Domain adapters owned by each source environment | Existing jobs, reporting and API foundations vary by domain | Enterprise Integration Hub governs credentials, tenant scopes, replay and audit; adapters call owner APIs |
| Benefits/value realization and PMO knowledge | Enterprise | Engineering contributes actual progress/cost/schedule outcomes | Not yet a complete capability | Enterprise owns strategic benefits, measures and organizational knowledge; project actuals remain Engineering-owned |
| Contract/commercial management (Unifier-informed) | Separate future domain / Enterprise integration boundary | Engineering and Portfolio consume approved commercial impacts | Not P6 EPPM or Primavera Cloud parity by itself; distinct product scope | Do not mix into schedule/CPM core; require separate feasibility and data ownership decision |

## 3. Boundary rules that preserve capability effectiveness

### 3.1 Do not duplicate calculations

1. Engineering calculates CPM, schedule health inputs, project resource demand/levelling, project cost/progress/EVM and project-level risk/simulation outcomes.
2. Enterprise calculates organizational/portfolio aggregation, strategic scoring, policy compliance, capacity allocation decisions and portfolio-level prioritization—not project CPM, EVM or Monte Carlo.
3. When Enterprise needs a project metric, it reads a source-revision-pinned result from Engineering. It must not reimplement the formula in a dashboard or reporting query.
4. Aggregation must preserve units, currency, calendars, data date, project revision, model version and freshness metadata. If inputs are stale or incomparable, show that state rather than silently combining them.

### 3.2 Keep execution close to the work

- Activity, WBS, schedule, project risk, field production, constraints and activity status belong in Engineering because they directly affect project execution.
- Enterprise generic tasks are for organizational actions, cross-project follow-up, decisions, requests and collaboration. They must never masquerade as schedule activities.
- A cross-environment task/reference stores an opaque typed reference (domain, object type, object id, source revision); the target domain rechecks authorization on every open/read/write. A reference never grants access.
- The UI may deep-link users into the owner environment with context preserved. It must not expose a second edit form that mutates the same record.

### 3.3 Separate policy from domain mutation

- Enterprise Workflow Studio owns workflow definitions, role/delegate resolution, deadlines, escalation and approval evidence.
- The owning domain validates the proposed change against its current revision and business rules, then performs the mutation transactionally.
- Rejected, stale, unauthorized, duplicate or partially applied operations fail closed and are auditable.
- Approval does not itself imply that a schedule, resource assignment, timesheet or project record has changed.

### 3.4 Make the product feel unified without forcing one shell

- Workbench provides one sign-in, global search, personal action inbox, notifications, recent projects and environment-aware navigation.
- Shared identity, tenant, project directory, authorization, audit, documents, reporting metadata and design tokens may be reused when their contracts are stable.
- Engineering and Enterprise retain specialist information architecture, interaction density and release independence.
- A single visual shell is not a prerequisite for product unity. Converge shared components only after representative workflows pass accessibility, responsive, RTL/LTR and regression checks.
- Use consistent project/person/team identifiers, breadcrumb conventions, terminology, notification semantics and deep links across environments.

## 4. Recommended navigation model

**Workbench (global):** Home, My Work, Notifications, Search, Recent Projects, Help, Profile.

**Engineering:** Projects / EPS, WBS, Activities & Schedule, Calendars, Baselines & Scenarios, Resources (project planning), Cost & Progress, Risk & Schedule Assurance, Field Production, Reports.

**Enterprise:** Organization & Access, Teams, Generic Tasks & Collaboration, Workflow Studio, Approvals, Portfolio & Executive, Enterprise Capacity, Project Portal & Documents, Integration Hub, Operations & Jobs, Enterprise Reports.

A user sees only modules allowed by tenant membership, product entitlement, role and project grants. Navigation visibility is a usability layer; every API and object operation still enforces authorization server-side.

## 5. Cross-environment contract pattern

Every cross-environment capability must use a versioned contract with:

- tenant and actor context derived server-side, never trusted from client payload;
- typed opaque source reference and source revision;
- explicit read/write scopes and purpose;
- source timestamp, data date and freshness/expiry semantics;
- idempotency key and optimistic revision guard for commands;
- audit event with actor, action, source and target revisions;
- stable error semantics for forbidden, not found, stale, conflict and unavailable;
- no implicit privilege inheritance from a task, dashboard, portfolio or document link.

Read models are snapshots, not a new source of truth. Commands are sent to the owning domain. For long-running calculations, create a tracked job and publish an immutable result with model version and reproducibility metadata.

## 6. Delivery order

Priority is governed by the existing project decision: Engineering is Priority 1 and Enterprise is Priority 2; Enterprise work must not slow Engineering or create shared release dependencies.

1. **Protect and finish the Engineering core:** complete P6 EPPM V26 schedule/resource/progress/calendar workflows already in flight; maintain regression evidence.
2. **Complete P6 EPPM Enterprise baseline:** dashboards/portlets, portfolio lifecycle, project/EPS overview, resource administration views, approvals, Team Member separation, reports, administration/security and project information. Use the mandatory V26 HTML traceability matrix.
3. **Close project execution gaps in Engineering:** project what-if/scenario UX, schedule health, quantitative risk simulation, and Last Planner / field production workflows.
4. **Build Enterprise capacity and portfolio decisioning:** central skills/availability, cross-project demand/capacity, portfolio prioritization and funding scenarios, using Engineering outputs.
5. **Unify Workbench and cross-environment actions:** global search, inbox, notifications, deep links and impact preview after source contracts are stable.
6. **Consider extensions only after parity:** benefits realization, PMO knowledge, advanced mobile/offline and Unifier-informed commercial workflows.

Each slice requires a feasibility record, owning-domain decision, source Help topic(s), contract, persistence and permission design, negative security tests, acceptance journey, and measurable runtime evidence. Do not mark a feature complete from a roadmap row, schema, mock or API contract alone.

## 7. Acceptance gates

A cross-environment feature is accepted only when:

- exactly one domain owns authoritative writes and calculations;
- no duplicated schedule/resource/cost/EVM/risk formula exists;
- tenant isolation, project grants, role checks and immediate revocation pass negative tests;
- source revisions and stale-data states are visible and handled;
- idempotency, concurrency, audit and retry behavior are tested;
- English LTR and Persian RTL, keyboard, responsive, empty/loading/error/conflict states pass;
- relevant Oracle P6 EPPM V26 HTML topic(s) are traced for parity features; Primavera Cloud sources are separately labelled as comparative references;
- end-to-end behavior is verified against real persistence and runtime on the exact candidate commit.

## 8. Evidence and reference documents

Repository sources reviewed:
- `docs/enterprise/CUBI_ENTERPRISE_FOUNDATION_V1.md`
- `docs/enterprise/CUBI_ENTERPRISE_IMPLEMENTATION_PLAN.md`
- `docs/enterprise/CUBI_ENTERPRISE_PRIMAVERA_P6_EPPM_HELP_PARITY_V26.md`
- `docs/roadmap/STAGE_34_2_9_PORTFOLIO_CONTROL_READ_MODEL.md`
- `docs/roadmap/STAGE_34_2_10_PORTFOLIO_DECISION_BOUNDARY.md`
- `src/construction_pm/control_intelligence/risk_engine.py`
- `src/construction_pm/portfolio_query.py`
- `apps/web/src/enterprise-task-center.ts` and Enterprise route composition.

Official Primavera Cloud comparison references (not normative P6 EPPM parity sources):
- Oracle Primavera Cloud product overview: https://www.oracle.com/construction-engineering/primavera-cloud-project-management/
- Oracle Schedule Management overview: https://docs.oracle.com/cd/E80480_01/English/user_guides/schedule_management_user_guide/90786.htm
- Oracle Task Management: https://www.oracle.com/customer-hub/construction-engineering/primavera-cloud/tasks-getting-started/task-management/
- Oracle field schedule / PPC: https://www.oracle.com/customer-hub/construction-engineering/primavera-cloud/primavera-cloud-getting-started-schedulers/managing-field-schedule/
- Oracle Primavera Cloud user guide index: https://docs.oracle.com/cd/E80480_01/87731.htm

## 9. Explicit non-goals

This document does not authorize source-code implementation, database migration, shared-shell refactor, route replacement, merge to main or production deployment. It records the product ownership and sequencing proposal so subsequent implementation can be scoped safely. Each implementation slice requires its own approved change contract and verification.
