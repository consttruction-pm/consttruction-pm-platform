# Client Integration Gap Matrix

## Scope

This matrix tracks the Web, Desktop and Mobile integration boundary against the versioned Client Parity contract. It is an integration/QA artifact; authoritative scheduling, calendar, Progress/EVM, Resource/Cost and financial calculations remain in the Shared Domain/Calculation Core.

## Current baseline

| Area | Web | Desktop | Mobile | Contract authority | Next gate |
|---|---|---|---|---|---|
| Project context | Implemented | Implemented | Implemented | `shared/contracts/client-parity.schema.json` | Runtime parity fixture |
| API transport | Implemented | Foundation only | Foundation only | Versioned Application/API contracts | Client adapter integration |
| Stable errors | Implemented | Foundation only | Foundation only | Application error contract | Cross-client error fixture |
| Offline project state | N/A / server-connected | Implemented | Implemented | Offline Project Context contract | Round-trip parity |
| Offline mutation queue | Consumer boundary | Foundation consumer | Foundation consumer | Sync mutation contracts | End-to-end client sync |
| Scheduling/P6 calculations | Shared Core only | Shared Core only | Shared Core only | Shared Domain/Calculation Core | Result-parity fixture |
| Progress/EVM calculations | Shared Core only | Shared Core only | Shared Core only | Shared Domain/Calculation Core | Result-parity fixture |
| Resource/Cost calculations | Shared Core only | Shared Core only | Shared Core only | Shared Domain/Calculation Core | Result-parity fixture |
| Localization | Presentation boundary | Presentation boundary | Presentation boundary | UI contract; calendar arithmetic stays Shared Core | Persian/English + Jalali/Gregorian fixtures |
| Conflict presentation | Implemented Web boundary | Foundation | Foundation | Sync conflict contract | Cross-client conflict fixture |

## Rules

1. Client code must not introduce authoritative scheduling/P6 or other business-calculation formulas.
2. Project identity, tenant identity and revision travel with the project context.
3. Shared JSON contracts are versioned and are the compatibility source for cross-client payloads.
4. A client may present or adapt authoritative results but must not reinterpret their calculation semantics.
5. Offline/online state and retry/conflict behavior must preserve mutation identity and expected revision.
6. Any semantic change to Shared Core contracts requires regression coverage before client adoption.

## Immediate implementation gate

The next client-integration gate is a deterministic parity fixture covering the same project context and capability envelope for Web, Desktop and Mobile. This gate validates contract shape and invariants before UI-specific integration work proceeds.
