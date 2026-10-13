# AI Action / Approval Boundary

This boundary governs proposed AI tool actions at the application layer.

- Every proposal is tenant/project scoped and carries an opaque proposal identity.
- Tool permission is evaluated through an explicit adapter.
- Actions requiring human approval cannot be approved without an actor identity.
- Approved and rejected decisions produce a stable audit event.
- Evidence references remain opaque IDs; this boundary does not interpret project-control calculations.
- AI model/provider execution, token verification, tool implementations and P6/Progress/EVM/Resource/Cost calculations remain outside this boundary.

## Binding V1 specification

This boundary is a supporting security contract, not the complete assistant implementation. The product-level scope and acceptance gate are defined in `docs/architecture/AI_ASSISTANT_V1_REQUIREMENTS.md`; fundamental calculation and product-release rules are defined in `docs/architecture/PRODUCT_PRINCIPLES.md` (Principles 1B and 6A).

Additional non-negotiable invariants:
- A proposal is not an executable capability by itself. A typed tool/use case must exist, be wired to real persistence/domain services, be authorized, execute, and return a verifiable result.
- The permission adapter must use trusted, current user/tenant/project policy. A hard-coded allow-list or in-memory audit sink is reference/test infrastructure only, not proof of production authorization or durable audit.
- Approval must bind to the exact proposal content/hash and base project revision, authenticated actor, and expiry/revalidation policy. Changed or stale proposals require re-validation and, where required, re-approval.
- Human approval is separate from base authorization: approval never grants a permission the actor does not have.
- Rejected, unauthorized, expired, stale-revision, invalid-schema or failed actions produce no unauthorized authoritative mutation and a stable audit/result state.
- Successful mutation is followed by a fresh authoritative read and, where relevant, a new calculation run. A planned action or successful model response is not evidence of persistence.
- Idempotency, transaction boundaries, durable audit, redaction, prompt-injection resistance, error handling and partial-failure recovery are part of the production execution path.
- The AI must never change the calculation authority: all applicable scheduling/P6, calendar, duration/lag, Progress/EVM, Resource/Cost, formula and financial calculations stay in the Shared Domain/Calculation Core.
