# Stage 33.4 Offline Mutation Queue Boundary

Date: 2026-09-24

## Purpose

Provide a portable typed envelope for client-side offline mutations. The envelope carries ProjectContext, operation, idempotency key and optimistic-locking precondition so Web/Desktop/Mobile synchronization can use the same boundary.

## Rules

- Clients queue the envelope; they do not execute business calculations locally through a duplicate engine.
- Project context and expected revision travel with the mutation.
- Idempotency key is mandatory.
- The mutation payload remains typed application data at the boundary.
- Retry attempts are metadata only and do not change business semantics.
- Conflict resolution remains an Application/API concern.

No Scheduling/P6 or Progress/EVM semantics are changed.
