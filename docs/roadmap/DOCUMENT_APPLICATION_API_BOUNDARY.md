# Document Application/API Boundary v1

## Scope

This boundary exposes the existing versioned p0-document-resource persistence contract through an Application/API layer for contract, drawing, correspondence, RFI, Submittal, delay-claim and evidence resources.

## Rules

- Tenant/project context is enforced before document mutation or read.
- Write permission and actor identity are enforced at the Application layer.
- Create uses the existing idempotent PostgreSQL document persistence path.
- Update requires an explicit expected revision.
- Approval/status transitions use the existing lifecycle transition matrix and approval authorizer.
- Mutations execute inside the Application transaction boundary.
- API transport returns the existing api-error.v1 shape for validation, conflict and authorization failures.
- No scheduling, calendar, Progress/EVM, Resource/Cost or financial calculation is introduced.

## Verification

Focused integration tests cover:
- RFI create/read with versioned DTO and project scope;
- cross-project and viewer write rejection;
- Submittal approval authorization;
- stale revision conflict mapping;
- idempotency-key reuse;
- transaction-wrapped document mutations.

This boundary consumes the existing document persistence and lifecycle contracts; it does not replace them.
