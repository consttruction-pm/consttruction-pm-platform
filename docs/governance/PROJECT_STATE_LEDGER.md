# CUBI Project State Ledger

**Snapshot date:** 2026-10-25
**Repository:** `consttruction-pm/consttruction-pm-platform`
**State rule:** Only merged-main behavior counts as implemented completion. PR/branch and documentation-only progress is not product completion.

## Current reconciliation checkpoint — 2026-10-25, after PR #1571 merge

- **Latest code-bearing merge SHA:** `f4b51292e8e61124e64ae11e756e8cbad27f66d9`; PR #1571 is merged at this commit. A subsequent ledger-only commit records this checkpoint; it does not change application code. It integrates the generated public-safe schedule reference catalogue into the existing Web workspace without removing the schedule-cycle mountpoint. The catalogue exposes 72 requirement records, 18 formula contracts and 16 documentation-review tracks; its statuses explicitly distinguish mapped requirements from proven implementation.
- **Exact PR-head checks on `27b774bc8b2b3dd2dfa2ae2f70976126cb81a600`:** [ConstructionPM CI #40156394018](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40156394018) — PASS on Python 3.11/3.12/3.13; [ConstructionPM Web CI #40156394020](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40156394020) — PASS; [Client Typecheck #40156394102](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40156394102) — PASS. The earlier PR-head generator/catalogue mismatch was corrected and these final-head checks passed before merge.
- **Post-merge main checks on `f4b51292e8e61124e64ae11e756e8cbad27f66d9`:** Web CI, Client Typecheck and PostgreSQL Sync are PASS; Python 3.12 is PASS; Python 3.11 and 3.13 were still in progress at the last check. Recheck the exact main SHA's final status before making a full-green CI claim.
- **Release deployment remains blocked:** [Deploy run #40156478651](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40156478651) failed at the Pages preflight because the repository Pages site is not enabled/readable (HTTP 404 and no `PAGES_ADMIN_TOKEN`). The connection available for this task cannot change repository Settings or create repository secrets. An owner/admin must enable Settings → Pages → Build and deployment → Source = GitHub Actions or add the authorized `PAGES_ADMIN_TOKEN`; then rerun deploy and smoke-test the actual published URLs.
- **Calculation gate remains open:** PR #1570 for the limited Resource Dependent duration subset is not merged. Passing tests do not replace the mandated independent semantic review. Requests are pending from Hasan and Farmj; do not claim full Resource Dependent / resource-calendar compatibility until the required review and accepted test evidence are present.
- **CUBISITE accounting remains evidence-based:** merged reference UI is not scheduling-calculation completion; the Library workbook remains the website schedule of record, all seven AI-C01–AI-C07 activities remain zero earned completion until their own acceptance criteria are proven, and the overall production site E2E/release gate remains open.

## Resource Dependent snapshot-fact binding — 2026-10-25

- **State:** In progress; not merged and not counted as implemented on `main`.
- **PR:** [#1577](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1577), draft, branch `fix/resource-dependent-snapshot-facts`, base `main` at `52483e55e19b927cc392b86808d6ff484cb26215`.
- **Changed paths:** `src/construction_pm/scheduling/authoritative_schedule.py`, `src/construction_pm/authoritative_schedule_input_composer.py`, `src/construction_pm/schedule_snapshot_materializer.py`, `tests/scheduling/test_authoritative_schedule.py`, `tests/test_schedule_snapshot_materializer.py`.
- **Implemented in branch:** a typed immutable snapshot field captures Resource Dependent assignment facts; composer binds fresh persisted facts in stable assignment-ID order; canonical payload/hash includes driving flags and resource rate/calendar fields; materializer decodes the facts with strict boolean/identifier checks; regression tests verify that toggling `is_driving` changes the snapshot hash, duplicate/noncanonical assignment facts are rejected, and assignment facts cannot be attached to a Task Dependent or time-aware activity.
- **Verification:** exact-head CI passed on `96eef60145476880b1dbb682ab00d669a85581f8`: ConstructionPM CI #40206352614, Client Typecheck #40206352608, and PostgreSQL Integration #40206352664 all completed successfully. A new validation slice at `bf40b3c09322ac8de5e522b0e3124fefb1d4de34` now explicitly rejects assignment facts attached to a non-Resource Dependent activity type; the regression tests were updated to use a typed Resource Dependent activity. Exact-head ConstructionPM CI #40209386931, Client Typecheck #40209386846, and PostgreSQL Integration #40209386945 are queued; this latest slice is not yet verified. Local tests were not run in this connector session.
- **Not implemented:** calendar/capacity-aware independent nondriving assignment placement, driving-resource limiting-duration semantic review, assignment-level failure diagnostics, Schedule Query integration proof, and SQLite/PostgreSQL persisted-read → snapshot → calculation end-to-end tests. The current fail-closed nondriving guard remains required. Issue #1517 remains open.
- **Next action:** run and review exact-head CI plus snapshot materialization round-trip tests; only then proceed to the placement algorithm and full integration coverage.

## Current baseline

| Item | Verified state |
|---|---|
| Latest source-code SHA inspected at reconciliation | `f4b51292e8e61124e64ae11e756e8cbad27f66d9` (2026-10-25; PR #1571 merged; post-merge Python 3.11/3.13 checks were still running at last inspection) |
| Default branch | `main` |
| CUBISITE schedule of record | Current ChatGPT Library search resolves `cubisite.xlsx` at 123,975 bytes (modified 2026-10-24); the Library result exposes `version_id=1`. The prior ledger's version-6 / 122,288-byte identity is not confirmed by the current Files result; verify whether the Library object/version metadata changed before declaring the mirrored workbook synchronized. |
| CUBISITE scope | Original T01–T45 retained; AI-C01–AI-C07 additive; risk reserve BUF retained separately |
| Schedule arithmetic | 193 active effort-days proposed (171 previous + 22 proposed AI), 25-day risk reserve, 218 total; 52 unique capability activity IDs plus BUF; active capability weights sum to exactly 100.00 points |
| Weighted progress | 26.89% formula estimate after denominator expansion; **not QA acceptance**. Prior 30.4% is historical only. All seven added AI activities keep earned completion at zero. |
| Forecast assumptions | One executor; half-day sequencing; Monday–Friday; excludes public holidays, leave and external waiting. Proposed base finish 2027-05-21; with 25-day risk reserve 2027-06-25. This is a forecast, not an approved contractual baseline. |
| CUBISITE exit gate | Full production site E2E and release sign-off remain open |

## Historical exact-main verification before PR #1571 merge (2026-10-25)

The following code/test runs target earlier merged source SHA `8e39b3b38a43ef0f80c56e6d2b8deb93099c0172`. They are historical and are superseded by the current reconciliation checkpoint above:

- [ConstructionPM CI #40148225285](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40148225285) — **PASS** on Python 3.11, 3.12 and 3.13.
- [PostgreSQL Sync State Integration #40148225226](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40148225226) — **PASS**.
- [Client Typecheck #40148225224](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40148225224) — **PASS** for Web, Desktop, Mobile and Client Sync.
- The latest [ConstructionPM Web CI #40147792425](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40147792425) passed on the preceding assistant-Web merge SHA `d54e4b55...`. PR #1555 modifies only the Python HTTP request parser and its regression test; it did not change Web assets.
- [Deploy CUBI Web to GitHub Pages #40147792411](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40147792411) — **FAIL** at `Verify GitHub Pages configuration`; Pages configuration is still not enabled/readable. Configure repository Settings → Pages with Source = GitHub Actions or set the authorized `PAGES_ADMIN_TOKEN` secret, then rerun deployment and smoke-test the published site. The available repository connection cannot change repository settings or create secrets, so public deployment remains **Blocked**.

The CI results prove the tested code paths, not live deployment or full V1 acceptance. The repository currently has no Vercel project connected for this repo and no configured live authenticated backend/runtime host evidenced here. A working production provider, session/project selection, current AI grants, database transaction wiring and server-side `CUBI_AI_*` configuration remain necessary for live assistant acceptance.

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

### PR #1553 — authenticated natural-language assistant turn and Web chat (merged)

- Merge SHA: `d54e4b55bb13b0cd941eeb15a319541b505c3045`
- Source: https://github.com/consttruction-pm/consttruction-pm-platform/pull/1553
- Tested PR head: `4e628ff62005c231398dc9516f9e742816369cc9`; all four PR-head checks passed:
  - [ConstructionPM CI #40147683394](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40147683394) — PASS on Python 3.11/3.12/3.13.
  - [PostgreSQL Integration #40147683412](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40147683412) — PASS.
  - [Client Typecheck #40147683404](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40147683404) — PASS for Web/Desktop/Mobile/Client Sync.
  - [ConstructionPM Web CI #40147683411](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40147683411) — PASS.
- Post-merge exact-main checks are recorded above and all four code/test gates passed.
- Added explicitly opt-in HTTPS OpenAI-compatible JSON provider configuration; bounded request/history/provider response/tool payload/output tokens; rejected redirects and malformed language tags; sanitized provider errors.
- Added authenticated `POST /api/projects/{project_id}/ai/assistant/turn` with current project revision, audit events without prompt text, and a server-owned schema for the first supported mutation, `activity.create`.
- Read-only project members may use non-mutating turns but receive no action tools; proposal creation requires project-write access and current exact-scope AI grant. All mutations still require separate human approval and explicit execution through the existing runtime.
- Added English/Persian Web chat with an explicit provider data-flow notice, bounded session-only history, response-schema validation, localization-completeness gating for extension locales, and automatic action-panel refresh.
- This is one proposal-only assistant vertical slice, **not** full AI Assistant V1 and **not** proof that the live site/backend is deployed. Provider/runtime composition is opt-in; no production credentials were committed.

### PR #1555 — malformed UTF-8 handling for assistant turn (merged)

- Merge SHA: `8e39b3b38a43ef0f80c56e6d2b8deb93099c0172`
- Source: https://github.com/consttruction-pm/consttruction-pm-platform/pull/1555
- Tested PR head: `2e0d5c8df78cd943042799642f0ff8caadcd9b39`; [ConstructionPM CI #40148146843](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40148146843) passed on Python 3.11/3.12/3.13 and [Client Typecheck #40148146813](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40148146813) passed.
- The authenticated assistant turn now catches `UnicodeDecodeError` as well as malformed JSON and returns `400 AI_ASSISTANT_REQUEST_INVALID` before contacting the provider or creating a proposal. A regression test proves no provider call or mutation occurs for invalid UTF-8 bytes.
- This is an input-hardening fix only and does not add assistant capabilities or release-completion credit.

### PR #1550 — web action proposal/approval panel (merged)

- Merge SHA: `7606c8cea841fd18455b7c263ef3148251d7246d` (historical; superseded by later merges)
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

- The first natural-language model/provider turn and bilingual Web chat are now merged (PR #1553), but production deployment wiring, provider credentials, current grant-provider setup and an authenticated backend host are not verified on a live service. Conversation history remains browser/session memory, not a durable transcript.
- WBS create/edit, activity edit, relationships, calendars, resources/cost and other project-control actions are not yet registered as production AI tools.
- The first create tool does not itself trigger a new authoritative Shared Core calculation run or return a revision-bound run ID plus grounded explanation/report.
- File/Excel/document/voice intake and mapping preview; report/chart/export integration; admin knowledge research/review and human publication; memory retention/deletion; backups/restore/migration; golden model/knowledge benchmarks and rollback remain open.
- `uncertain` and interrupted `executing` proposals are protected from blind retry, but no admin-authorized reconciliation/recovery workflow has been implemented.
- #1423, #1530 and #1540 remain open until a complete end-to-end acceptance path is proven.

## Canonical CUBISITE reconciliation

- The latest recovered CUBISITE Library workbook is version 7; it includes AI-C01–AI-C07 while preserving original T01–T45 and BUF. The weight sum was verified at exactly 100.00% in the recovered workbook; repository/Library mirror synchronization remains unverified.
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

1. **Still blocked on repository administration:** the post-merge deploy run #40147792411 again failed at Pages preflight. Enable GitHub Pages with Source = GitHub Actions in repository Settings, or add the authorized `PAGES_ADMIN_TOKEN` secret; then rerun deploy and smoke-test the published site and `/app` routes. This connection cannot alter repository settings/secrets.
2. **Completed on the latest source head verified in this ledger:** ConstructionPM CI #40148225285, PostgreSQL Sync State Integration #40148225226 and Client Typecheck #40148225224 pass on `8e39b3b38a43ef0f80c56e6d2b8deb93099c0172`. ConstructionPM Web CI #40147792425 passed on preceding Web SHA `d54e4b55bb13b0cd941eeb15a319541b505c3045`; PR #1555 changed only Python request parsing/tests. Confirm current `main` SHA and its checks before treating these results as latest.
3. **Code slice completed:** PR #1553 adds the proposal-only server-side provider orchestration and authenticated conversation endpoint. Next, wire it into a real deployed backend with production session/project selection, current grant provider, transaction manager and approved server-side `CUBI_AI_*` configuration; verify the live conversation → proposal → approve → execute → fresh-read path.
4. Implement authoritative reconciliation for interrupted/uncertain actions, then add WBS/relationship/calendar/resource/cost tools and Shared Core run/result grounding.
5. Keep #1423/#1530/#1540 and #82 open until the complete release acceptance suite, multilingual and Jalali/Gregorian coverage, import/export round-trip, and exact-main end-to-end gates pass.
