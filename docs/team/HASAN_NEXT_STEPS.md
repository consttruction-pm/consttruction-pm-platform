# Hasan — Next Steps / Continuation Note

## Purpose

This file is the authoritative continuation note for Hasan (Developer 2 / Client Integration track). It records exactly where to continue after PR #70 and prevents repeating completed client-sync work.

## Current repository state

- Repository: `consttruction-pm/consttruction-pm-platform`
- Main branch: `main`
- Latest checked main commit: `337429eae619e820d6167950a191880663d11ecf`
- Current project stage: **Stage 33.4 — System Integration & Platform Hardening**
- Latest documented completed gate: **Stage 33.4.69 — End-to-End Client Sync Outcome Regression**
- Stage 33.4.69 is documented as **100% runtime-verified**.
- The next documented gate is:
  **validate conflict/revision behavior against the real Application/API mutation boundary and ensure Web/Desktop/Mobile runtime adapters consume the same versioned outcome contract.**

## PR #70 status

PR #70:
- Title: `feat(client-sync): add authoritative outcome adapter boundary`
- Author: Hasan
- URL: https://github.com/consttruction-pm/consttruction-pm-platform/pull/70
- PR purpose: bridge `sync-outcome.v1` to authoritative `client-sync-outcome.v1` without duplicating business logic.
- Conflict was resolved once by reconciling the branch with the then-current `main`.
- Resolved head commit created during that repair: `d926748d3019f11b94e6f9e34a42313906b51090`.
- The PR was marked ready for review and an approval was submitted at that head.
- CI was queued for that repaired head at the time of the check.

### Important: main moved again

After the PR repair, `main` advanced to `337429eae619e820d6167950a191880663d11ecf`.

A fresh comparison currently shows:
- `main` is ahead of Hasan's branch by **3 commits**.
- Hasan's branch is ahead of `main` by **6 commits**.
- Therefore the branch is **diverged again**.

### First action before any new feature work

Do NOT start a new feature from the stale branch.

1. Fetch the latest `main`.
2. Reconcile/rebase the PR #70 branch against the latest `main`.
3. Preserve the two functional parts of PR #70:
   - `toAuthoritativeSyncOutcome()`
   - `fromAuthoritativeSyncOutcome()`
   - their regression tests.
4. Preserve the latest `main` implementation of `OfflineMutationQueue.retryAtRevision()`.
5. Do not re-introduce code that is already present in current `main`.
6. Run both:
   - `apps/client-sync` TypeScript typecheck/tests
   - Python integration/unit tests relevant to client-sync.
7. Push the reconciled branch and verify GitHub Actions before requesting/keeping approval.

## Do not change

Hasan must not redefine or duplicate:
- Scheduling/P6 semantics
- Shared calendar arithmetic
- Progress/EVM calculations
- Resource/Cost calculations
- authoritative business calculations inside Web/Desktop/Mobile clients
- Application/API/Repository boundary responsibilities
- versioned shared contract meanings

Client code remains an integration/presentation/transport consumer of the Shared Core and versioned contracts.

## Next development gate after PR #70

### Stage 33.4.70 — Real Application/API Conflict + Revision Boundary

Goal:

Connect the already-tested client conflict/outcome adapters to the real versioned Application/API mutation path.

Required sequence:

### A. Real conflict contract verification
Verify that a stale revision from the Application layer reaches the clients as the expected versioned outcome:
- mutation identity preserved
- tenant/project identity preserved
- expected revision preserved
- actual/server revision represented where the authoritative contract provides it
- stable `STALE_REVISION` error mapping preserved
- conflict action semantics preserved

### B. Retry semantics
The client must not invent a new retry protocol.

Use the existing shared semantics:
- `ACKNOWLEDGED` / authoritative `applied` or `replayed` => remove pending mutation
- `RETRY` => retain mutation and retry according to the existing retry policy
- `CONFLICT` => retain mutation and require refresh/reconciliation
- `REJECTED` => retain enough state for user-visible resolution/audit according to existing application rules

A lossy status mapping must fail explicitly rather than silently changing semantics.

### C. Revision refresh path
Implement/test the client flow:

`pending mutation -> API submit -> STALE_REVISION -> refresh authoritative revision/context -> explicit retry`

The refresh step must obtain authoritative project state; it must not locally guess or increment the revision.

### D. Cross-client parity
The same authoritative outcome contract must be consumed consistently by:
- Web
- Desktop
- Mobile

Add parity tests proving that all three clients preserve the same:
- status/disposition
- error code
- mutation identity
- operation
- idempotency identity
- revision context
- available conflict actions

Only UI presentation may differ.

### E. End-to-end tests
Add deterministic tests for at least:
1. successful apply
2. idempotent replay
3. transient retry
4. stale revision conflict
5. rejected mutation
6. conflict followed by authoritative refresh and retry
7. wrong tenant/project context rejection
8. idempotency-key mismatch
9. operation mismatch
10. no duplicate business calculation in any client

## Expected implementation boundaries

Preferred path:

- Shared contract: `shared/contracts/`
- Client sync adapter/runtime: `apps/client-sync/`
- Web integration: `apps/web/`
- Desktop integration: `apps/desktop/`
- Mobile integration: `apps/mobile/`
- Application/API authority: `src/construction_pm/client_sync/`
- Regression tests: `tests/integration/` and client package tests

Do not move authoritative conflict/revision reconciliation into a UI component.

## Working rules for Hasan

Before every task:
1. Read this file.
2. Read `docs/roadmap/STAGE_STATUS.md`.
3. Fetch the current `main` SHA.
4. Fetch the current file SHA before editing an existing file.
5. Check whether another developer already implemented the required behavior.
6. Make the smallest coherent change.
7. Add tests with the implementation.
8. Update Stage Status when the gate is actually completed and verified by CI.

## Definition of Done for Stage 33.4.70

Stage 33.4.70 is complete only when:
- PR #70 is reconciled with the latest `main`.
- Existing PR #70 semantics remain intact.
- Real Application/API stale-revision behavior is covered end-to-end.
- Web/Desktop/Mobile consume the same versioned outcome semantics.
- Refresh-before-retry is authoritative and deterministic.
- No client duplicates Shared Core business calculations.
- Required Python and TypeScript tests pass.
- GitHub Actions runtime verification succeeds.
- `docs/roadmap/STAGE_STATUS.md` is updated with the verified commit/run identifiers.

## Immediate next step

**First reconcile PR #70 with the latest `main`. Do not start Stage 33.4.70 implementation on the currently diverged branch.**

After PR #70 is clean and CI-verified, begin Stage 33.4.70 from the real Application/API conflict + revision boundary, not from another queue rewrite.
