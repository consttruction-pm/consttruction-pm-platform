# Stage 33.4.54 — End-to-End Conflict Synchronization Flow

The synchronization boundary now models the complete conflict handoff:

Offline Mutation -> Sync Transport -> Server Outcome -> Conflict Detection -> Refresh-required presentation.

## Guarantees

- mutation identity is preserved;
- expected_revision is never rewritten by the client flow;
- idempotency identity remains owned by the mutation;
- CONFLICT explicitly requires refresh before retry;
- ACKNOWLEDGED does not trigger refresh;
- business reconciliation remains outside the client synchronization flow.

This stage is a flow boundary and integration-test foundation. It is not production HTTP framework wiring and does not claim full end-to-end network execution.
