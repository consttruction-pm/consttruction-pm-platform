# Stage 33.3.4 — Authorization Boundary

## Purpose

Provide a framework/provider-neutral authorization boundary at the Application/API layer without coupling the Shared Domain/Calculation Core to authentication providers.

## Contract

- Authentication establishes the user identity outside the Shared Core.
- The Application layer receives a tenant_id, project_id, user_id, and effective roles.
- Authorization is evaluated against explicit permissions.
- Tenant/project context is carried with every project-scoped authorization decision.
- Denied operations raise a stable application-level AuthorizationError.
- The policy contains no scheduling, calendar, Progress/EVM, Resource/Cost, duration, or financial calculations.
- Web, Desktop, and Mobile consume the same permission semantics through the Application/API contract.
- A future external identity provider can replace role acquisition without changing Shared Core calculations.

## Initial permissions

- project.read
- project.write
- project.schedule
- project.admin

Initial role mapping:

- viewer -> read
- planner -> read/write/schedule
- project_admin -> read/write/schedule/admin

This mapping is a baseline contract, not a final product role catalog.

## Completion evidence

src/construction_pm/application/authorization.py implements the boundary and
tests/integration/test_authorization_boundary.py verifies allow/deny behavior,
stable error behavior, and tenant/project context preservation.

No Shared Scheduling/P6 semantics are changed by this stage.
