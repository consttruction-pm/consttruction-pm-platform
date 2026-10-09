# Current-main Audit Pointer — 2026-10-10

This document is the governance pointer for the repository integration state. It must be refreshed whenever `main` advances; a recorded percentage is not current unless its weighted evidence has been reconciled against this exact SHA.

## Authoritative main

- Repository: `consttruction-pm/consttruction-pm-platform`
- Current `main` HEAD verified for this audit: `82ae12a252b2a0d88c700656cdf5bbe2b151a710`
- Commit subject: `docs: record P6 timezone-safe datetime merge`
- Commit timestamp: 2026-10-09 22:29:49 UTC
- Current-main is the only integration baseline. Older SHAs in historical audit documents remain historical checkpoints.

## Weighted progress authority

- Governing weighting source: **Jalal 3**, subject to reconciliation against the current-main SHA above.
- The previously recorded snapshot **59.41% weighted complete / 40.59% remaining**, dated 2026-10-08, is a **historical snapshot only**. It has not been revalidated against the current-main SHA and must not be presented as today's completion percentage.
- Do not publish a current weighted completion percentage until the approved Jalal 3 weights and each capability's evidence have been reconciled to this exact `main` SHA.
- Progress rule: only merged work with independent verification can contribute. Open/unmerged PRs, issue counts, commit counts, file counts, additions/deletions, and duplicate or superseded work do not contribute by themselves.
- A verified capability without an approved distinct sub-weight may be recorded as verified work, but must not receive an invented incremental percentage.

## Open audit gates

- **Dashboard / Issue #1359:** `/api/v1/workspace/control-room/read` exists, but the inspected `InMemoryWorkspaceReadProvider` is a reference adapter, not evidence of production persistence or an authenticated production dashboard. Require authoritative provider composition and runtime proof before marking the dashboard production-verified.
- **Branding / PR #1368:** the logo candidate is open and unmerged. Its reported CI checks are green, but there is no submitted review in the last audit, and CI does not prove visual acceptance or deployment. Do not claim the updated logo is live until the PR is merged and the Pages deployment and live site are checked.
- **GitHub Pages:** `.github/workflows/deploy-pages.yml` defines a deployment on relevant pushes to `main` and manual dispatch. A successful Pages deployment run and live-site verification have not been established by this audit; ordinary CI success is not deployment evidence.
- **Repository governance:** the last inspected branch metadata reported branch protection and required status-check enforcement disabled. Recheck settings before relying on required-review or required-check safeguards.

## Active Jalal lanes

- Issue #1251 — calculation identity vs provenance policy.
- Issue #1226 — cross-platform P6 field/column/formula contract parity.

Issue #1249 was recorded as closed after #1314 and #1316 were merged and independently verified on the then-current `main`; revalidate only if new evidence changes that disposition. PR #1313 was recorded as superseded by #1316.

## Acceptance rule

For each reported capability, assign one evidence-based state: **Verified**, **In Progress**, **Audit Required**, or **Gap**. Record the exact commit/PR and test/runtime evidence. Reconcile the approved weights before reporting a current percentage. Required CI evidence must correspond to the latest PR head SHA; earlier successful checks do not satisfy the latest-head requirement.
