# CUBI Enterprise — Foundation, Feasibility & Delivery Framework

**Document ID:** CUBI-ENT-FOUNDATION-001  
**Status:** Active implementation baseline; feature completion remains gated by exact-head CI and runtime evidence  
**Date:** 2026-11-15  
**Parent:** Issue #1928

## 1. Product and delivery boundaries

CUBI Enterprise is an independent organizational and project-collaboration environment. CUBI Engineering remains the primary product-completion priority and the authoritative owner of engineering records and calculations.

- Enterprise work is isolated from Engineering routes, shells, schemas, calculation services and release cadence.
- Engineering is never a prerequisite for Enterprise, and Enterprise is never a prerequisite for Engineering.
- No duplicate schedule, CPM, resource, cost, EVM or critical-path engine is permitted.
- Cross-environment data access must use versioned, permission-checked contracts and revision-pinned references.
- No merge to main or deployment is implied by this implementation branch.
- Initial Enterprise UI design may be independent of Engineering. Shared shell, tokens, component library and visual convergence are optional future evaluations, not acceptance gates.

## 2. Target capability map

| Module | Ownership | Core responsibilities | Required foundations |
|---|---|---|---|
| Organization & Access Center | Enterprise | organizations, memberships, roles, project grants, invitations, access history | authenticated identity, tenant model, server-side authorization, audit |
| Team & Task Center | Enterprise | teams, tasks, assignments, dependencies, personal and cross-project actions | team membership, task repository, authorization, API |
| Workflow Studio | Enterprise | versioned workflow definitions, transitions, delegates, deadlines and templates | workflow contract, policy evaluator, audit, job scheduler |
| Feedback & Approval Center | Enterprise | submissions, correction, approve/reject/return, decision history | workflow, revision-pinned source data, transaction/idempotency |
| Operations & Job Center | Enterprise | jobs, queues, retries, operational history and scheduled reports | existing background jobs, reporting and monitoring |
| Integration Hub | Enterprise | versioned APIs/webhooks, scoped credentials, replay and import/export | identity, secrets, jobs, audit, tenant isolation |
| Project Portal | Enterprise | client/consultant/contractor access to approved content | project-level grants, document storage, expiring/revocable links |
| Portfolio & Executive Center | Enterprise | portfolio views, KPI, health, trends, decision support | existing Portfolio read models and authorized Engineering read contracts |

Cross-cutting capabilities (Personal Command Center, Cross-Project Action Center, Intelligent Escalation, Stakeholder Portal, Organizational Knowledge Center and Engineering Impact Preview) are built over these modules; they are not separate shells.

## 3. Reuse-first infrastructure inventory

Evidence is deliberately classified: a requirement or schema is not proof of a running feature.

| Foundation | Repository evidence | Current assessment | Enterprise action |
|---|---|---|---|
| Authentication/session | `src/construction_pm/identity_session.py`; production session runtime | Production password-session foundation exists | Reuse authenticated actor identity; do not create another login system |
| Identity/team requirements | `docs/requirements/CUBI_SUBSCRIPTIONS_IDENTITY_TEAMS_MESSAGING_AND_STORAGE_V1.md`; Issue #1605; shared identity/team schema | Requirements/contracts exist; they do not prove organization/team API and persistence are complete | Audit implementation before wiring; implement only verified gaps |
| Enterprise identity adapter | `src/construction_pm/enterprise_identity.py` | Claims-mapping adapter, not a complete organization/team store | Treat as adapter only |
| Authorization | `src/construction_pm/application/authorization.py` and existing project-scoped permission patterns | Reusable authorization primitives exist; organization/team/project object policy still needs explicit coverage | Add server-side tenant/team/project grants and negative IDOR tests |
| Portfolio | Stage 34.2.9 Portfolio Control Read Model; Stage 34.2.10 decision/approval boundary; portfolio snapshot/action contracts and query service | Strong read/decision foundation exists; verify lifecycle persistence and production composition per capability | Reuse read models and decisions; do not duplicate portfolio truth |
| Background jobs and operations | existing job processing, monitoring and operational reporting code | Reusable primitives exist; Enterprise UX and policy wiring are not certified | Adapt existing services; do not create a parallel queue |
| Reporting | report registry, execution and export services | Existing reporting foundation; scheduled delivery and per-module wiring vary | Reuse report definitions and permission boundaries |
| Audit | existing audit-event patterns and security event contracts | Audit infrastructure exists in multiple domains; append-only and actor provenance must be verified per store | Reuse canonical event conventions; no unaudited mutations |
| Storage/documents | document and object-storage repositories with scoped access patterns | Existing durable storage foundation | Reuse scoped storage, quotas and retention policy |
| Form Builder | `docs/engineering/PMBOK_FORM_BUILDER_AND_FORM_CALCULATIONS.md`; `CUBI-FORM-CALC-001`; `CUBI-FORM-DESIGN-002`; Issues #1481/#1617 | Shared contracts and implementation work exist; full end-to-end UI/runtime status must be verified | One shared Form Builder capability with environment-specific context and grants |
| Task application/API | `enterprise_task_repository.py`, `enterprise_task_application.py`, `enterprise_task_http.py`, production runtime and schema wiring | Authenticated personal/project task API is wired to the production session + CSRF boundary; team assignment and Engineering references remain closed | Reuse project authorization; add organization/team grants before team assignment |

## 4. Implementation priority and gates

### P0 — Organization and access foundation
1. Map the existing authenticated identity to organization and tenant membership.
2. Define versioned organization, membership, invitation and project-grant contracts.
3. Reuse current authorization primitives and enforce permissions server-side.
4. Add PostgreSQL persistence, audit and negative cross-tenant/cross-project tests.
5. Do not expose a role selector as production authentication.

**Exit gate:** authenticated actor → tenant membership → project/team grants are resolved server-side; unauthorized reads and writes fail closed; removal/revocation takes effect immediately.

### P1 — Team & Task Center
1. Stabilize the versioned task DTO and PostgreSQL repository.
2. Verify idempotency, revision concurrency, stable pagination, dependency cycles and append-only audit.
3. Extend authorization from personal/project scope to verified organization/team grants before team assignment.
4. Add cross-environment reference authorization through versioned Engineering contracts.
5. Build the UI only after real API and authorization tests pass.

**Exit gate:** fresh-connection read-after-write, tenant isolation, permission-denied cases, audit provenance and exact-head CI pass.

### P2 — Workflow and approvals
1. Define a closed, versioned workflow definition and instance contract.
2. Model explicit state transitions, role/delegate resolution, deadlines and escalation.
3. Pin approval requests to source revisions.
4. Keep submitted proposals separate from authoritative Engineering state.
5. Apply approved changes only through the owning domain service with optimistic concurrency, idempotency and audit.

**Exit gate:** invalid transitions, stale revisions, unauthorized approvals, duplicate requests and partial-commit cases are rejected and tested.

### P3 — Operations and Integration
Reuse the existing job queue, reporting, monitoring and secret-handling services. Add Enterprise policy and presentation; do not create duplicate workers or expose raw credentials.

### P4 — Project Portal
Use project-scoped grants and existing document storage. External stakeholder links must be scoped, expiring, revocable and auditable.

### P5 — Portfolio and Executive
Build on existing Portfolio read models and approved Engineering read APIs. Every snapshot must carry source revision/provenance; no shadow calculations.

### P6 — PMBOK and advanced Enterprise
Complete PMBOK process templates, knowledge, escalation, benefits and other extensions after the EPPM-first baseline and feasibility review.

## 5. EPPM-first capability sequence

1. Dashboards and portlets.
2. Portfolio management.
3. Project overview and EPS.
4. Resource administration and analysis (read from Engineering-owned resource truth).
5. Team member, status and approvals.
6. Risk and issue management (preserve Engineering ownership where records are engineering-authoritative).
7. Reports and performance status.
8. Enterprise administration and security.
9. Project documents and information.

Only after baseline coverage is reviewed may extensions be considered: capacity management, advanced risk/schedule assurance, what-if scenarios, benefits/value realization, PMO knowledge, document extensions, Unifier-informed contract/commercial management (a distinct scope), and field/mobile operations.

## 6. Non-interference and design independence

- Enterprise branches must be based on current main and remain isolated until review.
- Any Engineering change requires its own scope, compatibility evidence and explicit approval.
- No shared UI framework is mandatory. Each environment may optimize its initial UI for its own workflow and information density.
- Shared tokens/components may be evaluated only after representative screens, RTL/LTR, responsive, accessibility and regression testing.
- Enterprise may request Engineering impact analysis but must not recompute authoritative Engineering metrics.

## 7. Current slice and remaining gates

The foundation branch adds the versioned task contract/domain and PostgreSQL repository. The stacked Task API branch adds an authenticated application service and `/api/enterprise/tasks` WSGI middleware, mounted behind the production session and CSRF boundary and included in production schema initialization. The API currently supports personal and project-scoped tasks; project access is checked server-side, while team assignment and Engineering references fail closed until their owning authorization adapters are available.

Not yet claimed: production Organization/team persistence, team assignment, cross-environment reference authorization, Task Center UI, full PMBOK workflows or production readiness. These remain explicit subsequent gates.
