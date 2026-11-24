# P0 Project Recovery, Four-Project Continuity, and Enterprise Project Definition — Agent Execution/Handoff Protocol

**Status:** Owner-directed execution protocol; planning only until source/runtime evidence authorizes implementation.  
**Owner:** Product owner / platform owner.  
**Canonical repository:** `consttruction-pm/consttruction-pm-platform`.  
**Baseline inspected for this revision:** `main` at `17de9bd3004c7bc9420af063d327a4bc7b5f080f` (2026-11-24).  
**Parent execution issue:** [#2138](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2138).  
**Related protected recovery:** [#2131](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2131).  
**Dam shared build project:** [#2132](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2132), active WIP [PR #2133](https://github.com/consttruction-pm/consttruction-pm-platform/pull/2133).  
**Reference-project persistence:** [PR #2129](https://github.com/consttruction-pm/consttruction-pm-platform/pull/2129), already merged before this baseline.  
**P6 native interchange:** [#2136](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2136) / [PR #2137](https://github.com/consttruction-pm/consttruction-pm-platform/pull/2137).

This file is the durable handoff source. An agent must be able to resume from GitHub alone after another agent's token/session expires. Do not rely on ChatGPT memory, an agent's private notes, or an uncommitted local plan.

---

## 0. Repository audit — the mandatory first action (NO CODE OR DATA MUTATION)

The first agent and every replacement agent MUST start here. Do not begin by implementing the previous chat instruction or by deleting anything.

### 0.1 Read the repository's continuity and task rules

Read, in this order, from the current `main` revision:
1. `README.md`
2. `AGENTS.md` and every applicable nested `AGENTS.md`
3. `docs/governance/PROJECT_CONTINUITY_PROTOCOL.md`
4. `docs/governance/PROJECT_STATE_LEDGER.md`
5. `docs/standards/CUBI_PAGE_BY_PAGE_DESIGN_AND_ACCEPTANCE.md`
6. `docs/traceability/ENTERPRISE_PAGE_BY_PAGE_ICON_HELP_CROSSWALK.md`
7. `docs/traceability/CUBI_ENGINEERING_V26_TRACEABILITY.md`
8. `docs/traceability/CUBI_ENTERPRISE_V26_TRACEABILITY.md` and the corresponding JSON/CSV registries
9. `docs/engineering/CUBI_REFERENCE_PROJECTS_IMPORT_MAPPING.md` and its sheet inventory / validation evidence
10. `docs/database/CUBI_DATABASE_ARCHITECTURE.md`
11. Issues #2131, #2132, #2136, #2138; PRs #2129, #2133, #2137; and all newer linked PRs/commits/comments.

Also inspect the exact current router, page renderer, API, application service, repository, migration, importer, tests and CSS/icon files. For Enterprise, reconcile the 26 PageIds in `apps/web/src/enterprise/router.ts` against the current page crosswalk; do not assume old `/enterprise/*` routes are canonical.

### 0.2 Refresh source state before each work session

Record in the issue checkpoint:
- exact `main` SHA and timestamp;
- current branch and exact head SHA;
- all open PRs touching relevant paths, including changed-file lists, merge status and exact-head CI;
- current owner/path claims and any active PR conflict;
- relevant migrations and current schema-ledger version;
- deployment commit/alias for the canonical Preview (do not infer from branch name);
- exact files actually inspected and their revisions.

The known baseline above is historical. If `main` has moved, the new SHA supersedes it and must be written to the checkpoint before work.

### 0.3 Mandatory Preview and Help references

There is exactly one official Preview entry, defined in `docs/standards/CUBI_PAGE_BY_PAGE_DESIGN_AND_ACCEPTANCE.md`:

`https://cubi-web-preview-git-feat-vercel-p-8eb184-foroughichamshir-7811.vercel.app/app?project=preview-rps-01&view=live`

The owner also supplied this Enterprise test entry:

`https://cubi-web-preview-git-main-foroughichamshir-7811.vercel.app/login?next=/cubi/enterprise/projects%3Fproject%3DCUBI-REF-001%26utm_source%3Dchatgpt.com`

The latter is a login/deep-link test address, NOT permission to replace the canonical Preview alias. Resolve the exact deployment SHA and alias mapping. If the canonical alias is unhealthy or returns 404, stop and report; do not silently substitute a main alias, per-PR URL or another Vercel project.

- Engineering: official P6 Professional V26 HTML Help: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
- Engineering companion guide: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/index.html
- Enterprise: official P6 EPPM V26 Help: https://docs.oracle.com/cd/G48897_01/p6help/en/
- Use the correct product-family Help. Never use Professional Help as an EPPM substitute or EPPM Help as an Engineering substitute.
- For Project Details, also use the exact Professional V26 topic: https://docs.oracle.com/cd/G48902_01/client_help/en_US/defining_project_details.htm
- Record exact topic titles, URLs, section/steps and evidence for each control. No Oracle/Primavera/P6 branding may appear in CUBI product UI.

### 0.4 Required audit output before implementation

Create/update a repository audit report and issue checkpoint containing:
- canonical routes/PageIds and inheritance chains;
- current UI controls and icons;
- API → application service → repository → PostgreSQL table/migration mapping;
- all import/export paths, manifests, source artifacts and generated files;
- project identity inventory and source provenance;
- tests and current gaps;
- active branch/PR ownership conflicts;
- known preview and database blockers.

Classify every inspected file as **KEEP**, **MODIFY**, **MERGE/REUSE**, **REMOVE ONLY AFTER PROOF**, or **UNKNOWN / VERIFY**. For each: path, purpose, creator/commit if ascertainable, imports/dependencies, runtime usage, persistence source, tests and evidence. Do not delete a file merely because its name looks like a duplicate. Never claim that an absent search result proves a file or persisted record never existed.

**Exit gate 0:** the audit is committed or recorded in a GitHub checkpoint; exact starting SHA and next bounded work item are explicit. No source, database, identity, project or deployment mutation has occurred.

---

## 1. Absolute identity, password, dashboard and access preservation (P0, applies to every stage)

The owner's existing account and administrator access are protected invariants, not debugging variables.

### Never do any of the following
- Reset/change the owner's password; rewrite or re-hash the password; rotate, delete or recreate credentials; alter MFA, recovery settings or password-reset state.
- Read, export, print, log, commit, paste into issues, or otherwise expose the owner's password, password hash, OTP, recovery code, cookie, access token, refresh token, session secret or API key.
- Delete/recreate/remap/downgrade the owner identity or alter the owner's `global_admin` privilege, tenant membership, organization membership, environment grants, project permissions or role assignment.
- Revoke active sessions or force sign-out as a troubleshooting shortcut.
- Replace the existing Personal Workbench/Dashboard, Global Administration dashboard, administrator routes, role selector/authorization, or environment selector with a new shell or alternate login path.
- Bypass the required journey: authenticated owner → their Personal Workbench/personal dashboard → authorized environment selection → CUBI Engineering or CUBI Enterprise. Switching between already permitted environments must not require forced logout.
- Use the owner's account as a destructive test identity.

### Required baseline and protection
1. Read identity/authentication/authorization source and migration history. Use read-only checks to verify the owner account exists, is active, retains `global_admin`, has the expected tenant/environment grants and can access both environments. Never emit credential fields or secret values.
2. Record only safe, non-secret facts and integrity evidence in the restricted operational record. If a restorable backup is required, keep it encrypted and access-controlled; do not put identity secrets or database dumps in GitHub artifacts.
3. Use a disposable test user and disposable test project for create/edit/delete, permission, session and browser tests.
4. Any schema or authorization change must prove owner access and existing dashboard routes remain intact before/after; no broad role or RLS policy changes without table-specific policy design and regression coverage.
5. Preserve all existing dashboard data, widgets, saved layouts, preferences, navigation, personal workbench state and Global Administration functionality. Do not "fix" a missing dashboard by creating a second dashboard.

**Exit gate 1:** an owner-access preservation matrix is documented without secret material; no owner credential/session/identity/role/dashboard mutation occurred.

---

## 2. Reconcile project identity and resolve the "three wrong projects" safely

### 2.1 Important repository finding — do NOT confuse these project sets

The current repository/issue history already identifies:
- `CUBI-REF-001`, `CUBI-REF-002`, `CUBI-REF-003`: three frozen reference projects, imported by the merged durable PostgreSQL work in PR #2129. Issue #2131 explicitly says these three IDs must not be deleted, re-imported, overwritten or mutated during the project-creation/import recovery.
- `CUBI-DAM-001`: the shared in-progress dam build project, governed by #2132 and active WIP PR #2133. It is not a finished demo and must not be duplicated. PR #2133 reports that the Dam source bundle is not yet persisted at the time of its PR description; refresh the current PR and database evidence before relying on that status.
- `preview-rps-01` and other preview fixture IDs: separate preview/test data. Do not classify them as erroneous merely because they are not the four canonical showcase records.
- `CUBI-REF-001` in the owner's supplied Enterprise deep link is a target selection, not evidence that this ID is corrupt.

Therefore, the phrase "three incorrectly imported projects" in #2138 MUST NOT be interpreted as `CUBI-REF-001/002/003` or `CUBI-DAM-001`. The exact three bad immutable IDs are **NOT YET IDENTIFIED** by the repository evidence inspected for this plan.

### 2.2 Inventory first; no deletion on name or visual similarity

Use read-only database queries and canonical APIs to inventory every candidate in the affected tenant/workspace, including:
- immutable project ID / primary key;
- tenant, workspace, project class and owner;
- creation/import timestamps and actor (where available);
- import manifest ID, source workbook SHA-256, source file name and importer/version;
- revision, source provenance, original source identifiers and status;
- linked EPS/OBS/WBS/activity/relationship/calendar/resource/assignment/baseline/cost/Enterprise records;
- audit history, document references, portfolio memberships and cross-project links;
- whether the record is a canonical customer project, reference/showcase project, Dam build project, preview fixture, or accidental artifact.

Compare the live DB, API results, current UI selectors and import journals. Names, descriptions, row counts, display order and screenshots are not identity proofs.

### 2.3 Destructive gate

Before removing anything:
1. Identify the exact three erroneous immutable IDs and explain why each is wrong with provenance evidence.
2. Produce an exact before-state inventory, referential dependency closure and protected-record comparison.
3. Create and verify a recoverable encrypted backup/snapshot outside Git; record its secure location/reference and checksum only, never credentials or dump contents.
4. Confirm the target rows are not any of the protected IDs above, not valid user projects, and not shared records referenced by other projects.
5. Present the exact IDs, tenant/workspace and dependent artifacts to the product owner in #2138 and obtain explicit approval of that exact deletion set.
6. Only then perform a transactionally scoped deletion/retirement of the approved erroneous records and their strictly owned import artifacts. Preserve append-only audit/revision evidence and all shared dependencies. Prefer reversible quarantine/retirement if canonical semantics allow; do not cascade-delete unrelated records.
7. Verify exact target IDs are absent from the intended views while every protected/out-of-scope record fingerprint, user, role, grant, dashboard and session remains unchanged.

If the exact three IDs cannot be proven or owner approval is not recorded, **STOP before deletion**. Continue only with non-destructive audit and unrelated safe work.

**Exit gate 2:** exact three IDs, provenance, backup, owner approval, transaction result and before/after integrity evidence are recorded. If not, deletion remains BLOCKED and no destructive operation is allowed.

---

## 3. Recover and validate the intended project source files

1. Search the repository, current and prior Git branches/PR artifacts, issue attachments/comments, conversation uploads and the user's Library for the exact source workbook(s) and any project-specific files previously created by the owner/agents.
2. Known mapping source: `CUBI_Three_Reference_Projects_Master_Data_v1-1.xlsx`, recorded SHA-256 `0848454d2b8b77806986eb53cf36e95521d7e789ad8c4f0b2af78acb4e82fa26`, 94 sheets. Verify the actual binary and hash; a mapping document is not a substitute for the source workbook.
3. Read `docs/engineering/CUBI_REFERENCE_PROJECTS_IMPORT_MAPPING.md`, the CSV sheet inventory, source validation report and importer code. Identify every source file created by the owner/agents, its role and provenance; distinguish original source files from derived exports, staging files, HTML/JSON dumps and generated artifacts.
4. Preserve originals immutably. Never render workbook bytes, HTML, serialized sheets or sheet dumps in Project Information or Description.
5. Map only typed supported fields into canonical entities. Show unresolved/proposed extensions and unsupported fields in a staging report; no silent drop, fabricated value, default-calendar substitution or derived CPM/EVM import.
6. If the original source file cannot be found or its hash differs, mark **SOURCE MISSING / HASH MISMATCH** and stop any import based on it. Do not ask the owner to re-upload a file until repository, issue attachments and Library searches have been exhausted.

**Exit gate 3:** exact source artifacts, hashes, source-to-target mapping, unresolved fields and approval state are recorded. No import or overwrite occurred before approval.

---

## 4. Restore P6 Professional V26 project creation and Project Details in Engineering

Use the existing Engineering Projects flow and canonical lifecycle services. Do not create a second shell or a separate project entity.

### Verified gap from #2131

The current `main` empty-state form was found to collect Project Name, Business Domain, Description, Start Date and Date System, and auto-generate Project ID. It did not expose the complete P6 Professional V26 Create Project wizard fields. Reconfirm against the latest main before implementation.

### Required P6 V26-aligned create workflow

Use the official Professional V26 topic `Create a project` and related Help topics:
- select an authorized EPS node;
- enter a user-controlled unique Project ID;
- enter Project Name;
- set Planned Start;
- optionally set Must Finish By;
- select an authorized Responsible Manager from OBS;
- select Default Rate Type;
- complete creation, then open Project Details.

The client contract, authenticated HTTP API, application service, canonical PostgreSQL repository and migrations must all carry and validate the same typed fields. Enforce project-ID uniqueness, tenant scope, EPS/OBS authorization, project-admin permission and valid date ordering on the server. Do not implement only a front-end form.

Project Details must expose the relevant V26 tabs and persisted values, including schedule, project codes, summarization, defaults and activity numbering, plus supported project dates/status/default activity type/duration type/% complete type/calendar/cost account/float settings. Each field must round-trip through revision-bound APIs and survive reload/sign-in.

Implement project selection/open and Shared / Read Only / Exclusive modes only where the server actually enforces the corresponding privilege/checkout semantics. Do not display an unenforceable access mode.

### Regression tests before fix

Cover duplicate/missing Project ID, invalid dates, start-after-finish, unauthorized EPS/OBS, denied project-admin, concurrent duplicate ID, create→list→details→open, settings edit→save→reload, access modes, revision conflicts, no partial record, and owner/dashboard non-regression. Use disposable identities and projects only.

Track implementation under #2131 and coordinate with the existing owner/branch there; do not duplicate a parallel project-lifecycle implementation.

**Exit gate 4:** P6 wizard and Project Details are persisted through the canonical PostgreSQL path and verified by browser/API/DB read-back on the approved Preview.

---

## 5. Complete the Dam project by continuing the existing workstream

- The canonical Dam project requirement is #2132, ID `CUBI-DAM-001`.
- The active implementation is WIP/Draft PR #2133. Inspect its current branch, exact head SHA, changed paths, tests, migration 16, review threads, CI and merge status before touching anything.
- Do not regenerate a competing Dam project, importer, fixture bundle, or Enterprise dataset. Continue the existing branch/owner's work or obtain an explicit path handoff.
- Preserve the PR's intended classification `SHARED_BUILD_PROJECT`: an in-progress shared build workspace, not an ordinary private customer project and not a completed DEMO reference project.
- The PR description reports 720 activities, 192 WBS nodes, 730 relationships, 72 labour resources, 48 equipment resources, 1,440 assignments, 720 baseline rows and linked Enterprise registers. Treat these as claimed bundle counts until exact-head CI, PostgreSQL persistence and fresh read-back prove them.
- Preserve CUBI-REF-001/002/003 flags, IDs, data, visibility and schedule runs.
- The shared Dam workspace must remain separately presented from ordinary personal project lists when that is the approved #2132 contract; never turn it into a per-user copy or mass-grant membership.
- The live schema must be freshly inspected. Older audit evidence said resource/calendar/baseline tables were missing; PR #2133 reports RLS hardening but does not by itself prove every missing entity migration or Dam import has completed.
- No production write/import/deploy until table dependencies, migrations, RLS, server-only service access, tenant scope, and owner access are verified.

**Exit gate 5:** one canonical `CUBI-DAM-001` identity, complete validated engineering dataset and required Enterprise references persist in PostgreSQL; shared visibility and personal-project separation pass; PR #2133 ownership is respected.

---

## 6. Rebuild and complete Enterprise Project Definition (not a duplicate project store)

### 6.1 Existing Enterprise architecture to reuse

- Canonical Enterprise router: `apps/web/src/enterprise/router.ts`, PageId `projects`, route `/cubi/enterprise/projects/`; page renderer `apps/web/src/enterprise/pages/projects.ts`.
- Existing Enterprise project register/portal work is merged in PR #2130; inspect its current implementation and tests first.
- Enterprise traceability says the actual application has 26 PageIds under `/cubi/*`, rendered through `apps/web/src/enterprise/app.ts` and one shared Enterprise shell. Do not revive obsolete `/enterprise/*` routes or build another shell.
- Read the full current `ENTERPRISE_PAGE_BY_PAGE_ICON_HELP_CROSSWALK.md`, `CUBI_ENTERPRISE_V26_TRACEABILITY.md`, current route/page source and exact EPPM Help topics before touching each page.
- Enterprise uses P6 EPPM V26 Help; Engineering uses P6 Professional V26 Help. Keep those references separate.

### 6.2 Project Definition target

Make the Enterprise Projects area a complete operational project-definition and portfolio-facing portal while preserving the distinction between Enterprise governance and Engineering project controls. It must use the same canonical project IDs and permission-aware source APIs; never create an Enterprise shadow project or second schedule/calendar/resource store.

Required functional areas, only where supported by canonical services:
- Projects Center / project register with search, filters, status, ownership, EPS/organization context, pagination, saved view and correct access states.
- Project Definition / general details: project ID/name, description, status, planned/actual dates, data date, responsible organization/manager, owner, location, contract and approved metadata.
- EPS and organization/OBS relationships, responsible ownership and access-aware hierarchy.
- WBS and project scope overview via Engineering-owned read models; Enterprise must not calculate or mutate WBS/schedule facts through a parallel engine.
- Activity/schedule summary and Gantt links via Engineering APIs and revision-bound read models.
- Calendars, resources, assignments, baselines, cost and progress as source-backed read-only or authorized workflows; do not fabricate controls or data.
- Enterprise-owned portfolio, governance, risks/issues, contracts/procurement, tasks, workflows, approvals, documents and communications through their existing services and permissions.
- Full project detail/portal navigation and breadcrumbs; deep links preserve selected project and return path.
- Create/edit operations call the canonical project lifecycle service or approved Enterprise application contract; authorization is enforced server-side.

### 6.3 Every page/control/icon needs a page specification

For each PageId/route, document: route and inheritance; exact EPPM Help topic and section; each control/field/tab/action; icon ID and SVG asset; service/API and PostgreSQL table; permission; loading/empty/error/read-only states; keyboard/accessibility; tests; visual reference and screenshot comparison.

Do not invent an EPPM mapping for a CUBI-only capability. Mark it CUBI-owned or no exact Help equivalent in the traceability matrix.

**Exit gate 6:** Enterprise project pages use the existing shell/router, canonical IDs, persisted records and source-backed APIs; all visible controls work or are visibly unavailable; no duplicate project store or second shell exists.

---

## 7. Icons and visual design — complete inventory, then implement by page

The user requires the project-definition and Enterprise interface icons to be designed and implemented, not left as text labels or decorative placeholders.

1. First inventory the current semantic icon register, all icon IDs, existing SVGs, usage sites, duplicate aliases and missing assets. Reuse existing CUBI icon infrastructure.
2. Derive the icon set from the actual route/page/control inventory and the official Help symbol/icon crosswalk. Do not invent a second icon system.
3. Cover project, EPS, OBS/organization, WBS, activities, Gantt, relationships, calendars, resources, assignments, roles, curves, baselines, scheduling, progress, actuals, costs/budgets, documents, reports, tracking, issues, risks, thresholds, codes/UDFs, administration, permissions, import/export and audit only where those features actually exist.
4. Use CUBI's approved visual identity and theme tokens. Icons must have consistent grid, optical alignment, stroke/fill, sizing, RTL/LTR placement, accessible names, tooltip, hover/focus/selected/disabled/destructive states and high-DPI rendering.
5. Every icon must be connected to a real command/navigation target or clearly marked unavailable. No dead buttons, dummy actions, misleading icon-only controls or copied Oracle artwork.
6. Verify each registered icon in its actual page and each relevant theme/locale. Include screenshots and an icon-to-control acceptance matrix.

**Exit gate 7:** all in-scope icon IDs are present, semantically correct, visibly polished and behaviorally verified; no unconnected controls are represented as complete.

---

## 8. PostgreSQL, persistence, permissions and cross-page connectivity

1. PostgreSQL/Supabase is the only canonical persistent project-data store. Excel is source input only. Fixtures may be used only for isolated tests, never as silent production/project data.
2. Freshly inspect the actual live Supabase schema, migration ledger, tables, constraints, RLS, policies, grants, functions/search_path, indexes and current project rows. Earlier findings are historical and must not be repeated as current without rechecking.
3. Reconcile code migrations 14/15/16 and every dependency used by Engineering and Enterprise repositories. Apply only reviewed additive migrations with tested rollback/recovery; no blind RLS enablement, broad policy rewrite, destructive DDL or schema drift suppression.
4. Keep one canonical project ID/revision across Engineering and Enterprise. Enterprise reads Engineering-owned schedule/resource/cost facts through authorized revision-aware read models.
5. Verify every relevant page/API against persisted PostgreSQL records after process restart and browser reload. A green unit test, fixture render, local SQLite result or READY deployment is not live Supabase verification.
6. Maintain tenant isolation, owner/global-admin override, least privilege, server-side authorization, CSRF, idempotency, optimistic revisions, audit append-only behavior and all-or-nothing transactions.
7. The shared showcase visibility exception applies only to the explicitly designated records and must not create mass user memberships or expose ordinary customer projects.

**Exit gate 8:** exact migration IDs, database query evidence, row counts and canonical IDs are recorded; authorization/RLS and owner access pass; every page in the matrix reads the same persisted project revisions.

---

## 9. Preview safety, Safe Browsing and release controls

- Reconcile the canonical Preview alias from the repository standard with the owner-supplied Enterprise deep-link alias. Do not change aliases, domains, project settings, password protection, SSO or deployment target without explicit owner approval.
- A Chrome Safe Browsing "Dangerous site" interstitial was reported on the supplied host. Treat this as a release blocker. Verify host-specific Google Safe Browsing status and Search Console security issues, inspect redirects/final hosts and remediate the actual cause. Never ask the owner to bypass the warning or disable browser protection. Do not claim the host is safe based on TLS, successful build or READY state.
- Test authenticated flows only with an authorized disposable identity; never request or use the owner's password or session tokens.
- No production promotion, merge or alias change until exact-head CI, DB/browser verification, owner access preservation and the Safe Browsing gate pass.

---

## 10. Mandatory stage-by-stage GitHub checkpoint protocol (token-expiry safe)

This is a hard requirement. Every meaningful stage must be recoverable by the next agent from GitHub.

### 10.1 Before starting a stage
- Read this file, the continuity protocol, the ledger, parent issue and latest issue/PR comments.
- Refresh `main`, branch head, active PRs, path ownership and exact checks.
- State the stage number, scope, acceptance gate and protected records in a new comment on #2138 (and linked issue where relevant) before any destructive or cross-cutting action.

### 10.2 During a stage
- Work in small bounded changes. Use one commit per completed checkpoint/stage; do not leave critical work only in an uncommitted workspace.
- Update the relevant issue with evidence as soon as a stage ends or a blocker is found.
- Keep the ledger current at each meaningful handoff. Link the exact issue, PR, branch, commit and next stage.
- If a stage is interrupted, write a checkpoint immediately with completed items, incomplete items, current exact SHA, modified paths, commands/results, data/schema effects, blockers and the precise next action.
- Never say "done" if only a document, UI shell, mock, fixture, parser or local-only test exists.

### 10.3 Required checkpoint template

Use this exact structure in a GitHub issue comment (replace every placeholder; do not leave vague text):

```markdown
## Stage <N> checkpoint — <UTC timestamp>

- **Parent:** #2138
- **Related issue/PR:** #...
- **Stage:** <number and title>
- **Status:** VERIFIED / IMPLEMENTED_NOT_VERIFIED / BLOCKED / NOT_STARTED
- **Repository:** consttruction-pm/consttruction-pm-platform
- **Base main SHA:** <full SHA>
- **Working branch:** <branch>
- **Exact head SHA:** <full SHA>
- **Changed paths:** <paths or NONE>
- **Evidence inspected:** <files, issue/PR links, deployment SHA, DB facts>
- **Completed:** <specific facts>
- **Not completed:** <specific facts>
- **Data/schema impact:** <none or exact migrations/IDs/counts; never secrets>
- **Owner/password/dashboard/access preservation:** <checks; state explicitly no credential/session mutation>
- **Tests/commands:** <exact command, exit code, exact-head CI links>
- **Browser/DB evidence:** <actual results or NOT RUN with reason>
- **Known blockers/risks:** <specific>
- **Next action:** <one exact bounded action>
- **Next agent read-first:** this file + #2138 latest checkpoint + linked issue/PR + current main SHA
```

### 10.4 Handoff/resume rules
A replacement agent MUST:
1. Ignore private memory as an authority; read the latest GitHub checkpoint.
2. Re-read the repository instructions and compare current `main`/branch/PR head with the checkpoint.
3. Inspect uncommitted state and active path ownership in its own checkout; do not assume the prior agent's working tree is available.
4. Re-run or independently verify critical evidence that may have gone stale.
5. Continue only the explicitly recorded next action. Do not repeat completed work or silently change scope.
6. If the checkpoint and current source disagree, record the discrepancy and reconcile before proceeding.

**No stage is considered handed off until its checkpoint is visible on GitHub.**

---

## 11. Overall completion gates and final report

The program is complete only when:
- the exact three erroneous project records (if any) were positively identified and safely removed/retired with owner-approved IDs, or the deletion is explicitly marked blocked because IDs could not be proven;
- the three protected reference projects remain unchanged;
- the single Dam build project is completed through #2133/#2132 without duplication;
- Engineering project creation and Project Details meet the V26 workflow through canonical PostgreSQL;
- Enterprise Projects/Project Definition is operational on the existing router/shell and uses the same canonical IDs;
- all relevant page controls/icons are implemented and tested against the page-by-page Help crosswalk;
- every in-scope Engineering/Enterprise page is verified against PostgreSQL with authorization and reload persistence;
- owner password, identity, active sessions, global-admin grants, Personal Workbench/personal dashboard, Global Administration dashboard, environment selector and access to both environments are preserved;
- official Preview and Safe Browsing gates pass;
- exact-head CI, functional tests, browser E2E, visual comparisons, database verification and rollback/recovery evidence are linked.

Final report must include: exact main/base/head SHAs, branch/PR links, changed paths, stage statuses, protected project IDs, any approved deletion IDs, migrations and DB evidence, page-by-page matrix, icon matrix, screenshots, test commands/results, preview deployment SHA, Safe Browsing result, known limitations and the next owner decision. Explicitly distinguish **merged-main**, **open PR**, **documentation-only**, **local test**, **live Supabase verified**, **browser verified**, and **blocked external**.

**Absolute rule:** preserve the owner's password and administrator dashboard/access. Do not make a destructive change or a release claim without exact evidence and the required owner approval.
