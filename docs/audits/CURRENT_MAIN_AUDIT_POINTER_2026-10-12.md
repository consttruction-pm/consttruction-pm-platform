# Historical Audit Pointer — 2026-10-12 (Superseded)

**HISTORICAL SNAPSHOT — not the live reporting pointer.** This document records the audit state at the 2026-10-12 cut-off and is superseded for current reporting by [Jalal 4 Progress Control — 2026-10-18](JALAL4_PROGRESS_CONTROL_2026-10-18.md). Its SHAs, Jalal 3 percentage and prior open-PR list must not be reported as current.

## Authoritative integration baseline

- Repository: `consttruction-pm/consttruction-pm-platform`
- Default branch: `main`
- Current main HEAD at this refresh: `6c18e6ff3410390075c70b57ea1b1d53224aa399`
- Latest product-code baseline remains `488e683a8a65e4316cc14b106cda0989784372bc` (`fix(backend): serialize unconfigured workspace read errors`); commits after it on main are audit-documentation-only.
- Weighted matrix commit: https://github.com/consttruction-pm/consttruction-pm-platform/commit/d5fdf4024e7adbd34d2a672678bb3bc385001e6c

This pointer refresh itself is documentation-only; use the product-code baseline above when determining whether implementation evidence changed.

## Weighted progress — reconciled against Jalal 3

- Governing source: Library workbook `جلال3_اصلاح_مبنای_پیشرفت_2026-10-10.xlsx`, sheet `جلال 3`, updated after GitHub reconciliation on 2026-10-10.
- The workbook contains 23 weighted activities, weights sum to 100.00%, and its `S5:S27` weighted contribution values sum to **59.50**.
- **Current Jalal 3 weighted implementation indicator: 59.50% complete / 40.50% remaining.**
- Per-activity weight, completion fraction, contribution, and owner subtotal are recorded in [the 2026-10-12 reconciliation matrix](WEIGHTED_PROGRESS_RECONCILIATION_2026-10-12.md).
- This is an implementation progress indicator, **not release readiness, production acceptance, or full P6 parity certification**.
- The 2026-10-08 59.41% snapshot is superseded by the 2026-10-10 Jalal 3 workbook; older Jalal 1/2 percentages are not comparable because their scope/weights differ.
- Activity-level weights, completion fractions, earned contribution, and owner subtotals are documented in [the 2026-10-12 reconciliation matrix](WEIGHTED_PROGRESS_RECONCILIATION_2026-10-12.md).
- Open/unmerged PRs contribute zero incremental completion until merged and validated. PRs #1368, #1371, #1375 and #1376 remain open; no additional weight was credited for them.
- The product-code tree has not changed since the `488e683...` baseline; subsequent main commits were documentation-only. The latest open PRs do not increase the current score.

## Current material acceptance gates

1. **Web Beta runtime / workspace data** — Issue #1359: PR #1375 adds a useful authenticated API-composition test, but its fixture still uses `InMemoryWorkspaceReadProvider`; production authoritative workspace provider and deployed runtime evidence remain outstanding.
2. **Canonical logo and homepage visual acceptance** — Issue #1327 / PR #1368: exact-head CI passed on the recorded PR SHA, but the PR remains open; source tests do not prove pixel-level match to the supplied reference or live deployment. Original reference images are not yet committed as binary assets in the repository.
3. **Resource leveling / resource identity** — PR #1371 remains draft and open; its recorded PostgreSQL integration pass is not proof of the full scheduling test matrix. PR #1373's workflow change does not certify PR #1371 behavior.
4. **P6 ScheduleOptions parity** — Issue #403 retains field-by-field semantic disposition, metadata classification, external-project option verification, and deterministic evidence requirements. PR #1376 improves typed array validation but explicitly does not resolve canonical `PriorityList`/`ResourceList` mapping.
5. **Calendar exception precedence** — Issue #1284 is closed, but closure alone is not evidence. Its acceptance should be considered verified only if the production resolver wiring and tests are present on current main; do not infer this from issue state.
6. **Weighted governance** — Issue #680 remains the governing reconciliation item; keep it open for continuing updates and evidence.

## Ownership / non-overlap

- Jalal: Shared Core calculation semantics, P6 semantic evidence, cross-module integration, and final acceptance.
- Hasan: backend, persistence, API composition, workspace runtime and database evidence.
- Farmj22002: assigned web branding/homepage implementation and Help Center lanes.
- Javad: read-only observer unless explicitly reassigned; do not assign execution ownership implicitly.

## Reporting rule

Publish separate figures for (a) overall product scope, (b) Web Beta, (c) source implementation, and (d) Shared Core/P6 parity only when each has a traceable weighted matrix and evidence. Never infer any of these from a single domain percentage. Recompute after each merge that changes a weighted capability; documentation-only commits do not change the capability score.
