# Jalal 5 — Master Weighted Schedule and Completeness Control

**Prepared:** 2026-10-18  
**Plan ID:** JALAL-5-CUBI-2026-10-18  
**Status:** DRAFT — re-baseline required before approval. Product-owner decision in [Issue #1486](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1486) makes native Mobile mandatory in V1. The existing 100-point / 130-row workbook model does not yet reflect that added scope; its weights and forecast are not the final approved baseline.  
**Product-code baseline checked:** `main@faa34707957022ffa3f51c8d13561047cc7a44cc`  
**Workbook:** `Jalal5_Weighted_Master_Schedule_2026-10-18_MobileV1-Rebaseline.xlsx` (13 sheets; includes a new 14-candidate-row `Mobile V1 Rebaseline` inventory. The mobile candidates are not yet integrated into the main 130-row weighted denominator and have no final weights/effort. This is a rebaseline candidate, not the approved final schedule).

## 1. Mandatory governance

Every task/session follows the read-first [Project Continuity Protocol](../governance/PROJECT_CONTINUITY_PROTOCOL.md) and current [Project State Ledger](../governance/PROJECT_STATE_LEDGER.md). Use the [tracked-task issue template](../../.github/ISSUE_TEMPLATE/jalal5_task.yml) and [PR evidence template](../../.github/pull_request_template.md); these reduce omissions but do not replace review or live verification.

1. **Reuse approved decisions; do not re-design from scratch.** The existing CUBI brand/visual principles, Shared Domain/Calculation Core, Web-first execution sequence (not a scope exclusion: Web + Desktop + native Mobile are all V1), authentication/persistence contracts, project settings, Jalali/Gregorian rules and localization principle are fixed baselines. Reopen them only by a documented change request with impact analysis and approval.
2. **Jalal 5 has 100 weighted points.** Weights are allocated once across ten workstreams. Shared work is counted once. PRs, documentation, comments, mocks and isolated tests earn no product completion until the relevant implementation is merged, exact-head checks pass and acceptance evidence is recorded.
3. **No false current percentage.** Jalal 4's last calculated detailed snapshot is 48.13% (2026-10-13), not a newly certified 2026-10-18 value. Jalal 5 row-level acceptance and its earned total remain Pending until the 58 Jalal 4 activities are explicitly mapped to Jalal 5 rows against current-main evidence. Pending is not a claim that the whole product is 0% complete.
4. The last Jalal 4 workbook implies 535.21 remaining person-days. The Jalal 5 task allocations use that value only as a **temporary proportional effort envelope** because the new 130-row J4→J5 crosswalk is not yet accepted. The 1986 person-days in the gross lifecycle column are the unscaled scope estimate, not estimated remaining effort. Re-estimate individual rows after the crosswalk; do not silently preserve this proportional assumption as audited fact.
5. Date planning uses Monday 2026-10-19 as week 1, explicit predecessor relationships, one serialized primary-owner lane per owner and 80% focus capacity. The first computed owner/dependency forecast ends 2027-12-08; planning week 60 ends Friday 2027-12-10. This is about six weeks beyond the inherited Jalal 4 target (2027-10-29), is **conditional**, and must be recalculated after row-level crosswalk, Mobile V1 task/weight inclusion, blocker resolution and calendar-aware resource planning. The currently shown effort envelope and dates are not valid as the final Jalal 5 forecast until that recalculation passes QA. Public holidays and project-specific calendars are not yet modeled in this coarse planning calculation.

## 2. Workstream weights and exit criteria

| Workstream | Weight | Owner lead | Scope / exit test |
|---|---:|---|---|
| A — Scope, design decisions and traceability | 5 | Jalal | Freeze approved decisions, create 58-row J4→J5 crosswalk, establish one traceability/acceptance register and no-rework/change-control rule. |
| B — Primavera-aligned Shared Core and parity | 20 | Jalal | Map applicable P6 Release 26/26.4 rules to canonical Shared Core code, UI controls, data contracts and golden regression fixtures; fix current blocking schedule gates without weakening validation. |
| C — PMBOK form layer and project-management methods | 8 | Jalal | Adopt PMBOK as a tailoring/form/governance layer; label each formula by authority; typed validation, safe formulas, versioning, approvals and no shadow CPM/EVM calculation. |
| D — Professional AI assistant: server + Desktop-local | 16 | Hasan | Web server-hosted inference and end-to-end tools; Desktop local inference with provisionable model/runtime and real no-network proof; grounded reads, permitted mutations, approval, reporting and audit. |
| E — Public website: route inventory, pages, SEO and journeys | 10 | Farmj22002 | Implement only audited gaps against the 25-page public target plus two auth entry routes; every page has valid route/CTA/breadcrumb and per-page SEO/localization acceptance. |
| F — Web workspace: complete menus, screens and workflows | 13 | Farmj22002 | Preserve the existing nine root menus; map every planned submenu/action to a real screen/service, permission, state, error/empty case and relevant source/test ID. |
| G — Backend, persistence, APIs and enterprise controls | 10 | Hasan | Real project/WBS/activity/relationship/calendar/resource persistence; transactional write→commit→fresh-read; identity, tenant/project/revision, idempotency, authorization, audit and sync boundaries. |
| H — All-language experience, help and contextual guidance | 5 | Farmj22002 | Registry-driven languages in every declared supported workflow, RTL/LTR, Jalali/Gregorian, Help Center/deep links, reports and AI prompts/actions/errors. No fixed fa/en-only assumption. |
| I — Desktop integration and release package | 5 | Hasan | Desktop package, offline-capable local project workflows, local AI model install/provisioning, backup/restore, import/export, no hidden cloud fallback and recovery tests. |
| J — Cross-product verification, release gates and recovery | 8 | Jalal | Exact-SHA regression, security/negative tests, real user journeys, report/source consistency, restore evidence and final weighted recertification. |

The exact 130 activities, dependencies, owners, supporting roles, row-level weights, acceptance criteria, source links and provisional effort are in the workbook’s **Jalal5 Schedule** sheet. Do not use the stream summary as a substitute for accepting individual activity rows.

Two separate traceability artifacts support the schedule:
- [Jalal 4 → Jalal 5 crosswalk](../audits/JALAL4_TO_JALAL5_CROSSWALK_2026-10-18.md) maps all 58 historical Jalal4 activities to proposed Jalal5 activity IDs. It explicitly separates coverage mapping from progress transfer and identifies added scope with no precise Jalal4 equivalent.
- [P6/PMBOK contract section → Jalal5 task map](../audits/JALAL5_CONTRACT_SECTION_TO_TASK_MAP_2026-10-18.md) maps all 56 P6 contract sections and 33 PMBOK form/calculation sections to specific Jalal5 activity IDs.

The workbook's `Crosswalk جلال۴` column still needs to be populated from the reviewed mapping. Until the column is filled, the 58-row historical mapping and the 3 added-scope classifications are accepted by owners, and current-main activity evidence is reconciled, the task-to-task crosswalk remains **proposed/pending** and Jalal5 earned progress remains Pending. The section-to-task map and crosswalk are traceability artifacts, not evidence that implementation or tests are already complete.

## 3. Website inventory and journey contract

The workbook distinguishes target routes from implemented routes. The target inventory has **28 route records**:
- **25 public/indexable target pages:** Home; Platform overview; Features overview; Project Controls; Planning & Scheduling; Resources & Cost; Progress & EVM; Documents & Contracts; Field Operations; Change & Claims; Forms & Compliance; AI Assistant; Integrations; Solutions overview; Contractors; Owners & Developers; Project Controls Teams; Pricing; Resources; Documentation; Help Center; FAQ; About; Contact; Security & Privacy.
- **2 non-indexable authentication entry routes:** `/login` and `/get-started`.
- **1 private workspace route:** `/app`, which must never inherit public marketing canonical/SEO metadata or expose tenant/project data to crawlers.

This target count does **not** claim that all routes are implemented in current main. Current source has a partial landing/app-entry foundation; the page-by-page route audit remains an execution requirement under [Issue #1436](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1436) and [Issue #1101](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1101).

For each route, the workbook records the previous and next route, parent/journey context, primary entry source, cross-page CTAs, required content, localization policy, indexability, SEO acceptance and current-status note. Acceptance requires a built-artifact crawl: all intended internal links resolve; breadcrumbs and previous/next links match the route graph; no dead/orphan page; canonical/title/description/OpenGraph/structured data are accurate; sitemap/robots/index policy is correct; localized alternates exist before being advertised; and private app/auth pages are not indexed. Marketing content must not claim unverified features, model support or certifications.

## 4. Workspace menu coverage

The plan preserves the current **nine root menu keys**: Project, Schedule, Progress, Resources, Cost, Documents, Reports, Control and Settings. The workbook expands them into **62 planned submenu/action rows**. That is a coverage inventory, not proof that each screen/action already exists.

Each row has bilingual labels, target screen, previous/next sibling, functional scope and permission/status boundary. Detailed requirements include WBS/Work Packages, complete Activity Grid/custom fields, relationships/network, Gantt/timeline, schedule/recalculate and diagnostics, project/activity/resource/lag calendars, constraints, baselines, progress/actuals, resource assignments/leveling, costs/EVM, documents/RFI/Submittals/claims, procurement, field logs/inspections, form builder, dashboards, report/print/export, language settings, help and recovery. Every command that overlaps P6 must map to a stable control/action ID and calculation/test contract; UI-only placeholders do not count as implementation.

## 5. Native Mobile is a mandatory V1 client

The product-owner decision is explicit: **CUBI V1 includes the Website, Desktop application and a native Mobile application. Mobile is not deferred to V2.** See [governance Issue #1486](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1486); it supersedes the conflicting mobile-V2 language in the historical crosswalk.

V1 Mobile acceptance must include, at minimum:
- A real native host/runtime, authenticated session and project/workspace shell, with observable permission, loading, empty, error and recovery states.
- Core planning journeys: WBS/work-package navigation, activity create/edit, predecessor/successor relationship viewing/editing for FS/SS/FF/SF with lead/lag, schedule/recalculate invocation through the authoritative application contract, and relevant early/late/float/criticality results from that same calculation result.
- An explicitly scoped set of first field/control workflows aligned to the product schedule (such as field logs, attendance/timecards, equipment status, inspection/quality/safety observations and punch/closeout where included), using durable APIs and tenant/project/revision/authorization boundaries.
- Correct offline/online/sync behavior for every workflow declared offline-capable; clear conflict and stale-revision handling; no hidden success claim before write → commit → fresh-read proof.
- RTL/LTR, all declared supported languages, locale-aware project data and Jalali/Gregorian date presentation; mobile navigation, accessibility and responsive detail/report views.
- Mobile-specific negative, permission, accessibility, localization, integration, lifecycle/recovery and regression tests. AI/voice/OCR capabilities may only be advertised when the real runtime/provider capability is verified.

Mobile must reuse the same versioned contracts and authoritative Shared Domain/Calculation Core as Web/Desktop. **No client-side duplicate CPM, calendar, resource leveling, progress, cost or EVM engine is permitted.** Calculation parity and source-before-coding requirements remain unchanged.

**Owner lanes:** Farmj22002 owns the Mobile client/runtime and user journeys; Hasan owns backend/API/persistence/auth/sync contracts in his lane; Jalal owns shared calculation semantics, architecture and integration/release acceptance. Reassignments require a recorded decision and workbook update.

**Schedule and weight gate:** the companion backlog [`MOBILE_V1_REBASELINE_BACKLOG_2026-10-18.md`](MOBILE_V1_REBASELINE_BACKLOG_2026-10-18.md) defines 14 candidate activities (`MV1-01`–`MV1-14`) with owners, dependencies to validate and exit criteria. They are currently in a separate `Mobile V1 Rebaseline` sheet; estimates, dates and weights intentionally remain `TBD`, so the old 130-task/100-point/535.21-PD model is not certified for the expanded scope. Size each candidate, integrate accepted rows into the primary schedule, reallocate weights exactly to 100.00, then rerun formula, dependency, owner-lane and forecast QA. The former Jalal 3 mobile 20-point value is historical sizing context only, not an approved Jalal 5 weight. Do not award progress for documenting the backlog. Until this gate is complete, the plan remains DRAFT and Jalal 5 earned progress remains Pending.

## 6. AI assistant design contract

The goal is a **Pro-level construction project-controls assistant**, not a generic chat screen. The workbook lists 27 detailed capabilities and a P0 acceptance matrix. It covers text and supported file intake; project initialization; WBS/activity/relationship/resource proposals; natural-language schedule/control queries; revision-bound source grounding; scenarios; document/contract analysis; forms/report generation; error explanation and next steps; voice and OCR where actual provider/runtime capability is verified; and action proposal, preview, approval/rejection, execution, audit and report readback.

Execution is intentionally dual-mode:
- **Web:** private server-hosted model/runtime behind authenticated CUBI APIs.
- **Desktop:** a real local model plus inference runtime provisioned to run on the user's computer with network interfaces disabled. After provisioning, declared offline assistant workflows must function without external AI access. A capability flag/mock/injected loader is not enough. A missing/incompatible local model must produce a clear limitation, never a hidden cloud fallback.
- Both modes use the same versioned tool contracts, real persisted application services and authoritative Shared Domain/Calculation Core. Model output does not calculate or redefine P6 scheduling, calendar, resource, cost or EVM semantics.
- Every tool call is tenant/project/operation scoped; facts and predictions are separated; sources, revisions, model/action context and uncertainty are visible. Consequential mutations are previewed and approved by an authenticated authorized user, bind to exact proposal/base revision, execute transactionally/idempotently, and have durable audit plus fresh-read/report verification. Rejection/denial/stale revision produces no authoritative mutation.
- Desktop acceptance must run with networking fully disabled and prove local model loading, grounded local data/file query, allowed action, denied action, authoritative calculation identity, audit behavior and zero outbound AI-provider request. Voice/OCR are only claimed offline when their actual local engines also pass.

Implementation remains tracked by [Issue #1423](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1423) and [Issue #94](https://github.com/consttruction-pm/consttruction-pm-platform/issues/94); the desktop offline principle is also recorded in draft [PR #1482](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1482). These are not claims that the local inference engine is finished.

## 7. Source-driven P6 and PMBOK contracts

- The workbook’s P6/PMBOK ledger has **56 top-level P6 calculation contract sections** and **33 top-level PMBOK form/calculation contract sections**. Each row is a coverage anchor with authority, implementation map, expected tests and state.
- [PR #1478](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1478) contains the source-backed P6 calculation contract. As checked for this schedule, it is open/unmerged.
- [PR #1480](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1480) contains the PMBOK-aligned form/formula contract. As checked for this schedule, it is open/unmerged.
- P6 Release 26/26.4 is the compatibility and no-silent-omission baseline for overlapping behavior. Each rule must be traced to official edition/source evidence, a CUBI implementation mapping and a regression/parity fixture. Where public documentation leaves semantics unresolved, mark OPEN/PARITY TEST REQUIRED; do not guess.
- PMBOK is tailored and non-prescriptive. Distinguish PMI-documented rules from CUBI-approved techniques, project-configured formulas, Shared Core outputs, AI-proposed formulas and OPEN semantics. Forms, charts and reports may not introduce duplicate CPM/calendar/resource/EVM engines.

## 8. Current blockers and release gates

The rebaseline candidate workbook contains 22 release gates, including the two added gates for mandatory Mobile V1 scope/weight reconciliation and the read-first continuity/handoff protocol. The existing PASS values validate only the old 130-task model, not completeness after the scope change. Gates include:
- current-main CI failures for shared-resource over-allocation and backward SS/constraint handling: [Issue #1476](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1476) and source-before-coding evidence [Issue #1447](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1447);
- persisted Activity Master write/read → immutable schedule input composition, which cannot be proven by manually assembled test snapshots: [Issue #1462](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1462);
- full AI vertical slice #1423 and Desktop offline local inference #94;
- page route/SEO graph and all-language acceptance #1436/#1428;
- PMBOK formula authority and type/unit/null/rounding rules;
- transactional permissions, approval/rejection, durable audit/idempotency, stale revision, report/Gantt/chart/source identity;
- project import/export round trip, version-pinned calendars, restore/recovery and distinct Undo/Redo versus version restore versus backup restore.

The spreadsheet’s **Dependency QA** sheet has 300 explicit predecessor edges and 127 primary-owner-lane ordering checks; its computed model reports zero violations/overlaps. These are planning-calculation checks only, not test evidence from production software. The plan must be rebuilt if the accepted task crosswalk, actual owner capacity or a project calendar changes.

## 9. Workbook index

The revised candidate workbook contains thirteen sheets: Dashboard; Jalal5 Schedule; Workstream Summary; Site Route Matrix; App Menu Map; AI Capability Matrix; P6 PMBOK Ledger; Release Gates; Decision Register; Jalal4 Archive; Team Load; Dependency QA; Mobile V1 Rebaseline. The 14 candidate mobile activity rows are intentionally not added to the main schedule denominator until task-level sizing, weights and the predecessor/owner-lane network are reconciled. The workbook is therefore a candidate for re-baselining, not final approval.

The weighted-progress fields deliberately start Pending. On each accepted merge, update only the mapped activity row, attach current-main SHA, exact-head test/runtime evidence and acceptance URL, then recalculate earned points from row formulas. Keep overall delivery, Web Beta, P6 semantic parity and release readiness as separate metrics.