# Jalal 5 — Master Weighted Schedule and Completeness Control

**Prepared:** 2026-10-18  
**Plan ID:** JALAL-5-CUBI-2026-10-18  
**Status:** Planning baseline for review; not a product implementation completion claim.  
**Product-code baseline checked:** `main@faa34707957022ffa3f51c8d13561047cc7a44cc`  
**Workbook:** `Jalal5_Weighted_Master_Schedule_2026-10-18.xlsx` (12 sheets; row-level task, web route, menu, AI, source, gate, decision and dependency matrices).

## 1. Mandatory governance

1. **Reuse approved decisions; do not re-design from scratch.** The existing CUBI brand/visual principles, Shared Domain/Calculation Core, Web-first presentation, authentication/persistence contracts, project settings, Jalali/Gregorian rules and localization principle are fixed baselines. Reopen them only by a documented change request with impact analysis and approval.
2. **Jalal 5 has 100 weighted points.** Weights are allocated once across ten workstreams. Shared work is counted once. PRs, documentation, comments, mocks and isolated tests earn no product completion until the relevant implementation is merged, exact-head checks pass and acceptance evidence is recorded.
3. **No false current percentage.** Jalal 4's last calculated detailed snapshot is 48.13% (2026-10-13), not a newly certified 2026-10-18 value. Jalal 5 row-level acceptance and its earned total remain Pending until the 58 Jalal 4 activities are explicitly mapped to Jalal 5 rows against current-main evidence. Pending is not a claim that the whole product is 0% complete.
4. The last Jalal 4 workbook implies 535.21 remaining person-days. The Jalal 5 task allocations use that value only as a **temporary proportional effort envelope** because the new 130-row J4→J5 crosswalk is not yet accepted. The 1986 person-days in the gross lifecycle column are the unscaled scope estimate, not estimated remaining effort. Re-estimate individual rows after the crosswalk; do not silently preserve this proportional assumption as audited fact.
5. Date planning uses Monday 2026-10-19 as week 1, explicit predecessor relationships, one serialized primary-owner lane per owner and 80% focus capacity. The first computed owner/dependency forecast ends 2027-12-08; planning week 60 ends Friday 2027-12-10. This is about six weeks beyond the inherited Jalal 4 target (2027-10-29), is **conditional**, and must be recalculated after row-level crosswalk, blocker resolution and calendar-aware resource planning. Public holidays and project-specific calendars are not yet modeled in this coarse planning calculation.

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

The exact 130 activities, dependencies, owners, supporting roles, row-level weights, acceptance criteria, source links, provisional effort and J4 crosswalk fields are in the workbook’s **Jalal5 Schedule** sheet. Do not use the stream summary as a substitute for accepting the individual activity rows.

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

## 5. AI assistant design contract

The goal is a **Pro-level construction project-controls assistant**, not a generic chat screen. The workbook lists 27 detailed capabilities and a P0 acceptance matrix. It covers text and supported file intake; project initialization; WBS/activity/relationship/resource proposals; natural-language schedule/control queries; revision-bound source grounding; scenarios; document/contract analysis; forms/report generation; error explanation and next steps; voice and OCR where actual provider/runtime capability is verified; and action proposal, preview, approval/rejection, execution, audit and report readback.

Execution is intentionally dual-mode:
- **Web:** private server-hosted model/runtime behind authenticated CUBI APIs.
- **Desktop:** a real local model plus inference runtime provisioned to run on the user's computer with network interfaces disabled. After provisioning, declared offline assistant workflows must function without external AI access. A capability flag/mock/injected loader is not enough. A missing/incompatible local model must produce a clear limitation, never a hidden cloud fallback.
- Both modes use the same versioned tool contracts, real persisted application services and authoritative Shared Domain/Calculation Core. Model output does not calculate or redefine P6 scheduling, calendar, resource, cost or EVM semantics.
- Every tool call is tenant/project/operation scoped; facts and predictions are separated; sources, revisions, model/action context and uncertainty are visible. Consequential mutations are previewed and approved by an authenticated authorized user, bind to exact proposal/base revision, execute transactionally/idempotently, and have durable audit plus fresh-read/report verification. Rejection/denial/stale revision produces no authoritative mutation.
- Desktop acceptance must run with networking fully disabled and prove local model loading, grounded local data/file query, allowed action, denied action, authoritative calculation identity, audit behavior and zero outbound AI-provider request. Voice/OCR are only claimed offline when their actual local engines also pass.

Implementation remains tracked by [Issue #1423](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1423) and [Issue #94](https://github.com/consttruction-pm/consttruction-pm-platform/issues/94); the desktop offline principle is also recorded in draft [PR #1482](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1482). These are not claims that the local inference engine is finished.

## 6. Source-driven P6 and PMBOK contracts

- The workbook’s P6/PMBOK ledger has **56 top-level P6 calculation contract sections** and **33 top-level PMBOK form/calculation contract sections**. Each row is a coverage anchor with authority, implementation map, expected tests and state.
- [PR #1478](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1478) contains the source-backed P6 calculation contract. As checked for this schedule, it is open/unmerged.
- [PR #1480](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1480) contains the PMBOK-aligned form/formula contract. As checked for this schedule, it is open/unmerged.
- P6 Release 26/26.4 is the compatibility and no-silent-omission baseline for overlapping behavior. Each rule must be traced to official edition/source evidence, a CUBI implementation mapping and a regression/parity fixture. Where public documentation leaves semantics unresolved, mark OPEN/PARITY TEST REQUIRED; do not guess.
- PMBOK is tailored and non-prescriptive. Distinguish PMI-documented rules from CUBI-approved techniques, project-configured formulas, Shared Core outputs, AI-proposed formulas and OPEN semantics. Forms, charts and reports may not introduce duplicate CPM/calendar/resource/EVM engines.

## 7. Current blockers and release gates

The workbook contains 20 release gates, including:
- current-main CI failures for shared-resource over-allocation and backward SS/constraint handling: [Issue #1476](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1476) and source-before-coding evidence [Issue #1447](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1447);
- persisted Activity Master write/read → immutable schedule input composition, which cannot be proven by manually assembled test snapshots: [Issue #1462](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1462);
- full AI vertical slice #1423 and Desktop offline local inference #94;
- page route/SEO graph and all-language acceptance #1436/#1428;
- PMBOK formula authority and type/unit/null/rounding rules;
- transactional permissions, approval/rejection, durable audit/idempotency, stale revision, report/Gantt/chart/source identity;
- project import/export round trip, version-pinned calendars, restore/recovery and distinct Undo/Redo versus version restore versus backup restore.

The spreadsheet’s **Dependency QA** sheet has 300 explicit predecessor edges and 127 primary-owner-lane ordering checks; its computed model reports zero violations/overlaps. These are planning-calculation checks only, not test evidence from production software. The plan must be rebuilt if the accepted task crosswalk, actual owner capacity or a project calendar changes.

## 8. Workbook index

The saved workbook contains twelve sheets: Dashboard; Jalal5 Schedule; Workstream Summary; Site Route Matrix; App Menu Map; AI Capability Matrix; P6 PMBOK Ledger; Release Gates; Decision Register; Jalal4 Archive; Team Load; Dependency QA.

The weighted-progress fields deliberately start Pending. On each accepted merge, update only the mapped activity row, attach current-main SHA, exact-head test/runtime evidence and acceptance URL, then recalculate earned points from row formulas. Keep overall delivery, Web Beta, P6 semantic parity and release readiness as separate metrics.