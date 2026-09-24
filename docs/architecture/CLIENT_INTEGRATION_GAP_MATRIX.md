# Client Integration Gap Matrix

## Scope

This matrix tracks the Web, Desktop and Mobile integration boundary against the versioned Client Parity contract. This is an integration/QA artifact; authoritative scheduling, calendar, Progress/EVM, Resource/Cost and financial calculations remain in the Shared Domain/Calculation Core.

## Current baseline

| Area | Web | Desktop | Mobile | Contract authority | Next gate |
|---|---|---|---|---|---|
| Project context | Implemented | Implemented | Implemented | `shared/contracts/client-parity.schema.json` | Runtime parity fixture |
| API transport | Implemented | Foundation only | Foundation only | Versioned Application/API contracts | Client adapter integration |
| Stable errors | Implemented | Foundation only | Foundation only | Application error contract | Cross-client error fixture |
| Offline project state | N/A / server-connected | Implemented | Implemented | Offline Project Context contract | Round-trip parity |
| Offline mutation queue | Consumer boundary | Shared queue consumer | Shared queue consumer | `sync-mutation.v1` / `sync-outcome.v1` | End-to-end client sync |
| Scheduling/P6 calculations | Shared Core only | Shared Core only | Shared Core only | Shared Domain/Calculation Core | Result-parity fixture |
| Progress/EVM calculations | Shared Core only | Shared Core only | Shared Core only | Shared Domain/Calculation Core | Result-parity fixture |
| Resource/Cost calculations | Shared Core only | Shared Core only | Shared Core only | Shared Domain/Calculation Core | Result-parity fixture |
| Localization | Presentation boundary | Presentation boundary | Presentation boundary | UI contract; calendar arithmetic stays Shared Core | Persian/English + Jalali/Gregorian fixtures |
| Conflict presentation | Implemented Web boundary | Foundation | Foundation | Sync conflict contract | Cross-client conflict fixture |

## Shared offline queue gate

The Desktop and Mobile foundations now consume the same `apps/client-sync` TypeScript queue rather than maintaining client-specific queue semantics.

The shared queue:
- accepts only `sync-mutation.v1`;
- preserves mutation identity, ProjectContext and expected revision;
- rejects idempotency-key reuse across different mutation identities;
- treats only `acknowledged` `sync-outcome.v1` as queue removal;
- retains `retry`, `conflict` and `rejected` outcomes for later synchronization handling.

The queue is transport/business-rule neutral. It does not calculate Scheduling/P6, Progress/EVM, Resource/Cost or financial semantics.

## Rules

1. Client code must not introduce authoritative scheduling/P6 or other business-calculation formulas.
2. Project identity, tenant identity and revision travel with the project context.
3. Shared JSON contracts are versioned and are the compatibility source for cross-client payloads.
4. A client may present or adapt authoritative results but must not reinterpret their calculation semantics.
5. Offline/online state and retry/conflict behavior must preserve mutation identity and expected revision.
6. Any semantic change to Shared Core contracts requires regression coverage before client adoption.

## Next implementation gate

The next client-integration gate is end-to-end client synchronization: connect the shared queue to the existing versioned transport/application sync boundary and verify ACK/RETRY/CONFLICT/REJECTED behavior without duplicating business calculations in Desktop or Mobile.