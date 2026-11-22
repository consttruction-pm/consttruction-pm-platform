# CUBI — Qoder Instruction, Execution and Independent Acceptance Standard

**Status:** Mandatory engineering/governance rule  
**Effective:** 2026-11-02  
**Applies to:** Every Qoder/Codex/Copilot implementation task, especially the Primavera-aligned visual workspace and Shared Scheduling/Calculation Core.  
**Purpose:** Prevent repeated token expenditure, incomplete implementation being described as completion, and rework caused by approving a report instead of verifying the delivered product.

This is an internal CUBI engineering standard. Reference-product names and source URLs may appear here for traceability, but must never leak into customer-facing CUBI UI, help, branding or marketing.

---

## 1. Non-negotiable operating principle

**A task is not complete because an instruction was detailed, an agent says it is complete, a PR exists, a test suite passes, or the assistant previously approved it. A task is complete only when every in-scope requirement is traced from its authoritative source to the current implementation, exercised through the relevant user/API/runtime path, and independently accepted against the exact delivered commit.**

The assistant issuing an implementation instruction and the assistant reviewing the result are two separate responsibilities. The reviewer must not inherit the implementer's claims as facts. It must inspect the repository and evidence independently.

No one may:
- replace full feature coverage with a menu catalogue, static mock, screenshot, placeholder, or empty state;
- mark a feature complete because its name, type, route, test file, or menu entry exists;
- treat green CI as proof of product or reference parity;
- call a visual shell complete without opening and exercising every in-scope window, menu, dialog, tab and layout in the running application;
- call a calculation feature reference-equivalent without numeric reference fixtures or a clearly recorded reason why they are unavailable;
- silently downgrade, skip, delete, weaken or rewrite a failing test to obtain a green result;
- change the task scope during execution without recording the change and its impact;
- make the user pay for another broad execution merely because the previous instruction or acceptance process omitted an already-known requirement.

## 2. Resolve the authoritative target before writing an instruction

Every task must identify its target product/version and the source hierarchy. CUBI has two separate parity tracks; they must not be conflated.

### 2.1 Visual workspace track

The visual and functional reference baseline is the **latest available P6 Professional release, Version 26 (with the latest applicable 26.x release/update/patch)**. As of 2026-11-02, Oracle's current official documentation set is Version 26; the latest release family surfaced in Oracle's 2026 What's New documentation includes P6 Professional 26.10. Re-check Oracle's official release/update information before each major audit because the current patch may advance. The owner's 2026-11-02 decision explicitly supersedes the former Version 22 baseline. The older Version 22 screenshot may be retained only as historical geometry evidence, never as the controlling baseline:
- the user-supplied 1100 × 808 screenshot is the primary geometry/proportion reference;
- the latest Version 26 Professional User Guide, Help, Visualizer Help and release-specific documentation are the primary behavior/layout inventory and acceptance source;
- measured proportions in `CUBI_Primavera_P6_Reference_Index.md` are to be preserved as the initial visual baseline, subject to measured responsive adaptations;
- older-version references are historical cross-checks only. Do not preserve an older behavior where the latest release changes it; record the exact latest-version guide/topic, any backward-compatibility decision, and a test.

If the product owner explicitly changes the visual baseline version, update this standard, the reference index and affected acceptance matrices before implementation.

**Geometry is part of acceptance.** At the reference desktop viewport, preserve the title/menu/toolbar/layout rows, activity-table/Gantt split, bottom Details pane, gutters and icon rails measured in the reference index. Do not resize the Timeline/Gantt or other user-approved regions without explicit product-owner instruction. CUBI-only additions (for example, comments) must be additive and must not be assigned an invented reference proportion.

### 2.2 Calculation/core track

The current scheduling semantics target is **P6 Professional Version 26**, as identified by the core compatibility registry and its source links. Every row must identify the exact release/help section that governs it. If behavior changed between versions, document the applicable version and compatibility decision; do not blend versions.

The Version 26 target does not mean CUBI has been numerically parity-tested. Absence of a licensed P6 installation or direct P6 output is not a reason to stop implementation, local testing, or acceptance of engineering work that can be verified. Qoder must build and run exact numeric golden cases from official documented examples, formulae, boundary rules, and independently derived fixtures with transparent derivations. The assistant then independently checks formulas, units, calendars, expected values, actual outputs, and the authoritative persisted/API path. Record direct execution against the same licensed P6 scenario as a separate DIRECT_REFERENCE_COMPARISON evidence field/status. If that external comparison is unavailable, only the claim of direct product-to-product parity remains pending; do not downgrade completed implementation or local numeric verification, and do not claim direct parity.

### 2.3 Source precedence

For every requirement, use this precedence:
1. Explicit product-owner decision recorded in CUBI requirements/decision records.
2. Version-matched official product documentation and help for the selected parity track.
3. User-supplied reference screenshots/files and measured observations for visual geometry.
4. Existing CUBI architecture, product principles, compatibility registry and accepted contracts.
5. Existing implementation only as evidence of current behavior—not as authority for what behavior should be.

If two sources conflict, stop that requirement, record the conflict, identify the version/scope, and resolve it explicitly. Do not silently choose the easiest implementation.

---

## 3. Mandatory pre-instruction repository inspection

Before sending Qoder a task, the assistant must inspect and record:

1. Repository name (exact spelling), current `main` SHA, working branch, PR/issue, current PR head SHA and whether the branch is behind/ahead of main.
2. Existing architecture, requirements, inventories, compatibility registries, decisions, execution ledgers and known gaps.
3. Existing code paths, UI surfaces, API/application/repository paths, tests, generated files and mirrored assets relevant to the task.
4. Prior commits and PRs that already attempted the same requirement. Identify what is complete, partial, mock-only, superseded or broken.
5. Current CI status and exact tested SHA. A run on a parent or sibling SHA is not evidence for the proposed head.
6. Whether the target is a real product surface, an isolated preview/demo, a static renderer, a backend-only path or a connected end-to-end flow.
7. Any constraints that must not regress (for example: shared calculation core remains the sole scheduling authority; no client-side CPM; no reference branding in UI; Persian/English and registered locales; Jalali/Gregorian display separated from work calendars; preserve approved Timeline dimensions).

Do not ask Qoder to rediscover facts that the assistant can obtain from the repository. Do not issue a generic “continue and complete” prompt without a baseline SHA and a concrete remaining-work list.

---

## 4. Mandatory requirement-to-evidence matrix

Every implementation task must start from, or update, a durable matrix. Each row has a stable ID and these fields:

1. Requirement ID and exact requirement text.
2. Feature/window/menu/option and user-visible purpose.
3. Authoritative source URL, document title, release/version, section/page/paragraph.
4. CUBI decision or version-specific interpretation.
5. Required inputs, fields, choices, defaults, units and validation.
6. Required behavior/state transitions, including enabled/disabled and permission rules.
7. Expected visual placement/layout or calculation algorithm.
8. Actual source path, symbol/component/function/API/contract/repository.
9. Actual test path and test case name.
10. Expected result, including numeric expected values where relevant.
11. Runtime/browser/API/database path exercised.
12. Exact implementation SHA and exact test SHA.
13. Evidence link (CI run, browser screenshot/artifact, API trace, fixture, report).
14. Status and observed difference.
15. Remaining action, owner and blocker.

Allowed status values:
- `MISSING`
- `INVENTORY_ONLY` — documented/catalogued but not implemented
- `PLACEHOLDER` — visible but not functional
- `PARTIAL`
- `IMPLEMENTED_NOT_TESTED`
- `IMPLEMENTED_TESTED_PARITY_PENDING`
- `IMPLEMENTED_AND_PARITY_TESTED`
- `BLOCKED_EXTERNAL`

A requirement can be `IMPLEMENTED_AND_PARITY_TESTED` only when the exact target version has been exercised with an authoritative reference case and the CUBI output matches the expected result. A local hand-calculated test is valuable but is not a substitute for an external reference comparison where the requirement is reference parity.

No overall “complete” label or percentage may hide open rows. Report counts by status and list all blockers.

---

## 5. Visual workspace acceptance contract

The visual shell is a desktop-style, multi-window workbench—not a long page and not a dashboard made from wide cards.

### 5.1 Global shell and navigation
Verify in the running app:
- CUBI identity/project/revision/user/connection/language/calendar/theme status area.
- Complete hierarchical menu bar with nested submenus, separators, icons, disabled states, keyboard mnemonics and shortcut hints.
- Standard, Project, Layout, Schedule and CUBI toolbar groups, with accessible labels, tooltips and responsive overflow.
- Breadcrumb/context, Data Date, baseline and active layout.
- Independent collapsible/resizable left navigation tree with retained expansion/selection/width.
- Independent window tabs with active/dirty state, close, reorder, keyboard cycling, tab groups and Save/Discard/Cancel on dirty close.
- Page-specific horizontal contextual command bar.
- Separate narrow right-edge CUBI Add (+) rail; its popup is anchored and never overlays the grid/Gantt/details.
- Adjustable top/bottom and table/chart splitters with bounds, keyboard operation and reset.
- Docked page-specific Details pane with object identity, tabs, independent scroll and configurable placement.
- Status bar with project, Data Date, baseline, layout, filter, selection count, user/role, save/sync and contextual hints.

### 5.2 All windows and per-window controls
The target inventory must cover every applicable entry in `workspace-visual-shell-master-audit.md` and `workspace-window-inventory.md`, including at minimum:
- Projects / Business Domains / Portfolios
- Activities, Activity Network, Gantt, usage spreadsheet/profile and Trace Logic
- WBS
- Resource Assignments
- Resources and Roles
- Calendars and workweek/hour/exception/holiday editors
- Documents, Expenses, Thresholds, Issues and Risks
- Reports, report groups/batches/designer/preview/distribution
- Tracking layouts
- CUBI Form Builder and its separate Organization Form Library and Project Form Library
- CUBI Cost & Financial Control, Progress & Field Control, Procurement, Changes & Claims
- Administration and user/security/preferences windows.

For each window, verify its own top-layout modes, page-specific Details tabs, contextual commands, dialogs, table columns, filters, grouping/sorting, timescale/bars/chart options and selection behavior. A single generic Details pane or one generic list does not satisfy all windows.

### 5.3 Dialog and command behavior
Every visible control must be classified:
- working and connected to its owning workflow;
- disabled with a concise reason because the workflow is not yet connected; or
- explicitly visual-only and never allowed to report success.

Every menu item and toolbar action must be opened/exercised. Verify keyboard operation (Tab, arrows, Enter, Escape), focus handling, dialog scrolling, validation, cancel/close behavior and destructive-action confirmation.

### 5.4 Visual and responsive evidence
For each in-scope window and dialog:
- capture screenshots at the reference desktop viewport and at approved tablet/mobile breakpoints;
- inspect dimensions, clipping, overlap, text wrapping, scrolling, alignment, RTL/LTR, mixed-direction IDs/numbers and responsive behavior;
- compare the screenshot with the target reference and record measured differences;
- run browser E2E against the actual running application, not only a pure HTML renderer test.

A renderer/unit test proves markup generation only. It does not prove that the page opens, controls work, state is retained, or the layout is visually correct.

### 5.5 Localization
For every supported locale, test menus, dialogs, tables, chart labels, validation/errors, tooltips, Details tabs and status bar. Verify correct `lang`/`dir`, RTL shaping, mixed-direction identifiers, font coverage, date/number/currency formats and no clipped controls. English fallback is not proof of translation completion. Public-site locale routes are a separate acceptance surface.

---

## 6. Calculation/core acceptance contract

Every calculation requirement must be traced through the full authoritative path:

**official rule → CUBI compatibility row → typed input/contract → immutable snapshot/context → domain algorithm → authoritative service/API → persisted result/read model → UI/report/export → numeric and integration tests.**

No client-side calculation may become a second authority.

For every formula/algorithm, record:
- source version and exact source section;
- formula and variable definitions;
- units, precision, rounding and boundary convention;
- calendars/time zone and working-time basis;
- assumptions, defaults and missing-data behavior;
- input provenance and immutable/versioned context;
- expected numeric output for golden/reference cases;
- invalid-input and fail-closed behavior;
- persistence, transaction, authorization and revision boundaries;
- API/read-model and downstream display/export path.

The core matrix must explicitly cover all relevant combinations, not merely one happy path. Examples include:
- CPM forward and backward passes, early/late dates, Total/Free Float, float basis, critical threshold and longest path;
- FS/SS/FF/SF, positive lag and negative lead, lag-calendar choices and activity calendars;
- primary/secondary/mandatory constraints, open ends, Expected Finish and opened-project scope;
- Data Date, actual/remaining work, Retained Logic, Progress Override and Actual Dates;
- Task Dependent, Resource Dependent, Level of Effort, Start/Finish Milestones and WBS Summary;
- global/project/resource calendars, inherited calendars, split shifts, overnight work, exceptions, holidays and hours-per-time-period conversion;
- driving/nondriving resources, rates, Max Units/Time, capacity windows, priorities, float limits, selected resources, multi-project thresholds and infeasible placements;
- baselines, selective update, comparison and variance;
- EV/PV/AC/BAC, WBS techniques/overrides, weighted milestones, ETC/EAC/VAC, resource curves and future-period PV;
- typed XER/XML/XLSX/MS Project interchange and round-trip preservation.

For each matrix row, add:
1. unit tests;
2. boundary/edge-case tests;
3. regression tests;
4. persistence/API integration tests;
5. end-to-end tests through the authoritative production path;
6. numeric reference/golden tests;
7. negative/fail-closed tests.

A test that merely asserts that a field exists or an exception is raised is not sufficient when the requirement is a date, duration, float, capacity, cost or EVM result. Assert exact expected values and units.

Do not change a row's status based on CI green alone. Distinguish (a) documented-rule/golden-case numeric verification, (b) independent code/output review, and (c) direct P6 execution comparison. If licensed reference execution is unavailable, mark only (c) unavailable/pending and state precisely what external scenario is missing; continue all work in (a) and (b).

---

## 7. How the assistant must write the Qoder instruction

The assistant must prepare one complete, repository-aware execution instruction for a bounded work package. It must include:

1. **Objective and definition of done:** observable outcome, not a vague verb such as “continue”.
2. **Baseline:** exact repository, base SHA, branch, PR/issue and current head SHA.
3. **Authoritative references:** exact version, links, sections and conflict-resolution rules.
4. **Requirement IDs:** all rows included in this work package and explicit exclusions.
5. **Current state:** existing files/functions/tests and what is already complete; do not redo accepted work.
6. **Required implementation:** concrete behavior, fields, states, interactions, algorithms and error cases.
7. **Architecture boundaries:** what must be reused; forbidden duplicate engines, client-side calculations or unrelated rewrites.
8. **Acceptance tests:** exact test names/commands plus expected numeric/UI/runtime results.
9. **Browser/runtime evidence:** exact routes, workflows, viewports, locales and screenshot artifacts required.
10. **Regression protection:** existing behavior that must remain unchanged.
11. **Execution order:** inspect → map → implement → targeted tests → full tests → browser/API integration → fix all failures → Qoder-local final verification on the final commit → return evidence package. GitHub CI/PR queue is a later release/merge gate, not the primary place to discover whether Qoder's implementation works.
12. **Commit/PR discipline:** work on the existing authorized branch/PR where appropriate; no unrelated PR; commit coherent slices; update the matrix/ledger and PR body.
13. **Stop conditions:** stop and report a source conflict, missing required input, inaccessible licensed reference, unsafe migration or scope change; do not fabricate a pass.
14. **Final report schema:** the evidence package in Section 8.

If the whole inventory is too large for one safe work package, split it into explicitly sequenced work packages **before** execution, each with its own complete acceptance contract and dependency links. Do not call a slice “full parity”. The overall mission remains open until every required package passes.

The instruction must tell Qoder to implement and repair the scoped work, not merely produce an audit or recommendations. Conversely, it must not authorize unrelated refactoring or claim external parity it cannot demonstrate.

---

## 8. Mandatory Qoder completion response

Qoder must return a concise but evidence-rich report with:

- exact task/requirement IDs completed;
- repository, branch, PR, base SHA and final head SHA;
- files changed and purpose of each coherent change;
- requirement matrix updated with status and code/test paths;
- exact commands run and unedited pass/fail/skip counts;
- all CI workflow/run IDs and whether each run tested the exact final SHA;
- browser E2E routes, locales, viewport sizes, check counts and screenshot/artifact links;
- numeric reference fixtures and expected/actual comparisons;
- API/persistence/fresh-read evidence where applicable;
- unresolved gaps, blockers and explicit non-claims;
- commit/PR links and whether merge/deployment occurred (never imply either if not done).

“Done”, “complete”, “100%”, “fully aligned” or equivalent language is forbidden unless every in-scope row has accepted evidence. A test count without commands, SHA and test identity is not sufficient.

---

## 9. Mandatory independent review by the assistant

After Qoder responds, the assistant must not summarize or approve the response immediately. It must independently:

1. Fetch the current PR and exact head from GitHub.
2. Read the actual diff and inspect each changed source, test, generated file and documentation artifact.
3. Compare each requirement row to the code path and test; identify catalogue-only, mock-only, disabled, disconnected and missing behavior.
4. Run or inspect exact-head CI. Verify workflow head SHA and job conclusions, not just the latest green run on the branch.
5. Inspect browser E2E artifacts/screenshots for all required surfaces, viewports and locales; do not substitute unit tests.
6. For core work, verify expected numeric outputs and end-to-end persisted query path; compare to the selected reference version where possible.
7. Verify no tests were skipped, deleted, weakened, or made less meaningful to hide a defect; explain every skip.
8. Verify architecture boundaries, permissions, audit, tenant/revision scope, rollback and no-regression constraints.
9. Reconcile the PR description, issue, execution ledger, generated compatibility catalog and test evidence so none contradicts one another.
10. Report only independently verified facts. If evidence is absent, mark the row unverified—not assumed complete.

The assistant's prior approval is never evidence. The same assistant must be willing to reverse an earlier approval when fresh source inspection contradicts it.

---

## 10. Token and rework economy

Qoder execution is costly. The assistant must reduce avoidable repeat work:

- Inspect repository and existing work before preparing the prompt; do not spend a Qoder run discovering facts available in GitHub.
- Reuse the existing PR/branch and accepted code; never ask Qoder to recreate completed work.
- Send one comprehensive, bounded, acceptance-driven instruction rather than a sequence of vague prompts that rediscover the same requirements.
- Include known defects and exact failed assertions/logs so Qoder fixes root causes rather than guessing.
- Ask Qoder to complete the full agreed scope and run all required checks in the same execution, including fixing failures it introduces.
- Do not spend another run on cosmetic or isolated corrections when a known set of related requirements can be safely handled in the same bounded package.
- Do not combine unrelated high-risk work merely to save a run; token efficiency never overrides scope control or test integrity.
- During CI wait time, inspect logs, review adjacent risks and prepare evidence reconciliation rather than launching duplicate implementation work.
- Before any new prompt, compare it against the prior prompt, response, commits and open acceptance rows. State exactly why another execution is necessary and what new evidence/implementation it will produce.
- Record reported agent/token consumption when available, but do not infer token usage from code size or commit count.


### 10.1 What consumes Qoder Credits (official published guidance)

Qoder's published billing unit is Credits, not a fixed number of raw prompt tokens. Treat the user's stated daily allowance of 100 as 100 Credits only if that is what the account Usage panel labels it; never silently convert Credits to raw tokens.

Official references (check rates again before relying on them because Qoder changes models and pricing):
- Credits and task consumption: https://docs.qoder.com/Credits
- Desktop model selector and tier rates: https://docs.qoder.com/user-guide/chat/model-tier-selector
- Usage page: IDE bottom-right Credits usage; website Settings → Usage.

Published reference figures are estimates, not guaranteed per-request prices:
- Editor Ask Mode: median about 3 Credits/request at 50K context, 4 at 200K.
- Editor Agent Mode: median about 7 Credits/request at 50K, 12 at 200K.
- Quest Agent Mode: about 50 Credits/request at 200K.
- Quest Experts Mode: about 75 Credits/request at 200K.
- Repo Wiki generation: about 50 Credits/repository.
- Model selector examples for a moderately complex coding task: Auto ~10, Ultimate ~20, Performance ~11, Efficient ~3, Lite 0. These are tier examples and must not be conflated with the separate median task table above.
- Actual charge depends on selected model/tier, input/output tokens, context window, thinking/parameters, tool activity and task complexity. The current composer/model selector and Usage panel are authoritative for the user's account.
- Successful model API calls consume Credits; failed model requests are not charged according to Qoder's Credits page.

### 10.2 Operations that normally do not consume model Credits

The following are ordinary local/editor/repository operations and do not themselves call a paid model, so they normally do not consume Qoder model Credits:
- Reading, scrolling, searching and navigating files manually.
- Selecting text, editing/typing code manually, and saving files.
- Ordinary local terminal commands such as git status/diff/log, grep/ripgrep, find, cat, file inspection, running tests, linters, formatters, type checks, builds and local scripts.
- Local Git operations (status, diff, add, commit, branch, log) and ordinary GitHub web/API operations performed manually or through non-AI integrations.
- Opening existing test output, logs, screenshots, browser pages and generated artifacts.
- Writing/planning the prompt outside Qoder and inspecting the response manually.

Important qualification: if an AI agent is asked to interpret logs, explain code, generate/fix tests, edit code, summarize files, or use tools as part of an Agent task, the model calls involved consume Credits even though the underlying shell/test/Git operation itself is free. Inline Chat, Ask, Agent, Quest, Repo Wiki/Knowledge generation and AI autocomplete features are AI/model requests and may consume Credits according to the current product configuration. Do not promise that every autocomplete or plugin feature is free; inspect the current account/model display.

### 10.3 Budgeting a daily 100-Credit allowance

Use the following as planning ranges only, based on published estimates, not a promise:
- Low-cost clarification/review via Ask: roughly 3–4 Credits each.
- Focused Editor Agent task: roughly 7–12 Credits at the published median context sizes.
- One Quest Agent task: roughly 50 Credits at 200K context.
- One Quest Experts task: roughly 75 Credits at 200K context.
- A moderately complex task on Efficient tier: example ~3 Credits; Auto ~10; Ultimate ~20.

For a 100-Credit day, default to one bounded implementation task in Editor Agent/appropriate efficient tier plus a reserve for one targeted correction/review, rather than starting a large Quest/Experts run by habit. A large Quest/Experts run can consume most of the daily budget in one request. Before sending, inspect the displayed estimate/model/tier and context size. Use Lite/free tier for simple clarification or mechanical checks when available; use a stronger tier only where the task's risk justifies it. Do not select a large context window by default: include only relevant files and requirements, and compact/summarize long conversation context before it bloats the next request.

### 10.4 Mandatory preflight and postflight accounting

Before each Qoder request, the assistant's prompt-preparation checklist must record:
1. Task class: Ask / Editor Agent / Quest Agent / Experts / Knowledge.
2. Selected model/tier and context window, if visible.
3. Qoder's displayed estimate (or NOT_DISPLAYED).
4. Expected budget band and remaining daily Credits as reported by the user.
5. Why the selected mode is necessary and why a cheaper mode is insufficient.
6. Exact bounded deliverable and known files/tests to avoid rediscovery.

After the response, record:
1. Actual Credits before/after from Qoder Usage panel/log if the user provides it (NOT_AVAILABLE otherwise).
2. Final commit SHA and work completed.
3. Tests/build/browser/API commands and results run locally in Qoder.
4. Defects fixed in the same run and remaining gaps.
5. Whether another model call is genuinely necessary and its precise delta.

Never claim exact token/Credit use without the Usage panel/log. Do not estimate actual spend from prompt length, code diff size, line count or elapsed time. The assistant should prepare a token-efficient instruction; Qoder's actual cost is measured from account usage.

The user should not have to pay twice for the same requirement because the assistant failed to specify it or failed to verify it. If a repeat run is necessary due to a genuine new defect or changed requirement, identify that reason and the exact delta.

---

## 11. Merge, release and progress rules

- Keep PR draft/open while any mandatory acceptance row remains incomplete or unverified.
- Merge only when explicitly authorized and all required exact-head checks and independent reviews pass.
- Do not deploy or change secrets/admin settings without separate explicit authorization.
- A branch/PR being open, mergeable, green or large does not equal product completion.
- A visual renderer test does not equal browser acceptance.
- A passing Python suite does not equal P6 numeric parity.
- A compatibility registry marked `MAPPED_NOT_PROVEN` does not equal parity.
- A preview with sample data does not equal persisted project behavior.
- Progress reports must separate: implemented, tested, runtime-verified, reference-parity-tested, merged and deployed.
- Never invent an overall completion percentage when the weighted baseline or acceptance data is unavailable.

---

## 12. Current audit lessons recorded on 2026-11-02

These are concrete reasons this standard is mandatory:

### Visual workspace
- PR #1673 is a partial visual-shell/Projects-window branch, not proof of full visual parity.
- Its own `workspace-visual-shell-master-audit.md` explicitly says the current branch is incomplete and lists independent windows, full Details surfaces, contextual bars, layout dialogs and browser screenshot review as outstanding.
- The same audit says a menu catalogue/static placeholder is not completion evidence.
- The current visual branch contains a visual-demo renderer and sample-only data. It can prove selected markup behavior, but not a complete running multi-window workspace.
- The owner explicitly changed the visual baseline on 2026-11-02: latest P6 Professional Version 26 / current 26.x update governs visual, functional and behavioral parity. Version 22 imagery is historical only and must not constrain the new shell.

### Shared calculation core
- PR #1668 contains substantial core implementation and exact-head green CI evidence, but remains Draft/open.
- The execution ledger records 24 rows as `IMPLEMENTED_TESTED_PARITY_PENDING` and zero as `IMPLEMENTED_AND_PARITY_TESTED`, because no licensed Version 26 reference run was available.
- The latest PR body and ledger were inconsistent: the PR body retained an older test count and listed some rows as open that the later ledger stage records as implemented. This is a documentation/reconciliation defect and must be fixed before acceptance.
- Green CI proves the recorded test suite passed on its SHA; it does not by itself prove calculation correctness. Lack of a licensed P6 run must not block local numeric verification against documented rules and transparent golden fixtures; direct P6 comparison is a separately reported evidence level.
- The user's reported Qoder daily allowance is treated as a planning constraint. Qoder's official metering is Credits (not a fixed prompt-token count); actual account usage is only known from the Usage panel/log. Record actual usage only when observed.

These lessons are not permission to restart or rewrite the work. The next task must preserve accepted code, reconcile the evidence and complete only the actual open rows.

---

## 13. Required project-wide usage

This standard applies automatically to all future instructions the assistant prepares for Qoder or other coding agents on CUBI. It must be consulted before issuing a new implementation prompt and before approving a completion report.

If this standard conflicts with an older generic workflow note, this standard controls unless the product owner explicitly records a newer decision.

## 14. Owner's operating decision — Qoder-first verification and cost discipline (2026-11-02)

The product owner confirms the preferred high-speed workflow:
- Qoder must implement, run tests, fix failures and perform its final verification inside its own local/IDE environment before reporting back.
- The assistant must then independently inspect the returned code, exact commit, test evidence and calculation/UI behavior. The assistant's review is not replaced by Qoder's self-report.
- GitHub CI is a later integration/merge gate. Do not make GitHub Actions queue time the primary feedback loop or wait for it before reviewing Qoder's local evidence.
- Direct licensed P6 numeric comparison is desirable evidence when available, but it is not a prerequisite for implementing or testing documented rules. Only the direct product-to-product parity claim remains unavailable until such a comparison exists.
- The user's daily Qoder budget is limited (reported as 100 per day). Every prompt must therefore be complete, scoped, repository-aware, and designed to maximize finished work per successful model request while preserving correctness.
- The assistant must not send a new Qoder prompt until it has inspected the previous response and identified the exact remaining delta. No vague continuation prompts, repetitive rediscovery, unnecessary retries, or cosmetic micro-prompts.

## Owner decision — latest release is the sole controlling reference (2026-11-02)

The owner explicitly instructs that CUBI's visual shell, menus, windows, dialogs, controls, layouts, and interaction behavior must be designed and audited against the **latest available P6 Professional release**, not Version 22. Oracle's official documentation currently identifies Version 26 as the current documentation set. The latest 26.x patch/update must be checked from Oracle release information at each audit; a public Oracle community item identifies 26.10 release family, but do not assume that remains latest indefinitely. Version 22 screenshots and dimensions are superseded as controlling requirements; they may be consulted only as historical context. Do not preserve Version 22 geometry where it conflicts with latest-release behavior or UI. Where no reliable latest-version screenshot exists, reconstruct from the current official guides and document the evidence and any visual uncertainty rather than reverting to Version 22.

Official reference: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/ . Latest patch verification reference (re-check at time of work): https://community.oracle.com/mosc/categories/primavera_-_prim .
