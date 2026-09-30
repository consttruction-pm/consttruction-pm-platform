# Hasan — Current Continuation / Backend Track

## Current baseline — 2026-09-27

- Repository: `consttruction-pm/consttruction-pm-platform`
- Branch: `main`
- Current main baseline at this reconciliation: `e05364853669171789cbdb20ced42637cd9737da`
- Latest completed backend change in the preceding baseline: PR #273, merged after its exact-head CI passed.
- PR #273 added authoritative Field Assurance transition enforcement at the backend application write boundary.
- Exact-head checks for PR #273 passed:
  - ConstructionPM CI run `36306525146`
  - Client Typecheck run `36306525137`
- Stage 33.4.72–33.4.73 atomic sync/idempotency hardening is already runtime-verified through PR #171.
- Job-Step Transaction & Replay Boundary is already runtime-verified through PR #206.

## Do not repeat

Do not restart or reimplement:
- PR #70/client-sync queue work.
- Stage 33.4.69 end-to-end sync outcome work.
- Stage 33.4.70 authoritative revision refresh work.
- Stage 33.4.72–33.4.73 PostgreSQL/SQLite atomic idempotency hardening.
- PR #273 Field Assurance write-boundary guard.
- Existing Field Operations / Field Assurance persistence contracts.

Open historical PRs are not part of the current baseline unless first reconciled against current `main` and their changes are proven still missing.

## Current ownership

Hasan owns Backend / Database / Application / API / Enterprise Integration.

The backend must:
- preserve tenant/project context;
- preserve revision and optimistic-lock semantics;
- preserve idempotency and replay behavior;
- preserve transaction and audit boundaries;
- expose versioned typed contracts;
- keep authoritative business calculations in Shared Core;
- provide persistence/API support for Web/Desktop/Mobile without duplicating client calculations.

## Current Stage 34.3 backend support

Stage 34.3 Web/Site Experience is runtime-verified through 2026-09-27 for the completed Control Room and Field workflow slices.

Remaining Stage 34.3 product gates recorded in `docs/roadmap/STAGE_STATUS.md` are:
1. Voice interaction / speech-to-command UX against versioned query/action contracts.
2. Web/Desktop/Mobile parity for the expanded Control Room workflows.
3. Final Stage 34.3 integration/regression and runtime evidence reconciliation.
Document/RFI/Submittal, Procurement/Commercial, and AI Smart Guide/schedule-query request composition are already implemented and runtime-verified through PRs #280, #281, and #283.

For Hasan, the backend action is to provide or verify the authoritative contracts/persistence/application boundaries required by those client slices, not to duplicate UI behavior.

## Verified API/Web-readiness baseline

Current regression coverage already verifies:
- ProjectContext and tenant/project scope;
- optimistic revision conflicts;
- idempotency replay and key-reuse rejection;
- authorization allow/deny and cross-scope rejection;
- typed/versioned resource DTOs;
- transaction rollback;
- Field Assurance transition validation at the authoritative write boundary;
- sync conflict/revision refresh contracts.

PR #273 confirms invalid Field Assurance transitions are rejected before persistence while stale-revision behavior remains a conflict and idempotent replay remains safe.

## Immediate execution rule

Before starting another feature:
1. Read this file and `docs/roadmap/STAGE_STATUS.md`.
2. Fetch current `main` SHA.
3. Check open PRs for whether the required behavior already exists.
4. Fetch the current file SHA before editing an existing file.
5. Implement only the first missing Hasan-owned backend boundary.
6. Add focused tests and documentation with the implementation.
7. Require GitHub Actions runtime verification before marking the gate complete.
8. Update this file and Stage Status with exact verified commit/run identifiers.

## Hard boundaries

Never move these into API, persistence, Web, Desktop or Mobile:
- Primavera P6 scheduling semantics;
- calendar/duration calculations;
- Progress/EVM calculations;
- Resource/Cost calculations;
- financial formulas.

Shared Core remains authoritative for shared calculation semantics.

## Latest reconciliation — Stage 87

- PR #314 is already merged to `main` with merge commit `d7c5e8231ab3b25b3c283ee8901b068577fa25c7`.
- Its exact implementation head `cec20048e0eed2f80043d39ef85f5ebc460ac508` passed Client Typecheck run `36342222863` and ConstructionPM CI run `36342222381`.
- Stage 87 strict language-pack manifest validation, canonical signing-payload verification, integrity-boundary validation and activated-manifest snapshot protection are therefore already present on current `main`.
- PR #319 was a duplicate rebase attempt and has been closed without merge after current-main inspection proved the Stage 87 implementation was already present.

## Next point

Select the first **actually missing** Hasan-owned backend boundary supporting the remaining Stage 34.3 gates. Document/RFI/Submittal backend Application/API boundary is now implemented and runtime-verified through PR #280. The Procurement/Commercial read integration is implemented and runtime-verified through PR #286. The Schedule Query Application/API boundary is now implemented and runtime-verified through PR #295. For the remaining Stage 34.3 voice/presentation and cross-client parity gates, first verify whether the missing work is client/provider-adapter ownership per `VOICE_INTERACTION_BOUNDARY.md`; do not create a backend duplicate unless a concrete authoritative contract/application gap is found.

Do not revive stale PRs merely because they remain open.

Historical note: the previous version contained stale PR #70/Stage 33.4.70 continuation instructions; those are superseded by this current-main baseline.


### Latest reconciliation — Dependency Graph API boundary (PR #328)

- PR #328 is merged to `main` with merge commit `93af2ca34e3143d0e8a1bb456645c4b3282c61b1`.
- Exact implementation head: `05df8d1d7a6f237cad61514321ff3c336f51db05`.
- ConstructionPM CI run `36346154172` completed successfully.
- Client Typecheck run `36346154198` completed successfully.
- The new `dependency-graph.v1` API adapter delegates authorization, revision, idempotency and transaction semantics to the existing Application boundary and does not introduce Scheduling/P6, Calendar/Duration, Progress/EVM, Resource/Cost or financial calculations.
- The previously stale PR #326 is superseded and must not be revived.

## Next point

After PR #328, re-check current `main` and open PRs for the first actually missing Hasan-owned backend boundary. Do not invent a new numbered roadmap stage or duplicate client/provider-owned voice/parity work without a concrete authoritative backend gap.


### Latest reconciliation — Dependency Graph revision provenance (PR #331)

- PR #331 is merged to `main` with merge commit `0c713bac98e1ec3939c0368bd77941b578865103`.
- Exact implementation head: `869e17ae406a5d5e03257c47fe3786202678f31d`.
- ConstructionPM CI run `36346728936` completed successfully.
- Client Typecheck run `36346728879` completed successfully.
- The API now preserves `source_revision` and `target_revision` already supported by the authoritative DependencyLink persistence model, with focused validation and regression coverage.

## Next point

Re-read current `main`, Hasan's execution instructions and open PRs before the next implementation. Treat stale PRs as evidence only; implement only a concrete missing authoritative backend boundary.


### Latest reconciliation — Stage 34.3 cross-client voice adapter parity (PR #334)

- PR #334 is merged to `main` with merge commit `3942d9fd2df466e8c9c09157a80a0b979b12b9da`.
- Exact implementation head `3e58a0c1744ad92fa6a8a62d68b78741cb567f72` passed Client Typecheck run `36347809502` and ConstructionPM CI run `36347809550`.
- Desktop and Mobile now expose provider-neutral voice adapter wrappers that delegate normalization, scope validation and voice-output capability checks to the shared client-sync boundary.
- No backend voice endpoint, ASR/TTS provider, device permission, codec, cloud endpoint or Scheduling/P6 calculation was introduced.

## Next point

Re-read current `main`, Hasan execution instructions and open PRs before the next implementation. Cross-client voice adapter parity is now runtime-verified; remaining Stage 34.3 voice work is provider-specific/client UX work unless a concrete authoritative backend contract/application gap is demonstrated. Do not invent a new numbered roadmap stage or duplicate provider/client-owned work.


### 2026-09-27 — Portfolio Query Application/API Boundary (PR #336)
Status: **100% — merged and runtime-verified**
- Added the missing Hasan-owned versioned `portfolio-control-snapshot.v1` Application/API boundary over the existing authoritative Portfolio Control Snapshot/read-model provider.
- The boundary enforces tenant scope and `project.read` authorization, validates provider output, and preserves project/source revisions without recalculating portfolio metrics.
- PR #336 exact implementation head `a1d81740719827e0ed91ca4a075bf631abc64405` passed Client Typecheck run `36348158270` and ConstructionPM CI run `36348158292`.
- Merge commit: `181d00bb583d5a523ee0479c72e896caff3df61a`.
- No Scheduling/P6, Calendar/Duration, Progress/EVM, Resource/Cost or financial calculation semantics were moved into the API/application layer.

## Next point

Re-read current `main`, Hasan execution instructions and open PRs before the next implementation. Portfolio Query Application/API is now runtime-verified; select the next concrete missing Hasan-owned boundary only after reconciling the current contracts, application, persistence and integration state. Do not invent a numbered roadmap stage or duplicate client/provider-owned work.


### 2026-09-27 — ERP/Accounting Contract Version Identity (PR #339)
Status: **runtime-verified and merged**
- Corrected the concrete integration-boundary gap where the Python ERP/accounting operation/result models did not preserve the existing `erp-accounting-sync-result` v1 contract identity.
- `contract_version` is now preserved and validated as `1.0`; unsupported versions fail closed before adapter execution.
- PR #339 exact implementation head `1aa5216f67336a2a9365ad2e2ebff52aa80a3190` passed Client Typecheck run `36348391907` and ConstructionPM CI run `36348391989`.
- Merge commit: `c8076792dbc5896d6fb2c6fc667322a17da58c31`.
- No accounting formulas, AP/AR semantics, vendor SDK behavior or financial calculations were introduced.

## Next point

Re-read current `main`, Hasan execution instructions and open PRs before the next implementation. Continue only with the first concrete contract/application/persistence gap; do not duplicate the existing ERP, BI or Enterprise Identity provider-neutral seams.


### 2026-09-28 — AI Action Contract Version Identity (PR #348)
Status: **runtime-verified and merged**
- Corrected the concrete Application-boundary gap where the existing versioned `ai-action-proposal` contract required `contract_version=1.0`, while `AIActionProposal` did not preserve or validate that identity.
- `AIActionProposal` now preserves `contract_version` and rejects unsupported versions before permission/decision processing.
- Focused regression coverage verifies preservation of `1.0` and fail-closed rejection of unsupported versions.
- Exact implementation head: `00449763b2d17fc2733e2c202b6d1485861f6d8e`.
- Client Typecheck run `36350201852` completed successfully.
- ConstructionPM CI run `36350201964` completed successfully.
- PR #348 merged to `main` as `4e269ab95f55159e6c36b763761e83c730bdd19d`.
- No AI provider execution, tool implementation semantics, Shared Core calculations, Scheduling/P6, Progress/EVM, Resource/Cost or financial formulas were introduced.

## Next point

Re-read current `main`, Hasan execution instructions and open PRs before the next implementation. Continue only with the first concrete Hasan-owned contract/application/persistence/integration gap. Do not duplicate the open Web/client work in PR #349 unless a concrete backend-owned dependency is demonstrated.


### 2026-09-28 — Change Claim Contract Version Identity (PR #351)
Status: **runtime-verified and merged**
- Corrected the concrete Change Claim Application/Persistence boundary gap where the versioned change-claim contract identity was not preserved by the Python model and could be lost across persistence round-trips.
- `ChangeClaim` now preserves `contract_version=1.0`, includes it in its fingerprint/persisted representation, and rejects unsupported versions fail-closed.
- Focused regression coverage verifies preservation and unsupported-version rejection; PostgreSQL integration also passed.
- Final implementation head: `142150ab6e9bc5e04b7805e1bee12294b754c434`.
- Client Typecheck run `36350690841` succeeded.
- ConstructionPM CI run `36350690847` succeeded.
- PostgreSQL Integration run `36350690972` succeeded.
- PR #351 merged as `aa2690f3e6881819d128291d39fe4e2c1767856c`.
- No Shared Core calculation, Scheduling/P6, Progress/EVM, Resource/Cost, or financial formula semantics were changed.

## Next point

Re-read current `main`, Hasan execution instructions and open PRs before the next implementation. Continue only with the first concrete Hasan-owned contract/application/persistence/integration gap. Do not duplicate client/provider work in PR #352 unless a concrete backend dependency is demonstrated.


### 2026-09-28 — Current-main reconciliation after PR #352

- Current main is 8c923118034b4ad36770be4467901b1c4b29fe37, following the documentation reconciliation commit after PR #352.
- PR #352 is merged as d12143704ab603ca2475364620006cad639b2439; its exact implementation head 745fa80820eafbbe0eb8b69341f2961b0729c493 passed Client Typecheck 36350966019 and ConstructionPM CI 36350965989.
- No open PRs are currently present.
- Current-main inspection confirms the Hasan-owned Field Operations, Dependency Graph, Portfolio Query, ERP/Accounting, AI Action and Change Claim backend/application boundaries already exist on main and have runtime evidence recorded in STAGE_STATUS.md.
- The remaining open items in Offline AI/Voice Issue #94 are provider/native inference, STT/TTS, lifecycle concurrency, device benchmarks, privacy/provenance/audit end-to-end certification, and release certification. These must not be converted into a duplicate backend boundary unless a concrete authoritative Application/API/Persistence contract gap is demonstrated.

## Next point

Start the next Hasan implementation only after re-reading current main, this file, docs/roadmap/STAGE_STATUS.md, and open PRs. Select only a concrete missing Backend/Database/Application/API/Enterprise Integration boundary. If no such gap exists, do not invent a feature or numbered stage; record the verified blocker/ownership boundary instead.


### 2026-09-28 — Project Portability Contract Version Hardening (PR #359)

- Concrete Hasan-owned gap: `ProjectPortabilitySnapshot` accepted arbitrary `schema_version` values even though the authoritative portability contract is `project-portability.v1`.
- The portability boundary now fails closed with `UNSUPPORTED_SCHEMA_VERSION` for unsupported versions.
- Focused regression coverage verifies rejection during import and direct snapshot validation.
- PR #359 exact implementation head `225985af42a7075fb9280384864ccafcea8baca5` passed Client Typecheck `36351611141` and ConstructionPM CI `36351611127`.
- PR #359 merged to `main` as `c2aa9013f78f564d0fa5d03f811d548359b40beb`.
- PR #357 was stale after PR #356 advanced `main`; it was closed and not merged as a separate baseline.
- No Scheduling/P6, Calendar/Duration, Progress/EVM, Resource/Cost or financial calculation semantics changed.

## Next point

Re-read current `main`, Hasan execution instructions and open PRs before the next implementation. Continue only with the first concrete Hasan-owned Backend/Database/Application/API/Enterprise Integration gap. Do not duplicate client/provider work or invent a numbered stage.


### 2026-09-28 — Portfolio Decision Read Contract Version (PR #361)

- Concrete Hasan-owned gap: `portfolio-decision-read.schema.json` requires `contract_version=1.0`, while the Python `PortfolioDecisionRead` model omitted contract identity.
- `PortfolioDecisionRead` now preserves the v1 identity and fails closed on unsupported contract versions before query results are accepted.
- Focused regression coverage verifies the v1 identity and unsupported-version rejection.
- PR #361 exact implementation head `111121c583915622f4e8eb76e0354b8d3c9b2941` passed ConstructionPM CI `36351931398` and Client Typecheck `36351931153`.
- Merge commit: `e05364853669171789cbdb20ced42637cd9737da`.
- No portfolio decision lifecycle, Shared Core calculation, Scheduling/P6, Progress/EVM, Resource/Cost or financial calculation semantics changed.

## Next point

Re-read current `main`, Hasan execution instructions and open PRs before the next implementation. Continue only with the first concrete Hasan-owned Backend/Database/Application/API/Enterprise Integration gap. Do not duplicate client/provider work or invent a numbered stage.


### 2026-09-28 — Dependency Graph Schema/Conformance Reconciliation (PR #363)

- Concrete gap: persistence/conformance already supported the `rfi` compatibility prefix and explicitly projected it to the authoritative `document` Shared Core domain, while `dependency-graph.v1` schema omitted `rfi` from its domain enum.
- PR #363 aligned the shared schema with the existing explicit conformance contract; persistence support was preserved rather than removed.
- The initial implementation attempt exposed the mismatch through CI; the final correction restored the documented RFI compatibility path and added `rfi` to the schema enum.
- Exact final head `60291d045b0ec423f9c36b245613335c5338e397` passed ConstructionPM CI `36352316751` and Client Typecheck `36352316741`.
- Merge commit: `089a846d62ad121bfb346256e3ac2a468cefce59`.
- No scheduling/P6, Progress/EVM, Resource/Cost or financial calculation semantics changed.

## Next point

Re-read current `main`, Hasan execution instructions and open PRs before the next implementation. Continue only with the first concrete Hasan-owned Backend/Database/Application/API/Enterprise Integration gap. Do not duplicate client/provider work or invent a numbered stage.


### 2026-09-28 — Enterprise Identity tenant binding (PR #365)

- Concrete Hasan-owned integration gap: the Enterprise Identity adapter accepted a subject and roles without requiring the versioned enterprise identity claim's tenant binding.
- PR #365 now requires a non-empty `tenant_id` claim and rejects claims whose tenant differs from the configured tenant boundary.
- Exact implementation head: `01cd42d9fc623e052c625170935ea93ded8bf3ae`.
- Client Typecheck run `36352892657` and ConstructionPM CI run `36352892636` completed successfully.
- PR #365 merged to `main` as `f2ea99a1a097a5b3592d8cb362a84161fa17d776`.
- No Scheduling/P6, Calendar/Duration, Progress/EVM, Resource/Cost or financial calculation semantics changed.

### Current continuation point

- Current `main` is `f2ea99a1a097a5b3592d8cb362a84161fa17d776`.
- PR #366 was closed without merge after its original branch diverged from the newly advanced `main`; its authorization validation change remains unmerged.
- A fresh current-main implementation is tracked in PR #369. Its exact head is `5396415bd49ed93d07d12ae84939ab22ed596da3`; GitHub Actions has not yet produced a run/status for this head, so it must not be marked runtime-verified or merged until evidence appears.
- Next action: verify PR #369 Actions. If a concrete CI failure appears, fix only that failure; if no workflow is emitted, investigate the repository Actions trigger/status rather than bypassing the verification gate.


### 2026-09-28 — Current-main reconciliation after PR #394

- PR #394 (Field Assurance canonical reconciliation documentation) is merged to `main` as `8efe211686790dd01a13f6d3b5dd082c891d95cb`.
- The prior continuation note for PR #369 is stale: PR #369 is closed without merge and must not be revived.
- Current open Hasan-owned implementation PRs: none.
- The first concrete open Hasan-owned backend work is Issue #393, **P6 Parity Track — Hasan: Persistence, API & Import/Export**.
- PR #395 is an active Jalal-owned prerequisite for that track: it establishes the Shared/Core P6 Field Registry and business-object registry seam. Hasan must not duplicate or modify that active Core implementation.
- PR #395 currently has Client Typecheck green but ConstructionPM CI failing because `shared/contracts/p6-business-object-registry.v1.json` does not declare `$schema`; the failing regression is `tests/integration/test_contract_files_parse.py::test_all_shared_json_contracts_are_valid_json`. This is an evidence-backed blocker in the active Jalal PR, not a reason to bypass CI or create a duplicate backend fix.
- Once the authoritative P6 registry prerequisite is merged and current `main` is re-read, Hasan's first implementation slice under #393 is persistence/API/import-export for the registry metadata, with tenant/project scope, versioning, typed values, revision/concurrency and deterministic round-trip behavior.
- Do not redefine P6 scheduling/calendar/formula semantics in the backend. Consume the Shared Core contracts from the owning track.
- Do not start a backend branch from an unmerged Jalal PR or resurrect stale PR #384; start from the current `main` after the prerequisite is merged.


### 2026-09-28 — P6-2 Typed Field/UDF Backend Slice (PRs #400, #406, #407, #408)

Status: **implemented and runtime-verified through the completed persistence/API slices**

- PR #400 added tenant/project/revision-scoped persistence for the Shared/Core P6 Field Registry. It preserves typed metadata, registry version and immutable definitions, and rejects stale revision access with `REVISION_CONFLICT`.
- PR #400 final implementation head `5a57766c5c0198c81c79afb29203cb204009cb60` passed ConstructionPM CI **1688** and Client Typecheck **1391**; merge commit: `20d2d59f7cd3b122ada09ab0be4e3e5b6def86ba`.
- PR #406 added tenant/project/revision-scoped custom/UDF definition persistence with typed data type, nullability, unit and enum-domain metadata. ConstructionPM CI **1690** and Client Typecheck **1393** passed; merge commit: `01c4b74f2f1c7a04e9465fc3ab26cc46ec600894`.
- PR #407 added the versioned P6 Field Registry API boundary for standard fields and UDF definitions, including project.read/project.write authorization and cross-scope rejection. ConstructionPM CI **1692** and Client Typecheck **1395** passed; merge commit: `1da1ce3db870b0a09d7894cd07bed53cf59edc9f`.
- PR #408 added typed UDF value persistence for Date, DateTime, Decimal, Integer, Boolean, Enum and Duration storage, preserving duration value/unit without performing calendar conversion. Its initial CI exposed a real exception-boundary mismatch for stale revisions; the final correction normalized that error at the value boundary. Final head `f148e023ba443065b2b3f21d8fdd4f66f384c8ce` passed ConstructionPM CI **1695** and Client Typecheck **1398**; merge commit: `f60d1708adfea0d559d54e9de8434aa11ad08daf`.
- No Scheduling/P6 calculation semantics, Calendar arithmetic, Progress/EVM, Resource/Cost or financial formulas were moved into persistence/API.
- Do not repeat the four completed slices above.

### Current Backend Continuation Point

- Current `main`: `f60d1708adfea0d559d54e9de8434aa11ad08daf`.
- P6-2 now has the field-registry persistence, UDF definition persistence, versioned API boundary and typed UDF value storage slices.
- Remaining P6-2 work must be selected only after a fresh current-main/open-PR inspection. In particular, verify whether compatibility/version migration or another concrete typed persistence gap is actually missing before implementation.
- P6-3 Column/View/Layout remains Javad-owned; do not duplicate it.
- P6-4 Formula semantics remain Shared Core/Jalal-owned; Hasan may only implement a concrete persistence/API dependency after the authoritative Shared/Core contract exists.
- Continue with the first concrete Hasan-owned gap; do not revive stale PRs or invent a numbered stage.


### 2026-09-28 — P6-2 PostgreSQL production persistence (PR #410)

Status: **implemented and runtime-verified**

- PR #410 added production PostgreSQL adapters for P6 Field Registry metadata, custom/UDF definitions, and typed UDF values.
- Tenant/project/project-revision scope, immutable definitions, typed round-trip behavior and application transaction ownership are preserved.
- Live PostgreSQL coverage verifies field isolation/revision conflict/rollback plus UDF definition immutability and typed Date/Duration value round trips.
- The first PostgreSQL gate also exposed two unrelated existing Field Assurance integration-fixture defects and one Dependency Graph conflict-mapping gap; these were corrected narrowly on the same continuation branch so the authoritative production gate could complete. No P6 calculation semantics were changed.
- Final implementation head: 8051aa9c085dae858e528158f30c6ff40492644e.
- ConstructionPM CI 1707, Client Typecheck 1410, PostgreSQL Integration 120 all passed.
- Merge commit: a59fe3873409cac28d9f76e1aa0ee1479705ad12.
- No Scheduling, Calendar arithmetic, Formula, Progress/EVM, Resource/Cost or financial calculation semantics were introduced.

### Current P6 Backend Continuation

- Current main: a59fe3873409cac28d9f76e1aa0ee1479705ad12.
- P6-2 now has SQLite + PostgreSQL persistence for the Field Registry, UDF definitions and typed UDF values, plus the versioned API boundary.
- The remaining P6-2 acceptance item is compatibility/version migration. Do not invent a target version; first wait for or reconcile an authoritative Shared/Core registry version transition before implementing a concrete migration.
- P6-3 Column/View/Layout remains Javad-owned; P6-4 Formula semantics remain Shared Core/Jalal-owned unless a concrete Hasan-owned persistence/API dependency is established.


### 2026-09-28 — P6 continuation gate: no safe migration target yet

- Fresh current-main reconciliation after PR #410 confirms P6-2 Field Registry/UDF SQLite + PostgreSQL persistence, typed UDF values and the versioned API boundary are already complete and must not be repeated.
- P6-2 still lists compatibility/version migration, but the authoritative Shared/Core registry currently provides no concrete target version transition to migrate to. No fabricated migration target is permitted.
- PR #409 (Jalal, Shared/Core) is the only currently open PR and provides the P6 formula-semantics prerequisite. Its exact head aa46cc3aecf16152e7651fb15dc7fe46eaced899 has ConstructionPM CI 1702 and Client Typecheck 1405 green, but it is not yet merged. Hasan must not create formula persistence/API semantics against an unmerged contract.
- P6-3 Column/View/Layout remains Javad-owned. P6-7 interchange depends on the authoritative field registry/mapping surface and remains a later concrete gate rather than a reason to invent an adapter now.
- Current evidence establishes an ownership/version prerequisite, not a missing backend implementation. Next Hasan implementation starts only when a concrete Shared/Core contract/version transition is merged and reconciled against current main.


### 2026-09-28 — Reconciliation after Shared/Core PR #411

- The prior note naming PR #409 as the active Shared/Core prerequisite is superseded: PR #409 is closed without merge and must not be revived.
- PR #411 is now the active Jalal-owned Shared/Core P6 formula field-type bridge. Its head `1b053f8f5e20c63c1fafc8d81cc45b89b2a5f41e` passed ConstructionPM CI **1713** and Client Typecheck **1416** and is mergeable, but it is not yet merged.
- PR #411 is Shared/Core semantics only. Hasan must not implement formula persistence/API semantics against this unmerged branch.
- PR #395 remains an older Jalal-owned Field Registry PR and is currently non-mergeable against the newer baseline; do not revive it. The already-merged Hasan persistence/API work remains authoritative on current main.
- Once #411 (or its authoritative successor) is merged into current main, re-read the resulting contracts and implement only the concrete Hasan-owned persistence/API dependency that the merged formula contract requires.


### 2026-09-28 — P6 resource-spread persistence (PR #434)

Status: **implemented, PostgreSQL runtime-verified, merged**

- Fresh current-main reconciliation found no existing resource-spread persistence implementation and no open duplicate PR.
- PR #434 added tenant/project/project-revision-scoped resource-spread future-period buckets with immutable identity (tenant_id, project_id, spread_id, period_id).
- Decimal values are persisted without float coercion; unit and currency metadata are explicit and mutually constrained by metric type.
- SQLite + PostgreSQL repositories preserve deterministic reads, stale-revision rejection and identical replay idempotency; application service owns transactions.
- PostgreSQL workflow trigger was extended specifically for this P6 persistence boundary and its live integration test.
- Exact implementation head: 0634a385f287963e8cfa134c85ac1da3e44b6d0d.
- ConstructionPM CI 1793, Client Typecheck 1496, PostgreSQL Integration 137 all passed on the exact head.
- PR #434 merged as 76628e5ddb995551fcf1b63eecf14bc15af71bfa.
- No resource leveling, cost/rate calculation, calendar conversion, Scheduling/P6 calculation or financial semantics were introduced.

## Next point

Reconcile current main and open P6 work again. Resource-spread persistence is complete; remaining Hasan-owned P6 working-data candidates include codes/code scopes and baseline persistence, plus applicable interchange/conformance gaps. Implement only the first concrete missing boundary and do not duplicate Jalal/Farmj22002 work.


### 2026-09-28 — P6 code scope persistence (PR #435)

Status: **implemented, PostgreSQL runtime-verified, merged**

- Fresh main reconciliation found no existing P6 code-scope persistence and no duplicate open implementation.
- PR #435 added tenant/project/revision-scoped code definitions with explicit GLOBAL, PROJECT and EPS scope kinds and immutable typed code values.
- Identical writes replay idempotently; changed definitions and stale revisions fail closed; deterministic listing is preserved.
- SQLite and PostgreSQL repository boundaries plus application-owned transaction support were added.
- PostgreSQL workflow triggers were extended to execute the live P6 code persistence test.
- Exact implementation head: 63d1c3f68cc8a8d66c3819bdb31a2cbf183630c7.
- ConstructionPM CI 1800, Client Typecheck 1503, PostgreSQL Integration 139 all passed on the exact head.
- PR #435 merged as 8501456c12e3458e6133839d0da45be499658ee6.
- No code assignment/inheritance calculation, Scheduling/P6 calculation, Resource/Cost or financial semantics were introduced.

## Next point

Reconcile baseline support against current Shared Core contracts. Baseline persistence must preserve authoritative snapshot/version identity but must not implement schedule comparison/calculation semantics in Backend/API.


### 2026-09-28 — P6-8 Activity Steps persistence (PR #438)

Status: **implemented, merged and runtime-verified**

- Added tenant/project/project-revision scoped P6 Activity Step persistence with deterministic sequence, Decimal weight, optional dates and explicit UDF metadata.
- Added SQLite and PostgreSQL repository boundaries with application-owned transaction semantics.
- Added round-trip, deterministic ordering, tenant/project isolation, stale-revision, replay/immutability and live PostgreSQL rollback coverage.
- Exact implementation head: fad3c6c390c6859fcdd0038b63ff9f5aa8af3446.
- ConstructionPM CI #1827, Client Typecheck #1530, PostgreSQL Integration #142 all passed on the exact head.
- PR #438 merged to main as e5344b4a02c9e1ba01137f892f4e13b674577225.
- No Scheduling, Calendar/Duration, Progress/EVM, Resource/Cost or financial calculation semantics were introduced.

### Current P6 Backend Continuation

- Activity Steps persistence is complete; do not repeat it.
- Baseline comparison persistence remains blocked until an authoritative Shared Core baseline snapshot/version contract exists. Do not invent baseline comparison semantics in Backend/API.
- Next action is a fresh current-main/open-work inspection for the next concrete Hasan-owned P6-8 data surface, with baseline ownership explicitly rechecked first.


### 2026-09-28 — P6 Activity Resource Assignment persistence (PR #449)
Status: **implemented, merged and runtime-verified**
- Added tenant/project/project-revision scoped Activity Resource Assignment persistence with typed Decimal units/cost snapshots and explicit unit/currency/calendar metadata.
- Added SQLite and PostgreSQL repository boundaries, deterministic reads, immutable replay semantics, stale-revision rejection and application-owned transaction service.
- Added focused unit coverage for round-trip, filters, isolation, revision conflict, immutability, Decimal preservation and fail-closed validation.
- Added live PostgreSQL coverage for round-trip, tenant isolation, revision conflict, Decimal values, immutable replay and rollback; the PostgreSQL workflow now triggers the new live test.
- Exact implementation head: 22f21b7d880fd04cbc702f424ff00dba3a2cae12.
- ConstructionPM CI #1874, Client Typecheck #1577 and PostgreSQL Integration #156 all passed on the exact head.
- Merge commit: b24c0ecbeabe806e05f27d31b48df662d47a31c1.
- No P6 scheduling, calendar, resource-rate, leveling, cost calculation or financial calculation semantics were introduced.

### Current P6 Backend Continuation
- Expense persistence and Activity Resource Assignment persistence are now merged; do not repeat them.
- Baseline comparison persistence remains blocked until an authoritative Shared Core baseline snapshot/version contract exists.
- Continue from the next concrete P6 working-data surface on current main, with Role/Assignment/Document/Issue/Work Product coverage reconciled before implementation and no duplication of Shared Core or client-owned semantics.


### 2026-09-28 — Current-main reconciliation after P6 persistence continuation

- Current main is `c35d6e3374109511f833823118e62a9bafe27634` after the Expense persistence and Activity Resource Assignment continuations.
- PR #448 merged the P6 Expense persistence boundary as `8264965ebe3cc9fefaab2978baaebcf677f73e88`; Expense persistence is complete and must not be repeated.
- PR #449 merged the Activity Resource Assignment persistence boundary as `b24c0ecbeabe806e05f27d31b48df662d47a31c1`; resource-assignment persistence is complete and must not be repeated.
- Stale PR #444 was closed because its branch diverged from current main and duplicated the already-merged Expense boundary from #448.
- Baseline comparison persistence remains explicitly blocked: no authoritative Shared Core baseline snapshot/version contract is currently established for Backend/API consumption. Backend must not invent baseline comparison or scheduling semantics.
- Before any new P6 persistence slice, reconcile Role/Assignment/Document/Issue/Work Product against current main and open work. Implement only a concrete Hasan-owned boundary with authoritative contract evidence, focused tests, PostgreSQL verification, and documentation.


### 2026-09-28 — P6 baseline metadata persistence (PR #450)

Status: **implemented, runtime-verified and merged**

- Added tenant/project/project-revision scoped baseline metadata persistence.
- Persisted stable baseline identity, explicit PRIMARY/SECONDARY/TERTIARY/USER_SELECTED role, source project revision provenance and immutable metadata.
- Added SQLite/PostgreSQL repositories and application-owned transaction boundary.
- Added focused SQLite coverage for round-trip, deterministic ordering, scope isolation, stale revision rejection, immutable replay and transaction ownership.
- Added live PostgreSQL coverage for round-trip, tenant isolation, stale revision rejection and rollback.
- Exact implementation head: fb4d7f9576136ae91f7bfdd94cc6fdf5a37e9fac.
- ConstructionPM CI 1878, Client Typecheck 1581, PostgreSQL Integration 158: all passed on the exact head.
- PR #450 merged as 6b0eb9d9c7f0b58e486af66e7c7ce1f5843fc5e6.
- No baseline comparison/variance, scheduling, calendar, progress/EVM, resource/cost or financial calculation semantics were introduced.

### Current P6 Backend Continuation

- Baseline **metadata persistence** is complete; do not repeat it.
- Baseline comparison/variance/selection calculation remains blocked until an authoritative Shared Core snapshot/version contract exists. Backend/API must not invent those semantics.
- Continue with a fresh current-main/open-work inspection for the next concrete Hasan-owned P6 working-data surface.


### 2026-09-28 — P6 code assignment persistence and PostgreSQL verification (PRs #468–#471)

Status: **implemented, runtime-verified and merged**

- PR #468 added tenant/project/project-revision scoped P6 code assignments with immutable assignment identity and deterministic reads.
- PR #469 added the application transaction boundary for code-assignment save/read/list operations.
- PR #470 changed SQLite/PostgreSQL upsert to an atomic insert-or-ignore/on-conflict path followed by read-back, preserving immutable metadata behavior.
- PR #471 added live PostgreSQL verification for code-assignment round trips, scope/revision isolation, immutable metadata and the atomic conflict/replay path from independent connections.
- ConstructionPM CI #2003 passed on Python 3.11, 3.12 and 3.13; Client Typecheck #1706 passed.
- PR #471 merged as `6762d4d9d03142611dea4e5af2c67161d3e62f8a`.
- The #471 independent-connection test verifies the conflict/replay path; it is not a simultaneous-write stress test.
- No P6 scheduling, calendar, formula, progress/EVM, resource/cost or financial calculation semantics were introduced.

### Current P6 Backend Continuation

- Code definitions and code assignments are complete; do not repeat them.
- Baseline metadata persistence is complete; baseline comparison/variance/selection calculation remains blocked until an authoritative Shared Core snapshot/version contract exists.
- P6-7 interchange codecs and round-trip conformance fixtures are already merged; do not recreate them.
- Before another P6 persistence slice, reconcile the remaining Role/Assignment/Document/Issue/Work Product surfaces and active Shared/Core prerequisites against current `main`.
- Implement only the first concrete Hasan-owned Backend/Database/Application/API/Enterprise Integration boundary with authoritative contract evidence, focused tests, PostgreSQL verification where applicable, and documentation.
- If no concrete backend gap exists, record the ownership/blocker instead of inventing a feature or reviving stale PRs.


### 2026-09-29 — PostgreSQL live-gate reconciliation (PR #479)

- PR #479 aligned PostgreSQL Integration push/PR path filters with the live P6 tests already executed by the workflow and corrected the Field Assurance repository `execute()` contract duplication exposed during reconciliation.
- Exact PR #479 head: `9620680fe2d65c843cb2101a03e87ab3ddab7360`.
- Client Typecheck run `36637815089`, ConstructionPM CI run `36637815099`, and PostgreSQL Integration run `36637815146` all completed successfully on that exact head.
- PR #479 was squash-merged to `main` as `7f6d5c4faefa3b43ce9422d00311ff3ea65e72bb`.
- This is a verification/CI-boundary reconciliation, not a new Hasan P6 data-surface implementation; do not count it as a new persistence/API feature.

### Current Backend Continuation Point

- Current `main`: `7f6d5c4faefa3b43ce9422d00311ff3ea65e72bb`.
- PR #70 remains historical/stale and must not be revived.
- Issue #393's latest reconciliation states that no new concrete Hasan-owned P6 persistence/API gap is evidenced after the merged working-data surfaces. Do not duplicate interchange codecs, code assignments, baseline metadata, resource-spread, financial-period, activity-step, activity-actual, cost-account, expense, resource-assignment, or report/profile persistence.
- Before the next implementation, re-read current `main`, this file, `docs/roadmap/STAGE_STATUS.md`, and open PRs; implement only the first newly evidenced Hasan-owned backend contract gap with focused tests and runtime verification.


### 2026-09-30 — Current-main reconciliation / execution gate

- Current main at reconciliation: `1eb36c2a016ff377d9967569d27c7a1d8774d214`.
- Stage 33.4.73 atomic idempotency work is already merged and runtime-verified through PR #171; do not reimplement it.
- The obsolete authoritative-schedule-materializer PR #482 was closed after current-main reconciliation; the authoritative schedule materializer/evaluator/query path is already on current main.
- Current execution priority is: CI/branch hygiene, then Stage I/J scheduling work owned by Jalal, then P6 parity integration. Hasan continues only when a concrete Backend/Database/Application/API/Enterprise Integration gap is evidenced.
- Open PRs must be treated by ownership and current-main ancestry; stale/non-mergeable branches are not active implementation bases.
- No new Hasan feature is authorized by this reconciliation without a concrete missing contract/persistence/application boundary, focused tests, and runtime verification.


### 2026-09-30 — Current-main CI gate / no concrete Hasan backend gap

- Current main: `5c33d991ec6276640445a78a125c8c49da05d369` (`p6: reconcile Activity field evidence inventory on current main (#500)`).
- Current-main push verification is green: ConstructionPM CI run #2128 (`36652211742`), Client Typecheck run #1831 (`36652211392`), and PostgreSQL Sync State Integration run #748 (`36652211405`).
- PR #500 has already reconciled the Activity P6 evidence inventory on current main. No open PR currently supplies a new Hasan-owned Backend/Database/Application/API contract that is both non-duplicate and current-main based.
- The stale branch `hasan/reconcile-p6-no-backend-gap-20260930` is 69 commits behind and diverged; its documentation conclusion remains valid but the branch itself must not be merged or revived.
- Issue #382 (Field Assurance repository/application reconciliation) is already represented by merged current-main work (#383/#386 and subsequent CI coverage); do not duplicate it.
- Issue #104 is an infrastructure-level GitHub-hosted runner entitlement/provisioning investigation, not an application/backend defect; do not alter application code to compensate for it.
- Continuation rule: until a concrete authoritative Shared Core contract or reproducible Backend/API/Persistence defect appears, record the boundary rather than inventing a feature. When one appears, branch from that exact current `main`, add focused regression tests, obtain PostgreSQL verification where applicable, and record exact CI run identifiers.


### 2026-09-30 — Post-#518 current-main reconciliation

- PR #518 (Stage 73.16 working-day relationship regression evidence) has merged successfully as `4fa18bcc83d86aa1d44feff232a791f00ecc78b1`; its exact head passed ConstructionPM CI, PostgreSQL Integration and Client Typecheck.
- The only remaining open PR is #517, a draft owned by `farmj22002-droid` for Shared Scheduling semantics; it is not a Hasan-owned backend implementation and must not be modified as Hasan work.
- Fresh issue/open-PR inspection confirms no new concrete, non-duplicate Hasan-owned Backend/Database/Application/API/Enterprise Integration gap is currently evidenced.
- Existing P6 persistence slices and Stage 33.4.73 work remain complete; do not duplicate them.
- Continue by monitoring for a concrete authoritative Shared Core contract or reproducible Backend/API/Persistence defect. When one appears, branch from that exact current `main`, add focused regression coverage, obtain PostgreSQL verification where applicable, and record exact CI evidence.


### 2026-09-30 — Web/API boundary deep audit

- Deep current-main inspection covered the Web transport (apps/web/src/client.ts), Workspace read contract (apps/web/src/workspace-read-api.ts), Backend P0 API/application boundary (src/construction_pm/backend_p0/api.py, application.py) and Workspace read service.
- The current Web layer is explicitly a framework-neutral integration foundation: it consumes versioned API/Application contracts through FetchApiTransport; the Web package does not claim to contain a concrete HTTP server/runtime.
- The Backend P0 layer exposes typed application/API adapters and the Workspace Control Room read contract with tenant/project/revision authorization and validation; it does not contain a competing calculation engine.
- No reproducible Hasan-owned defect was found in this boundary. A concrete HTTP server/runtime or complete Web Beta shell would be a product/runtime delivery item and must follow the registered ownership split rather than being invented as a backend duplicate.
- Open PR #517 remains scheduling-owned by farmj22002-droid; PR #519 is governance-owned by Jalal. Neither is modified as Hasan work.
- Continue from the first reproducible Backend/Database/Application/API defect or authoritative contract dependency; do not create implementation solely to manufacture progress.
