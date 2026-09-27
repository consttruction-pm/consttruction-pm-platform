# Stage 33.3.2 — Stable API Error Contract

Application/API adapters expose stable machine-readable error categories: validation, context, conflict, authorization and persistence.

Framework/database exception details remain implementation concerns. The contract preserves a retryable flag for clients without prescribing retry policy for domain operations.

This boundary is transport-neutral and does not alter Shared Core calculation semantics.