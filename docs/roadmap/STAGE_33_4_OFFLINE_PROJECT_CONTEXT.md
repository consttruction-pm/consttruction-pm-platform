# Stage 33.4 Offline Project Context Contract

Date: 2026-09-24

The backend-owned `offline-project-context.v1` preserves tenant/company/project identity, project schema version, calendar identity/version and scheduling/calculation settings versions for reproducible offline execution. It does not define Scheduling/P6 formulas or client UX.

Clients consume this shared context; local storage and workflow UX remain client-track responsibilities. Regression coverage validates deterministic fingerprinting and invalid context rejection.
