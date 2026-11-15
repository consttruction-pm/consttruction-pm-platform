# CUBI Engineering P1 — Schedule Scenarios / What-if Phase 1 Contract

**Status:** Phase 1 contract draft recorded; not approved for source-code implementation yet.
**Execution issue:** #1989.
**Architecture / ownership parent:** PR #1988 (Draft, open, unmerged).
**Reviewed main SHA:** `376af9e2751ea1260ea3b4ed9be050eb1722afbf`.
**Decision date:** 2026-11-15.

## 1. Binding product-owner decisions

1. The source hierarchy applies to every existing and newly introduced CUBI capability, not only this feature:
   - P6 EPPM Version 26 HTML Help is the universal primary parity baseline.
   - For a capability that is genuinely new in Primavera Cloud and absent from EPPM Help, the official Primavera Cloud HTML Help is the functional source specification. CUBI must cover the complete relevant workflow, states, permissions, fields and user outcomes, implemented in CUBI's own architecture.
   - Where both sources cover a concept, reconcile them explicitly. Preserve EPPM semantics for the existing EPPM capability and add Cloud-origin improvements only where they do not contradict or duplicate it.
   - A Cloud-only feature remains explicitly classified as a Cloud extension; it must not be mislabeled as EPPM parity.
   - Oracle wording, branding, proprietary assets and implementation code are not copied. Functional behavior and workflow coverage are.
2. Every capability requires a dual-source disposition row: exact EPPM HTML topic(s) or explicit NOT PRESENT; exact Cloud HTML topic(s) or NOT APPLICABLE; classification; semantic differences and resolution; CUBI owner and menu/API/data boundary; tests and open evidence.
3. All Engineering-owned new capabilities are feasibility-assessed, assigned a domain owner and integration boundary, and then handed to the Qoder engineering agent for implementation. Engineering is Priority 1.
4. Enterprise-owned capabilities are Priority 2. ChatGPT coordinates and owns their product architecture, integration/non-interference review and implementation planning after Engineering dependencies/contracts are stable. Enterprise must consume Engineering-owned versioned facts and must not reproduce Engineering calculations or mutable records.
5. Existing Primavera P6 EPPM capabilities must be checked against P6 EPPM EPPM Help before adopting a Cloud analogue. No duplicate menu, entity, API, calculation engine, workflow, or owner is permitted.
6. This contract is a design artifact, not implementation evidence. No weighted Jalal 5 progress is credited and no workbook weights are changed.

## 2. Source inventory and exact disposition — Schedule Scenarios

### 2.1 P6 EPPM V26 HTML Help (primary)

Canonical TOC: https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm

The V26 EPPM Help TOC was opened and inspected. Its project/schedule domain includes Projects, EPS, Activities, Activity Views, WBS, Baselines, Scheduling Projects, Resource Leveling, Activity Progress, Activity Owners, Team Member Status Updates, Portfolio Views and **About What-if Analysis** (under Portfolios).

A search of the complete TOC for the literal topic family **Reflection** returned no match. The TOC also has no topic named **Schedule Comparison**. Therefore:
- A project-level schedule scenario/what-if lifecycle equivalent to Primavera Cloud Schedule Scenarios is **NOT PRESENT as a named feature/topic in the inspected EPPM V26 Help TOC**.
- Portfolio-level **About What-if Analysis** is present, but it is not the same domain behavior as project schedule scenario editing, execution, comparison and promotion. It must not be conflated with project schedule scenarios.
- EPPM baseline behavior still governs the underlying shared project/schedule concepts: project and EPS security, activity/WBS/relationship/resource/baseline semantics, schedule calculation, progress and data integrity.
- Exact topic-level pages and field/privilege references must be opened and mapped during implementation acceptance. The TOC-only absence finding is not a claim that every EPPM integration guide or API has no related object; it is specifically a Help-topic inventory result.

Relevant EPPM V26 TOC anchors:
- Projects / EPS: https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm
- Activities / WBS / Relationships: same canonical TOC, Activities section.
- Baselines / Scheduling Projects / Resource Leveling / Activity Progress: same canonical TOC.
- Portfolio Views > About What-if Analysis: same canonical TOC.

**Classification for project Schedule Scenarios:** Cloud-only extension at the workflow level, integrated with EPPM schedule primitives and governed by the EPPM schedule/security semantics wherever those primitives overlap.

### 2.2 Primavera Cloud HTML Help (functional source for the Cloud-origin workflow)

Canonical Cloud Help TOC: https://primavera.oraclecloud.com/help/en/user/toc.htm

Required direct topics:
- Schedule Scenarios Overview: https://primavera.oraclecloud.com/help/en/user/107323.htm
- Add a Scenario: https://primavera.oraclecloud.com/help/en/user/107329.htm
- Open a Scenario: https://primavera.oraclecloud.com/help/en/user/178412.htm
- Manage a Scenario: https://docs.oracle.com/cd/E80480_01/English/user_guides/schedule_management_user_guide/107330.htm
- Set a Scenario as the Current Schedule: https://primavera-us2.oraclecloud.com/help/en/user/107331.htm
- Schedule Comparison Overview: https://primavera.oraclecloud.com/help/en/user/191095.htm
- Compare Two Versions of a Project Schedule: https://primavera.oraclecloud.com/help/en/user/191096.htm
- Merge Overview: https://primavera-us2.oraclecloud.com/help/en/user/288769.htm
- Project Security Privileges Definitions: https://primavera.oraclecloud.com/help/en/user/82318_1.htm

Cloud behavior to cover in CUBI:
- Create scenarios from current schedule, another scenario, or a baseline; preserve the chosen source as immutable scenario provenance.
- Support multiple independent scenarios; each scenario's data and operations are isolated from the current schedule and other scenarios.
- Scenario lifecycle includes What-if, Closed and Retired; closed scenarios are hidden from active selection and retired scenarios are read-only.
- Open/switch between current schedule, visible scenarios and baselines, with an unmistakable scenario-context banner.
- Scenario editing, schedule calculation, resource/role leveling and health checks operate on the scenario's own data, not on the live project.
- Compare two selected schedule versions (current, scenario, baseline and supported point-in-time versions) with read-only variance output, added/deleted/changed items, activity/detail/Gantt/analysis views, and permission-filtered values.
- Merge is a separately permissioned operation from comparison. It must support preview, selected scope, field/entity-specific behavior, merge audit/log and optional pre-merge backup.
- The Cloud "Set as Current Schedule" behavior can overwrite current schedule details and is documented as non-undoable. CUBI must not reproduce an unsafe one-click overwrite. CUBI's promotion is a guarded, explicit, selected-change transaction with a pinned source revision, conflict preview, atomic apply, append-only audit and verified rollback/recovery path.

### 2.3 P6 Professional V26 (supplementary only)

P6 Professional V26 HTML Help includes Creating and Using Reflections, Create a Reflection, Printing a reflection difference report, Merging a Reflection with the Source project and reflection FAQs. These pages are supplementary cross-checks only; they do not replace the P6 EPPM V26 primary Help baseline and must not be cited as proof that EPPM web has a Reflection workflow.

- V26 TOC: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
- Creating and using reflections: https://docs.oracle.com/cd/G48902_01/client_help/en_US/creating_and_using_reflections.htm
- Reflection FAQ: https://docs.oracle.com/cd/G48902_01/client_help/en_US/frequently_asked_questions_about_reflections.htm

## 3. CUBI ownership and placement

- **Authoritative owner:** CUBI Engineering.
- **Placement:** existing project > Activities/Schedule workspace, contextual Scenarios / Compare experience beside existing Schedule and Baselines. Use the existing Engineering Scenario Lab shell only after wiring it to the authoritative service. No new top-level menu, duplicate schedule editor or replacement shell.
- **Enterprise:** Priority 2. It may later consume approved scenario summaries and portfolio exposure/capacity facts through versioned read-only contracts. Enterprise does not create/edit Engineering scenarios, invoke CPM, level project resources or promote schedule changes.
- **Workbench:** navigation, notifications and personal action entry only; no scenario business records.
- **Qoder handoff:** all Engineering-owned code changes after feasibility/ownership and contract gates are handed to Qoder. This Phase 1 artifact defines the first implementation boundary but does not authorize edits to shared scheduling files while ownership conflicts remain unresolved.

## 4. Proposed domain contract (Phase 1)

### 4.1 Scenario aggregate

Required immutable identity/provenance:
- scenario_id, tenant_id, project_id;
- source_kind = current_schedule | scenario | baseline | point_in_time (point_in_time only if an authoritative snapshot can be composed);
- source_schedule_snapshot_id and content_hash;
- source_project_revision and source_schedule_revision;
- source_baseline_id/revision when applicable;
- source_scenario_id/revision when applicable;
- created_by, owner_id, created_at, updated_at;
- lifecycle_state = WHAT_IF | CLOSED | RETIRED;
- scenario_revision (optimistic concurrency token);
- schema_version and provenance metadata.

The source kind and source snapshot are immutable after creation. Scenario content is a separate aggregate. A scenario is not a mutable alias of the current project.

### 4.2 Scenario revisions and typed changes

- Every accepted mutation creates a new scenario revision with actor, timestamp, idempotency key, correlation ID, before/after hashes and a typed change set.
- Only explicitly supported entity/field combinations are writable. No arbitrary JSON patch, direct ORM sharing, client-side calculations or silent fallback.
- Preserve stable internal identity across source/scenario copies so comparisons do not rely solely on mutable display IDs or names.
- Validate field units, duration/calendar semantics, nullable fields, references and cross-entity invariants against the shared domain model.
- Unsupported fields/entities return a typed unsupported-operation error; they are not dropped silently.

### 4.3 Authoritative run record

Each run is immutable and references:
- run_id, scenario_id and scenario_revision;
- source snapshot identity/hash and scenario input hash;
- calculation context hash (calendars, data date, options, resource/role inputs and relevant versions);
- scheduler engine name/version and algorithm/configuration identity;
- run parameters and deterministic seed if stochastic work is ever supported;
- queued/started/completed/failed/cancelled state, timestamps and structured diagnostics;
- immutable output snapshot ID/hash and result metadata.

Runs must execute through the existing Shared Scheduling Core and authoritative snapshot composer. No new CPM or resource-leveling engine is allowed. A run may not write to the live project or another scenario.

### 4.4 Comparison result

- Comparison is a persisted, reproducible read model of two pinned schedule versions.
- Record left/right snapshot IDs and hashes, project calendar and comparison rules/version, execution identity and output hash.
- Report added, deleted, changed, unchanged and non-comparable entities/fields with explicit reasons.
- Compare activities, WBS, relationships, resource assignments, schedule dates/durations, supported costs/progress, baseline references and supported risk/other linked data only where authoritative snapshots contain them.
- Apply project-calendar date variance semantics where the Cloud Help specifies them; record any CUBI-specific divergence.
- Respect permissions at query time and redact restricted values rather than leaking them through counts, diffs or exports.
- Comparison is read-only and cannot mutate either source.

### 4.5 Promotion / merge command (not in first backend slice)

Promotion is a separate application command, not a side effect of compare or run:
- Require distinct promote permission and reauthorize source + scenario access at execution time.
- Require expected source project and schedule revisions to exactly match the pinned source; fail closed on stale state.
- Require explicit selected entity/field scope and a conflict preview.
- Detect identity collisions, deleted/changed source entities, resource identity conflicts, unsupported changes, locked/checked-out projects and permission changes.
- Offer a pre-merge backup snapshot; require all-or-nothing transaction semantics.
- Apply once, advance the source revision once, append immutable audit/merge log, and verify by fresh authoritative read-back.
- Idempotent retries return the original operation result; they never apply twice.
- No last-write-wins, silent overwrite or automatic promotion.
- Phase 5 remains a separate release gate; do not expose a working promotion API in the first vertical slice.

## 5. API and persistence boundaries

- Follow existing API/Application/Repository separation; domain services own invariants.
- Reuse existing tenant/project authorization, project revision, immutable schedule snapshot and shared calculation context abstractions.
- Storage must follow the repository's established SQLite and PostgreSQL adapter contracts, migrations and transaction ownership. Do not create a second storage subsystem.
- Candidate versioned operations for the first slice: create scenario, list scenarios, read scenario, append supported scenario changes, request run, read run/history, request comparison, read comparison. Final route names and payloads must be aligned to existing API naming conventions after repository source inspection.
- No promotion endpoint until its dedicated contract and atomicity/security tests pass.
- No cross-database joins, shared ORM entity across environments, circular module imports or direct Enterprise writes into Engineering storage.

## 6. Required state transitions

| From | Command | To | Preconditions |
|---|---|---|---|
| — | Create from pinned source | WHAT_IF | Source snapshot exists; actor can view source and create scenarios |
| WHAT_IF | Edit supported fields | WHAT_IF (new revision) | Scenario write permission; expected scenario revision matches |
| WHAT_IF | Run | WHAT_IF + immutable run | Current scenario revision pinned; scheduler available |
| WHAT_IF | Compare | unchanged | Both input versions pinned and readable |
| WHAT_IF | Close | CLOSED | Owner/project permission; expected revision |
| CLOSED | Reopen | WHAT_IF | Explicit reopen permission; expected revision |
| WHAT_IF/CLOSED | Retire | RETIRED | Explicit lifecycle permission; expected revision |
| RETIRED | Any mutation | denied | Terminal read-only state |
| WHAT_IF | Promote selected changes | separate promotion operation | Phase 5 gate only; all source locks/revisions/permissions/conflicts valid |

The exact Cloud status transitions and role privileges must be traced topic-by-topic before final API contract approval.

## 7. Threat, concurrency and failure cases

Minimum negative and recovery tests:
- cross-tenant and cross-project scenario reads/writes denied;
- access revoked between create, edit, run, compare and promotion;
- source snapshot missing, malformed or hash-mismatched;
- source revision changed after scenario creation;
- stale scenario revision on concurrent edit;
- duplicate request and idempotency-key reuse with different payload;
- concurrent runs against same scenario revision;
- scheduler failure, timeout, cancellation and worker restart;
- transaction rollback and failed immutable output persistence;
- comparison across changed identities, renamed IDs and deleted source objects;
- restricted costs/risks redacted from comparison and export;
- project exclusive lock / checkout / unsupported object changes block promotion;
- pre-merge backup failure blocks apply;
- promotion replay, partial-write prevention and fresh read-back.

## 8. Dual-source disposition matrix (initial)

| Capability slice | P6 EPPM V26 HTML disposition | Primavera Cloud HTML disposition | Classification | CUBI owner / boundary |
|---|---|---|---|---|
| Project / EPS identity and permissions | Present: Projects, EPS, security and project privileges | Scenario source is project-scoped | Reconciled shared primitive | Engineering owns project and source authorization |
| Activities, WBS, relationships, calendars, baselines | Present in EPPM Help | Scenarios copy and isolate schedule data; source may be current, scenario or baseline | Reconciled shared primitives + Cloud extension lifecycle | Engineering schedule core remains sole calculation owner |
| Portfolio what-if | Present: Portfolio Views > About What-if Analysis | Cloud has portfolio/resource/budget scenario capabilities | Reconciled at portfolio level only; not same as project schedule scenarios | Enterprise P2 owns portfolio analysis; reads Engineering snapshots |
| Project schedule scenario lifecycle | No Reflection or Schedule Scenarios topic found in EPPM V26 Help TOC; portfolio what-if is not equivalent | Present: Schedule Scenarios Overview, Add/Open/Manage/Set Current | Cloud-only extension | Engineering P1, contextual to existing Schedule |
| Schedule comparison / merge | No Schedule Comparison or Reflection topic found in EPPM V26 Help TOC | Present: Compare Two Versions, Merge Overview, Merge Log, Backup | Cloud-only extension integrated with EPPM schedule primitives | Engineering P1; compare read-only, promotion guarded |
| Reflection project workflow | No Reflection topic found in EPPM V26 Help TOC; P6 Professional V26 has supplementary Reflection docs | Scenario workflow is the Cloud analogue, not identical semantics | Cloud extension; Professional supplementary cross-check only | Engineering |
| Activity Owner progress collection | Present: Activity Owners and Team Member Status Updates | Cloud team/task/progress flows are distinct | Reconcile only after field/permission mapping | Engineering execution truth; Enterprise identity/access provider |
| Scenario summary / portfolio capacity roll-up | EPPM has Portfolio Views / Capacity Planning / What-if | Cloud Portfolio Resource Planning Scenarios / Scenario Comparison | Reconciled portfolio capability; preserve separate data owners | Enterprise P2 consumes authorized Engineering facts; Enterprise owns capacity allocation |

## 9. Phase 1 exit checklist and blockers

Phase 1 is **DRAFTED / IN REVIEW**, not complete. Exit requires:
- [x] Product-owner source hierarchy and environment ownership recorded in parent PR #1988 / tracker §12.
- [x] EPPM V26 and Primavera Cloud HTML TOCs inspected.
- [x] Initial dual-source disposition and Engineering/Enterprise/Workbench boundary written.
- [x] Initial aggregate, revision, run, comparison and promotion contracts drafted.
- [ ] Open exact EPPM V26 pages for every shared primitive, security privilege and Activity Owner/status-update flow; record exact topic URLs and fields.
- [ ] Open every Cloud topic above, including full manage/merge/permissions workflow; verify topic versions and all state/permission nuances.
- [ ] Resolve root AGENTS.md absence (GitHub lookup returned 404 on main and documentation branch); repository execution environment must confirm whether instructions are supplied externally or truly missing.
- [ ] Refresh active schedule PR changed-file lists and exact head SHAs in canonical Codex workspace; assign file-level ownership before any code edit.
- [ ] Obtain/inspect the supplied 815-page V26 PDF where required as supplementary evidence; HTML remains normative. Missing PDF is recorded, not used to block HTML research.
- [ ] Independent review of domain contract and security/concurrency table.
- [ ] Record final Phase 1 contract approval and Qoder implementation handoff.

**Current blocker:** GitHub connector can inspect GitHub text and PR metadata but cannot run the repository's canonical test/runtime environment. It is not a substitute for Qoder/Codex code execution. No source code, migration, route, test or runtime behavior was changed by this contract artifact.

## 10. Next execution sequence

1. Finish exact-topic source crosswalk and resolve the blockers above.
2. Confirm active writer/path ownership against the current main and open PRs; do not touch shared schedule core, resource-leveling files, `apps/web/src/main.ts`, or any active writer's paths.
3. Hand the approved Engineering contract to Qoder for the thinnest backend vertical slice: isolated scenario create/read/edit/run with authoritative shared scheduler, immutable run records and tests. Comparison follows after reliable snapshots; promotion remains separate Phase 5.
4. After Engineering APIs are stable, wire the existing Scenario Lab shell; do not rebuild its visual presentation.
5. Only after Engineering foundations are stable, plan Enterprise portfolio scenario/roll-up consumers under Priority 2, with no duplicate CPM or scenario write model.
