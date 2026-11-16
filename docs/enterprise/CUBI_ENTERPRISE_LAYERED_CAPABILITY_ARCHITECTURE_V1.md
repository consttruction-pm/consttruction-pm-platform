# CUBI Enterprise — Layered Capability Architecture & Cloud Deduplication

**Decision reference:** CUBI-ARCH-ENV-001; master register ENG-01..14 / ENT-01..12 / SH-01..10  
**Status:** Architecture refinement for product-owner review; no new business capability is approved by this document unless already present in the controlling architecture/register.  
**Priority:** Engineering P1 remains protected; Enterprise P2.  
**Purpose:** Turn the Enterprise capability inventory into a layered, non-duplicative environment and explicitly separate Primavera Cloud capabilities already assigned to Engineering from those legitimately owned by Enterprise.

## 1. Controlling rules

1. P6 EPPM V26 HTML Help remains the primary parity authority. Use Primavera Cloud HTML Help only for genuinely absent EPPM functionality or documented additive behavior.
2. Preserve the complete Cloud capability scope; do not reduce Cloud behavior to the smaller EPPM feature set. Reconcile overlaps as a full, non-destructive union while retaining one canonical owner for each record, API, workflow and calculation.
3. CUBI has two work environments, Engineering and Enterprise, plus the shared Workbench entry surface. Workbench is not a third business environment.
4. Engineering owns project execution truth and calculations. Enterprise owns organization-wide and cross-project governance, decisions and coordination.
5. No new Enterprise menu, service, record store, calculation engine or workflow is created merely because a feature appears in Primavera Cloud. First check the ownership matrix below and the actual repository implementation.
6. Form Builder is intentionally shared. The designer/library may be entered from both environments, but forms, submissions, permissions and workflow usage remain context-scoped. Calculated fields use the approved shared Formula/Calculation Core.
7. Any capability not already approved in the controlling architecture is **OPEN — PRODUCT-OWNER DECISION REQUIRED**. This document must not be interpreted as permission to implement it.

## 2. Layered Enterprise architecture

The layers describe responsibility and dependency, not separate application shells. The Enterprise navigation should expose only the relevant user-facing modules; shared foundations should not become duplicate business menus.

### Layer 0 — Shared platform and entry foundations (not Enterprise-owned duplicates)

- Personal Workbench: personal landing, environment selection, inbox/notifications and personal action projection.
- Identity, tenant, session, entitlements and authorization primitives: one platform authority; environment grants remain explicit.
- Audit/event, idempotency, revision/concurrency, job/queue, localization/timezone, storage and permission-filtered search primitives.
- Shared Form Builder and Formula/Calculation Core.
- Shared notification and messaging infrastructure.

**Rule:** Enterprise consumes these contracts. It must not build another login, identity/team store, job queue, audit trail, notification engine, storage authority, formula engine or personal dashboard. Engineering and Enterprise may have context-specific views over the same shared capability.

### Layer 1 — Enterprise organization and governance

**Purpose:** Define who the organization is, who is responsible, and who may do what.

1. **Organization & Access Center (ENT-01)**
   - Organization/tenant structure, members, invitations, teams and memberships.
   - Enterprise roles, global/project grants, security profiles, OBS responsibility and access reviews.
   - Delegation/approver assignment, access reports, change history and immediate revocation.
   - One authorization authority; Engineering project/resource-specific enforcement remains at the owning service boundary.

2. **Enterprise Resource Directory & Skills (ENT-03)**
   - Enterprise people/resource pool, skills, qualifications, availability and capacity.
   - Organization-level demand/supply visibility.
   - Does not own project resource assignments, time-phased activity units, rates posted to a project, resource leveling or schedule calculations.

### Layer 2 — Portfolio, strategy and executive governance

**Purpose:** Help executives choose and govern the right collection of projects, without operating each project schedule.

3. **Portfolio & Executive Center (ENT-02, ENT-05, ENT-12)**
   - Portfolio lifecycle, project intake/ideas, strategic alignment, scorecards, ranking and funding/priority decisions.
   - Executive portfolio health and authorized cross-project status.
   - Portfolio-level risk appetite, exposure, escalation and strategic dependencies.
   - Benefits/value realization and PMO/organizational knowledge, where explicitly scoped.
   - Portfolio resource envelopes and cross-project allocation scenarios (ENT-04), subject to approval/review; Engineering owns the project-level assignment and schedule outcome.
   - Project and portfolio what-if concepts must remain distinct (see §5).

4. **Executive Dashboards & Reporting (ENT-06, ENT-10)**
   - Role-aware executive dashboards, configurable portlets, portfolio KPIs, trends and authorized cross-project reports.
   - Read models must expose source revision, data date, freshness, unit/currency and provenance.
   - Engineering remains the authoritative source for project schedule/cost/progress/EVM measures; Enterprise aggregates authorized snapshots rather than recalculating them.

### Layer 3 — Enterprise coordination, process and stakeholder services

**Purpose:** Coordinate people and decisions around projects while leaving project execution records with Engineering.

5. **Team & Task Center (ENT-07)**
   - Generic organizational/personal/team tasks, action ownership, due dates, dependencies and cross-project follow-up.
   - Typed, permission-checked references to Engineering activities, WBS, risks and documents.
   - Must not become a second Activity list, Team Member update workflow or Field Work Plan.

6. **Workflow Studio & Approval Center (ENT-08)**
   - Versioned workflow definitions, stages, conditions, delegates, review/approve/reject/return, escalation, reminders and decision history.
   - Enterprise owns workflow definitions and approval evidence.
   - The source domain validates and commits the final business mutation; an approval cannot bypass Engineering authorization or revision checks.

7. **Project & Stakeholder Portal (ENT-09)**
   - External stakeholder access, approved status/report publication, approved document access and revocable/expiring grants.
   - Enterprise owns the portal grant and audience experience.
   - Engineering owns structured project/WBS/activity attachments and project document references; the portal must call owner services and never bypass their permissions.

8. **Operations & Integration Hub (ENT-11 plus existing SH foundations)**
   - Enterprise-governed integration definitions, API/webhook scopes, connector credentials, exchange history, controlled replay/retry and operational visibility.
   - Reuse existing job/queue, audit and integration infrastructure; do not add parallel infrastructure.
   - Operations & Job Center is a user/admin view over the shared job registry, not a new queue.

9. **Organizational Knowledge Center (ENT-12)**
   - Curated lessons learned, decisions, reusable organizational guidance and PMO knowledge with provenance and access control.
   - Do not duplicate Engineering's activity/project knowledge, document store or assistant memory. Link to those authoritative sources through typed references.

### Layer 4 — Contextual shared capability, not a separate Enterprise-only module

10. **Form Builder (SH-09) — shared across Engineering and Enterprise**
    - One shared designer/core and governed form-definition/version model.
    - Organization-wide forms can be governed from Enterprise; project/engineering forms can be consumed from the Engineering context.
    - Each submission is owned by its destination domain and workflow; do not duplicate the form engine or let a form become a shadow schedule/cost/resource record.
    - The same capability is visible in both environments, with context-specific libraries, permissions and submission routes.

## 3. Reconciliation of the earlier 12-section sketch

The earlier 12 headings were a useful brainstorming list, not a separate approved menu specification. Reconcile them as follows:

| Earlier heading | Canonical placement | Boundary |
|---|---|---|
| Enterprise Dashboard | Layer 2 — Executive Dashboards & Reporting; personal view stays in Workbench | No second personal dashboard or duplicated Engineering dashboard |
| Enterprise Portfolio Management | Layer 2 — Portfolio & Executive Center | Portfolio lifecycle and cross-project decisions only |
| EPS | Engineering project hierarchy; Enterprise may show authorized portfolio/project discovery | Do not create a second EPS/project master |
| OBS & Organizational Management | Layer 1 — Organization & Access Center | One organization/OBS/security authority |
| Enterprise Security & Access | Layer 1 — Organization & Access Center | Shared authorization primitives; no shadow permission engine |
| Enterprise Resource Management | Split: Layer 1 enterprise pool/capacity; Engineering project assignments/leveling | One enterprise capacity owner; Engineering assignment owner |
| Enterprise Risk Management | Split: Engineering project risk/quantitative analysis; Enterprise portfolio risk appetite/exposure | No duplicate project risk register or Monte Carlo engine |
| Enterprise Cost & Financial Control | Engineering project cost/budget/actual/EVM; Enterprise portfolio funding/benefits only where approved | No Enterprise project-cost calculation |
| Workflow & Approval | Layer 3 — Workflow Studio & Approval Center | Domain owner performs final mutation |
| Documents & Knowledge | Split: Engineering structured project attachments; Enterprise portal grants and organizational knowledge | One document identity/storage authority |
| Quality & Safety | Not approved as a new Enterprise module by this architecture | Project inspections, quality records and field safety need source/ownership audit; ask product owner before creating an Enterprise surface |
| Reporting & Analytics | Layer 2 — Executive Dashboards & Reporting | Governed read-only aggregation; source-domain calculations remain authoritative |

## 4. Primavera Cloud capability ownership — explicit no-duplication matrix

The following Cloud-origin or Cloud-informed features are already assigned to Engineering in the master capability register / Engineering P1 tracker. They must **not** be added as Enterprise modules or reimplemented there:

| Cloud capability family | Canonical CUBI owner | Enterprise role |
|---|---|---|
| Project schedule scenarios, scenario compare/merge/current-schedule promotion | Engineering ENG-04 | No schedule scenario editor or second scheduler. Enterprise may later consume approved, revision-pinned summaries only. |
| Monte Carlo / quantitative project risk analysis, iterations, distributions, confidence and sensitivity | Engineering ENG-09 | Portfolio-level roll-up of approved results only; no second simulation engine. |
| Work Plan / Last Planner, lookahead, hand-offs, constraints, commitments, pull plans and missed-commitment history | Engineering ENG-10 | Generic organizational follow-up tasks may link to these records but must not reproduce their lifecycle. |
| Assigned activity / Team Member updates and review | Engineering ENG-11 | Workflow/approval services may provide shared infrastructure; Enterprise must not create a parallel contributor update feature. |
| Project timesheets and approved labor actual posting | Engineering ENG-12 | No second timesheet or labor-actual record. Enterprise may consume approved cost/capacity summaries. |
| Project resources, activity assignments, rates, spreads, units and leveling | Engineering ENG-06 | Enterprise owns workforce directory/skills and portfolio capacity envelopes only. |
| Project risk register, issue links, responses and schedule-linked actions | Engineering ENG-08 | Enterprise owns portfolio risk governance/roll-up, not the project risk register. |
| Project documents and structured activity/WBS/project links | Engineering ENG-13 | Enterprise owns external sharing grants, portal presentation and organizational knowledge links, not a second project document store. |
| Schedule health/diagnostics and schedule-derived metrics | Engineering ENG-05 | Enterprise may display authorized summary indicators, never recalculate or edit them. |

Enterprise-owned Cloud/EPPM capability families, subject to the exact source crosswalk and implementation evidence, are:

- Portfolio lifecycle, ideas/intake, strategic prioritization and portfolio decisions (ENT-02).
- Enterprise resource pool, skills, qualifications and time-phased portfolio capacity/resource planning scenarios (ENT-03/ENT-04), while Engineering retains project assignments and leveling.
- Portfolio risk appetite, exposure and cross-project escalation (ENT-05), while Engineering retains project risk records and quantitative runs.
- Workflow design, organizational approvals, delegation and workflow inbox (ENT-08); Workbench inbox is only a projection.
- Executive dashboards/portlets and cross-project reporting (ENT-06/ENT-10), using authorized source read models.
- Generic organizational tasks (ENT-07), distinct from Engineering activities and Work Plan.
- External stakeholder portal grants, integration governance and organization-wide benefits/knowledge (ENT-09/ENT-11/ENT-12), reusing shared storage, audit, jobs and identity.

Every row remains subject to exact feature-topic inspection in both Help systems and the full Cloud UI parity gate. This ownership table is an architectural placement decision, not a claim that those capabilities are already implemented.

## 5. Scenario decision — keep two approved concepts distinct; ask before adding a third

There are already two distinct scenario concepts in the architecture:

1. **Engineering project schedule scenario (ENG-04):** a planner tests schedule changes against a pinned project schedule, compares runs and may promote a selected scenario through guarded Engineering controls. It owns schedule data and uses the one authoritative scheduler. It stays in Engineering.
2. **Enterprise portfolio resource-planning scenario (ENT-04):** executives/resource managers compare time-phased role/resource demand and capacity envelopes across projects, negotiate allocations and approve a portfolio allocation envelope. It does not edit activity assignments or run CPM; Engineering applies/levels project assignments within its own authority. This is already present in the master register as an Enterprise capability and still requires full source crosswalk, feasibility and product acceptance.

**Additional proposal — Enterprise Executive Portfolio Decision Scenario (NOT APPROVED):**

A possible third capability would let an executive compare strategic choices such as:
- prioritize Project A over Project B;
- defer or accelerate a project;
- change a funding/benefit target;
- compare portfolio composition and strategic value;
- view the combined impact on capacity, risk exposure and expected benefits.

Why it may be valuable: an Engineering schedule scenario answers “what happens to this project's plan if we change these activities?”; an Enterprise executive scenario answers “which portfolio choice should the organization make, given strategy, funding, capacity and risk across many projects?” The latter is a governance/decision-support question, not a schedule-editing question.

Proposed safety boundary if approved: Enterprise stores only scenario assumptions and decision alternatives; it requests revision-pinned projections from Engineering and other authoritative owners; it never calculates CPM, project cost/EVM, project resource leveling or Monte Carlo itself; approval records a human decision and does not silently mutate projects.

**Decision required from product owner:** Should CUBI Enterprise include this separate Executive Portfolio Decision Scenario, in addition to the already-listed ENT-04 resource-planning scenarios? No implementation, menu, API or data model for this additional concept is authorized until the product owner has reviewed the rationale, scope, source Help, overlap and cost, and explicitly approves it.

## 6. Other items requiring consultation before Enterprise expansion

Do not add these as Enterprise menu modules without a separate proposal and explicit approval:

- Quality & Safety Center: first determine whether the required records belong to Engineering Field Assurance, project execution, corporate governance or a separately authorized enterprise compliance layer.
- Contract & Commercial Management: Primavera Unifier is a distinct product; a Unifier-inspired feature is not P6 EPPM parity and needs a separate scope decision.
- A standalone Enterprise Scenario Lab beyond the existing ENT-04 resource planning concept.
- A second document-management, resource-assignment, risk-register, timesheet, field-work, personal dashboard, workflow engine, identity, job queue or reporting calculation system.

For every such proposal, provide: user and decision-maker; exact business question; why the canonical owner cannot serve it; source Help topic(s); distinct data and decision lifecycle; read/write boundary; security/audit impact; smallest UI placement; reuse candidates; risks/cost; and acceptance journey. Ask the product owner before adding it to the approved scope.

## 7. Navigation proposal — menu follows the layers

A restrained Enterprise navigation proposal (not a mandate for extra shells):

- **Overview** — executive landing and authorized portfolio snapshot.
- **Organization & Governance**
  - Organization & Access
  - People, Teams & Skills
- **Portfolio & Strategy**
  - Portfolio
  - Capacity & Resource Planning
  - Portfolio Risk
  - Benefits & Value
  - Executive Dashboards & Reports
  - Executive Portfolio Decision Scenario — hidden/not created unless separately approved
- **Coordination & Delivery Governance**
  - Team & Task Center
  - Workflow & Approvals
  - Project & Stakeholder Portal
  - Operations & Integration
  - Organizational Knowledge
- **Shared tools**
  - Form Builder — same shared capability available from both environments, context-aware
  - Help / Search / Notifications — shared services, not duplicate domain modules

Engineering-only capabilities listed in §4 are not included in this Enterprise navigation.

## 8. Acceptance checklist before implementation or parity claims

- [ ] Exact P6 EPPM V26 Help topic and exact Primavera Cloud Help topic are recorded for every row, or NOT PRESENT / NOT APPLICABLE after a documented search.
- [ ] Cloud-origin UI is inventoried topic-by-topic, procedure-by-procedure, including fields, options, states, tables, charts, reports and responsive behavior.
- [ ] EPPM/Professional collision and source-specific differences are recorded; no Professional source is substituted for EPPM authority.
- [ ] Canonical owner, record owner, calculation owner, menu placement and API/persistence boundary are explicit.
- [ ] Existing Engineering Cloud-origin features in §4 are not duplicated or moved into Enterprise.
- [ ] Shared foundations are reused; no duplicate identity, auth, teams, forms, formula core, document store, audit, jobs, notifications or reporting engine is introduced.
- [ ] Positive/negative authorization, tenant isolation, revocation, stale revision, idempotency and cross-environment reference tests are specified.
- [ ] Exact-head tests and runtime/browser evidence exist before any implementation is marked verified.
- [ ] Executive Portfolio Decision Scenario and all items in §6 remain blocked until explicit product-owner approval.

**Current conclusion:** the Enterprise target is the layered organization/portfolio/coordination architecture above, not the earlier flat 12-module list. Cloud features assigned to Engineering remain in Engineering. The only intentionally shared feature explicitly confirmed here is Form Builder (alongside platform-level primitives and shared services that must be reused rather than cloned). New Enterprise capabilities require consultation before scope expansion.
