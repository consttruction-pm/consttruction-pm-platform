# Client Integration Gap Matrix

Date: 2026-09-24
Owner: Javad Foroughi — Developer 2
Base: main at `c1e8490d1dd382837ac1ae42efe7a54316e4d5b5`
Branch: `feature/javad/client-integration-audit`

## Executive finding

The repository has established the architectural rules and backend/client-sync foundations, but the three product-client directories are currently documentation-only. There is no Web, Desktop, or Mobile executable client implementation under `apps/*` yet.

Therefore the immediate client-track blocker is not a UI bug; it is the absence of concrete client foundations capable of consuming the already-defined contracts.

## Gap matrix

| Area | Current state | Gap | Priority | Safe next action |
|---|---|---|---|---|
| Web | `apps/web/README.md` only | No application shell, routing, API client, ProjectContext/session, DTO layer, error/conflict UX, localization or feature workflows | P0 | Establish Web client foundation and typed contract adapter without business calculations |
| Desktop | `apps/desktop/README.md` only | No standalone shell, local persistence adapter, offline state/sync UX, portability workflow or Core integration boundary | P0 | Establish standalone client boundary and offline adapter around authoritative Core/contracts |
| Mobile | `apps/mobile/README.md` only | No field UI, offline planning UI, queue/sync presentation, conflict UX, capture workflows or shared-contract client layer | P0 | Establish Mobile foundation focused on field workflows and approved offline planning |
| Shared client contract | `shared/client/CLIENT_INTEGRATION_CONTRACT.md` exists | Contract rules are documented, but no concrete client implementation/typed consumer exists | P0 | Implement client-side typed adapter once authoritative API DTO set is confirmed |
| Shared API schemas | v1 resource/resource-assignment/portability schemas exist | ProjectContext, stable ApplicationError, scheduling DTOs and complete mutation/sync API envelope are not represented as shared JSON schemas in `shared/contracts` | P0 / coordination | Coordinate with Hasan before changing authoritative shared contracts |
| Offline sync | Python client-sync models + regression tests exist | No Web/Desktop/Mobile consumer exists; no UI state mapping exists for queued/applied/replayed/conflict outcomes | P1 | Build a platform-neutral client sync state adapter; preserve existing server/core semantics |
| Scheduling integration | Shared scheduling core and extensive regression pack exist; 33.4.27 time-aware calendar extension is established | No client integration layer exists to display/submit scheduling data; time-aware contracts are not yet explicitly integrated into client APIs | P0 / coordination | Consume authoritative scheduling DTOs; do not invent client scheduling formulas |
| Cross-client parity | Tests exist for backend/client-sync contracts | No three-client parity suite can run because clients do not yet exist | P1 | Add parity fixtures/tests after first client contract adapters are created |
| Localization | Requirements and client READMEs define Persian/English + Jalali/Gregorian presentation | No implementation | P1 | Add shared presentation/formatting boundary; keep calendar arithmetic in Shared Core |
| CI | Project records runtime CI as not yet verified | Client tests cannot yet be meaningful without client implementations/toolchains | P1 | Add client test execution with the selected client stacks |

## Architectural guardrails

1. Client code must consume, not redefine, Shared Domain/Calculation Core semantics.
2. Web/Desktop/Mobile must use the same versioned Application/API contracts.
3. ProjectContext, revision, idempotency and stable error semantics must survive client boundaries.
4. Decimal-like values remain canonical decimal strings at API boundaries.
5. Client presentation may format dates/numbers, but calendar/scheduling/financial arithmetic remains authoritative elsewhere.
6. Desktop and approved Mobile offline planning must use the portable Shared Scheduling Core semantics, not a second scheduling engine.

## Current blocker / coordination item

The highest-priority implementation cannot safely invent the missing authoritative DTO semantics. The repository explicitly assigns backend/API/shared-contract ownership to Hasan/Developer 1. Before adding new authoritative schemas for ProjectContext, stable errors, scheduling DTOs or sync envelopes, the client track should consume the existing backend contracts or coordinate a documented contract change.

## Recommended execution order

1. Confirm the authoritative API DTO set and client contract versions with Hasan.
2. Establish Web/React/TypeScript, Desktop, and Mobile client foundations using the agreed stack.
3. Implement a shared typed contract adapter layer for ProjectContext, DTOs, errors, revisions and mutation idempotency.
4. Add scheduling read/recalculate integration against Shared Core/API contracts.
5. Add offline/online state + sync/conflict UX.
6. Add cross-client parity fixtures and regression tests.
7. Only then expand WBS/Gantt/dashboard/report/field workflows.

## Definition-of-done mapping

- Meaningful client integration has tests.
- All three clients consume the same versioned contracts.
- No authoritative calculation is duplicated in clients.
- Approved offline workflows reproduce Shared Core results.
- PR targets `main`.
- Shared semantic changes are documented and announced before becoming authoritative.
