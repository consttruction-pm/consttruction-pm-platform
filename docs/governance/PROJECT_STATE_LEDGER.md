# CUBI Project State Ledger

**Snapshot date:** 2026-10-25
**Repository:** `consttruction-pm/consttruction-pm-platform`
**State rule:** Only merged-main behavior counts as implemented completion. PR/branch and documentation-only progress is not product completion.

## Current baseline

| Item | Verified state |
|---|---|
| Current main SHA inspected at reconciliation | `4133dd8af6a98921c19f9049c1eb565a09dad6d2` (2026-10-25) |
| Default branch | `main` |
| CUBISITE schedule of record | Current ChatGPT Library search resolves `cubisite.xlsx` at 123,975 bytes (modified 2026-10-24); the Library result exposes `version_id=1`. The prior ledger's version-6 / 122,288-byte identity is not confirmed by the current Files result; verify whether the Library object/version metadata changed before declaring the mirrored workbook synchronized. |
| CUBISITE scope | Original T01–T45 retained; AI-C01–AI-C07 additive; risk reserve BUF retained separately |
| Schedule arithmetic | 193 active effort-days proposed (171 previous + 22 proposed AI), 25-day risk reserve, 218 total; 52 unique capability activity IDs plus BUF; active capability weights sum to exactly 100.00 points |
| Weighted progress | 26.89% formula estimate after denominator expansion; **not QA acceptance**. Prior 30.4% is historical only. All seven added AI activities keep earned completion at zero. |
| Forecast assumptions | One executor; half-day sequencing; Monday–Friday; excludes public holidays, leave and external waiting. Proposed base finish 2027-05-21; with 25-day risk reserve 2027-06-25. This is a forecast, not an approved contractual baseline. |
| CUBISITE exit gate | Full production site E2E and release sign-off remain open |

## Latest exact-main verification (2026-10-25)

The following GitHub Actions runs all target the inspected current main SHA `4133dd8af6a98921c19f9049c1eb565a09dad6d2`:

- [ConstructionPM CI #40143297145](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40143297145) — **PASS**.
- [PostgreSQL Sync State Integration #40143297002](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40143297002) — **PASS**.
- [Client Typecheck #40143297007](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40143297007) — **PASS**.
- [Deploy CUBI Web to GitHub Pages #40143297031](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40143297031) — **FAIL** at the Pages preflight/configuration boundary. The workflow reports that no readable Pages site is configured; resolving it requires repository Settings → Pages (Source: GitHub Actions) or the authorized `PAGES_ADMIN_TOKEN` secret. The available repository connector cannot change Pages settings or create secrets, so the live-site deployment remains **Blocked** and must not be described as released.
- No dedicated Web CI run is present in the exact-SHA run list above. The earlier Web CI success for `7606c8c...` is historical evidence only, not a fresh Web CI result for this SHA.

The newer main commit contains governance/Pages-diagnostic changes, not a new assistant capability. The assistant remains one authenticated `activity.create` vertical slice with proposal/approval/execute UI; model/provider orchestration, natural-language conversation, additional project tools, calculation-result grounding and full E2E remain open.

## Implementation evidence on main

### PR #1548 — SQLite Activity Master transaction ownership (merged)

- Merge SHA: `7eaeea4fda70f447c4ad1969d52a18ffaaac8ceb`
- Source: https://github.com/consttruction-pm/consttruction-pm-platform/pull/1548
- The repository commits/rolls back only a transaction it started itself. Caller-owned transaction boundaries survive successful writes and revision-conflict failures.
- Regression coverage includes outer rollback, revision conflicts, and rollback of a repository-owned failed write.

### PR #1547 — authenticated AI action runtime and Activity Master create (merged)

- Merge SHA: `259461b18d71d8185ad02cfb9f443e05cdad2648`
- Source: https://github.com/consttruction-pm/consttruction-pm-platform/pull/1547
- Tested code head: `bf110ac62b9ff88539ced03b6bd16952df83a4de`; its later commit only updated the integration document.
- Exact code-head checks: [ConstructionPM CI](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40139930835) — PASS on Python 3.11/3.12/3.13; [PostgreSQL Integration](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40139930827) — PASS; [Client Typecheck](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40139930828) — PASS for Web, Desktop, Mobile and Client Sync.
- Main post-merge check set on `259461b...` also passed ConstructionPM CI, Client Typecheck and PostgreSQL Sync State Integration.
- Implemented: authenticated proposal list/detail/create/approve/reject/execute; fail-closed server-owned registry; scope and grant rechecks; stale/denied/uncertain non-replayable states; explicit execution reservation; typed `activity.create` via existing `P6ActivityMasterAPI`; transaction-bound idempotency and audit; fresh-connection SQLite and live PostgreSQL read-back tests.
- Remaining: admin-authorized reconciliation of interrupted/uncertain actions; other mutation tools; scheduling recalculation and result grounding via the Shared Domain/Calculation Core; model/provider orchestration and conversation flow.

### PR #1550 — web action proposal/approval panel (merged)

- Merge SHA / current main SHA: `7606c8cea841fd18455b7c263ef3148251d7246d`
- Source: https://github.com/consttruction-pm/consttruction-pm-platform/pull/1550
- Tested PR head: `407b24dd4cc7b8417e850814dbfcdde384967877`.
- Exact PR head checks: [ConstructionPM CI](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40142349490) — PASS on Python 3.11/3.12/3.13; [Client Typecheck](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40142349499) — PASS for Web/Desktop/Mobile/Client Sync; [ConstructionPM Web CI](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40142349497) — PASS.
- Added typed client and localized English/Persian workspace panel for first `activity.create` proposal: prepare → inspect → explicit approve/reject → explicit execute. Stale, executing, blocked or uncertain records cannot be replayed through the panel. It fails honestly when server runtime isn't composed; no mock success is shown.
- Post-merge on current main `7606c8...`: [ConstructionPM Web CI](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40142526994) — PASS and [Client Typecheck](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40142527026) — PASS. [ConstructionPM CI](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40142526937) and [PostgreSQL Sync State Integration](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40142526995) were still running at snapshot time and must be recorded after completion.

### Release deployment — unresolved environment configuration

- [Deploy CUBI Web to GitHub Pages](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40142526930) built and tested the web app successfully, then failed at `actions/configure-pages@v5` with 404 `Get Pages site failed`; the job skipped site assembly, artifact upload and deploy.
- This is a repository Pages enablement/access configuration blocker, not a TypeScript/build/test failure. The workflow currently uses the default `GITHUB_TOKEN`; the official `actions/configure-pages` input contract says enabling a missing Pages site requires a token other than `GITHUB_TOKEN` with appropriate repository administration + Pages write permission. Do not mark website release complete until Pages configuration is fixed and the actual public deployment URL is smoke-tested.
- Issue #82 and the full-site E2E exit gate remain open.

## Explicitly open assistant V1 gaps

- Natural-language model/provider orchestration and a complete conversation turn are not wired; the merged panel covers only the first Activity Create action.
- WBS create/edit, activity edit, relationships, calendars, resources/cost and other project-control actions are not yet registered as production AI tools.
- The first create tool does not itself trigger a new authoritative Shared Core calculation run or return a revision-bound run ID plus grounded explanation/report.
- File/Excel/document/voice intake and mapping preview; report/chart/export integration; admin knowledge research/review and human publication; memory retention/deletion; backups/restore/migration; golden model/knowledge benchmarks and rollback remain open.
- `uncertain` and interrupted `executing` proposals are protected from blind retry, but no admin-authorized reconciliation/recovery workflow has been implemented.
- #1423, #1530 and #1540 remain open until a complete end-to-end acceptance path is proven.

## Canonical CUBISITE reconciliation

- Workbook version 6 (both Library paths) includes AI-C01–AI-C07; original T01–T45 and BUF are preserved; weight sum verified at exactly 100.00%.
- 52 capability IDs are unique; formula error scan found no `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?` or `#N/A` matches.
- The seven AI added activities remain proposed estimates with zero earned completion. Current 26.89% is a formula-derived forecast indicator only and is not QA-certified.
- The schedule remains a Library artifact, not a committed workbook in the repository. Preserve both paths as synchronized mirrors and keep the version and snapshot SHA aligned with this ledger.

## Other active pull requests / audits to reconcile

- #1545 — CUBISITE AI learning schedule addendum; do not treat it as replacing the whole website schedule.
- #1522 — option-level scheduling compatibility reference; resource-dependent behavior and calendar inheritance still need complete proof.
- #1520 — WBS persistence slice; not proof of complete WBS production UI.
- #1518 / #1511 / #1509 — resource-driving/leveling items remain gated by full end-to-end semantics and latest-head CI.
- #1519 — localization error-message slice; not proof of every-language coverage.
- #1486 — whole-product V1 Mobile requirement and continuity gate; separate from CUBISITE website schedule.
- #680 — evidence-based weighted progress rules; do not infer completion percentages from PR/commit counts.

## Required next actions

1. **Blocked on repository administration:** enable GitHub Pages with Source = GitHub Actions in repository Settings, or add the authorized `PAGES_ADMIN_TOKEN` secret; then rerun deploy and smoke-test the published site and `/app` routes. ChatGPT's available GitHub connection cannot alter these repository settings/secrets.
2. **Completed:** reconcile latest-main CI and PostgreSQL Sync State Integration at `4133dd8...` — both pass; Client Typecheck also passes. Exact run links are recorded above.
3. Implement the server-side model/provider orchestration and conversation endpoint around the proposal-only boundary; all side effects must still require explicit approval and current-scope authorization.
4. Implement authoritative reconciliation for interrupted/uncertain actions, then add WBS/relationship/calendar/resource/cost tools and Shared Core run/result grounding.
5. Keep #1423/#1530/#1540 and #82 open until the complete release acceptance suite, multilingual and Jalali/Gregorian coverage, import/export round-trip, and exact-main end-to-end gates pass.
