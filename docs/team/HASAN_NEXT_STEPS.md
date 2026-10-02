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


### 2026-09-30 — Post-#521 Web shell reconciliation

- PR #521 (executable browser workspace shell) is merged on current main as `c694411a0aef3108f840f07f289b7c066d883e3e`.
- Its exact implementation head `2cf98580fe0c39469e6852160af060b204565463` passed Client Typecheck run `36670851884` and ConstructionPM CI run `36670851924`.
- The merged Web shell explicitly identifies its next dependency as real authenticated project/session selection and authoritative API workflow.
- Current backend inspection confirms that `AuthorizationContext` and tenant/project/revision authorization already exist, but no concrete session/authentication or project-selection provider contract was found on current main.
- Therefore no speculative authentication implementation is added under Hasan ownership. The next Hasan implementation must start only when the concrete session/project-selection contract or reproducible backend/API gap is defined; otherwise this remains a Web/provider integration boundary.
- PR #517 remains the only open PR and is owned by `farmj22002-droid` in Shared Scheduling; do not modify it as Hasan work.


### 2026-09-30 — Authenticated Web project lifecycle bridge

- PR #522 added the provider-neutral session-bound Project Lifecycle contract: authenticated session validation, authorized project listing/opening/creation, and authoritative ProjectContext derivation. It merged as `e801142d70bf987db63ec1193e648fb4a2e6b86e`.
- PR #523 added the versioned application/API response boundary over that lifecycle service and merged as `2fce468d183cdda4a0b3182c98ca9aa3fb6a5da9`.
- PR #525 then closed the remaining Application ↔ Web HTTP boundary gap with a framework-neutral `cp_session` cookie route adapter for `/api/session`, `/api/projects`, and `/api/projects/:id/open`. Its exact head `3dbe683416cf7fef30256b578ac0410cdedadb8c` passed Client Typecheck run `36672896453` and ConstructionPM CI run `36672896458`; it merged as `9a4dd0914072168ca6e16fbba59b646358720400`.
- The HTTP adapter does not trust browser tenant/user/project headers as identity and delegates authorization to the existing ProjectLifecycleAPI; it introduces no authentication engine, database repository, or scheduling/P6 logic.
- The next boundary is now explicitly outside this Hasan API adapter: connect the chosen ASGI/WSGI host and the Web session/project-selector client to these routes. Open PR #524 is the Javad-owned Web client integration; PR #517 remains scheduling-owned and must not be modified as Hasan work.
- Do not create another authentication or project-selection implementation. Continue from the first reproducible backend defect after the host/Web integration, with exact current-main reconciliation and focused regression evidence.


### 2026-09-30 — Current-main reconciliation after P6 Field Registry PostgreSQL persistence (PR #533)

- Current `main` is `f18318ab82ac4728e2c13dd6b7cf957d1f6defd1`; PR #533 (P6 Field Registry PostgreSQL persistence) is merged and its exact implementation head `ceb2724380fbc9da07ae2de4d9bf0698b04bf5f5` passed ConstructionPM CI, Client Typecheck and PostgreSQL Integration before merge.
- The P6 Field Registry PostgreSQL repository now exists on current main; do not duplicate Field Registry persistence/API work.
- Issue #393 remains the Hasan ownership boundary, but its previously identified P6 working-data surfaces and interchange codecs are already represented by merged current-main work. Baseline metadata is persisted; baseline comparison/variance semantics remain Shared Core-owned and must not be invented in Backend/API.
- Current open-PR inspection found no open PR requiring Hasan-owned Backend/Database/Application/API work. Historical/stale Web or Scheduling PRs must not be revived merely because they exist in Git history.
- Therefore no new feature is started at this reconciliation point. The next Hasan implementation must begin only when a concrete authoritative contract or reproducible Backend/API/Persistence defect appears on current `main`.
- Execution rule remains: branch from exact current `main`, add focused regression coverage, obtain PostgreSQL verification where applicable, and record exact CI evidence before merge.


### 2026-09-30 — P6 Mapping Registry contract reconciliation (PR #535)

- PR #535 corrected a concrete API-contract drift on current main: the authoritative `shared/contracts/p6-mapping-registry.v1.schema.json` requires `contract_version=1.0`, while the API previously emitted `p6-mapping-registry-api.v1`.
- The API now emits `1.0`, and focused regression coverage compares the API version identity directly with the schema constant.
- Exact implementation head: `1e214c92a18db0d3f0975377be77735defef1aa4`.
- Client Typecheck #1959 and ConstructionPM CI #2256 both completed successfully on the exact head.
- PR #535 merged to `main` as `ea71d9bbfb6d2aea296c121e6030cc3faaa45c22`, and `main` was verified at that SHA.
- No persistence, scheduling, P6 calculation, or client/UI semantics were changed.

### Current continuation point

- P6 Mapping Registry API contract-version drift is resolved; do not repeat it.
- Current open PRs remain outside Hasan ownership (Javad Web and Shared Scheduling); do not revive or modify them as Hasan work.
- Continue only from a newly evidenced Backend/Database/Application/API/Enterprise Integration defect or authoritative contract dependency on current `main`.
- When one appears, branch from the exact current `main`, add focused regression coverage, obtain PostgreSQL verification where applicable, and record exact CI evidence before merge.


### 2026-10-01 — Post-PR #632 current-main reconciliation

- Current `main` is `0804562c793a6232ffbee1a18f2c3408156b52d7`, the verified merge commit for PR #632 (PostgreSQL UDF persistence verification).
- PR #632 is merged and its post-merge push workflows are all green on the exact merge commit:
  - ConstructionPM CI #2531 — success
  - Client Typecheck #2234 — success
  - PostgreSQL Integration #402 — success
  - PostgreSQL Sync State Integration #848 — success
- P6 UDF PostgreSQL persistence is now covered for typed values, scope/revision isolation, immutable replay/conflict and rollback; do not duplicate this slice.
- Current-main/open-PR reconciliation found no new concrete, non-duplicate Hasan-owned Backend/Database/Application/API/Enterprise Integration gap. Existing P6 resource-spread persistence, resource read API, layout persistence/API, financial-period API, formula/baseline/mapping/UDF verification and other completed slices remain merged and must not be repeated.
- Shared Scheduling/Core work remains outside Hasan ownership; do not modify it as backend work.

### Current continuation point

- Stay at the evidence boundary until a new authoritative contract or reproducible Backend/API/Persistence defect appears on current `main`.
- When a new gap appears: branch from the exact current `main`, add focused regression coverage, obtain PostgreSQL verification where applicable, update this file with exact commit/run identifiers, and only then merge.
- Do not revive stale PRs or create duplicate P6 calculation/scheduling/calendar/resource/cost semantics.


### 2026-10-01 — P6-2 field/UDF contract verification (Issue #633 / PR #634)

- Issue #633 was the next Hasan-owned continuation after PR #632: audit the existing P6 field/UDF persistence and API boundary for typed contracts, stable identifiers, tenant/project/revision isolation, transaction behavior, and compatibility handling.
- PR #634 started from exact current main `18b10ffa705194a92b1647ccdd39c5493062727e` and added only focused evidence; no P6 calculation/scheduling/calendar semantics were changed.
- PR #634 merged with head `ab8fafd80c3952277ff0f90946c9324140720f35` as merge commit `890b5a3b4b337804754177f9fb7fb3beb35b0132`.
- Acceptance evidence on the PR head: ConstructionPM CI #2534 success; PostgreSQL Integration #403 success; Client Typecheck #2237 success.
- Post-merge evidence on merge commit: ConstructionPM CI #2535 success; PostgreSQL Integration #404 success; Client Typecheck #2238 success; PostgreSQL Sync State Integration #850 success.
- The verification now explicitly covers unsupported registry-version rejection at the typed API boundary and application-level rollback after a repository write/failure for both field and UDF persistence, plus live PostgreSQL API round trips and scope/revision isolation.
- Do not duplicate P6 field/UDF persistence/API verification or introduce a second calculation authority.

### Current continuation point

- Reconcile current main for the next concrete Hasan-owned Backend/Database/Application/API/Enterprise Integration acceptance gap or reproducible defect.
- Do not revive stale PRs or modify Shared Scheduling/Core work. Any new change must branch from the exact current main, stay within Hasan ownership, add focused regression evidence, and obtain PostgreSQL verification where applicable.


### 2026-10-01 — P6 Activity Period Actual API boundary (Issue #393 / PR #635)

- The next concrete Hasan-owned gap after P6 field/UDF verification was the missing versioned API/application boundary for the already-persisted P6 Activity Period Actual resource.
- PR #635 started from exact current main `114780fefd66b60bda1a744ebe252bc3231bedef` and added only the typed API/schema and focused verification; no P6 calculation, scheduling, calendar, formula, Progress/EVM or Resource/Cost semantics were changed.
- Initial CI exposed one real defect in the new JSON Schema: a decimal regex contained an invalid JSON escape. The schema was corrected on the same branch before merge.
- Final implementation head: `6e9566bb52eb316eac75e98203df6cc19d7ab37e`.
- PR-head acceptance evidence: ConstructionPM CI #2538 success; PostgreSQL Integration #406 success; Client Typecheck #2241 success.
- PR #635 merged with merge commit `b18f86cef830beadbe0082e210418b8018e97d0a`.
- Post-merge evidence on the exact main merge commit: ConstructionPM CI #2539 success; Client Typecheck #2242 success; PostgreSQL Integration #407 success; PostgreSQL Sync State Integration #852 success.
- The new boundary preserves tenant/project/project-revision scope, authorization, canonical Decimal wire values, and create/get/list behavior over the existing authoritative application service, with live PostgreSQL API verification.
- Do not duplicate Activity Period Actual persistence/API verification.

### Current continuation point

- Reconcile current main for the next concrete Hasan-owned Backend/Database/Application/API/Enterprise Integration acceptance gap or reproducible defect.
- Do not revive stale PRs or modify Shared Scheduling/Core work. Any new change must branch from the exact current main, stay within Hasan ownership, add focused regression evidence, and obtain PostgreSQL verification where applicable.

### 2026-10-01 — Post-PR #645 / #647 current-main reconciliation

- Current main baseline is `435b61033284c579db88e45c4db29acef9cf08c9`, after PR #645 merged successfully.
- PR #647 is Jalal/Shared Core-owned and remains open; its current head `041b9aa8f74c5dd0cb395433c42c27b401f7094e` has all three workflows green: ConstructionPM CI #2562, Client Typecheck #2265, PostgreSQL Integration #419.
- The earlier #647 test failure was diagnosed as a test-construction error: the invalid `LevelingActivity` demand is rejected by authoritative model validation before the boundary call. No Hasan code was changed because this is Shared Core ownership.
- Current open-PR inspection found no open Hasan-owned PR. Open Hasan issue tracks remain #393, #459, #79, #26 and process issue #3; none currently supplies a newly evidenced non-duplicate backend implementation gap.
- Completed Hasan P6 slices through #635 and the current-main backend verification work #636/#643 are already merged; do not repeat resource-assignment spread persistence/read API, field/UDF verification, activity-period-actual API, or backend runtime authorization/revision tests.
- PR #647's own stated next slice is the actual scheduler execution path with CPM recalculation and `PreserveScheduledEarlyAndLateDates` regression coverage; that work belongs to Shared Core/scheduling ownership, not Hasan backend ownership.

### Current continuation point

- Remain at the evidence boundary until a new authoritative backend/API/persistence contract or reproducible Backend/API/Persistence defect appears on current `main`.
- When a Hasan-owned gap appears, branch from exact current `main`, add focused regression coverage, obtain PostgreSQL verification where applicable, and update this document with exact commit/run identifiers before merge.
- Do not modify PR #647 or invent duplicate P6 scheduling/resource-leveling semantics under the Hasan backend lane.


### 2026-10-01 — P6 ResourceAssignment period write API seam

- Current main baseline for this slice: `ee515ba0bed7e9413edfedeb0688b56f3ed31e8c`.
- Fresh #393/#597 reconciliation identified the remaining backend seam as a versioned write boundary for already-persisted `ResourceAssignment` time-phased period values.
- PR #608 already provides authoritative SQLite/PostgreSQL persistence and immutable/replay-safe application behavior; PR #609 already provides the corresponding read API. Neither is duplicated here.
- This slice adds `p6-resource-write-api.v1` with `save_assignment_period`, enforcing tenant/project scope and `project.write` authorization while delegating revision/conflict/replay semantics to the existing repository/application service.
- No leveling, CPM, calendar, spread calculation, cost calculation, or second resource model is introduced.
- Focused tests cover typed Decimal round-trip, identical replay, immutable conflict, scope/authorization rejection, and revision-conflict propagation.
- Documentation: `docs/architecture/P6_RESOURCE_PERIOD_WRITE_API_V1.md`.

### Current continuation point

- Verify this exact branch through GitHub Actions, including PostgreSQL verification where the existing resource-period integration suite applies.
- After merge, reconcile #393/#597 against the new API seam and continue only from the next concrete Hasan-owned backend contract.


### 2026-10-01 — P6 resource leveling read adapter

- Current main baseline for this slice: c58e91b55ca7acaa925dacf1799791f884f9e9b4 after PR #661 merged the authoritative ResourceCapacity contract.
- PR #661 resolves the previous blocker by defining capacity from ResourceCalendar.capacity_on(period) via assignment calendar_id; AssignmentPeriod and ResourceSpreadBucket remain demand/spread data.
- This Hasan slice adds an application adapter that consumes only P6ResourceReadAPI for authoritative assignment/period data and maps it into the existing SchedulerLevelingInput boundary.
- Capacity is consumed through p6_resource_capacity_contract.py; no second persistence model and no scheduling calculations are introduced.
- Focused tests cover Decimal preservation, deterministic demand/capacity ordering, typed SchedulerLevelingInput output, and the existing API authorization boundary.
- Documentation: docs/architecture/P6_RESOURCE_LEVELING_READ_ADAPTER_V1.md.

### Current continuation point

- Verify the fresh adapter branch with focused tests and all relevant GitHub Actions.
- Open the Hasan PR with exact CI evidence; if a concrete integration gap remains, record the exact file/type/module rather than inventing semantics.


### 2026-10-01 — Post-PR #683 current-main reconciliation

- Current main is `94476f94ade2c7fc23aed2c756894dc5ce080d2d`; the latest main commit is governance documentation by Jalal, not a Hasan implementation change.
- Hasan PR #683 (Change/Claim API → atomic PostgreSQL persistence) is merged as `ff6c7cc04a0019d87ae05dfc4a8cc19f4f960337`. Its final implementation head `7681a150c980516db7574d507922f7af15b77241` passed ConstructionPM CI #2674, PostgreSQL Integration #457 and Client Typecheck #2377.
- The concrete defect found by PostgreSQL runtime verification was fixed: the API service now delegates to the authoritative PostgreSQL `persist()` path, and the read API unwraps the PostgreSQL stored envelope before serialization. No duplicate domain/calculation logic was introduced.
- Issue #678 is closed as completed. Its runtime regression gate exposed the Change/Claim PostgreSQL seam and the follow-up #681/#683 work resolved it.
- Current open-PR inspection shows no Hasan-owned implementation PR. Open PRs are outside this ownership lane (Web/client and Shared Core/P6 evidence/documentation); they must not be revived or modified as Hasan work.
- The master audit matrix currently records PostgreSQL-backed Beta verification as `In progress` while #678 is completed; this is a governance-document synchronization issue for the matrix owner, not a reason to duplicate backend verification.

### Current continuation point

- No new non-duplicate Hasan Backend/Database/Application/API/Enterprise Integration implementation gap is currently evidenced on current `main`.
- Remain at the evidence boundary until a new authoritative contract dependency or reproducible backend defect appears.
- When a new gap appears: branch from the exact current `main`, add focused regression coverage, obtain PostgreSQL verification where applicable, update this document with exact commit/run identifiers, and only then merge.
- Do not revive stale PRs or duplicate completed P6 persistence, API, interchange, resource-leveling, scheduling, calendar, duration, formula, Resource/Cost or EVM semantics.

### 2026-10-01 — Post-PR #699 / P6-5 #697 reconciliation

- Current `main` baseline: `149e115f4203c9cb78e50ebd53d4660a7de04761`, merge of PR #699.
- PR #699 completed the last evidenced Hasan-owned P6 ScheduleOptions backend/application seam: resource-leveling requests are routed through the authoritative `schedule_with_resource_leveling()` boundary and missing authoritative leveling input is rejected explicitly.
- Exact PR #699 head: `853d2edfd5d316d8226136a3441266940116ca22`.
- Exact PR #699 verification: ConstructionPM CI run `36850622918` (#2792) passed; Client Typecheck run `36850622823` (#2495) passed.
- Direct current-main inspection for issue #697 found no new persistence/API mapping defect. `AuthoritativeScheduleBatch` supplies batch boundary/priority data but does not execute multi-project scheduling; `evaluate_schedule_snapshot()` still evaluates one snapshot at a time.
- Searches for alternate batch execution surfaces (`schedule_many`, `schedule_all`, `evaluate_batch`, `batch_evaluator`, `multi_project`, orchestration variants) found no authoritative multi-project execution harness on current main.
- Issue #697 therefore remains a Shared-Core/E2E execution gap: the seven-case external-project conformance matrix requires an authoritative multi-project scheduler/orchestrator and runtime evidence. Hasan must not add duplicate scheduling semantics to Backend/API.

### Current continuation point

- Remain at the evidence boundary for Hasan Backend/Database/Application/API/Enterprise Integration.
- Do not revive stale PRs or implement duplicate multi-project scheduling, CPM, calendar/duration, Resource/Cost, EVM, relationship, float, or external-assignment semantics in Backend/API.
- When a concrete Hasan-owned dependency or reproducible backend defect is exposed by the authoritative E2E execution, branch from the exact current `main`, add the smallest focused regression, obtain PostgreSQL verification where applicable, and record exact commit/run identifiers here before merge.


### 2026-10-02 — Post-PR #786 current-main reconciliation

- Current `main` includes PR #786 with merge commit `98a277a2c292c58529542b21f7ee741a56ae9831`.
- Exact PR #786 head `fccf0e5881bac5635aaad26cc38dc6b4f2f32496` passed the final ConstructionPM CI run **3190** and Client Typecheck run **2893** before merge.
- PR #786 reconciled the current Activity evidence-inventory count only; it did not add a Hasan-owned Backend/API/Persistence seam.
- Fresh open-PR inspection after the merge found no open Hasan-owned Backend/API/Persistence/Import-Export implementation PR. Open P6 Activity evidence work (#787 and related stale evidence PRs) remains Jalal/Shared-Core ownership and is not a Hasan task.
- Issue #709 therefore remains the audit parent. No concrete new Hasan-owned implementation gap is evidenced at this checkpoint; do not invent or duplicate functionality.

### Current continuation point

- Re-run the Hasan current-main conformance audit when a concrete backend contract, persistence, import/export, authorization, revision/idempotency, or PostgreSQL defect is evidenced.
- Until then, preserve the ownership/evidence boundary and do not revive stale PRs or duplicate P6 Shared-Core/Activity evidence work.


### 2026-10-02 — Current-main coordination recheck

- Current main baseline: `8bb47a49300ac3ae1f900c8d85f67ca91a3277e2`.
- Hasan currently has no open PR; Issue #709 remains the active bounded backend continuation.
- Do not create a duplicate feature task while #709 is open.
- First action: audit current `main` against the P6-2 backend acceptance criteria and reconcile already-merged work.
- Implement only the first concrete Hasan-owned backend/API/persistence gap proven by evidence; otherwise record the blocking dependency and stop without speculative code.
- Preserve the single authoritative Shared Scheduling/Core calculation boundary and do not revive stale PRs.


### 2026-10-02 — Tranche 4 WBS/WorkPackage evidence boundary

- Exact current main inspected: `9261a0781f230cafc319925445edfbd8cd31a1ac`.
- Repository-wide recursive tree inspection found only two WBS-named implementation files: `apps/web/src/p6-activity-wbs-grid.ts` and its test. The WBS grid is a Web presentation contract; it is not a canonical WBS/WorkPackage persistence, mapper, or API contract.
- Searches for backend/domain WBS and WorkPackage contracts, persistence, API, and mapping returned no additional implementation surface. Therefore no Hasan-owned backend seam can be safely derived from the presentation layer.
- Issue #713 identifies the remaining Release 26 Activity semantic reconciliation as Jalal / Shared Core ownership. Tranche 4 fields including `WBSCode`, `WBSName`, `WBSNamePath`, `WBSObjectId`, `WorkPackageId`, and `WorkPackageName` remain pending certification rather than registry promotion.
- Disposition: Blocked at the evidence boundary. Do not invent a WBS/WorkPackage mapper or persistence/API semantics under Hasan ownership. The next executable step is authoritative field-level WBS/WorkPackage mapping/certification from Shared Core; once that contract exists, Hasan can implement only the resulting concrete backend persistence/API seam.


### 2026-10-02 — Status/Type/StatusCode persistence gate rechecked

- Current main was rechecked against the Activity Status/Type/StatusCode seam.
- `src/construction_pm/activity_master_repository.py` is the authoritative Activity Master persistence surface, but its persisted model currently contains only activity_id, duration, duration_unit, actual_start, record_revision and expected_finish; it has no Status, Type or StatusCode columns or fields.
- `src/construction_pm/scheduling/activity.py` contains canonical typed `ActivityStatus`, `ActivityType` and `ActivityStatusCode` values and P6 wire-value validation, but this is Shared Scheduling/Core semantics rather than persistence.
- `docs/architecture/P6_ACTIVITY_STATUS_TYPE_WRITE_EVIDENCE_2026-10-02.json` explicitly records that Status and Type persistence mapping is not certified and requires an authoritative persisted P6 mapping definition before changing ActivityMaster or adding an interchange mapping.
- `src/construction_pm/p6_interchange_mapping.py` is deliberately registry-driven; it cannot establish a Status/Type/StatusCode mapping by itself. Repository code search found no certified Activity Status/Type/StatusCode mapping definition on current main.
- Disposition: no Hasan implementation is authorized at this gate. The actual dependency is a certified persisted/interchange mapping definition for the exact P6 Activity fields. Once supplied by the semantic authority, the smallest resulting persistence/API seam can be implemented with focused PostgreSQL regression coverage.


### 2026-10-02 — PR #806 completion and P6-2 closure

- Current main advanced to `dd0660150fa1c8f8fddf47545539e3451ef2c6cd` by merge of PR #806.
- PR #806 fixed a concrete Import/Export no-silent-drop defect: mapper-preserved extensions that XER/MPX cannot represent are now rejected explicitly instead of being silently discarded.
- Focused regressions were added for both XER and MPX; the merge was accepted only after the required checks were green.
- Issue #709 is now closed as completed. Its audit/implementation boundary is therefore satisfied and must not be reopened for duplicate work.
- No new Hasan-owned implementation PR is open. Current open PRs #805/#807 are Web ownership and are outside this lane.

### Current continuation point

- Continue from exact main `dd0660150fa1c8f8fddf47545539e3451ef2c6cd`.
- The next Hasan action is a fresh audit of the still-open P6 parity track (#393), limited to Backend/Database/Application/API/Import-Export and database-backed verification.
- Implement only a newly reproducible Hasan-owned defect or an authoritative contract-backed seam. Do not infer missing Activity/WBS/WorkPackage semantics from names or presentation code, and do not duplicate Shared Core calculations.
- If no concrete defect is found, record the evidence and dependency rather than creating speculative code.


### 2026-10-03 — P6 PostgreSQL concurrency verification completed (PR #810)

- Fresh #393 audit identified a concrete DB-backed verification gap: concurrent writers to the same P6 baseline key were not covered by PostgreSQL runtime evidence.
- PR #810 added a two-connection PostgreSQL regression proving that the unique-key race produces exactly one committed writer and an explicit immutable conflict for the losing writer, without changing production semantics.
- Exact implementation head: `f5d95a2b24e61af1e29923f02e56dc48864ed83b`.
- ConstructionPM CI run #3256 passed on Python 3.11/3.12/3.13; Client Typecheck #2959 also passed.
- PR #810 merged to `main` as `8428d94298b19346d73c9c818756eaf69aa9978c`.

### Current continuation point

- Continue from exact current `main` `8428d94298b19346d73c9c818756eaf69aa9978c`.
- No Hasan-owned PR is currently open. The next action remains a fresh audit of #393 for the first newly reproducible Backend/Database/Application/API/Import-Export defect or authoritative contract-backed seam.
- Do not infer semantics from names/presentation code, revive superseded PRs, or duplicate Shared Core scheduling/calendar/formula/resource/cost behavior.
- If no concrete Hasan-owned gap is evidenced, record the dependency and remain at the evidence boundary rather than creating speculative implementation.

### 2026-10-03 — Post-PR #812 current-main reconciliation

- Current main is `7ff2d364231cb1467a9214e08613a15ab9518401`, the merge commit for PR #812.
- PR #812 exposed the authenticated P6 layout write HTTP route over the existing `P6LayoutDefinitionAPI.save()` boundary, with session/project scope binding and focused round-trip/invalid-request/unauthenticated tests.
- PR #812 passed ConstructionPM CI #3262 and Client Typecheck #2965 and was merged without changes to Shared Core scheduling/calendar/formula/resource/cost semantics.
- Fresh #393 audit after the merge reviewed the remaining backend-owned P6 categories and current Web consumers. No newly reproducible Hasan-owned persistence/API/import-export defect or authoritative contract-backed seam is currently proven beyond the completed #810/#812 slices.
- The Web formula API files are empty placeholders and do not constitute a backend contract requirement; no speculative HTTP formula adapter is being created. Baseline/financial-period/mapping/interchange/field-registry persistence and DB verification are already covered by existing current-main work.

### Current continuation point

- Remain at the evidence boundary under #393 until a new authoritative contract dependency or reproducible Backend/Database/Application/API/Import-Export defect appears.
- Do not duplicate P6 layout HTTP/API, PostgreSQL concurrency, field/UDF, baseline, financial-period, mapping/interchange, resource-period, activity-period-actual, or Shared Core scheduling/calendar/formula semantics.
- Next executable action: fresh current-main audit when new evidence appears; if a concrete Hasan-owned gap is found, branch from the exact current `main`, add focused regression coverage and PostgreSQL verification where applicable, then update this checkpoint before merge.


### 2026-10-03 — Post-PR #826 fresh #393 evidence audit

- Current main at audit start: `33b691ef53611e6c2d3ed64c56330842bcd0af92`.
- PR #826 (PostgreSQL verification for Financial Period, Baseline, and Formula Definition repositories) is already represented in current main; no duplicate verification was created.
- Current-main P6 persistence inventory was rechecked for remaining PostgreSQL-backed repositories, including Code, Code Assignment, Cost Account, Expense, Report Profile, and Activity Period Actual. Existing live/integration tests already cover round-trip, scope/revision, rollback and/or concurrency for these repositories.
- ScheduleOptions was rechecked against the authoritative Release 26 disposition artifact. The current Shared Core type and registry contain the documented fields, but the architecture document still marks the formal time-aware schedule-options contract as a remaining gate. Therefore no Hasan-owned Backend/API contract was invented from the Shared Core type alone.
- Disposition: evidence boundary. No new reproducible Hasan-owned Backend/Database/Application/API/Import-Export defect or authoritative contract-backed seam was proven in this audit.
- Next executable action: re-audit current main when new authoritative evidence appears. If a concrete seam appears, branch from that exact main, add the smallest focused regression and PostgreSQL verification where applicable, then record exact commit/CI/merge identifiers here.
