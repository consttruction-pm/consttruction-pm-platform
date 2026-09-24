# Stage 33.4.55 — Durable Server Sync State Boundary

Idempotency records and synchronization conflicts now have explicit persistence interfaces.

## Required scope

Idempotency is scoped by tenant_id + project_id + idempotency_key.

Conflict history is scoped by tenant_id + project_id + mutation_id.

The shared conflict contract preserves mutation_id, idempotency_key and operation.

## Persistence rule

The current implementation provides deterministic in-memory reference stores behind persistence protocols. It does not claim database durability.

Production adapters must provide transactional persistence and preserve the same keys, fingerprints and conflict semantics.

## Safety

A reused idempotency key with a different fingerprint remains an error. Conflict presentation remains read/presentation-only for clients.
