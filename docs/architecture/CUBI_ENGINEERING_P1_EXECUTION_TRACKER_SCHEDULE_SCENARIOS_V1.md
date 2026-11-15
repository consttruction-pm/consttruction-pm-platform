# CUBI Engineering P1 — Execution Tracker: Schedule Scenarios / Reflections

**Status:** Phase 0 discovery recorded; implementation not started.  
**Parent architecture PR:** #1988 (Draft, unmerged).  
**Execution issue:** #1989 — https://github.com/consttruction-pm/consttruction-pm-platform/issues/1989  
**Audit baseline:** `main` = `376af9e2751ea1260ea3b4ed9be050eb1722afbf` (2026-11-15).  
**Jalal 5 schedule:** `Jalal5_Weighted_Master_Schedule_2026-10-18_EXECUTION-BASELINE.xlsx` (Library artifact inspected; no dedicated weighted activity for standalone Scenario Lab/Reflection was found).  
**Progress credit:** 0 until merged implementation and accepted exact-head/runtime evidence. This tracker does not rebaseline or alter workbook weights.

## 1. Why this is the next Engineering P1 slice

The existing Engineering shell already contains a `scenario-lab` window with a scenario register, source revision, changed variables, run state, comparison and history. However, the canonical visual migration ledger explicitly says this shell is **not mapped to a verified live service**. The current shell is therefore a presentation placeholder, not a shipped scenario capability.

The current Schedule workspace is wired to authoritative schedule and baseline routes, but numerical Version 26 parity is not fully proven. The generated P6 code reference also records reflection creation/comparison/controlled merge as inventory-required; no complete reflection entity, difference report or merge-conflict implementation was verified at the audit SHA.

**Decision:** build on the existing Engineering Scenario Lab and the existing authoritative schedule snapshot/scheduler. Do not create a second schedule engine, new top-level navigation, or a replacement shell.

## 2. Phase register

| Phase | Scope | Status | Exit evidence |
|---|---|---|---|
| 0 | Current-main, continuity, schedule, UI/service gap and collision audit | **Recorded** | Exact SHA, code/docs findings, PR #1989 |
| 1 | Contract and domain boundary | **Not started** | Approved typed contract, lifecycle/state model, invariants and threat/concurrency review |
| 2 | Backend vertical slice | **Blocked pending Phase 1** | Persistence/API tests, PostgreSQL integration, immutable run read-back |
| 3 | Existing Engineering UI wiring | **Blocked pending Phase 2** | Real API wiring, truthful states, Web tests and browser evidence |
| 4 | V26 conformance and regression gate | **Not started** | HTML Help trace matrix, exact-head CI, numeric fixtures, en/fa browser evidence |
| 5 | Controlled promotion/merge | **Separate future release gate** | Conflict preview, explicit approval, atomic apply, audit and fresh read-back |

## 3. Phase 0 — discovery findings (2026-11-15)

### 3.1 Repository and continuity
- Main SHA: `376af9e2751ea1260ea3b4ed9be050eb1722afbf`.
- PR #1988 is open, Draft, unmerged; head SHA at audit: `6c4c5f1c8c8d92f665891bd3c297511e643b0c4b`.
- README and `docs/governance/PROJECT_CONTINUITY_PROTOCOL.md` require the repository's GitHub/Codex environment for code execution and tests. ChatGPT may coordinate and record state, but cannot substitute its GitHub connector for runtime verification.
- Root `AGENTS.md` lookup returned 404: **MISSING / VERIFY**. Resolve before code changes.
- The supplied 815-page V26 PDF was not available in the reviewed artifacts: **MISSING / VERIFY**. Do not claim full parity without it.
- Jalal 5 execution baseline inspected. No separate weighted activity for standalone Schedule Scenarios/Reflection exists. Keep this work unweighted and at zero earned progress until an approved schedule rebaseline maps it. Do not silently alter the workbook.

### 3.2 Current implementation evidence
- `apps/web/src/workspace-engineering-shells.ts`: `scenario-lab` shell defines scenario register, source revision, changed variables, run state, comparison and history.
- `docs/workspace/CANONICAL_VISUAL_WORKSPACE_MIGRATION_LEDGER.md`: `scenario-lab` explicitly marked “Not yet mapped to a verified live service”.
- `docs/engineering/WEB_SURFACE_TRACEABILITY_MATRIX.md`: Schedule page is wired to current schedule/baseline routes; numeric V26 parity remains unproven.
- `src/construction_pm/p6_code_reference.py` and `apps/web/src/scheduling-reference-catalog.generated.ts`: reflection creation, comparison and controlled merge are not fully implemented/verified; no complete reflection entity, difference report or merge-conflict implementation was verified.
- Multiple active scheduling branches/PRs exist across schedule snapshots, resource leveling, schedule query, Activity Master and workspace UI. This is a high-collision area. Re-fetch exact main, open PRs, changed paths, head SHAs and active writer ownership immediately before any source write. Do not touch shared scheduling/leveling files or `apps/web/src/main.ts` until collision is resolved.

### 3.3 Normative Version 26 HTML references
- P6 Professional Help V26 TOC: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
- P6 Professional User Guide V26 HTML: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/index.html
- Create a Reflection: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/create_a_reflection.htm
- Creating and using reflections: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/creating_and_using_reflections.htm
- Reflection FAQ: https://docs.oracle.com/cd/G48902_01/client_help/en_US/frequently_asked_questions_about_reflections.htm
- Required V26 topics from the TOC: What is a reflection; Creating and using reflections; Create a Reflection; Printing a reflection difference report; Merging a Reflection with the Source project; Using Reflection projects and Activity Owner features (P6 EPPM Only).
- P6 EPPM V26 Help HTML remains the authority for EPPM-only semantics. Do not infer EPPM behavior from Professional-only topics. Keep the P6 EPPM Help V26 TOC and Team Member Help in the acceptance crosswalk where relevant.

## 4. Phase 1 — contract and domain boundary (next execution phase)

Before backend coding, write and review the contract for:

1. **Scenario identity and scope:** tenant, project, scenario ID, creator/owner, source project revision, immutable source schedule snapshot ID/hash, calculation-context hash, selected baseline references, lifecycle state and optimistic scenario revision.
2. **Fork isolation:** scenario records and edits are isolated from the live project. No scenario mutation may write to source activity, relationship, resource assignment, baseline, progress or cost records.
3. **Typed change set:** only explicitly supported fields and entities; field units, null semantics, validation and unsupported-field behavior are explicit. No arbitrary JSON patch or browser-side scheduler.
4. **Authoritative run:** execute through the existing Shared Domain/Calculation Core using a pinned snapshot and context. Persist immutable run ID, engine/version, input/output hashes, run parameters, seed if applicable, timestamps and terminal state.
5. **Comparison:** compare supported typed source/scenario entities and fields from persisted authoritative read models; show added/changed/deleted and non-comparable items with reasons.
6. **Concurrency and security:** reauthorize every request; enforce tenant/project/object scope; expected revisions, idempotency keys, audit correlation IDs; fail closed on stale source, missing snapshot or revoked grant.
7. **Promotion boundary:** separate command, separate permission and separate release gate. Require pinned source revision, explicit selected-change scope, conflict preview, all-or-nothing semantics and append-only audit. Never silently merge or last-write-wins.

Phase 1 deliverables: versioned API contract, state-transition table, data ownership diagram, error taxonomy, concurrency/idempotency table, security test matrix and V26 traceability rows.

## 5. Phase 2 — backend vertical slice

- Add scenario persistence/repository and application service through existing API/Application/Repository boundaries.
- Implement create/list/read and run/read-run operations first; no promotion endpoint in this slice.
- Reuse existing authoritative schedule snapshot composer and scheduler; never create a second CPM calculation implementation.
- Persist scenario input and output revisions immutably; read-back after writes.
- Required tests: create and duplicate; source unchanged after scenario edit/run; source snapshot missing; stale project/scenario revision; idempotent replay and key reuse; cross-tenant/project isolation; permission revoked between requests; invalid/unsupported change set; scheduler failure; deterministic replay; transaction rollback.
- Add PostgreSQL integration tests in the canonical GitHub/Codex environment.

## 6. Phase 3 — Engineering UI wiring

- Wire the existing `scenario-lab` window to the versioned real service.
- No new top-level menu, no second Schedule/Activities/Gantt editor, no new shell and no global `main.ts` replacement.
- Scenario creation should be contextual to the active project/schedule; display exact source revision, source snapshot and baseline references.
- Show truthful loading, empty, error, unauthorized, stale and completed states. Unsupported actions remain disabled with a reason.
- Provide create, inspect, edit supported assumptions, run, compare and history only when each action has a real backend contract.
- Preserve existing window layout, route state, keyboard/focus behavior, RTL/LTR, Persian/Jalali/Gregorian, locale and permission conventions.

## 7. Phase 4 — V26 conformance and regression

- Map every user action and state to exact V26 HTML Help topic and paragraph/step.
- Validate reflection creation privilege and project context; selected baseline copy; multiple reflections; source-project link; difference report; merge availability restrictions; checked-out/exclusive project restrictions; resource duplicate behavior; scheduling date changes; merge failure handling.
- Add reference-derived numeric fixtures and independent expected values. If no licensed P6 V26 reference run/PDF is available, label those cases **MISSING / VERIFY** and do not mark parity complete.
- Run focused backend and Web tests, full proportionate CI, PostgreSQL integration, typecheck/build and real-browser E2E at exact final SHA.
- Capture English and Persian RTL browser evidence; verify no API 5xx, browser exceptions or console errors.
- Re-run affected existing schedule, Gantt, resource-leveling and project portability regression suites.

## 8. Phase 5 — controlled promotion (not part of the first vertical slice)

Promotion may begin only after Phase 1 contract review and dedicated authorization. Require:
- source project and scenario permissions checked at execution time;
- source project not checked out/exclusively locked by another actor;
- source revision still exactly matches the pinned revision;
- selected entities/fields and conflicts shown before apply;
- no duplicate resource identity or unsupported update is silently accepted;
- atomic apply, one source revision advance, idempotency and immutable audit;
- fresh authoritative read-back proves the intended changes and no others.

Any stale revision, unresolved conflict or revoked permission blocks the operation.

## 9. Non-interference rules

- Engineering owns project schedule, CPM, baselines, resource assignments/leveling, progress and project risk calculations.
- Enterprise may consume authorized versioned scenario summaries later; it must not run or duplicate CPM or edit Engineering scenarios.
- Workbench is an entry/notification surface only.
- Typed cross-environment references do not grant permission.
- No cross-database joins, direct module imports, shared ORM entities, circular dependencies or silent last-write-wins.
- Do not mix Monte Carlo into this first slice. Quantitative risk is a later Engineering P1 capability that depends on stable scenario/snapshot and risk-input contracts.
- Enterprise portfolio resource scenarios remain P2 and consume Engineering snapshots only.

## 10. Handoff template — update after every phase

For each phase update, record:
- Phase and status (Not started / In progress / Blocked / Verified on main).
- Exact main SHA, branch, head SHA and changed paths.
- Linked issue/PR and current merge state.
- Contract/code changes and observable behavior.
- Exact commands, check URLs, exit status and test counts.
- PostgreSQL/read-back/security/browser evidence as applicable.
- V26 HTML topic mapping and missing evidence.
- Remaining risks/blockers.
- One concrete next action.

**Do not mark a phase complete from a document, PR, branch, test assertion without execution, or a worker summary alone.**


## 11. Documentation-branch verification checkpoint — 2026-11-15

- Documentation branch at checkpoint: `docs/cubi-cloud-gap-environment-ownership-v1`.
- Prior branch head: `882e605a3daf37188946cd79f0bab3e4623f4934`; the tracker and continuity-ledger writes are committed separately and are visible in PR #1988.
- PR #1988 compare against main: documentation-only; 5 commits ahead, 0 behind at the latest check. Changed paths are the three architecture documents and `docs/governance/PROJECT_STATE_LEDGER.md`; no source code, schema, API, route or runtime changed.
- Exact combined status for the then-current docs head reported **Vercel – cubi-web-preview: failure**, target URL indicating **build-rate-limit / upgrade required**. This is a preview-provider quota failure, not a passing test and not evidence of an application defect. No test suite ran from this ChatGPT GitHub-connector operation.
- Tracker was fetched back from GitHub after creation; continuity-ledger entry was fetched back and its appended issue/status/next-action text was confirmed.
- PR #1988 remains Draft/open/unmerged. Issue #1989 remains open. No merge, deployment or source implementation occurred.
- **Next required action:** execute Phase 1 in the repository's canonical GitHub/Codex environment after resolving the missing `AGENTS.md` and current schedule PR ownership; do not treat the Vercel check as green.


## 12. Normative Help hierarchy — owner clarification (2026-11-15; supersedes any conflicting wording above)

This rule applies to **all existing and newly added product capabilities**, not only Schedule Scenarios:

1. **Primary and universal parity authority is P6 EPPM V26 HTML Help (the EPPM Help HTML / HDML source designated by the product owner).** Every feature, workflow, permission, field, state, calculation, integration and UI behavior that exists in the EPPM Help must be inventoried and traced. Do not substitute P6 Professional Help, PDFs, marketing pages, or assumptions for this primary source.
2. **For a capability/topic newly introduced in Primavera Cloud and not present in P6 EPPM Help, use the corresponding official Primavera Cloud HTML Help as the source specification.** Copy the complete relevant functional behavior and workflow conceptually into CUBI's capability inventory and acceptance criteria, while implementing it in CUBI's architecture and ownership boundaries. “Copy” means faithful functional coverage, not copying Oracle source text, branding, proprietary assets or implementation code.
3. **Where a Cloud capability has a corresponding P6 EPPM capability, reconcile and integrate the two logically.** EPPM behavior remains the baseline for the existing EPPM capability; Cloud additions may extend it where useful. Preserve semantic distinctions, permissions, lifecycle, calculations and object ownership. Do not duplicate menus, entities, APIs, calculations or workflows, and do not overwrite a proven EPPM behavior with a conflicting Cloud convention.
4. **Where no EPPM counterpart exists, retain the Cloud-origin capability as a clearly identified Cloud extension**, with its own source trace, scope, owner, dependencies, permissions, acceptance tests and explicit integration points. Do not pretend it is an EPPM feature.
5. **Every feature must have a dual-source disposition record:** (a) exact EPPM V26 HTML topic(s), including “not present” when absent; (b) exact Cloud HTML topic(s), including “not applicable” when absent; (c) classification: EPPM baseline / Cloud-only extension / reconciled extension / not applicable; (d) behavior differences and the resolution; (e) CUBI owner/menu/API/data boundary; and (f) test evidence and unresolved gaps.
6. **Conflict-resolution order:** preserve mandatory EPPM parity for the existing EPPM capability; adopt Cloud-origin functionality for genuinely new Cloud capabilities; integrate shared concepts only after an explicit semantic and data-ownership review. If the sources conflict and the correct behavior cannot be established, mark **OPEN — OWNER DECISION REQUIRED**; do not silently choose one.
7. **No feature is “complete” or “fully Primavera-aligned” until both source inventories have been checked and the disposition is recorded.** Missing access to a Help page is a blocker marked **MISSING / VERIFY**, not an excuse to infer behavior.

### Correction to the Scenario / Reflection references above

The P6 Professional V26 HTML links listed in §3.3 are **supplementary only**, useful for cross-checking desktop-client concepts. They are not the universal primary authority and must not be used to establish EPPM parity. For Scenario/Reflection specifically:
- First inspect the exact P6 EPPM V26 HTML Help topic(s) and record whether EPPM supports the behavior in question.
- Then inspect Primavera Cloud HTML Help for the corresponding scenario/what-if/reflection behavior.
- Where both products support the concept, reconcile object model, lifecycle, permissions, calculations, comparison and promotion semantics without duplication.
- Where the Cloud Help documents a capability absent from EPPM Help, implement it as a Cloud-origin extension under Engineering ownership if it is project-schedule execution behavior.
- The current issue's V26 Reflection topic links must therefore be supplemented by the exact EPPM Help HTML and Cloud Help topic crosswalk before Phase 1 contract approval.

### Required implementation gate added to every future phase

No design approval, code merge or acceptance sign-off until the phase artifact includes the dual-source disposition matrix above. This requirement applies across Engineering, Enterprise and shared Workbench surfaces.
