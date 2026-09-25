# Client Integration Gap Matrix

## Scope

This matrix tracks the Web, Desktop and Mobile integration boundary against the versioned Client Parity contract. This is an integration/QA artifact; authoritative scheduling, calendar, Progress/EVM, Resource/Cost and financial calculations remain in the Shared Domain/Calculation Core.

## Current baseline

| Area | Web | Desktop | Mobile | Contract authority | Next gate |
|---|---|---|---|---|---|
| Project context | Implemented + enforced in sync runtime | Implemented | Implemented | `shared/contracts/client-parity.schema.json` | Runtime parity fixture |
| API transport | Implemented | Foundation only | Foundation only | Versioned Application/API contracts | Client adapter integration |
| Stable errors | Implemented | Foundation only | Foundation only | Application error contract | Cross-client error fixture |
| Offline project state | N/A / server-connected | Implemented | Implemented | Offline Project Context contract | Round-trip parity |
| Offline mutation queue | Shared queue consumer | Shared queue consumer | Shared queue consumer | `sync-mutation.v1` / `sync-outcome.v1` | End-to-end outcome regression |
| Authoritative revision refresh | Implemented | Implemented | Implemented | `sync-project-revision.v1` | Runtime CI verification |
| Stale-revision retry | Implemented | Implemented | Implemented | Versioned sync revision boundary | Runtime CI verification |
| Scheduling/P6 calculations | Shared Core only | Shared Core only | Shared Core only | Shared Domain/Calculation Core | Result-parity fixture |
| Progress/EVM calculations | Shared Core only | Shared Core only | Shared Core only | Shared Domain/Calculation Core | Result-parity fixture |
| Resource/Cost calculations | Shared Core only | Shared Core only | Shared Core only | Shared Domain/Calculation Core | Result-parity fixture |
| Localization | Presentation boundary | Presentation boundary | Presentation boundary | UI contract; calendar arithmetic stays Shared Core | Persian/English + Jalali/Gregorian fixtures |
| Conflict presentation | Implemented Web boundary | Foundation | Foundation | Sync conflict contract | Cross-client conflict fixture |

## Shared synchronization gate

All three clients now consume the same `apps/client-sync` queue and versioned API/revision transport boundaries rather than maintaining client-specific synchronization semantics.

The shared synchronization path:
- accepts only `sync-mutation.v1`;
- preserves mutation identity, ProjectContext and expected revision;
- rejects idempotency-key reuse across different mutation identities;
- treats only `acknowledged` `sync-outcome.v1` as queue removal;
- retains `retry`, `conflict` and `rejected` outcomes for later synchronization handling;
- refreshes authoritative project revision through `sync-project-revision.v1` before stale-revision retry;
- rotates retry idempotency metadata from the refreshed revision.

The queue and transport layers are business-rule neutral. They do not calculate Scheduling/P6, Progress/EVM, Resource/Cost or financial semantics.

## Rules

1. Client code must not introduce authoritative scheduling/P6 or other business-calculation formulas.
2. Project identity, tenant identity and revision travel with the project context.
3. Shared JSON contracts are versioned and are the compatibility source for cross-client payloads.
4. A client may present or adapt authoritative results but must not reinterpret their calculation semantics.
5. Offline/online state and retry/conflict behavior must preserve mutation identity and expected revision.
6. Any semantic change to Shared Core contracts requires regression coverage before client adoption.

## Next implementation gate

Client synchronization semantics are implemented through the shared queue, API transport and authoritative revision boundary. The remaining gate is runtime CI verification; the latest GitHub-hosted runs have failed before any workflow step starts, with no executable step logs, so they are not interpreted as application test failures.
