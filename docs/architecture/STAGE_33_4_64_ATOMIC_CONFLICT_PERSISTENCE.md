# Stage 33.4.64 — Atomic Conflict Persistence

Conflict outcomes now have an explicit persistence integration point within the sync transaction boundary.

## Contract

A conflict preserves:

- mutation identity;
- tenant/project context;
- expected revision;
- stable error code;
- standard available actions.

The conflict record is presentation-neutral and contains no client-side recalculation.

## Important implementation boundary

The conflict hook is intentionally isolated from Scheduling/P6 semantics. A later integration step must wire conflict persistence directly into the transaction coordinator so that outcome and conflict record commit or roll back together.

## Verification

The current tests verify the conflict outcome contract. Full database atomicity between outcome and conflict rows remains a subsequent integration gate.
