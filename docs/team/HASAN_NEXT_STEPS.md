# Hasan — Current Continuation / Backend Track

## Current baseline — 2026-09-27

- Repository: `consttruction-pm/consttruction-pm-platform`
- Branch: `main`
- Current main baseline at this reconciliation: `f008f4d20b797b7fc8c7fbe4b9af37fd96d9716d`
- Latest completed backend change in the preceding baseline: PR #273, merged after its exact-head CI passed.
- PR #273 added authoritative Field Assurance transition enforcement at the backend application write boundary.
- Exact-head checks for PR #273 passed:
  - ConstructionPM CI run `36306525146`
  - Client Typecheck run `36306525137`
- Stage 33.4.72–33.4.73 atomic sync/idempotency hardening is already runtime-verified through PR #171.
- Job-Step Transaction & Replay Boundary is already runtime-verified through PR #206.

## Do not repeat

Do not restart or reimplement:
- PR #70/client-sync queue work.
- Stage 33.4.69 end-to-end sync outcome work.
- Stage 33.4.70 authoritative revision refresh work.
- Stage 33.4.72–33.4.73 PostgreSQL/SQLite atomic idempotency hardening.
- PR #273 Field Assurance write-boundary guard.
- Existing Field Operations / Field Assurance persistence contracts.

Open historical PRs are not part of the current baseline unless first reconciled against current `main` and their changes are proven still missing.

## Current ownership

Hasan owns Backend / Database / Application / API / Enterprise Integration.

The backend must:
- preserve tenant/project context;
- preserve revision and optimistic-lock semantics;
- preserve idempotency and replay behavior;
- preserve transaction and audit boundaries;
- expose versioned typed contracts;
- keep authoritative business calculations in Shared Core;
- provide persistence/API support for Web/Desktop/Mobile without duplicating client calculations.

## Current Stage 34.3 backend support

Stage 34.3 Web/Site Experience is runtime-verified through 2026-09-27 for the completed Control Room and Field workflow slices.

Remaining Stage 34.3 product gates recorded in `docs/roadmap/STAGE_STATUS.md` are:
1. Voice interaction / speech-to-command UX against versioned query/action contracts.
2. Web/Desktop/Mobile parity for the expanded Control Room workflows.
3. Final Stage 34.3 integration/regression and runtime evidence reconciliation.
Document/RFI/Submittal, Procurement/Commercial, and AI Smart Guide/schedule-query request composition are already implemented and runtime-verified through PRs #280, #281, and #283.

For Hasan, the backend action is to provide or verify the authoritative contracts/persistence/application boundaries required by those client slices, not to duplicate UI behavior.

## Verified API/Web-readiness baseline

Current regression coverage already verifies:
- ProjectContext and tenant/project scope;
- optimistic revision conflicts;
- idempotency replay and key-reuse rejection;
- authorization allow/deny and cross-scope rejection;
- typed/versioned resource DTOs;
- transaction rollback;
- Field Assurance transition validation at the authoritative write boundary;
- sync conflict/revision refresh contracts.

PR #273 confirms invalid Field Assurance transitions are rejected before persistence while stale-revision behavior remains a conflict and idempotent replay remains safe.

## Immediate execution rule

Before starting another feature:
1. Read this file and `docs/roadmap/STAGE_STATUS.md`.
2. Fetch current `main` SHA.
3. Check open PRs for whether the required behavior already exists.
4. Fetch the current file SHA before editing an existing file.
5. Implement only the first missing Hasan-owned backend boundary.
6. Add focused tests and documentation with the implementation.
7. Require GitHub Actions runtime verification before marking the gate complete.
8. Update this file and Stage Status with exact verified commit/run identifiers.

## Hard boundaries

Never move these into API, persistence, Web, Desktop or Mobile:
- Primavera P6 scheduling semantics;
- calendar/duration calculations;
- Progress/EVM calculations;
- Resource/Cost calculations;
- financial formulas.

Shared Core remains authoritative for shared calculation semantics.

## Next point

Select the first **actually missing** Hasan-owned backend boundary supporting the remaining Stage 34.3 gates. Document/RFI/Submittal backend Application/API boundary is now implemented and runtime-verified through PR #280. The Procurement/Commercial read integration is implemented and runtime-verified through PR #286. The Schedule Query Application/API boundary is now implemented and runtime-verified through PR #295. For the remaining Stage 34.3 voice/presentation and cross-client parity gates, first verify whether the missing work is client/provider-adapter ownership per `VOICE_INTERACTION_BOUNDARY.md`; do not create a backend duplicate unless a concrete authoritative contract/application gap is found.

Do not revive stale PRs merely because they remain open.

Historical note: the previous version contained stale PR #70/Stage 33.4.70 continuation instructions; those are superseded by this current-main baseline.
