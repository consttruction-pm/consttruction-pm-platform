# Qoder execution packet — Issue #1989 — Schedule Scenarios Phase 1

**Priority:** Engineering P1  
**Status:** READY FOR QODER REPOSITORY EXECUTION AFTER LIVE PATH-OWNERSHIP CHECK  
**Prepared:** 2026-11-15  
**Issue:** https://github.com/consttruction-pm/consttruction-pm-platform/issues/1989  
**Architecture parent:** https://github.com/consttruction-pm/consttruction-pm-platform/pull/1988  
**Phase 1 contract:** `docs/architecture/CUBI_ENGINEERING_P1_SCHEDULE_SCENARIOS_PHASE1_CONTRACT_V1.md`  
**Tracker:** `docs/architecture/CUBI_ENGINEERING_P1_EXECUTION_TRACKER_SCHEDULE_SCENARIOS_V1.md`  
**Baseline main SHA at last verified inspection:** `376af9e2751ea1260ea3b4ed9be050eb1722afbf`  
**Documentation branch head at packet creation:** refresh from GitHub before execution; never assume this packet's SHA is current.

## 0. Instruction to the Qoder agent

This is an implementation handoff, not a request to write another report. Work directly in the canonical repository checkout. Do not stop after inventory, design, or a checklist. Resolve each gate, implement the next safe vertical slice, run tests, fix failures, commit, push, and continue to the next in-scope step until the defined slice is delivered. Do not claim runtime, tests, parity, merge, or deployment without exact-SHA evidence.

The user has explicitly established:
- P6 EPPM V26 HTML Help is the primary universal parity source for existing capabilities.
- When a new Primavera Cloud capability has no EPPM counterpart, use the official Cloud HTML Help as the functional specification.
- Where concepts overlap, preserve EPPM semantics and reconcile Cloud additions without duplicate menus, domain records, APIs, workflows, calculations, or owners.
- Engineering-owned capabilities are P1 and must be implemented by Qoder after feasibility and ownership checks.
- Enterprise-owned capabilities are P2 and are architected/implemented by ChatGPT after Engineering contracts stabilize. Enterprise consumes Engineering-owned facts; it must not duplicate scheduling calculations or scenario mutations.
- Workbench is only an entry/notification surface, not an owner of scenario records or calculations.

## 1. Mandatory source hierarchy and direct references

### 1.1 EPPM V26 primary baseline

P6 EPPM V26 HTML Help TOC:
https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm

Use this source for all existing EPPM concepts: project/EPS identity and security, activities, WBS, relationships, calendars, baselines, scheduling options, resource assignments/leveling, progress, activity owners, team-member status updates, and portfolio features.

The inspected EPPM V26 TOC contains Portfolio Views > About What-if Analysis. It does not expose a Reflection or Schedule Comparison topic. Do not conflate portfolio what-if with project schedule scenario/reflection workflows. For each EPPM overlap, open the exact topic page and map fields, privileges, states and semantics. If a concept is absent, record **NOT PRESENT IN EPPM V26 HTML HELP** with the inspected TOC/topic evidence; do not infer absence from memory.

### 1.2 Primavera Cloud HTML Help — source for Cloud-only schedule-scenario workflow

Cloud Help TOC:
https://primavera.oraclecloud.com/help/en/user/toc.htm

Required topics:
- Schedule Scenarios Overview: https://primavera.oraclecloud.com/help/en/user/107323.htm
- Add a Scenario: https://primavera.oraclecloud.com/help/en/user/107329.htm
- Open a Scenario: https://primavera.oraclecloud.com/help/en/user/178412.htm
- Manage a Scenario: https://docs.oracle.com/cd/E80480_01/English/user_guides/schedule_management_user_guide/107330.htm
- Set a Scenario as the Current Schedule: https://primavera-us2.oraclecloud.com/help/en/user/107331.htm
- Schedule Comparison Overview: https://primavera.oraclecloud.com/help/en/user/191095.htm
- Compare Two Versions of a Project Schedule: https://primavera.oraclecloud.com/help/en/user/191096.htm
- Merge Overview: https://primavera-us2.oraclecloud.com/help/en/user/288769.htm
- Project Security Privileges Definitions: https://primavera.oraclecloud.com/help/en/user/82318_1.htm

Open and verify every topic in the current Help version. Record exact page title, updated/version details when present, feature behavior, permissions, fields, lifecycle states and differences from EPPM. Some URLs may redirect or be legacy paths; record the final canonical destination rather than silently assuming the supplied URL is current.

### 1.3 P6 Professional V26 supplementary only

P6 Professional V26 Help is not the universal EPPM baseline and must not be used to assert EPPM-only behavior. It is a supplementary cross-check for desktop Reflection workflows:
- TOC: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
- Creating and using reflections: https://docs.oracle.com/cd/G48902_01/client_help/en_US/creating_and_using_reflections.htm
- Reflection FAQ: https://docs.oracle.com/cd/G48902_01/client_help/en_US/frequently_asked_questions_about_reflections.htm

The user-supplied 815-page V26 PDF is supplementary evidence. If not present in the canonical checkout, mark MISSING / VERIFY; continue with normative HTML and do not claim PDF review.

## 2. Repository baseline and collision gate — do this first, then proceed

1. Fetch latest main and record exact SHA.
2. Read root and nested `AGENTS.md` files, package-specific instructions, and the Qoder execution/acceptance standard in the repository. A prior GitHub lookup of root `AGENTS.md` returned 404; verify in the actual canonical checkout (including case and nested files). If genuinely absent, create the minimal root instructions required by repository policy and commit that separately before implementation.
3. Refresh every open scheduling-related PR's head SHA and complete changed-file list. Include at least active work in schedule core, immutable snapshots, resource leveling, Activity Master, calendars, and visual workspace. The previous audit saw PRs including #1716, #1711, #1676, #1644, #1582, #1518, #1511, #1510, #1509, #1485, #1474, #1469, #1464, #1461, #1459, #1457, #1454, #1453, #1452, #1446, #1438, #1434, #1432 and #1926; this list is a historical prompt, not a current exhaustive list.
4. Inspect each PR's exact files and commits. Build an ownership matrix (path, current writer, PR/head, overlap, safe integration point). Do not edit a shared path until its owner has completed/merged or the owning agent has explicitly coordinated a safe handoff.
5. Inspect latest main source paths for scenario shell, route/API patterns, tenant/project security, snapshot composer, schedule core, database adapters/migrations, background jobs, audit/idempotency and tests. Reuse the canonical implementations. Do not infer from documentation alone.
6. Do not edit global shell, `apps/web/src/main.ts`, resource-leveling, or shared CPM engine unless the ownership matrix proves the path is free and the change is essential. Prefer additive scenario-domain modules and integration through established contracts.

## 3. First implementation target — thin but real vertical slice

The first delivered slice must create and persist an isolated scenario from a pinned authoritative schedule snapshot and run it through the existing shared scheduler.

Required capabilities:
1. Create scenario from current schedule snapshot (and baseline only if existing snapshot composer supports it safely).
2. List/read scenarios scoped to tenant and project.
3. Store immutable source snapshot ID/hash, project revision, schedule revision, baseline/source references, actor/owner, timestamps, lifecycle, schema version and optimistic scenario revision.
4. Persist typed scenario changes through domain validation; no arbitrary client JSON patch and no silent dropping of unsupported fields.
5. Run the scenario through the existing Shared Scheduling Core with pinned calendars, data date, scheduling options, resources and versioned calculation context.
6. Persist immutable run record with input/context/output hashes, scheduler version, run parameters, state, timestamps and structured diagnostics.
7. Prove source project/schedule and all other scenarios remain unchanged after scenario edits and runs.
8. Add authorization checks on every read/write/run, project/tenant isolation, optimistic concurrency and idempotent request handling.
9. Provide API/application/repository separation and SQLite + PostgreSQL adapter parity using established repository patterns and migrations.
10. Wire the existing Scenario Lab shell only after the API is real. No new top-level menu or duplicate schedule editor. If the UI cannot yet perform an operation, disable it with a truthful reason.

Comparison should follow only when authoritative immutable source and scenario snapshots are available. Comparison must pin both sides, identify added/deleted/changed/unchanged/non-comparable values and respect field permissions. Promotion/merge is a separate later gate; do not expose a live merge endpoint in this first slice.

## 4. Required tests — no success-by-existence

Add and execute:
- scenario create/read/list, tenant/project isolation and permission denial;
- scenario source snapshot immutable provenance and hash verification;
- typed edit validation, unsupported field rejection and optimistic revision conflict;
- source project unchanged after scenario edits and run;
- scenario A unchanged after scenario B edit/run;
- scheduler invocation uses authoritative shared core and exact pinned calculation context;
- immutable run output and fresh read-back;
- duplicate idempotency key same payload returns same operation result; key reuse with different payload rejected;
- concurrent run/edit behavior, worker restart/failure/timeout/cancellation;
- SQLite and PostgreSQL migrations/repository integration;
- authorization revoked between create/edit/run;
- no regression in CPM, calendars, resource-leveling, baselines, activities and existing Schedule workspace.
Use exact numeric fixtures where documented rules allow expected dates/durations/float/resource results to be calculated. State units and calendar basis. A passing test that only asserts a row exists is insufficient.

## 5. V26 acceptance matrix

Create/update a durable requirement-to-evidence matrix with one row per source behavior:
- EPPM source topic or explicit NOT PRESENT;
- Cloud source topic or NOT APPLICABLE;
- classification: EPPM parity / reconciled shared primitive / Cloud-origin extension / CUBI-only;
- semantic delta and resolution;
- CUBI domain owner and menu/API/data boundary;
- required permissions and lifecycle states;
- implementation paths, tests, expected outputs, exact tested SHA and evidence links;
- status from the repository's accepted status vocabulary.

Do not label Cloud-only scenario lifecycle as EPPM parity. The portfolio-level EPPM What-if topic is not equivalent to project schedule scenarios. Do not copy Oracle branding, labels, URLs, screenshots or proprietary assets into customer-facing CUBI UI/help.

## 6. UI integration acceptance

Existing shell file: `apps/web/src/workspace-engineering-shells.ts` (verify current main before editing). Migration ledger previously states `scenario-lab` is not mapped to a verified live service.

Wire the existing surface to real services. Test actual browser path and preserve:
- current canonical single visual workspace and project context;
- Activities/Schedule/Gantt and Details layout;
- RTL/LTR, Persian/Jalali display and Gregorian/timezone semantics;
- registered localization conventions;
- keyboard navigation, loading/empty/error/unauthorized/stale states;
- no decorative enabled controls, no false success toast and no fake comparison results.

## 7. Required delivery behavior

Do not stop after updating docs or reporting findings. After each bounded implementation step:
1. commit the working implementation and tests;
2. run focused tests;
3. run all relevant package/type/build checks;
4. run integration/browser E2E in the canonical execution environment;
5. inspect failures and fix them (do not weaken/delete tests);
6. refresh exact branch/PR head and CI;
7. record evidence and continue to the next in-scope phase.

Create/refresh a PR with implementation code only after the first working vertical slice exists. Do not merge or deploy without the product owner's explicit approval. If a Vercel build-rate limit blocks preview, continue local/API/browser tests and record deployment as externally blocked; do not treat the Vercel failure as a test failure or as success.

## 8. Phase exit gates

- Phase 1 contract: approved after exact topic crosswalk, ownership matrix, independent architecture/security review and no unresolved contradiction.
- Backend slice: create/read/edit/run end-to-end; source immutability; auth/concurrency/idempotency; SQLite/PostgreSQL tests green.
- UI: real browser workflow connected to APIs; all controls honest; browser evidence recorded.
- V26: exact dual-source matrix and numeric/reference fixtures accepted. Direct licensed P6 comparison may remain a separate external evidence item; do not claim it if unavailable.
- Promotion: separate Phase 5 release only after selected-change semantics, atomic transaction, conflict detection, backup/recovery, audit and authorization are independently tested.

## 9. Priority boundary

Engineering P1 is this issue. Enterprise P2 begins only after Engineering scenario/run/compare contracts are stable. Enterprise may later consume versioned read-only scenario summaries and portfolio capacity facts. It must not own or duplicate scenario mutation, CPM, resource leveling or schedule-of-record state. ChatGPT coordinates Enterprise design and implementation after Engineering contracts stabilize. Workbench remains non-owning.

## 10. Mandatory response to the product owner

The Qoder agent's completion response must include:
- exact branch, base SHA, head SHA and PR;
- changed files and why each changed;
- implementation behavior actually reachable in app/API;
- exact commands and results, test counts, skipped tests and reasons;
- exact CI run/check URLs on final SHA;
- browser routes, locale, viewport, screenshots and workflow evidence;
- dual-source Help traceability and unresolved source gaps;
- remaining blockers with named path/owner, not generic statements;
- explicit confirmation whether scenario source data stayed unchanged;
- next phase started, not just recommended.

A report without implementation and fresh evidence does not satisfy this handoff.
