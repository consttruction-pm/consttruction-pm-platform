# Client Contract Inventory v1

## Purpose

This inventory freezes the currently available authoritative client-facing contracts before executable Web/Desktop/Mobile implementation begins.

It is an integration inventory, not a new business-logic specification. No scheduling, duration, calendar, progress, resource, cost, or EVM semantics are introduced here.

## Authority chain

`Shared Domain/Calculation Core → Application → versioned API/contracts → typed client adapters → Web/Desktop/Mobile`

Clients format and orchestrate these contracts. They must not reproduce authoritative calculations.

## Confirmed contracts

| Area | Authoritative contract | Client obligation |
|---|---|---|
| Project scope | `shared/client/CLIENT_INTEGRATION_CONTRACT.md` | Carry ProjectContext on every project-scoped operation |
| Application errors | `docs/contracts/application_error_v1.schema.json` | Branch on category/code; localize message presentation |
| Online mutation | `docs/contracts/client_sync_mutation_v1.schema.json` | Send contract version, context, idempotency key, expected revision |
| Sync outcome | `docs/contracts/client_sync_outcome_v1.schema.json` | Handle applied/replayed/conflict/rejected deterministically |
| Offline mutation | `docs/contracts/offline_mutation_v1.schema.json` | Persist operation/context/idempotency/revision/mutation |
| Offline queue | `docs/contracts/offline_mutation_queue_v1.schema.json` | Track attempts without changing mutation semantics |
| Offline project context | `docs/contracts/offline_project_context_v1.schema.json` | Pin project/calendar/settings schema versions |
| Resource API | `docs/contracts/resource_api_v1.schema.json` | Consume typed resource operations and revision outcomes |
| Project portability | `shared/contracts/project-portability.schema.json` | Preserve calculation/calendar assignment context across import/export |

## Calendar contract

Stage 33.4.29 establishes versioned calendar references:

- `calendar_id`
- `calendar_version`
- `kind`: `working-day` or `working-time`

Effective calendar selection is authoritative:

1. activity calendar → project calendar fallback
2. relationship-lag calendar → activity calendar → project calendar fallback
3. a requested missing calendar version is an error; clients must not silently substitute another version.

Clients may present/select these references, but calendar arithmetic remains in Shared Core.

## Time-aware scheduling boundary

Time-aware duration/lag and working-time calendar semantics exist in Shared Core, but full Forward/Backward/Float integration is not yet the client implementation target.

Until the authoritative scheduling API surface is explicitly released, clients must not calculate time-aware schedule dates, float, or lag locally.

## Missing client implementation

Repository inspection found no React/TypeScript, Vite, Electron, Tauri, Flutter, or React-Native implementation currently established under `apps/web`, `apps/desktop`, or `apps/mobile`.

Therefore this phase does not invent a UI framework. The next executable client work requires an explicit stack decision/coordination point while preserving the contracts above.

## Required next implementation order

1. Shared typed adapter model generated/maintained from the authoritative contracts.
2. ProjectContext/session boundary.
3. Stable error mapping and presentation.
4. Revision/conflict and idempotency handling.
5. Calendar reference presentation.
6. Scheduling read/recalculate integration after the authoritative API surface is available.
7. Offline queue/sync UX.
8. Resource/Cost/Progress/Reporting workflows.
9. Cross-client parity fixtures and CI.

## Non-negotiable constraints

- No client-side duplicate calculation engine.
- No silent calendar-version fallback.
- No mutation without project context where project scope is required.
- No retryable mutation without idempotency handling.
- No optimistic update that ignores revision/conflict outcomes.
- Decimal-like authoritative values remain canonical decimal strings at API boundaries.
- ISO-8601 remains the date boundary representation.
- Localization changes presentation, not calculation semantics.
