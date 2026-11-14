# CUBI Enterprise — staged implementation plan

**Status:** Active implementation workstream  
**Product decision:** `CUBI-ARCH-ENV-001`  
**Tracking:** GitHub issue #1928  
**Baseline:** `main` at `d7e128f57804323b985917c1f2d680005b63d0c2`  
**Implementation branch:** `feat/cubi-enterprise-task-domain-v1`

## Product boundary

CUBI Enterprise is a separate organizational and project-collaboration environment in the CUBI platform. It is not a replacement for CUBI Engineering and must not change or delay the Engineering workstream.

- Engineering remains authoritative for schedule, CPM, resource, cost, progress, EVM and critical-path calculations and records.
- Enterprise may orchestrate and present Engineering outputs only through explicit, versioned, permission-checked, revision-pinned contracts.
- The personal workbench is the entry and coordination surface, not a third environment.
- Existing identity, team, invitation, messaging, storage, authorization, audit, job, reporting, portfolio and Form Builder capabilities must be reused where their actual implementation is verified.
- Form Builder remains shared, with environment-specific grants and workflows.
- No production deployment, main merge, route replacement or Engineering refactor is included in this workstream without separate approval.

## Delivery sequence

| Order | Work package | Deliverable | Gate |
|---|---|---|---|
| 0 | Baseline and boundary | Evidence inventory, source ownership map, no-regression checks | Current-main SHA and open-PR collision review |
| 1 | Team & Task domain foundation | Versioned task contract, validated domain model, focused tests | Domain and schema tests; no Engineering imports |
| 2 | Durable task lifecycle | PostgreSQL schema/repository, tenant scope, revision guard, idempotent writes, audit events | PostgreSQL read-after-write, stale revision, replay and cross-tenant tests |
| 3 | Enterprise task API | Authenticated list/create/update/complete endpoints, explicit task permissions | HTTP contract and fail-closed authorization tests |
| 4 | Enterprise application surface | Isolated Enterprise entry and Task Center UI consuming real API | Browser E2E, RTL/localization, no fixture data |
| 5 | Team and communication integration | Reuse verified identity/team/membership/messaging contracts | Membership revocation and tenant isolation tests |
| 6 | Workflow and approvals | Versioned workflow definitions, submissions, decisions and history | Transition, actor, revision and permission tests |
| 7 | Operations and integration | Existing jobs/reporting plus controlled integration operations | Idempotency, retry and operational audit tests |
| 8 | Portal and portfolio | Stakeholder-scoped project portal and executive read models | Grant-filtered read tests and revision provenance |
| 9 | Cross-cutting capabilities | Cross-project actions, escalation, knowledge and Engineering impact preview | Policy, provenance and authoritative-service contract tests |

## Initial implementation slice

The first code slice is the Team & Task Center domain contract. It deliberately introduces no UI mock, demo records, API endpoint or second identity/authorization system. It defines the durable task shape and validates domain invariants before persistence and transport are added.

Task scope supports:
- personal tasks;
- team-scoped tasks;
- project-scoped tasks;
- assignment to at most one person or one team;
- priority, lifecycle status, due date and dependencies;
- opaque, revision-aware links to Engineering activities, WBS elements, documents and risks.

The model is tenant-scoped. Team/project membership and permission checks remain application-boundary responsibilities and must be revalidated on every read/write. A task reference never grants access to its target.

## Baseline findings (source inspection at the recorded SHA)

- Web client: `apps/web`, TypeScript, dependency-light, with `npm test`, `npm run typecheck` and `npm run build`.
- Production API: Python WSGI composition under `src/construction_pm`, PostgreSQL-backed through `deployment/production_runtime.py`.
- Production session/authentication exists in `identity_session.py`; current generic project authorization is in `application/authorization.py`.
- `enterprise_identity.py` is currently a claims-mapping adapter, not a complete organization/team persistence or authorization implementation.
- `shared/contracts/cubi-identity-team-messaging-entitlements.v1.schema.json` and the identity/team requirement define important data contracts, but explicitly do not prove end-to-end runtime implementation.
- Portfolio read/decision foundations exist in source and tests; they must be reused, not cloned.
- Initial source search found no Team & Task Center task lifecycle API/repository. This is an inventory finding, not proof that no related prototype exists elsewhere.

## Explicit non-goals for this first slice

- No changes to `apps/web/src/main.ts`, `/app`, current workspace shell, Engineering routes, schedule models or calculation services.
- No temporary role selector promoted to authentication or authorization.
- No fabricated task rows or enabled-looking controls.
- No new team/identity/messaging store.
- No deployment, merge to `main`, production schema migration or change to Vercel settings.

## Verification and promotion policy

Every slice must pass its focused tests before expansion. Persistence/API/UI slices additionally require real PostgreSQL round-trip, tenant and permission negative tests, stale-revision/replay protection and browser E2E where applicable. A branch or documentation/schema-only change is not described as a production feature. Only merged-main behavior counts as completed product implementation.


## Updated product-owner priority and roadmap (2026-11-14)

This section is the current controlling delivery direction and supersedes any earlier wording that could imply Enterprise is an equal-priority delivery stream or that the initial task-domain slice determines the functional product order.

### Product priority and non-interference

1. **CUBI Engineering is Priority 1.** Engineering's active implementation agent, delivery plan, schedule, resources and release path take precedence. Enterprise work must not divert Engineering capacity, slow reviews, add shared dependencies, create CI/runtime contention or delay Engineering milestones.
2. **CUBI Enterprise is Priority 2.** It is a separately owned workstream and progresses only within available, isolated capacity. When parallel execution creates a conflict, Enterprise pauses or is resequenced.
3. No Enterprise shell, dashboard, PMBOK capability, task module, identity redesign, shared styling change or release dependency may block Engineering.
4. Shared code or infrastructure changes require evidence of compatibility and explicit approval whenever Engineering behavior, route, shell, schema, calculation, tests or release path could be affected.

### Functional priority: P6 EPPM first

The first Enterprise product objective is a coherent functional baseline covering the organizational/project-management capabilities of Oracle Primavera P6 EPPM. Use official, version-specific Oracle Help as the functional reference and record exact Help topics for each capability.

| Sequence | P6 EPPM capability group | CUBI Enterprise target |
|---:|---|---|
| 1 | Dashboards and portlets | Personal/role-aware landing views and configurable dashboard panels |
| 2 | Portfolio management | Portfolio views, project health and executive monitoring |
| 3 | Project overview and EPS | Project hierarchy, authorized project discovery and overview |
| 4 | Resource administration and analysis | Resource directory, assignments and capacity views |
| 5 | Team Member, status and approvals | Assigned work, status updates, time/work reporting where relevant, approval lifecycle |
| 6 | Risks and issues | Risk/issue registers, scoring, response and follow-up |
| 7 | Reports and performance status | Operational reports, KPIs and management summaries |
| 8 | Administration and security | Enterprise settings, role/access governance and audit visibility |
| 9 | Documents and project information | Project document access and lifecycle controls within the selected P6 scope |

This is a CUBI product priority, not a requirement to copy Oracle's UI. P6 EPPM and Primavera Unifier are distinct products. Unifier's contract, cost and commercial business processes are not to be described as P6 EPPM parity.

### Proposed extensions after EPPM baseline — feasibility gate

The following proposals are individually assessed only after the relevant EPPM baseline and existing CUBI foundations have been inspected:

1. Resource & Capacity Management extensions.
2. Advanced Risk & Schedule Assurance.
3. Scenario & What-if Analysis.
4. Benefits & Value Realization.
5. Enterprise Knowledge & PMO Framework.
6. Document & Information Management extensions.
7. Contract & Commercial Management (Unifier-informed, separate from P6 EPPM parity).
8. Field & Mobile Operations.

Each proposal requires a short feasibility record covering: user/business value, existing CUBI overlap, reuse candidates, data ownership, smallest required change, UI/API/persistence gap, permissions/audit, performance/operational risks, cost/complexity and measurable acceptance tests. No proposal is automatically approved for implementation by appearing in this list.

### Reuse-first, minimum-change delivery

- Verify actual code, runtime, persistence and tests before creating anything new.
- Reuse current identity/access, teams, tasks, Workflow Studio foundations, Form Builder, portfolio read/decision models, reporting, jobs/operations, audit and storage wherever they fit.
- Add the smallest missing capability at a clear ownership boundary; do not create shadow services or duplicate calculation authority.
- Broad third-party integrations are not an active priority. Keep contracts extensible, but do not let connector expansion consume current Enterprise capacity.
- The existing task-domain foundation remains a technical foundation only; it does not override the EPPM-first functional roadmap.

### Initial product design and future visual convergence

A coherent CUBI experience is a long-term design objective, **not a mandatory shared-design implementation constraint at this stage**.

- Allow the initial CUBI Enterprise design to emerge from its actual user roles, EPPM-first workflows, information density and product requirements.
- Do not require Enterprise to adopt shared Engineering tokens, components, shell patterns, colors or navigation before its initial design is evaluated.
- Preserve the existing Engineering shell. No visual refactor, shared CSS migration or component replacement in Engineering is authorized by this plan.
- Keep the CUBI design-system document as an exploratory design brief and candidate set of principles—not a binding implementation specification or release gate.
- After initial representative screens and user journeys exist in the relevant environments, evaluate which visual and interaction patterns genuinely benefit from convergence.
- Any proposed shared tokens, components or shell conventions must be tested for usability, RTL/Persian and LTR behavior, accessibility, responsive behavior, regression risk and compatibility with each environment.
- Adopt shared elements only after the relevant tests pass, evidence is reviewed and the responsible product owners explicitly approve the change. Until then, environment-specific design is acceptable.
- Do not spend Enterprise capacity on premature visual harmonization, and do not let design-system work delay the P6 EPPM functional baseline or the higher-priority Engineering workstream.

Reference: `docs/design/CUBI_PRODUCT_DESIGN_SYSTEM_AND_ENVIRONMENT_SHELLS.md` (exploratory; non-binding pending validation and approval).
