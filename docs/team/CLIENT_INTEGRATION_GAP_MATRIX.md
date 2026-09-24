# Client Integration Gap Matrix

Date: 2026-09-24
Owner: Javad Foroughi — Developer 2
Base: main at `6938c466ba38b4c8ee7edfc9c794f5f44f0b5b2b`
Branch: `feature/javad/client-integration-audit-v2`

## Executive finding

The Shared Core and backend contract foundations are substantially ahead of the product clients. `apps/web`, `apps/desktop` and `apps/mobile` currently contain architectural READMEs rather than executable client applications.

Stage 33.4 has reached 33.4.29: calendar selection is explicitly versioned for project/activity/relationship-lag scopes, and project portability carries calendar-assignment policy. The client layer must therefore preserve explicit calendar references rather than assume an implicit/default calendar.

## Authoritative architecture

Shared Domain/Calculation Core -> Application orchestration/transaction/authorization -> versioned API/Application contracts -> typed client adapters -> Web/Desktop/Mobile presentation.

Offline uses the same portable Core semantics through local persistence, mutation queue, synchronization, revision and idempotency contracts. Clients never implement a second Scheduling/P6, Progress/EVM, Resource/Cost, duration, calendar or financial engine.

## Gap matrix

| Area | Current state | Gap | Priority | Next action |
|---|---|---|---|---|
| Web | README-only foundation | No executable shell, routing, typed API adapter, ProjectContext/session, error/conflict UX, localization or workflows | P0 | Establish Web foundation against existing v1 contracts |
| Desktop | README-only foundation | No standalone shell, local persistence, offline state/sync UX or Core integration boundary | P0 | Establish Desktop boundary and offline adapter |
| Mobile | README-only foundation | No field UI, offline planning UI, queue/sync presentation or capture workflows | P0 | Establish Mobile field foundation using the same contracts |
| Shared client rules | CLIENT_INTEGRATION_CONTRACT exists | No concrete client SDK/adapter | P0 | Implement typed client boundary without changing business semantics |
| Shared contracts | Resource/ResourceAssignment/Portability schemas plus error/sync schemas exist | Activity/Scheduling/Progress/EVM client-facing DTO inventory is incomplete | P0 / coordination | Inventory authoritative API DTOs; coordinate additions before defining new semantics |
| Stable errors | ApplicationError v1 and regression tests exist | No client mapping/localization/presentation | P0 | Map category/code/retryable to typed client errors |
| ProjectContext | Offline ProjectContext v1 exists and is tested | No client propagation/session implementation | P0 | Build context provider/interceptor |
| Revision/idempotency | Backend and offline mutation contracts are implemented/tested | No client mutation middleware/state handling | P0 | Build mutation envelope and conflict/retry handling |
| Offline queue | Persistent attempts and identity protection exist | No product-client consumer | P1 | Connect Desktop/Mobile adapters and expose sync states |
| Calendar resolution | 33.4.29 adds versioned project/activity/lag references and deterministic inheritance | No client selector/editor integration | P0 | Preserve references; Shared Core remains resolver authority |
| Time-aware scheduling | Working-time resolver and TimeQuantity/LagQuantity foundations exist | Not yet integrated into Forward/Backward/Float | P0 / later gate | Do not create client-side conversion or CPM formulas |
| Scheduling | Date-based CPM/constraints/parity tests are extensive | No client integration | P0 | Add read/recalculate adapter when authoritative API surface is ready |
| Resource/Cost | Domain/API/Decimal contracts and tests exist | Client workflows absent | P1 | Consume typed contracts; never recalculate client-side |
| Cross-client parity | Backend/client-sync regression exists | No executable clients to compare | P1 | Add shared fixtures after client foundations |
| Localization | Persian/English + Jalali/Gregorian rules are explicit | No implementation | P1 | Presentation formatting only; arithmetic remains Core |
| CI | No GitHub Actions workflow runs reported | Runtime verification unconfirmed | P1 | Enable repository/client test execution |

## Critical logic to preserve

### Calendar inheritance
Project calendar -> Activity calendar if explicitly set, otherwise project -> Relationship-lag calendar if explicitly set, otherwise activity, otherwise project.

Calendar references contain `calendar_id`, `calendar_version`, and `kind` (`working-day` or `working-time`). Missing requested versions must error; clients must not silently substitute another version.

### Time-aware scheduling
The repository intentionally keeps existing date-based CPM APIs compatible while time-aware Forward/Backward/Float integration is still a gate. Clients may display/edit typed quantities but must not convert hours to days or calculate finish/float independently.

### Contract boundary
Decimal-like values are canonical decimal strings. Dates are explicit ISO-8601. Nullable fields are explicit. Stable errors are branched by category/code, not message text. ProjectContext, revision and idempotency must survive the client boundary.

## Execution order

1. Freeze the authoritative API/DTO inventory from main.
2. Establish Web/Desktop/Mobile client foundations and shared typed client models.
3. Implement ProjectContext + revision + idempotency + stable error handling as reusable client infrastructure.
4. Implement calendar-reference presentation without local calculation.
5. Add Scheduling read/recalculate integration.
6. Add offline queue/sync/conflict UX for approved Desktop/Mobile workflows.
7. Add Resource/Cost, Progress/EVM, reporting and field workflows.
8. Add cross-client parity fixtures and CI.

## Definition of done

- All clients consume the same versioned contracts.
- ProjectContext is mandatory for project-scoped operations.
- Revision/idempotency/error semantics survive the client boundary.
- Financial Decimal values remain canonical decimal strings at API boundaries.
- Calendar id/version/kind survive client workflows.
- No client owns authoritative scheduling or financial formulas.
- Offline results use the same portable Shared Core semantics.
- Shared semantic/API changes are coordinated and documented before becoming authoritative.
