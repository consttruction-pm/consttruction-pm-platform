# Hasan — Current Continuation / Backend Track

## Current baseline — 2026-09-27

- Repository: `consttruction-pm/consttruction-pm-platform`
- Branch: `main`
- Current main: `b74a761ad3993cef19dffccb509d53552621fedf`
- Latest completed backend change: PR #273, merged with main at the current baseline.
- PR #273 added authoritative Field Assurance transition enforcement at the backend application write boundary.
- PR #273 exact-head checks passed:
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

Open historical PRs are not part of the current baseline unless they are first reconciled against current `main` and their changes are proven still missing.

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

Remaining product gates recorded in `docs/roadmap/STAGE_STATUS.md` include:
1. Document / RFI / Submittal / document-linkage Web workflow.
2. Procurement / Commercial Commitments Web workflow.
3. AI Copilot / Smart Guide / voice presentation.
4. Web/Desktop/Mobile parity for newly integrated Control Room workflows.
5. Final Stage 34.3 integration/regression and runtime evidence reconciliation.

For Hasan, the backend action is to provide or verify the authoritative contracts/persistence/application boundaries required by those client slices, not to duplicate UI behavior.

## Current verified API/Web-readiness baseline

The current backend already has regression coverage for:
- ProjectContext and tenant/project scope;
- optimistic revision conflicts;
- idempotency replay and key-reuse rejection;
- authorization allow/deny and cross-scope rejection;
- typed/versioned resource DTOs;
- transaction rollback;
- Field Assurance transition validation at the authoritative write boundary;
- sync conflict/revision refresh contracts.

PR #273 confirms that invalid Field Assurance transitions are rejected before persistence while stale-revision behavior remains a conflict and idempotent replay remains safe.

## Immediate next execution rule

Before starting another feature:
1. Read this file and `docs/roadmap/STAGE_STATUS.md`.
2. Fetch current `main` SHA.
3. Check open PRs for whether the required behavior already exists.
4. Fetch the current file SHA before editing an existing file.
5. Implement only the first missing Hasan-owned backend boundary.
6. Add focused tests and documentation with the implementation.
7. Require GitHub Actions runtime verification before marking the gate complete.
8. Update this file and Stage Status with the exact verified commit/run identifiers.

## Hard boundaries

Never move these into API, persistence, Web, Desktop or Mobile:
- Primavera P6 scheduling semantics;
- calendar/duration calculations;
- Progress/EVM calculations;
- Resource/Cost calculations;
- financial formulas.

For shared semantics, Shared Core remains authoritative.

## Next point

The next Hasan-owned work should be selected from the first **actually missing** backend boundary supporting the remaining Stage 34.3 gates. Prefer Document/RFI/Submittal backend linkage or Procurement/Commercial backend integration only where current `main` does not already provide the required contract. Do not revive stale PRs merely because they remain open.

Historical note: the previous version of this continuation file contained stale PR #70/Stage 33.4.70 instructions; those instructions are superseded by this current-main baseline.
