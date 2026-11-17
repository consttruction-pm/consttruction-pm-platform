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


## 8. Binding source-to-capability inheritance and implementation rule — 2026-11-16

This section establishes a traceable inheritance contract for every Enterprise capability. It is a product architecture rule, not a claim that all Help topics have already been extracted or implemented.

### 8.1 Source hierarchy and precedence

1. **Primavera P6 EPPM V26 HTML Help** is the primary software-behavior authority for features that exist in P6 EPPM. Use the exact V26 topic, its procedures, field definitions, security behavior and lifecycle states.
2. **Primavera Cloud Help** is the authority for Cloud-origin capabilities absent from EPPM, and for documented Cloud-specific additive behavior. Preserve the complete Cloud behavior; never reduce it to the EPPM subset.
3. **Primavera Unifier Help (current applicable release, including V26 where published)** is the source authority for contract/commercial, procurement, cost business processes, change orders, schedule of values, payment applications, funding, cash flow and connected commercial controls. Unifier is an additional source family, not a replacement for P6 EPPM or Cloud.
4. **PMI standards** provide management theory, governance principles, portfolio/benefits practices and project lifecycle concepts. They do not override documented software behavior or supply undocumented product-specific screen behavior.
5. **Complementary standards** (for example ISO 31000 for risk, ISO 9001 for quality, COBIT for governance/control, BPMN for process modeling) are used only for the domain they govern. Confirm the current edition and licensed text before claiming conformance.
6. If sources conflict, preserve source-specific behavior and record a documented decision in the crosswalk. Do not silently blend incompatible workflows, definitions, formulas or legal terms.

### 8.2 Mandatory inheritance packet for every capability

Before a capability is designed or built, its work package must contain:
- Capability ID, canonical owner, environment(s), user roles and business outcome.
- Exact source product, release, Help landing page and deep topic URLs; topic title/ID; section and procedure-step references.
- A bidirectional Help-to-CUBI and CUBI-to-Help crosswalk, including every screen, tab, dialog, field, default, option, validation, dependency, permission, status, transition, report, table, chart, export and error/empty/loading state applicable to the feature.
- Data dictionary mapping: source field → canonical CUBI field → type/unit/currency/timezone/nullability/validation/provenance.
- Lifecycle and state-transition model; role/segregation-of-duties matrix; approval and delegation rules.
- Formula register: exact formula, variable definitions, units, rounding, calendar/time basis, inclusion/exclusion rules, source revision, worked examples and independently derived expected results. Where Help does not prescribe a formula, label the proposed CUBI policy explicitly and obtain product-owner approval.
- API/event mapping, idempotency and concurrency behavior, audit evidence, integration/retry behavior, retention and access rules.
- UI parity inventory and side-by-side evidence for inherited software behavior.
- Acceptance tests mapped to each Help procedure and state; negative authorization tests; regression tests in both environments where shared behavior applies.
- Open gaps explicitly marked MISSING / VERIFY. No parity, conformance or completion claim while applicable rows remain unresolved.

### 8.3 Build-time enforcement — do not rely on developer memory

The capability implementation template and delivery gate must require a machine-readable source manifest (for example `capability.sources.yaml`) containing capability ID, source product/release, official Help URLs/topic IDs, standard references, inheritance type (exact / additive / adapted), owner, formula IDs, lifecycle model and acceptance-test IDs. CI or the repository validation workflow should reject a new or materially changed capability package when:
- its source manifest is absent or has no official Help reference;
- a Help-derived UI/procedure has no crosswalk disposition;
- a calculation has no formula owner, unit definition and independent test;
- a workflow has no lifecycle/state-transition definition and permission matrix;
- a shared feature creates a second canonical record/calculation owner;
- an unresolved MISSING / VERIFY row is incorrectly marked parity-complete.

Implemented in this repository:
- Validator: `scripts/validate_capability_sources.py` (Python standard library only).
- Manifest contract: `capability.sources.yaml`, encoded as the JSON-compatible YAML subset so CI requires no new YAML parser dependency.
- Initial capability manifest: `docs/enterprise/capabilities/ENT-13/capability.sources.yaml`, with lifecycle, permissions, formula register, source anchors and mapped acceptance-test paths.
- CI integration: `.github/workflows/ci.yml` validates manifests on pushes and, on pull requests, compares changed implementation files under `apps/`, `src/`, `api/` and `shared/` against declared `implementation_paths`. An unmapped code change or a mapped capability not marked `implementation-ready` fails the gate.
- Unit and formula-example tests: `tests/architecture/test_capability_source_manifest.py` and `tests/architecture/test_contract_commercial_formula_examples.py`.

Coverage is intentionally incremental: ENT-13 is the first registered capability. Existing capability packages without manifests must add their own before implementation code in their paths can change in a PR. ENT-13 remains `source-mapped`, not `implementation-ready`, because its current-release Unifier topic inventory and parity evidence still contain MISSING / VERIFY gaps. The validator enforces manifest structure and readiness claims; it does not independently prove that a cited Help page is complete or that UI parity is true.

### 8.4 Section-level source map (initial authoritative map; topic expansion remains mandatory)

| CUBI capability / area | Primary software Help inheritance | Theory / control reference | Ownership and calculation rule |
|---|---|---|---|
| Organization, EPS discovery, OBS, project hierarchy | P6 EPPM V26 Help: EPS, OBS, projects, user access/security topics | PMI governance; COBIT for enterprise control | One organization/security authority; EPS remains Engineering's project hierarchy. |
| Project schedule, activities, WBS, baselines, schedule health | P6 EPPM V26 Help: projects, activities, relationships, calendars, baselines, schedule calculations; Cloud Help only for documented additive schedule features | PMBOK project schedule management | Engineering owns CPM and project schedule calculations. |
| Project resources, assignments, units, rates and leveling | P6 EPPM V26 Help: resources, roles, assignments, resource curves/leveling; Cloud Help for Cloud-only additions | PMBOK resource management | Engineering owns project assignment/leveling; Enterprise owns workforce directory and capacity envelope only. |
| Project risk and quantitative analysis | P6 EPPM V26 risk topics where applicable; Primavera Cloud Help: Risk, Risk Analysis, Iteration Analysis and associated procedures | PMI risk practices; ISO 31000 | Engineering owns project risk records and Monte Carlo engine; Enterprise owns portfolio risk appetite/exposure roll-up. |
| Work Plan / Last Planner / Team Member / Timesheets | Primavera Cloud Help: Work Planning, lookahead, constraints, commitments, pull plans, Team Member and timesheet topics; P6 Team Member Help where relevant | PMBOK delivery/resource practices; Last Planner methodology where applicable | Engineering owns project execution records and approved time actuals. |
| Portfolio intake, selection, prioritization and governance | P6 EPPM V26 portfolio/project portfolio Help topics where present; Primavera Cloud Help: Portfolio Management and portfolio planning topics | PMI Standard for Portfolio Management; PMBOK | Enterprise owns cross-project selection and prioritization; source calculations remain revision-pinned. |
| Enterprise resource capacity and scenario planning | Primavera Cloud Help: Portfolio Resource Planning and resource planning procedures; P6 resource Help for overlap only | PMI portfolio/resource governance | Enterprise owns enterprise pool and capacity envelopes; no project assignment or leveling duplicate. |
| Executive dashboards, reports and analytics | P6 EPPM V26 Dashboards/Reports Help; Primavera Cloud Help for Cloud-only portlets/analytics | PMI performance/value governance; COBIT monitoring | Read models aggregate authorized, revision-pinned source measures; no re-computation of source KPIs. |
| Workflow, approvals and shared Form Builder | Primavera Cloud Help: Workflow Design/Workflow Inbox where applicable; P6 Help for relevant approval/security behavior; Unifier Help for cost-BP workflows | BPMN; COBIT control/segregation of duties | Shared workflow/form primitives; destination domain validates and commits its own business mutation. |
| Contract & Commercial Management | Primavera Unifier Help: Contracts BP, Cost Type BP, Change Orders, Payment Applications, Schedule of Values, Cost Manager, funding and cash-flow topics | PMBOK procurement/contract and cost practices; applicable procurement law and contract terms | See §9. Contract master and commercial events must have one canonical owner; Engineering consumes approved schedule/cost impacts. |
| Stakeholder portal and project documents | Primavera Cloud Help portal/document topics where present; Unifier Document Manager and business-process attachment Help; P6 document topics for applicable overlap | PMI stakeholder/communications practices; ISO 27001 controls where adopted | Project document identity remains with its owner; Enterprise governs external grants and publication. |
| Integration, operations and audit | Relevant P6/Cloud/Unifier integration, REST/API, import/export and audit Help topics | COBIT; applicable security standards | Shared integration/job/audit primitives; no second queue or audit authority. |
| Quality, safety and assurance | Unifier Help for configured quality/safety business processes when selected; Cloud/P6 Help only where corresponding features exist | ISO 9001, applicable occupational safety rules | Not a standalone approved Enterprise module yet; source inventory and product-owner scope decision remain required. |

## 9. Contract & Commercial Management — added to Enterprise scope

**Decision:** Contract & Commercial Management is added as a required Enterprise capability family because excluding the commercial contract lifecycle leaves a material gap between portfolio approval, project delivery, commitments, changes, payment and closeout. It is a scoped architecture decision; it does not authorize a legal template, jurisdiction-specific clause library or production implementation without the applicable review gates.

### 9.1 Capability placement and ownership

- Add **ENT-13 — Contract & Commercial Management** as a new Enterprise capability. Update the master register count from 36 to 37 when the register row is added; do not renumber existing ENG/ENT/SH IDs.
- Enterprise owns the contract/commercial lifecycle workspace, contract register, procurement/commercial governance, vendor/contract relationships, commercial events, approval evidence, obligations, notices, claims/change governance, payment certification workflow and closeout evidence.
- A contract may be associated with an Engineering project, WBS/CBS/cost code, activity, risk or document through typed, permission-checked references. Those references do not transfer ownership of the Engineering records.
- Engineering remains authoritative for project schedule, activity progress, project cost/EVM calculations, resource assignments and schedule-linked impacts. Contract events send approved, revision-pinned changes through explicit domain APIs; Engineering decides and records its own schedule/cost projection or approved mutation.
- Enterprise portfolio reporting consumes approved contract commitments, exposure, forecast and cash-flow projections from the appropriate financial/project owner. It must not create a competing project cost sheet, EVM engine, schedule engine or payment ledger.
- Shared Form Builder, Workflow Studio, identity, audit, document/storage and job services are reused. Contract-specific forms and workflows are configuration over shared primitives, not parallel engines.

### 9.2 End-to-end commercial lifecycle

1. **Need / sourcing strategy:** define business need, scope/package, procurement route, budget authority, funding source, delivery strategy and approval thresholds.
2. **Solicitation / tender:** create tender/RFQ/RFP package, bidder list, issue/addenda log, clarification questions, submissions, compliance checks, evaluation criteria, scoring and recommendation. Keep evaluation access segregated.
3. **Award recommendation and authorization:** compare bids, document due diligence and conflicts, verify budget/funding/capacity, route approval, record award decision and delegated authority.
4. **Contract formation and execution:** create contract record with parties, contract type, scope, price model, currency, dates, milestones, bonds/insurance, securities, tax, retention, payment terms, notice requirements, deliverables, obligations, governing law and executed document versions. Track signatures and effective date; do not infer legal execution from workflow approval.
5. **Mobilization and administration:** establish baseline contract value, schedule of values (SOV), deliverable/submittal register, insurance/bond expiry, notices, correspondence, obligations, key dates, vendor performance and linked project controls.
6. **Progress measurement and payment:** capture measured work/earned quantities, supporting evidence, invoice/payment application, review/certification, deductions, retention, tax, advance recovery, previous payments, approved amount and payment status. Payment authorization and actual disbursement remain distinct events; connect to the designated finance/ERP owner rather than inventing a bank-payment ledger.
7. **Variations / change orders:** initiate change event, classify cause, record scope/time/cost/contract-term impacts, quotations and substantiation, evaluate entitlement, route thresholds/approvals, issue formal instruction only under authorized policy, then publish approved effects to the canonical contract and the owning project cost/schedule services. Pending changes must remain separate from approved commitments.
8. **Claims, disputes and notices:** maintain notice deadlines, event chronology, contractual clause references, correspondence, evidence, quantum/time submissions, assessments, negotiation, dispute escalation and settlement/decision outcomes. Preserve privilege/confidentiality controls and legal hold where required.
9. **Risk, compliance and performance:** track contract-specific obligations, deliverable acceptance, vendor KPIs, non-conformance, insurance/bond validity, sanctions/compliance checks, risk events and escalation; link rather than duplicate the project risk register.
10. **Forecast, cash flow and portfolio exposure:** show original value, approved changes, approved commitment, pending exposure separately, certified/paid amounts, retention, forecast-to-complete and cash-flow timing with explicit formula definitions, currency and as-of date. Reconcile to source financial records; never add pending values to approved commitments without a clearly labeled scenario.
11. **Suspension, termination and closeout:** manage suspension/resumption, termination grounds and approvals, final account, final payment, release of retention/security, warranties/defects period, deliverable/document handover, claims/disputes disposition, lessons learned, audit archive and contract closure. Reopening requires controlled authorization and immutable history.

### 9.3 Canonical records and core data

At minimum, model distinct versioned records for: procurement package; solicitation/addendum; bidder/submission; evaluation; award decision; contract and contract version; party/vendor reference; obligation/deliverable; notice/correspondence; SOV and SOV revision; invoice/payment application; payment certification; change event/change order; claim/dispute; performance/compliance event; forecast snapshot; closeout record.

Each commercial transaction must retain: unique ID, project/portfolio context, contract ID and version, currency, tax basis, amount/unit, status, effective/received/approved dates, approver and delegated authority, source document/evidence, source revision, audit trail, idempotency key, and links to any resulting Engineering/Finance mutations. Never overwrite executed contract versions or approved commercial events; supersede them with controlled revisions or linked events.

### 9.4 Required commercial calculations and safeguards

The formula register must explicitly define and test, as applicable:
- Original contract value; approved change value; revised contract value.
- Approved commitment versus pending change exposure (separate measures).
- SOV line totals and remaining balance.
- Gross measured work, prior certified amount, current gross amount, retention, advance recovery, deductions, tax and net certified amount.
- Paid-to-date, certified-not-paid, retention outstanding and remaining contract balance.
- Forecast final contract value / estimate at completion, with assumptions and confidence/status labels.
- Cash-flow periodization and currency conversion using a named rate source/date.
- Claim amount and time-impact estimates as claims/submissions, not automatically accepted liabilities or schedule changes.

Every formula requires a named owner, exact variable semantics, unit/currency, sign convention, rounding, tax/retention treatment, effective date, worked example and independent expected-value test. The source system's documented formula takes precedence for inherited behavior; new CUBI policy formulas require product-owner approval.

### 9.5 Controls and acceptance gates

- Role separation for requester, procurement, evaluator, commercial manager, project manager, finance, approver, legal reviewer, vendor and auditor.
- Threshold-based approval, delegated authority, conflict-of-interest declarations, immutable decision history and no self-approval where prohibited.
- Contract-version locking and controlled amendment; pending vs approved vs executed states are never conflated.
- Idempotent event processing and reconciliation for approved changes, SOV updates, certifications and downstream project/finance messages.
- Permission-filtered vendor portal; time-limited external grants; confidential bid, claim and legal material protected by need-to-know rules.
- Explicit legal-jurisdiction, tax, procurement-policy and retention-policy configuration. CUBI must not present generic workflow as legal advice or assume a contract is enforceable.
- Acceptance tests replay each inherited Unifier Help procedure and validate cross-system consistency, approval boundaries, calculations, revision pinning, duplicate delivery/retry and full lifecycle closeout.

### 9.6 Initial official source anchors (topic-level crosswalk must be expanded)

- P6 EPPM V26 documentation landing page: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/user.html
- P6 EPPM V26 Help — Configuring Project Calculations: https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/7955.htm
- Primavera Unifier Help V25 — Cost Type BP: https://docs.oracle.com/cd/G18097_01/help/user/en/10292725.htm
- Primavera Unifier Help — Contracts Business Process: https://docs.oracle.com/cd/F50962_01/English/User_Guides/proj_controls/80340.htm
- Primavera Unifier Help — Change Orders: https://docs.oracle.com/cd/F50962_01/English/User_Guides/proj_controls/10284927.htm
- Primavera Unifier Help — Payment Applications: https://docs.oracle.com/cd/F50962_01/English/User_Guides/proj_controls/80345.htm
- Primavera Unifier Help — Cost Manager Overview / Cost Sheets / SOV: https://docs.oracle.com/cd/E37673_01/English/User_Guides/UnifierHelp/WebHelp/content/unifier_user_guide/cost_manager/cost_manager_overview.htm
- Primavera Unifier 26 uDesigner Help — Cost Management Levels / SOV: https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/udesigner/costmanagementlevels-77650a.html
- PMI Standard for Portfolio Management (official PMI-hosted reference): https://www.pmi.org/-/media/pmi/documents/public/pdf/certifications/standard-for-portfolio-management-third-edition.pdf?rev=67c367d7cf8f483d8e67f99af78205f7
- All official Help URLs must be checked for current applicable release before each implementation; older version-specific Unifier topics are source anchors only and cannot be silently treated as V26 parity evidence.

**Open evidence:** The exact current-release Unifier topic inventory for solicitation, vendor, claims, notices, bonds/insurance, closeout and every workflow variant still requires direct Help extraction. Those topics are MISSING / VERIFY until captured. This addition defines the target lifecycle and source family; it does not claim complete Unifier parity.

