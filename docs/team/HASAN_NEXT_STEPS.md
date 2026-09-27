# Hasan — Current Continuation / Backend Track

## Current baseline — 2026-09-27

- Repository: `consttruction-pm/consttruction-pm-platform`
- Branch: `main`
- Current main baseline at this reconciliation: `d7c5e8231ab3b25b3c283ee8901b068577fa25c7`
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

## Latest reconciliation — Stage 87

- PR #314 is already merged to `main` with merge commit `d7c5e8231ab3b25b3c283ee8901b068577fa25c7`.
- Its exact implementation head `cec20048e0eed2f80043d39ef85f5ebc460ac508` passed Client Typecheck run `36342222863` and ConstructionPM CI run `36342222381`.
- Stage 87 strict language-pack manifest validation, canonical signing-payload verification, integrity-boundary validation and activated-manifest snapshot protection are therefore already present on current `main`.
- PR #319 was a duplicate rebase attempt and has been closed without merge after current-main inspection proved the Stage 87 implementation was already present.

## Next point

Select the first **actually missing** Hasan-owned backend boundary supporting the remaining Stage 34.3 gates. Document/RFI/Submittal backend Application/API boundary is now implemented and runtime-verified through PR #280. The Procurement/Commercial read integration is implemented and runtime-verified through PR #286. The Schedule Query Application/API boundary is now implemented and runtime-verified through PR #295. For the remaining Stage 34.3 voice/presentation and cross-client parity gates, first verify whether the missing work is client/provider-adapter ownership per `VOICE_INTERACTION_BOUNDARY.md`; do not create a backend duplicate unless a concrete authoritative contract/application gap is found.

Do not revive stale PRs merely because they remain open.

Historical note: the previous version contained stale PR #70/Stage 33.4.70 continuation instructions; those are superseded by this current-main baseline.


### Latest reconciliation — Dependency Graph API boundary (PR #328)

- PR #328 is merged to `main` with merge commit `93af2ca34e3143d0e8a1bb456645c4b3282c61b1`.
- Exact implementation head: `05df8d1d7a6f237cad61514321ff3c336f51db05`.
- ConstructionPM CI run `36346154172` completed successfully.
- Client Typecheck run `36346154198` completed successfully.
- The new `dependency-graph.v1` API adapter delegates authorization, revision, idempotency and transaction semantics to the existing Application boundary and does not introduce Scheduling/P6, Calendar/Duration, Progress/EVM, Resource/Cost or financial calculations.
- The previously stale PR #326 is superseded and must not be revived.

## Next point

After PR #328, re-check current `main` and open PRs for the first actually missing Hasan-owned backend boundary. Do not invent a new numbered roadmap stage or duplicate client/provider-owned voice/parity work without a concrete authoritative backend gap.


### Latest reconciliation — Dependency Graph revision provenance (PR #331)

- PR #331 is merged to `main` with merge commit `0c713bac98e1ec3939c0368bd77941b578865103`.
- Exact implementation head: `869e17ae406a5d5e03257c47fe3786202678f31d`.
- ConstructionPM CI run `36346728936` completed successfully.
- Client Typecheck run `36346728879` completed successfully.
- The API now preserves `source_revision` and `target_revision` already supported by the authoritative DependencyLink persistence model, with focused validation and regression coverage.

## Next point

Re-read current `main`, Hasan's execution instructions and open PRs before the next implementation. Treat stale PRs as evidence only; implement only a concrete missing authoritative backend boundary.


### Latest reconciliation — Stage 34.3 cross-client voice adapter parity (PR #334)

- PR #334 is merged to `main` with merge commit `3942d9fd2df466e8c9c09157a80a0b979b12b9da`.
- Exact implementation head `3e58a0c1744ad92fa6a8a62d68b78741cb567f72` passed Client Typecheck run `36347809502` and ConstructionPM CI run `36347809550`.
- Desktop and Mobile now expose provider-neutral voice adapter wrappers that delegate normalization, scope validation and voice-output capability checks to the shared client-sync boundary.
- No backend voice endpoint, ASR/TTS provider, device permission, codec, cloud endpoint or Scheduling/P6 calculation was introduced.

## Next point

Re-read current `main`, Hasan execution instructions and open PRs before the next implementation. Cross-client voice adapter parity is now runtime-verified; remaining Stage 34.3 voice work is provider-specific/client UX work unless a concrete authoritative backend contract/application gap is demonstrated. Do not invent a new numbered roadmap stage or duplicate provider/client-owned work.


### 2026-09-27 — Portfolio Query Application/API Boundary (PR #336)
Status: **100% — merged and runtime-verified**
- Added the missing Hasan-owned versioned `portfolio-control-snapshot.v1` Application/API boundary over the existing authoritative Portfolio Control Snapshot/read-model provider.
- The boundary enforces tenant scope and `project.read` authorization, validates provider output, and preserves project/source revisions without recalculating portfolio metrics.
- PR #336 exact implementation head `a1d81740719827e0ed91ca4a075bf631abc64405` passed Client Typecheck run `36348158270` and ConstructionPM CI run `36348158292`.
- Merge commit: `181d00bb583d5a523ee0479c72e896caff3df61a`.
- No Scheduling/P6, Calendar/Duration, Progress/EVM, Resource/Cost or financial calculation semantics were moved into the API/application layer.

## Next point

Re-read current `main`, Hasan execution instructions and open PRs before the next implementation. Portfolio Query Application/API is now runtime-verified; select the next concrete missing Hasan-owned boundary only after reconciling the current contracts, application, persistence and integration state. Do not invent a numbered roadmap stage or duplicate client/provider-owned work.
