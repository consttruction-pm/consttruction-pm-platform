# Stage 33.4 Offline Project Context Contract

Date: 2026-09-24

## Backend-owned support

This contract defines the minimum versioned context that must travel with a local/offline project so the same Shared Domain/Calculation Core can reproduce results on Desktop or approved Mobile workflows.

It carries tenant/company/project identity plus project schema, calendar identity/version, scheduling-settings version and calculation-settings version.

The contract does **not** define Scheduling/P6 formulas or client UI behavior. It only establishes the persistence/API boundary required to preserve calculation context across offline and online execution.

## Rules

- `offline-project-context.v1` is explicit and versioned.
- Project identity is mandatory.
- Project schema version is mandatory and positive.
- A calendar version cannot exist without its calendar identity.
- Fingerprint payload is deterministic and suitable for sync/conflict context.
- Clients must not mutate calculation semantics locally; they consume the shared context.

## Ownership

Hasan/Developer 1 owns this backend contract and persistence/API boundary. Client storage, offline workflow UX and synchronization orchestration remain client-track work.

## Regression

`tests/client_sync/test_offline_project_context.py` covers deterministic fingerprinting and invalid context rejection.
