> **Historical snapshot notice:** The original 2026-10-01 matrix is retained as historical evidence. The authoritative live-main SHA and weighted-progress reference are maintained in [CURRENT_MAIN_AUDIT_POINTER_2026-10-08.md](audits/CURRENT_MAIN_AUDIT_POINTER_2026-10-08.md).

# V1 Master Audit Matrix

> **Snapshot:** 2026-10-01  
> **Baseline:** `main` @ `94476f94ade2c7fc23aed2c756894dc5ce080d2d`  
> **Parent:** #459 — V1: Full Project Audit + Functional Web Beta  
> **Owner:** Jalal — Shared Core / P6 semantic reconciliation / integration acceptance
>
> This is an evidence index, not a claim that every V1 capability is complete. A capability is marked **Verified** only when the current `main` tree and/or runtime/CI evidence support the statement. **Open / Gap** means a material seam still requires implementation or verification.

## Status vocabulary

| Status | Meaning |
|---|---|
| Verified | Present on current `main` with identifiable code/test or merge evidence. |
| In progress | Explicitly assigned active work exists, but the requested acceptance evidence is not complete. |
| Gap | A known requirement is not yet represented or is materially incomplete. |
| Audit required | The area exists but full parity/behavior has not yet been reconciled against the P6 baseline. |

## Architecture and ownership

| Area | Current evidence | Status |
|---|---|---|
| Shared Domain / Calculation Core separation | Repository rules require the Shared Core to remain independent of UI, Windows, PostgreSQL, filesystem and auth; P6 calculation authority is centralized. | Verified |
| API / Application / Repository separation | Current backend work contains application authorization/project lifecycle and repository/API seams. | Verified |
| PostgreSQL persistence boundary | PostgreSQL-backed persistence and integration tests are present; recent #600 hardened schedule snapshot upsert concurrency. | Verified |
| Tenant / project scope | Authorization and resource-read tests cover tenant/project isolation. | Verified |
| Revision / optimistic concurrency | Existing idempotency/revision tests cover stale revision and atomic state behavior; #636 evidence has been superseded by merged current-main work. | Verified |
| Client business-rule isolation | P6-3 UI contracts consume authoritative registry/layout/formula results and do not implement a formula evaluator or scheduler. | Verified |

## P6 scheduling and calculation authority

| Area | Evidence / disposition | Status |
|---|---|---|
| CPM forward/backward pass | `src/construction_pm/scheduling/` contains forward/backward scheduling and float calculations. | Verified |
| FS/SS/FF/SF relationships | Relationship handling and Stage 73.16 matrix tests exist in `tests/scheduling/test_schedule.py`. | Verified |
| Current-main FS audit | Issue #631 documented a direct current-main audit with no reproducible FS defect; stale PR #517 was closed as obsolete and is not a baseline. | Verified |
| Calendar-aware relationship lag | `schedule.py` accepts relationship lag resolvers; tests cover explicit resolver behavior. | Verified |
| Float / criticality | Schedule result includes early/late dates, total/free float, criticality and multiple float-path structures. | Verified |
| P6 ScheduleOptions completeness | Issue #403 records remaining options still requiring typed Shared-Core implementation/verification, including out-of-sequence, lag-calendar choice, multiple float paths and resource-leveling semantics. | Audit required |
| Constraints / open-ended behavior | Constraint validation and application are present in scheduling modules. Full P6 option parity still needs reconciliation. | Audit required |
| Project portability of calculation context | Project export/import rules require calendar/settings/context travel with the project; prior portability work is merged. | Verified |
| Progress / EVM / Earned Schedule | Existing Shared/Core stages cover substantial progress/EVM work; latest saved stage was Earned Schedule reconciliation. Full P6 parity matrix remains to be maintained. | Audit required |
| Resource assignment / spread read authority | #603 completed the typed Assignment/Spread read API from authoritative persistence for Shared Core consumption. | Verified |
| Formula semantics | Web Formula Editor is authority-backed; client is not a formula parser/evaluator. P6 formula-field parity still requires catalog-level audit. | Verified / Audit required |

## Backend / API / persistence

| Area | Evidence | Status |
|---|---|---|
| ProjectContext / lifecycle | `application/project_lifecycle.py`, `project_lifecycle_api.py` and tests exist. | Verified |
| Authorization | `application/authorization.py` and tests cover viewer/planner/admin and invalid tenant/roles. | Verified |
| Atomic idempotency | Contract, lock, gateway and SQLite transaction tests exist; PostgreSQL lock coverage is present. | Verified |
| Typed Assignment / Period / Spread API | #603 and subsequent #635 API work provide typed read/actual-period seams. | Verified |
| Beta project/activity/WBS/calendar/schedule-option API surface | Current main contains multiple API modules; historical #636 work is superseded and is not a separate completion item. Remaining runtime verification is tracked by #678. | In progress |
| PostgreSQL-backed Beta verification | Current bounded Hasan verification is #678; PostgreSQL evidence is required where available, with deterministic fallback coverage explicitly recorded if unavailable. | In progress |
| Import / export compatibility | P6 mapping, project portability and typed round-trip work exist; complete P6-26.4 field coverage remains an audit track. | Audit required |

## Web-first Beta surface

| Area | Current evidence | Status |
|---|---|---|
| Real Web entry point | `apps/web/src/workspace-view.ts` renders Project, WBS, Activity Grid, Gantt and Details surfaces from current main. | Verified |
| Workspace state | `apps/web/src/workspace-model.ts` contains WBS/activity/column state and server-projected cells. | Verified |
| P6-3 Field Chooser/Layout foundation | Registry-backed field/layout contracts are merged. | Verified |
| Layout persistence boundary | `p6-layout-persistence-adapter.ts` validates versioned layouts and delegates persistence to a transport; it does not own local storage. | Verified |
| Grid sort/group/filter | `p6-activity-wbs-grid.ts` provides typed presentation models and registry validation. | Verified |
| Formula Editor | `p6-formula-editor.ts` consumes authoritative validation/dependency/type results only. | Verified |
| Report / print field selection | `p6-report-print-field-selection.ts` provides normalized selection from the layout/registry. | Verified |
| Real workspace integration of P6-3 contracts | #674 merged the P6-3 presentation contracts into the real workspace; #677 then merged V1 navigation coverage with focused tests and green Web/Client/Core CI. | Verified |
| Client scheduling/CPM calculations | Explicitly prohibited in #637; current architecture keeps those semantics out of the Web presentation layer. | Verified |

## Localization and language packs

| Area | Evidence | Status |
|---|---|---|
| Shared language-pack infrastructure | Client-sync language manifest/resource/activation infrastructure exists. | Verified |
| Web language-manager route | `apps/web/src/language-manager-route.ts` supports active pack, offline activation, update, rollback and error state. | Verified |
| Workspace locale coverage | `workspace-model.ts`, `workspace-view.ts`, `workspace-navigation.ts` and `landing.ts` use hard-coded `fa`/`en` locale unions/maps. Verified language-pack lifecycle is not yet the source of all rendered workspace strings. Issue #1531 tracks extensible resource integration. | Gap — hard-coded two-language surface |
| All-language requirement | Product requirement is all-language UI/data with offline downloadable packs, RTL/LTR and typography support. Current workspace does not yet satisfy the all-language surface. | Gap |
| README terminology | README still says “bilingual Persian/English”; this is stale relative to the current all-language requirement and should be corrected in a documentation-only follow-up. | Gap |

## Multilingual and AI permission contract — corrected disposition

| Area | Current evidence / required disposition | Status |
|---|---|---|
| Binding multilingual scope | `docs/requirements/CUBI_MULTILINGUAL_AND_AI_PERMISSION_REQUIREMENTS.md` defines all declared supported languages, per-surface coverage, RTL/LTR, language packs, offline and release evidence. Persian/English are initial baselines, not a two-language ceiling. | Requirement recorded; implementation gap remains |
| Language-pack infrastructure vs product translation | Manifest/resource/activation and Web language-manager infrastructure exist, but do not prove every language is integrated across every workspace surface, report/help output or AI capability. | Partial / Gap |
| Assistant operation-level permissions | PR #1529 introduced exact-scope grants; PR #1536 (merge `f1e581df1b881f51220ec1901970126b29b9c1e3`) prevents requester spoofing by matching grants against an explicit authenticated-layer `subject_id`. PR #1538 (merge `e943f0f043dde96c767c586e3ff60accaf3ac411`) now rejects and audits missing/blank authenticated subjects before consulting any adapter, including the reference allowlist adapter. CI passed Python 3.11/3.12/3.13 and client typecheck/runtime tests for desktop, mobile, web and client-sync on PR #1538 head `342ada828cfb9e6fa7929a34df1be4130224b76d`. `src/construction_pm/http/production_composition.py` still does not compose an AI action route/service, and `src/construction_pm/ai_action_boundary.py` still exposes only an in-memory audit sink in this path; issue #1530 remains open for production wiring and durable audit. | Boundary security fix verified; production gap remains |
| Assistant end-to-end execution | Specification requires real tool calls, proposal/approval, authoritative Core calculation, persistence/read-back and audit. Existing contracts/classes are not proof of the full flow. | Audit / runtime evidence required |
| Language and permission regression matrix | Add tests for each declared language/surface and operation × grant × scope, including RTL/mixed script, fallback, default deny, revocation, stale proposal, cross-tenant rejection and audit. | Gap |

## Help / documentation

| Area | Evidence | Status |
|---|---|---|
| Multilingual Help Center information architecture | PR #624 has been merged. | Verified |
| Beta Help content completeness | Required to document Web/Desktop/Mobile behavior, menus, fields, options, P6 semantics and user workflows in all supported languages. | Audit required |
| P6/MS Project guide parity of Help detail | Requirement is documented, but completeness must be checked against the authoritative Help coverage matrix. | Audit required |

## V1 execution queue at snapshot

| Work item | Owner | Current state | Next evidence |
|---|---|---|---|
| #636 Backend/API verification | Historical/superseded | Superseded; do not count as an active implementation task or duplicate #678. | No rework |
| #637 Web P6-3 workspace integration | Farmj22002 / `farmj22002-droid` | Completed via merged #674; navigation follow-up #677 is also merged. | Broader V1 Web surface under #459 |
| #631 FS scheduling audit | Jalal | Closed; no reproducible current-main defect. | No rework; do not revive #517 |
| #459 Master V1 audit | Jalal | Active; matrix is synchronized to the current governance baseline. | Continue current-main evidence reconciliation and weighted refresh |
| #403 P6 ScheduleOptions remaining parity | Shared Core track | Known remaining audit/implementation scope exists. | Typed option disposition + deterministic regression scenarios |

## Stale-work policy

The following historical lines are **not** valid implementation baselines unless independently reconciled to current `main` and explicitly re-approved:

- Old Farmj P6-3 branches and PRs such as #528 and #593.
- Obsolete scheduling branch/PR #517.
- Closed duplicate CI/build/lockfile branches previously reconciled during the 2026-10-01 cleanup.
- Any branch that is materially behind current `main`.

## Acceptance rule for future updates

1. Every changed status must cite a current-main file, test, merged PR, or runtime/CI result.
2. No “complete” status is inferred from branch existence, static code appearance alone, or an unmerged PR.
3. Shared P6 calculation semantics remain authoritative in the Shared Domain/Calculation Core.
4. Backend/API and Web clients expose/consume those semantics; they do not redefine them.
5. Web-first V1 remains the active product delivery order; Desktop follows V1 Web stabilization and Mobile remains V2 unless explicitly reprioritized.
