# Team Execution Plan — Priority / Ownership / Collision Control

## Status
Effective immediately. This document supersedes ambiguous branch-level task ownership while preserving the 3-person role boundaries in `docs/team-responsibilities.md`.

## Priority order
1. **P0 — Current release gate:** Stage 33.4.73 PostgreSQL Atomic Idempotency Verification Hardening.
2. **P0 — Integrity:** CI/runtime failures, stale/non-mergeable branches, duplicate implementations, and regression repair.
3. **P1 — Scheduling authority:** Stage I completion (Query → Real Scheduling), then Stage J End-to-End Evidence.
4. **P1 — P6 parity contracts:** semantics → persistence/API → client UX, in that order.
5. **P2 — Web Beta / UI expansion:** only after authoritative contracts and release-gate work are stable.
6. **P2 — New feature work:** no new parallel feature stream may bypass the above gates.

## Ownership and collision rules
- **Jalal:** Shared Core, scheduling semantics, P6 semantic authority, integration, conformance and final acceptance.
- **Hasan:** PostgreSQL, persistence, API/application boundaries, synchronization/idempotency, import/export persistence.
- **Javad:** Web/Desktop/Mobile UX, workspace/grid/layout/formula-editor presentation, consuming authoritative contracts.
- No person may create a second implementation of an existing authoritative calculation/contract.
- A dependent task starts only after its upstream contract is present on current `main`.
- A branch older than 20 commits behind `main`, or containing a superseded implementation, must be rebased/reconciled or closed before more work continues.
- One logical area has one active implementation branch at a time. Follow-up fixes use a fresh branch from current `main`.
- Do not merge large stale branches merely to preserve history; port the still-valid work onto current `main`.
- Every PR must declare: stage, owner, upstream dependency, touched boundary, and validation evidence.

## Current stream disposition
### Hasan
- Finish/verify Stage 33.4.73 PostgreSQL atomic idempotency.
- Do not continue the obsolete authoritative-schedule-materializer branch; the current authoritative materializer/evaluator path is already on `main`.
- Backend P6 persistence/API work may proceed only where it does not duplicate current core semantics.

### Jalal
- Complete Stage I safely.
- Then execute Stage J End-to-End Evidence.
- Maintain scheduling/P6 semantic authority and perform integration review before dependent client work is accepted.

### Javad / client stream
- Continue only against contracts already present on current `main`.
- The Farmj P6-3 work has been reconciled into PR #483 from current `main`; do not continue the stale Farmj branch.
- Workspace/layout/formula-editor UX must consume Shared Core Field Registry and Formula contracts; no client-side calculation authority.

## Branch hygiene
- Stale branches are historical evidence, not active workspaces.
- Active work must be visible through an open PR based on current `main`.
- Before starting a task, compare its branch to `main` and check changed files against active PRs.
- If overlap exists, consolidate rather than parallelize.

## Acceptance gates
A stage is not complete until:
1. focused tests pass;
2. relevant regression suite passes;
3. PostgreSQL-backed claims have real PostgreSQL evidence;
4. source/contract/evidence provenance is present where required;
5. the PR is based on current `main`;
6. no active duplicate implementation remains.

## Immediate next sequence
**33.4.73 → CI/branch hygiene → Stage I → Stage J → P6 parity integration → Web Beta expansion.**
