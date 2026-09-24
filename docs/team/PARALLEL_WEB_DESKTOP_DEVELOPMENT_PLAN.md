# Parallel Web + Desktop Development Plan

## Objective
Build the ConstructionPM Website/Web Application and Desktop Application in parallel from the existing project, with the same capabilities, shared calculation logic and compatible data contracts.

## Repository organization
- `shared/` — shared contracts, calculation rules, schemas and cross-client specifications.
- `apps/web/` — Website/Web Application client.
- `apps/desktop/` — Desktop Application client.
- `src/` — current Domain/Application/Infrastructure implementation; shared business logic remains here until extracted into the final shared package boundaries.
- `tests/` — shared and integration regression tests.
- `docs/` — architecture, product, developer and parity specifications.

## Division of work

### User — Product/Client Track
Owns:
- Web Application UI/UX and client integration.
- Desktop Application UI/UX and client integration.
- Shared navigation, workspace, WBS/Activity views, Gantt presentation, dashboards, reports/print presentation.
- Client-side localization and Jalali/Gregorian presentation.
- Client-side AI Smart Guide presentation and voice-entry UX.
- Client integration tests and cross-client visual/workflow parity.
- Product acceptance against the finalized requirements.
- No client-side reimplementation of scheduling, progress, EVM, resource or cost calculations.

### Hasan — Backend/Platform Track
Owns:
- Shared Domain/Application contracts assigned to backend.
- API contracts and adapters consumed by both Web and Desktop.
- Database/repository/persistence.
- Tenant/company/project context isolation.
- Transactions and optimistic locking.
- Resource/Cost backend and integration.
- Import/export backend contracts.
- Document storage/application services.
- Backend AI service contracts.
- Integration/regression tests for backend and cross-module behavior.
- Documentation of every shared semantic change and explicit announcement to the user/product owner.

## Parallel delivery model
Every feature is delivered as a vertical slice:
1. Define shared business contract.
2. Implement authoritative calculation/domain behavior.
3. Implement API/Application contract.
4. Hasan integrates backend/persistence.
5. User integrates Web client.
6. User integrates Desktop client.
7. Run shared calculation tests.
8. Run Web/Desktop parity tests.
9. Review and merge.

## Current priority
Start with the existing Stage 33.2 integration hardening and then expose the stable contracts to both clients. Do not start a second independent calculation engine for either client.

## Branch policy
Recommended branches:
- `feature/web/<feature>`
- `feature/desktop/<feature>`
- `feature/shared/<feature>`
- `feature/hasan/<feature>`
- `feature/integration/<feature>`

No direct client branch may change Shared Calculation Core semantics without a dedicated shared change and review.

## Definition of Done
A feature is complete only when Web and Desktop have the same business capability, use the same authoritative calculations, preserve typed data, respect permissions/context, and pass the applicable shared regression/parity tests.
