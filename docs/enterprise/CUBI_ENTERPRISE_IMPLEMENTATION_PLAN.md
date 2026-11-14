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
