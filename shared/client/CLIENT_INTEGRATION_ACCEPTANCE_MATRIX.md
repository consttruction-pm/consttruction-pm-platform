# Client Integration Acceptance Matrix

## Purpose

This matrix is the release-facing acceptance gate for the Web/Desktop/Mobile client integration foundation on this branch. It records which shared semantics are already implemented and what evidence is required before a client surface is considered integrated.

## Shared acceptance dimensions

| Dimension | Required invariant | Current evidence |
|---|---|---|
| Project context | Tenant/company/project context is preserved end-to-end | Project session, mutation envelope, offline context |
| Contract version | Versioned client contracts are explicit | client-sync, offline, calendar, resource/control contracts |
| Idempotency | Retryable mutations preserve a stable idempotency key | mutation request/queue/sync boundaries |
| Revision | Authoritative revision is supplied by successful server outcomes only | session, sync, conflict boundaries |
| Errors | Clients branch on stable category/code/retryability | ApplicationError presentation boundary |
| Conflict | Conflict exposes explicit discard/refresh-and-retry/defer actions | conflict presentation/resolution boundary |
| Offline | Queued mutations retain original context and mutation identity | offline queue/sync presentation |
| Calendar | Clients present calendar identity/version/kind and fallback context only | calendar presentation boundary |
| Decimal values | Resource/Cost decimal-like values cross boundaries as strings | typed DTO and control presentation |
| Calculations | No client duplicates authoritative scheduling, cost, Progress/EVM, or calendar arithmetic | shared client boundary documents |
| Localization | Persian/English and Jalali/Gregorian are presentation concerns | localization presentation boundary |
| Cross-client parity | Web/Desktop/Mobile preserve semantic payload/outcome equivalence | parity fixtures and acceptance documents |

## Surface readiness

### Web

Ready for implementation of UI adapters once concrete API/client framework wiring exists. The semantic boundary must use the shared envelopes and DTOs; no browser-local authoritative calculations.

### Desktop

Ready for standalone/offline presentation integration using the same queue, context, revision, idempotency, and conflict semantics. Offline mode must not create a second scheduling or cost engine.

### Mobile

Ready for field/offline presentation integration using the same mutation and conflict semantics. Platform-specific interaction may differ, but mutation identity, revision, and calculation semantics must remain equivalent.

### Progress, Reporting, WBS/Activity, Gantt, Dashboard

No new client DTOs are introduced here without an authoritative client-facing contract. Once such a contract exists, the same acceptance dimensions above are mandatory before client integration is marked complete.

## Evidence rule

A section is complete only when:

1. its implementation or contract artifact is committed independently;
2. focused tests exist when executable behavior is introduced;
3. the client-sync CI check for the resulting commit concludes success;
4. the artifact does not introduce a parallel authoritative calculation path.

## Current gate

The Resource/Cost client integration foundation and the offline/online presentation boundary satisfy the shared semantic gates above. The remaining client surfaces should advance only from authoritative contracts rather than speculative client-side models.
