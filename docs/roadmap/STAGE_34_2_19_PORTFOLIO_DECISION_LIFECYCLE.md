# Stage 34.2.19 — Portfolio Decision Lifecycle Application Boundary

## Scope
Expose the already-persisted Portfolio Decision lifecycle through the Application boundary without moving business semantics into persistence.

## Lifecycle operations
- approve
- reject
- cancel
- implement
- close

## Invariants
- tenant scope is enforced before transition;
- Portfolio Admin permission is required;
- domain transition rules remain in the Control Intelligence domain;
- persistence owns revision/idempotency/audit atomicity;
- transition event type must match the resulting status;
- no P6 scheduling, Progress/EVM, Resource/Cost or financial calculation semantics change.

## Acceptance evidence
- lifecycle operations have focused application tests;
- invalid transitions are rejected;
- cross-tenant and non-admin calls are rejected;
- implementation requires an implementation reference;
- close requires implemented state.
