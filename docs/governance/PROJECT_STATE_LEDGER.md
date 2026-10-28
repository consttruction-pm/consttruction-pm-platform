# CUBI Project State Ledger

**Snapshot date:** 2026-10-25
**Repository:** `consttruction-pm/consttruction-pm-platform`
**State rule:** Only merged-main behavior counts as implemented completion. PR/branch and documentation-only progress is not product completion.

## Review-split checkpoint — 2026-10-26 (layout-concurrency fix `4b140c89` plus the evidence head on PR #1583; full-stack preview and Web slices; not merged)

- **Branch:** `feat/full-stack-preview-workspace`, split from the over-coupled PR #1582 so the preview/Web delivery can be reviewed and merged independently. It carries the preview runtime, formula validation panel, interchange panel, typed effective-dated capacity, typed Jalali entry, durable layout history and explicit revision restore. The Resource Dependent placement and AI execution-verification work remains on PR #1582 (`fix/resource-dependent-nondriving-leveling`) and is deliberately not claimed here. Review PR: #1583.
- **Typed Jalali entry:** DATE_BASED schedule settings render the persisted start in the selected display calendar, accept a typed Jalali date, convert it to the canonical ISO value on the server, and fail closed with `INVALID_PROJECT_START` for impossible dates without mutating stored data. Time-aware settings keep the ISO control; other workspace date cells remain read-only display values.
- **Durable layout history:** the layout repository/API/HTTP route exposes `GET .../p6/layouts/{scope}/{view}/revisions` as an append-only, newest-first `p6-layout-definition-api.v1` envelope with read-permission and scope checks. The Web field chooser loads that history, offers Undo/Redo with localized notices, and a revision picker that restores any older revision by saving it as a new head revision. Every undo, redo and restore appends a revision; prior rows are never rewritten, and undo remains available after a full browser reload. Layout notices survive the asynchronous history prefetch so the outcome is not erased before it can be read.
- **Concurrency review fix (`4b140c89`):** the store previously compared a two-field slice with the three-field encoded row, so an identical retry never matched and stale writers were always labelled immutable. A single `_decide_write` helper now classifies retries, appends, immutable revisions and stale bases for both SQLite and PostgreSQL; a matching retry writes nothing, a stale base or revision gap returns `REVISION_CONFLICT`, and changing an already-published revision returns `IMMUTABLE_LAYOUT_REVISION`. The layout POST maps both to HTTP 409 with `error.p6.layout.conflict`. The Web client reloads the authoritative head for either code and shows the localized conflict notice instead of dropping history as a generic failure. Typed Jalali/datetime input now clears a stale canonical ISO value when parsing fails.
- **Local verification on this split branch:** full Python `2781 passed, 126 skipped, 2 warnings` (the RD/AI-specific tests are intentionally absent); focused layout repository/API/HTTP/PostgreSQL-twin `100 passed, 1 skipped`; Web `323` TypeScript tests plus `7` preview-resolver tests; `npm run typecheck` and `npm run build` passed; isolated browser E2E `36 checks, 25 screenshots` on `bde7ef73` (the artifacts' `evidence.json` records that `git_head`) with temporary SQLite and random loopback port, including undo → redo → restore older revision → two competing-writer conflict branches → undo after reload with server revision assertions, `04c-layout-restore.png`, `04d-layout-conflict.png` and `04e-layout-conflict-gap.png`. The same-revision branch publishes a competing revision (head 12→13) and the stale UI write receives `IMMUTABLE_LAYOUT_REVISION`; the gap branch advances the head by two (stale base 14, authoritative head 16) and receives `REVISION_CONFLICT`. In both, the UI reloads the authoritative head, keeps the competing presentation and appends nothing. The invalid-Jalali path is also checked after switching calendars to prove no stale ISO resurrection. PostgreSQL execution is covered by repository CI modules; the layout PostgreSQL twin skips locally because `P6_TEST_POSTGRES_DSN` is unset.
- **Exact-head CI:** all four workflows and nine checks succeeded on `bde7ef73` (E2E conflict-gap and evidence head): [ConstructionPM CI #40333341662](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40333341662) (Python 3.11/3.12/3.13), [PostgreSQL Integration #40333341392](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40333341392), [ConstructionPM Web CI #40333341654](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40333341654), [Client Typecheck #40333341526](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40333341526). The final documentation-only head repeats these workflows; PR #1583 records that exact-head run. Earlier head `d8840a20` also passed 9/9 ([Python](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40329629363), [PostgreSQL](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40329629302), [Web](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40329629053), [Client typecheck](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40329629082)). These certify branch heads, not merged `main`.
- **Independent review:** two review rounds found no remaining code blocker. The first found the layout retry/stale-write defect and the single-code Web recovery; both are fixed and covered at repository, PostgreSQL-twin, HTTP and browser layers. The second found documentation overclaiming (AI-05/07/08 and stale OPS rows) and a missing browser branch for the revision-gap conflict; both are corrected in the evidence commit, whose matrix marks AI-07 `missing` and AI-05/AI-08 `partial` on this tree because the verification module and AI browser E2E remain on PR #1582.
- **Not claimed:** production identity/deployment, Resource Dependent nondriving placement or AI execution verification (remain on PR #1582), undo or restore for activities, WBS, schedule/settings or commercial edits, a project-wide backup/restore UI, assignment-level early/late and backward placement, a WBS hierarchy editor, applying imported rows to activities, and saving formula definitions/calculated-column bindings remain open as recorded in `CUBI_V1_ACCEPTANCE_MATRIX.md`. No production deployment, secret change or sensitive admin change was performed.

## Branch delivery checkpoint — 2026-10-26 (`0dcad35f`; typed capacity write/read slice; not merged)

- **Branch:** `fix/resource-dependent-nondriving-leveling`. Earlier checkpoints: full-stack preview at `17540c75`, formula authority at `bf46108c`, interchange Web panel at `5aa44b3f`. This capacity slice is committed at `0dcad35f` (21 files, 3,234 insertions, 63 deletions). It is branch evidence, not merged-main completion.
- **Exact-head CI:** `0dcad35f` passed all 9 checks: [ConstructionPM CI #40315561582](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40315561582) (Python 3.11/3.12/3.13), [PostgreSQL Integration #40315561686](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40315561686), [ConstructionPM Web CI #40315561581](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40315561581), and [Client Typecheck #40315561589](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40315561589) (Web/Desktop/Mobile/Client Sync). These certify this branch head, not merged `main`.
- **Preview:** `npm run preview:full` (or `PYTHONPATH=src py -3 -m construction_pm.preview --web-root apps/web --port 4174`) serves the built Web client through the real WSGI API, SQLite persistence and Shared Core. There is still no external preview URL: the repository has no GitHub Pages site and no deployment was performed.
- **Typed capacity vertical slice:** the Web workspace now exposes `Resources → Max units / time` backed by versioned read and write contracts (`p6-resource-capacity-read-api.v1`, `p6-resource-capacity-write-api.v1`). The panel lists persisted effective-dated segments, resolves a period to an authoritative server-side capacity with an explicit basis factor, and submits an authenticated effective change. The server derives the source (`manual-entry:{user_id}`) and the content identity; the browser never computes capacity, never supplies an identity or source, and never invents a value for an unregistered resource (404 `RESOURCE_CAPACITY_NOT_REGISTERED`). An effective change closes an open-ended prior segment through a separately identified closed copy plus a supersession link; the original row is never mutated, and a retried identical change is idempotent in both SQLite and PostgreSQL.
- **Local verification:** full Python `2840 passed, 126 skipped, 1 warning`; Web `322` TypeScript tests plus `7` preview-resolver tests; `npm run typecheck` and `npm run build` passed; isolated browser E2E `30 checks, 21 screenshots` with temporary SQLite and random loopback port, including capacity edit, supersession, resolve, full-reload persistence and viewer write denial. PostgreSQL execution is covered by repository CI modules; the new `tests/test_p6_postgres_resource_capacity.py` skips locally because no PostgreSQL DSN is configured.
- **Not claimed:** production identity, external deployment, official CUBISITE weights/percentages, assignment-level early/late/backward placement, undoing/redoing edits, a WBS hierarchy editor, typed Jalali date entry, applying imported rows to activities and saving formula definitions/calculated-column bindings remain open as recorded in `CUBI_V1_ACCEPTANCE_MATRIX.md`. PR #1582 remains unmerged and no production deployment, secret change or sensitive admin change was performed.

## Prior branch delivery checkpoint — 2026-10-26 (`5aa44b3f`; preview, capacity read, formula authority and interchange; not merged)

- **Branch:** `fix/resource-dependent-nondriving-leveling`. Preview/capacity/project-creation delivery is committed at `17540c75` (`feat(preview): deliver full-stack workspace preview with typed capacity`, 45 files, 8,861 insertions). The formula-authority slice is committed at `bf46108c`; the interchange Web panel is committed at `5aa44b3f`. This checkpoint is branch evidence, not merged-main completion.
- **Preview:** `npm run preview:full` (or `PYTHONPATH=src py -3 -m construction_pm.preview --web-root apps/web --port 4174`) serves the built Web client through the real WSGI API, SQLite persistence and Shared Core. There is still no external preview URL: the repository has no GitHub Pages site and no deployment was performed.
- **Local verification:** full Python `2837 passed, 124 skipped, 1 warning`; focused formula/HTTP `108 passed`; preview runtime `7 passed`; Web `308` TypeScript tests plus `7` preview-resolver tests; `npm run typecheck` and `npm run build` passed; isolated browser E2E `27 checks, 18 screenshots` with temporary SQLite and random loopback port. PostgreSQL execution is covered by repository CI modules but was not run locally in this checkpoint because the configured service was unavailable.
- **Formula authority:** the workspace posts expressions to the versioned Shared Core route. A valid expression returns authoritative dependencies and result type; a context self-reference returns `FORMULA_SELF_REFERENCE`; a registered field without a safe formula representation returns its explicit diagnostic instead of poisoning unrelated validation or becoming an HTTP 400. The editor is validation-only: saving formula definitions and binding calculated formula columns remain open.
- **Exact-head CI:** `301dee8686bfc10e6494c11ab2c935a8049f7395` passed all 9 checks: Python 3.11/3.12/3.13, PostgreSQL integration, Web CI, and Client/Web/Desktop/Mobile typecheck. The only annotation was a hosted-runner image migration notice. This certifies the branch head, not merged `main`.
- **Interchange UI:** `Project → Import / Export` exports all loaded activities through the real persisted mapping registry and provider codec, offers the server-generated document for download, and maps a pasted/uploaded document back to canonical rows with warnings. The panel never encodes, parses or invents mappings in the browser. A malformed document surfaces `INVALID_XML`, and a viewer import is denied with the authoritative `project.write` error while export remains readable. Import is review-only; mapped rows are not applied to activities.
- **Not claimed:** production identity, external deployment, official CUBISITE weights/percentages, assignment-level early/late/backward placement, undoing/redoing edits, a WBS hierarchy editor, typed Jalali date entry and applying imported rows to activities remain open as recorded in `CUBI_V1_ACCEPTANCE_MATRIX.md`. PR #1582 remains unmerged and no production deployment, secret change or sensitive admin change was performed.

## Release-gate reconciliation — 2026-10-26

- **Source state checked:** default branch `main` resolves to `52483e55e19b927cc392b86808d6ff484cb26215`. The previously recorded statement that PR #1570 had not merged was stale; GitHub reports PR #1570 merged at that SHA. Its merged scope remains limited, as recorded above.
- **Exact-head CI recheck:** PR #1575 head `2470b62c045db288ce4669d35fd3680689e08140`, PR #1576 head `83111ea79d3ddc5afe9eda265185ce5d1fa41320`, PR #1577 tested heads `0e1522ff3396cf005b7366cc8fa74ef9c6fec221` and `23ab7b1c0b72ab020cec96fb1cc9f272507957a8`, and PR #1579 head `e99acb4071290dc7d5d532ecee4a7b385c6d3377` each report successful ConstructionPM CI, PostgreSQL Integration and Client Typecheck runs. These results apply to their specific commits and do not imply that they are merged or that issue #1517 is complete.
- **Pages gate:** `.github/workflows/deploy-pages.yml` explicitly stops when the Pages API returns 404 and `PAGES_ADMIN_TOKEN` is absent. The current connector cannot read repository secrets or change the repository Pages settings. Verify Settings → Pages → Build and deployment → Source = GitHub Actions (or configure the authorized admin token), then rerun deployment and smoke-test the published URL. Do not mark deployment complete until that check passes.

## Current reconciliation checkpoint — 2026-10-25, after PR #1571 merge

- **Latest code-bearing merge SHA:** `f4b51292e8e61124e64ae11e756e8cbad27f66d9`; PR #1571 is merged at this commit. A subsequent ledger-only commit records this checkpoint; it does not change application code. It integrates the generated public-safe schedule reference catalogue into the existing Web workspace without removing the schedule-cycle mountpoint. The catalogue exposes 72 requirement records, 18 formula contracts and 16 documentation-review tracks; its statuses explicitly distinguish mapped requirements from proven implementation.
- **Exact PR-head checks on `27b774bc8b2b3dd2dfa2ae2f70976126cb81a600`:** [ConstructionPM CI #40156394018](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40156394018) — PASS on Python 3.11/3.12/3.13; [ConstructionPM Web CI #40156394020](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40156394020) — PASS; [Client Typecheck #40156394102](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40156394102) — PASS. The earlier PR-head generator/catalogue mismatch was corrected and these final-head checks passed before merge.
- **Post-merge main checks on `f4b51292e8e61124e64ae11e756e8cbad27f66d9`:** Web CI, Client Typecheck and PostgreSQL Sync are PASS; Python 3.12 is PASS; Python 3.11 and 3.13 were still in progress at the last check. Recheck the exact main SHA's final status before making a full-green CI claim.
- **Release deployment remains blocked:** [Deploy run #40156478651](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40156478651) failed at the Pages preflight because the repository Pages site is not enabled/readable (HTTP 404 and no `PAGES_ADMIN_TOKEN`). The connection available for this task cannot change repository Settings or create repository secrets. An owner/admin must enable Settings → Pages → Build and deployment → Source = GitHub Actions or add the authorized `PAGES_ADMIN_TOKEN`; then rerun deploy and smoke-test the actual published URLs.
- **Calculation gate remains open (reconciled 2026-10-26):** PR #1570 **is merged** at `52483e55e19b927cc392b86808d6ff484cb26215` and delivers only the supported not-started Resource Dependent driving-duration subset. It does not implement independent nondriving assignment placement or certify full resource-leveling parity. Current follow-ups: PR #1575 (input identity validation; exact-head ConstructionPM CI, PostgreSQL Integration and Client Typecheck passed; still open), PR #1576 (persisted fail-closed regression coverage; still open), PR #1577 (immutable assignment facts/hash binding; draft; exact-head CI gates passed, but assignment placement remains unimplemented), and PR #1579 (assignment metadata propagation through Shared Core demand; draft; CI gates passed, but placement/output diagnostics remain unimplemented). These are prerequisites and tests, not completion credit for issue #1517. Keep the production fail-closed guard until calendar/capacity-aware independent nondriving placement, assignment-level result diagnostics, and authenticated persisted-read → snapshot → Schedule Query acceptance tests are implemented and pass. Do not claim full Resource Dependent or resource-calendar compatibility from CI alone.
- **CUBISITE accounting remains evidence-based:** merged reference UI is not scheduling-calculation completion; the Library workbook remains the website schedule of record, all seven AI-C01–AI-C07 activities remain zero earned completion until their own acceptance criteria are proven, and the overall production site E2E/release gate remains open.

## Current baseline

| Item | Verified state |
|---|---|
| Latest source-code SHA inspected at reconciliation | `52483e55e19b927cc392b86808d6ff484cb26215` (2026-10-26; current `main` ref confirmed; PR #1570 merged with restricted duration semantics; full #1517 parity and Pages deployment remain open) |
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


## Engineering Intelligence owner decision and implementation checkpoint — 2026-10-28

**Audit baseline:** `main` at `91274b13eadea0512e26a07b0b836a28a837ebb8`.  
**Implementation branch:** `feat/cubi-internal-engineering-intelligence-2026-10-28`.  
**Latest tested branch head:** `e6cee61478c9af690027fbf90be3f46def66161d`.  
**Draft PR:** [#1618 — local-only inference and traceable engineering-intelligence gaps](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1618).  
**New P0 issue:** [#1617 — takeoff/estimating, resources/equipment, risk mitigation, Form Builder and PMBOK reports](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1617).  
**Companion blockers:** #1423 (assistant V1), #1530 (real action authorization/execution), #1540 (learning/memory), #1546 (website scope/schedule).

### Findings confirmed on the audit baseline
- The assistant V1 and toolchain documents already specify a professional project-controls assistant, project build/edit recommendations, resource/equipment recommendations with provenance, risk/reporting guidance, controlled learning, a single calculation authority and no universal remote API-key dependency.
- Despite that architecture intent, the previous production/preview provider composition was remote-only: `CUBI_AI_ENABLED` selected `OpenAICompatibleChatProvider`, requiring `CUBI_AI_API_KEY`, `CUBI_AI_BASE_URL` and `CUBI_AI_MODEL`. There was no local inference adapter wired through the product's environment factory.
- The production assistant still has a narrow real tool/runtime surface. The standard model-facing action slice is limited; a preview project-plan builder exists, but full production WBS/relationship/calendar/resource/equipment/cost integration is not complete.
- Risk engine, learning-memory record/repository contracts, resource/cost/schedule cores and report infrastructure exist. Their existence does not prove a connected assistant workflow to retrieve those results, propose mitigation, persist and retrieve vetted lessons, conduct owner-authorized source research or run the required reporting workflows.
- Repository code search did not identify an implemented quantity-takeoff/BOQ workflow or a persisted/versioned Form Builder domain and UI. PMBOK is present as a governance baseline, but assistant-led report tailoring with data/source evidence still needs implementation. These gaps are tracked in #1617 rather than treated as complete.
- Existing learning-record persistence is only a foundation. Automatic candidate-lesson capture, approved retrieval/promotion, authorized research and publication, deletion/retention, persistent deployment wiring, backup/restore/migration, golden evaluations and rollback remain open under #1540.

### Changes in PR #1618
- Added `LocalOllamaChatProvider` and `build_ai_chat_provider_from_environment`. Product selection accepts only `local-ollama`; the adapter restricts the configured endpoint to loopback, sends no API key/Authorization header, bounds JSON input/output, rejects redirects and returns sanitized local-runtime errors without a remote fallback.
- Changed production and local preview composition to select the local-only provider factory. Missing local model configuration leaves the assistant route unavailable rather than crashing the site or weakening authorization.
- Added tests for the local provider contract, no external API key, loopback restriction, remote-provider selection rejection, missing model/runtime and the preview proposal → approval → execution → calculation/read-back path. The preview test explicitly configures its test model.
- Updated the assistant requirements, provider configuration, toolchain plan, product principles and this ledger to preserve the owner's scope, local-only model policy and explicit implementation/acceptance gaps.
- Created #1617 with verifiable scope and Definition of Done for quantity takeoff/BOQ and estimating; resource/labor/equipment planning and approval; evidenced risk detection and corrective action; a real persisted/versioned Form Builder; and PMBOK-tailored, evidence-grounded reporting.

### Exact-head CI evidence
The following checks passed for branch head `e6cee61478c9af690027fbf90be3f46def66161d`:
- [ConstructionPM CI](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40606533326): Python test suites on 3.11, 3.12 and 3.13 all passed.
- [PostgreSQL Integration](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40606533310): passed.
- [Client Typecheck](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40606533335): Web, Desktop, Mobile and Client-Sync typechecks passed.

An earlier run correctly caught a missing explicit model setup in the preview integration test and then a missing local-provider assignment in the guarded preview composition. Both issues were corrected; the matrix above is from the later exact branch head, not those failed attempts.

### What this does not claim
- The PR remains a **draft** and is not merged to `main`; existing merged-main behavior is unchanged.
- The local Ollama runtime and approved model weights have not been provisioned or proven in a production/hosted environment. A green adapter test does not prove deployed model availability, construction-domain quality or true Desktop offline packaging.
- Full production project construction and action wiring still need #1530: current authenticated grants, exact-revision proposal approval, real typed handlers, transaction/idempotency protections, durable audit and authoritative fresh read-back.
- #1617 remains open: quantity takeoff/BOQ, cost estimating, resource/equipment recommendations that can be accepted into real activities, risk-action workflows, persisted Form Builder and PMBOK-tailored reports are not delivered by the provider slice.
- #1540 remains open for automatic experience-to-candidate-lesson capture, authorized article research, provenance/review/approval/publishing, scoped durable retrieval, retention/deletion, backup/restore, migration and benchmark/rollback.
- No hosted site deployment was performed. Do not enable the public read-only preview's assistant by weakening its guard.

### Required next steps
1. Keep PR #1618 in draft until local model provisioning and assistant/tool runtime wiring are verified for the intended deployment; review exact-head checks before any merge.
2. Complete #1530's production integration and test non-mutating turns, proposal persistence, explicit approval/execution, revoked/read-only permissions, stale revisions, replay/partial-failure handling and fresh authoritative read-back.
3. Implement #1617 as staged vertical slices with typed contracts, persistence/migrations, real UI, source-backed golden fixtures, authorization/approval, audit and end-to-end read-back.
4. Complete #1540's real learning/research/retrieval/retention/backup/migration/rollback lifecycle.
5. Reconcile accepted work into CUBISITE and Jalal 5 without silently changing either 100.00-point denominator. Documentation and open PRs alone receive no implementation completion credit.
