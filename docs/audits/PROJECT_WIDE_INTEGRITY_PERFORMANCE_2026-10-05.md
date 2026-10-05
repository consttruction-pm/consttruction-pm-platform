# Project-wide integrity, performance and architecture audit — 2026-10-05

## Audit scope

This audit is intentionally broader than Jalal 3. It covers the project history represented in the current repository, the registered project requirements, the prior performance/design audits, and the current `main` branch.

Reference point:
- Performance fixes: `d020df11cd28be1b30c1ee44546e01a287a69cfa` and `857f32adb361abc1224a2df1a9d743f03c0388e5`
- Previous Jalal 3 baseline: `772d4c5f31a631e72d1fc6e4f26927df6113e3e6`
- `main` was 49 commits ahead of the Jalal 3 baseline before this audit fix.

## Binding architecture requirements checked

1. Shared Domain/Calculation Core remains authoritative and UI/OS/DB independent.
2. Web, Desktop and Mobile consume shared scheduling/calculation contracts; no client-side replacement CPM engine.
3. Primavera/P6 semantics are preserved rather than simplified for UI convenience.
4. Jalali/Gregorian and working-day/working-time calendar semantics remain centralized.
5. Calendar inheritance/exception persistence remains deterministic and does not silently alter CPM arithmetic.
6. P6 field/layout presentation is a presentation layer and does not redefine calculation semantics.
7. CUBI visual rules remain calm/data-first; brand colors do not become calculation/status semantics.
8. No unnecessary runtime dependency or visual effect should be introduced into dense project-control surfaces.
9. GitHub `main` is the canonical integration baseline.

## Findings and actions

### A. Web workspace rerender overhead — fixed

Before this audit, every workspace selection/menu/language/layout update replaced the entire application shell with `container.innerHTML`, recreated the status/language controls, and then rebuilt the workspace.

This was unnecessary DOM churn and could become visible as activity/field counts grow.

Action taken:
- The application shell is now created once and reused.
- The status/language control is updated in place.
- Workspace content is still deliberately rendered from the authoritative immutable state; this does not move any calculation into the UI.
- No scheduling, CPM, calendar, P6 formula, EVM or persistence semantics were changed.

Commit: `d020df11cd28be1b30c1ee44546e01a287a69cfa`.

### B. CUBI visual system — registered and retained

The prior color/frame audit is included in this project-wide baseline:
- Deep Navy / Navy Dark
- Engineering Blue
- Copper Orange
- Brushed Titanium family
- calm neutral workspace surfaces
- semantic Success/Warning/Error colors
- Inter + Vazirmatn
- restrained brushed-metal treatment limited to brand chrome
- no decorative metallic backgrounds in dense Gantt/table/control panels

The existing visual-system document and tests enforce the main brand anchors and logo color restrictions.

### C. Homepage performance risk — bounded, not converted into product UI debt

The homepage contains gradients, a dashboard illustration, a grid-glow and limited backdrop/transform effects. These are confined to the marketing surface rather than the dense scheduling workspace.

The audit rule is therefore:
- keep visual effects out of core Gantt/grid/control panels;
- do not add large image/video assets merely for decoration;
- keep the existing CSS-only visual treatment unless runtime evidence shows a real regression.

No P6 or project-control calculations are coupled to homepage presentation.

### D. Scheduling/P6 separation — confirmed in reviewed areas

The current calendar inheritance/exception work explicitly stores persistence-ready semantics while leaving scheduling arithmetic in Shared Core. Mobile project-shell code likewise presents relationship/lag data and delegates scheduling through the shared adapter.

No new client calculation engine was introduced by the reviewed changes.

### E. Calendar parity — correctly identified as incomplete rather than falsely marked complete

The repository now has first-class persisted calendar inheritance/exception structures and regression tests, but the repository itself explicitly classifies full P6 Calendar CRUD / Copy / Replace / REST API parity as outside the completed slice.

Open follow-up work remains in the calendar API parity issue. This is a genuine product gap, not a reason to rewrite completed Shared Core work.

### F. CI/runtime evidence — gap

The repository contains PostgreSQL-backed CI configuration and client typecheck/test workflows. However, the GitHub connector currently reports no workflow-run evidence for the exact current head and no combined status entries.

Therefore this audit does **not** claim fresh runtime-green verification for the current head. Code reading and repository configuration are evidence of intended gates, not proof that those gates executed successfully on this exact commit.


### G. Marketing-page compositing overhead — reduced

A second performance pass removed two nonessential browser compositing costs from the marketing homepage: sticky-header backdrop blur and the hero grid mask effect. The dashboard visual keeps a restrained perspective treatment, but no longer depends on the heavier perspective stack previously used. This is intentionally limited to the marketing surface and does not alter the registered CUBI color/frame system or any product-control UI.

Commit: `857f32adb361abc1224a2df1a9d743f03c0388e5`.

## Repository organization decision

The repository's current high-level separation is coherent:
- `src/construction_pm/` — authoritative Python/domain/calculation/persistence implementation
- `apps/web/` — Web presentation/integration
- `apps/desktop/` — Desktop presentation/integration
- `apps/mobile/` — Mobile presentation/integration
- `apps/client-sync/` — shared client synchronization boundary
- `docs/` — contracts, design, responsibilities and implementation evidence
- `tests/` — Python/domain/integration/regression tests
- `infra/` and `tools/` — infrastructure and utilities

No duplicate Shared Core folder or second calculation engine was added during this audit.

## Visual + performance rule for future work

A UI change is not accepted merely because it looks better. It must preserve:
- data readability;
- P6/CPM authority;
- deterministic calculations;
- shared client contracts;
- low DOM/runtime overhead;
- semantic status colors;
- multilingual RTL/LTR behavior.

Dense scheduling, Gantt, cost, EVM and control surfaces must remain calmer and lighter than the marketing homepage.

## Verdict

**Specification:** Partial — the architectural and visual requirements reviewed here are aligned, but full P6 Calendar API parity and some end-to-end product surfaces remain unfinished.

**Engineering quality:** Partial — the reviewed separation is sound and the identified Web shell rerender inefficiency has been fixed, but fresh exact-head CI/runtime evidence is currently unavailable through the connected GitHub status/run interface.

**Important:** This audit is a whole-project integrity baseline. Jalal 3 remains a progress/workload baseline, not the scope of the audit.

## H. Exact-main integration hygiene — checked 2026-10-05

Fresh repository inspection confirms the current `main` head is:
- `3dfa3e725ceda476055a84737b348244eaacc01e`

The connected GitHub status/run interface currently reports:
- no combined status entries for this exact head;
- no workflow runs attached to this exact head.

Therefore exact-head CI remains **unverified**, and no release-green claim is made.

Open UI PR hygiene was also checked:
- PR #1223 was based on an older performance-audit head and was superseded; it has been closed rather than allowed to merge stale UI work.
- PR #1224 is a newer rebuild than #1223 but is still behind the current `main`; it has been explicitly marked for exact-current-main rebuild/rebase before merge.

This preserves the repository rule that open PRs are not part of the integration baseline until reconciled with current `main`.

## I. Calendar parity remains the next substantive P6 gap

The current calendar work is materially better than the earlier audit baseline: inheritance and first-class exceptions are persisted and regression-tested. The remaining P6 gap is still the API/product contract layer tracked by Issue #1209:
- Global / Resource / Project calendar type semantics;
- calendar CRUD;
- Copy Calendar;
- Replace with Global / Project / Resource;
- standard work week and standard detailed work-hours operations;
- detailed work hours / total work hours operations;
- HolidayOrExceptions API operations;
- SQLite/PostgreSQL API-level verification and deterministic concurrency behavior.

This is intentionally kept separate from CPM arithmetic. No second calendar calculation engine should be introduced to solve it.

## J. Calendar implementation evidence — rechecked on current main

The current repository contains a coherent persistence foundation:
- `p6_calendar_read_api.py` exposes only catalog and versioned snapshot reads;
- `CalendarMaster` supports versioned identity, inheritance references, assignments and optimistic revisions;
- first-class calendar exceptions support nonwork, total-work-hours, detailed work-hours and reset-to-standard;
- deterministic snapshots are persisted for both SQLite and PostgreSQL;
- dedicated unit/integration tests exist for these boundaries.

The evidence also confirms that the missing surface is intentionally API/product functionality, not missing Shared-Core persistence primitives. Issue #1209 remains the authoritative follow-up for P6 Global/Resource/Project type semantics, CRUD, Copy/Replace, standard/detailed work-hour operations, HolidayOrExceptions and API-level regression coverage.

A prior calendar-version snapshot immutability change was incorporated into the current line of development; comparison against its earlier PR shows the current main contains the calendar master/snapshot/exception changes while continuing to diverge with subsequent UI and audit work. No stale PR is being treated as the integration baseline.

## K. Calendar resolver / P6 parity recheck — current main `5f1cd188839a1255aaf754b8676dfb4d0711ac47`

Fresh source inspection confirms the Shared Core calendar boundary is structurally sound but not yet full P6 Calendar parity:

- `calendar_resolution.py` resolves version-pinned project and activity calendars before scheduling and rejects missing/mismatched resolver registrations.
- `CalendarReference` preserves calendar id/version, working-day vs working-time kind, and Gregorian/Jalali system identity.
- Relationship lag resolution is centralized in Shared Core and supports predecessor, successor, project-default and 24-hour choices.
- `AuthoritativeScheduleInput` carries immutable project-calendar and activity-calendar assignments and includes them in the canonical snapshot hash, supporting deterministic replay.
- **Remaining gap:** the authoritative schedule contract currently models activity-calendar assignments, but not a first-class resource-calendar assignment/resolution path. Global → Project → Resource inheritance/override precedence is therefore not yet fully materialized into the CPM calendar provider.
- The legacy `resources/calendar.py::ResourceCalendar` remains intentionally outside the authoritative resolver and must not be expanded into a second calendar engine.

This finding reinforces Issue #1209 and Issue #1207: implement explicit Global/Project/Resource semantics and effective-rule precedence in the Shared Core/API boundary, with RESET_TO_STANDARD distinct from absence of a local record. Web/Desktop/Mobile must continue consuming the resulting shared resolver rather than reproducing precedence locally.

### Field Registry / Formula authority recheck

The repository now has canonical `p6_field_registry.py`, `p6_field_registry_api.py`, `p6_formula_engine.py`, and `p6_formula_authority_api.py` boundaries. The formula engine implements the required tokenizer/parser/AST/dependency/type-analysis direction, while the API delegates validation to that Shared Core authority. However, `P6_FIELD_REGISTRY_STATUS` is still explicitly `seeded_not_certified`, so full P6 field disposition/parity remains incomplete by design. This is consistent with the parity baseline and must not be reported as complete.

### Exact-head verification status

For `5f1cd188839a1255aaf754b8676dfb4d0711ac47`, the connected GitHub status interface currently returns no combined status entries and no workflow runs for that SHA. Therefore exact-head runtime verification remains **unverified**; no green-CI claim is made.

**Audited implementation baseline:** `5f1cd188839a1255aaf754b8676dfb4d0711ac47`.

**Current `main` after this audit documentation commit:** this documentation commit is now the latest integration head.

## L. P6 Field / Column / Formula cross-platform recheck

The Shared Core contains the canonical field registry, layout definition API/repository, formula authority, typed formula engine and dependency graph. The Web adapter consumes these contracts and does not implement a local parser or scheduler.

A new cross-platform gap is recorded in Issue #1226: Desktop and Mobile currently expose project/sync/scheduling boundaries but do not yet expose equivalent P6 Field Registry + Column/Layout + Formula Authority consumption contracts. This means scheduling architecture is correctly shared, but full three-platform P6 presentation/formula parity is not yet demonstrated.

The empty `apps/web/src/p6-formula-api.ts` file is also recorded as a cleanup/documentation seam: it should not become a second transport or formula implementation. Any future implementation must consolidate on the existing versioned API/authority boundary.

No calculation engine was duplicated. P6 registry certification remains blocked while the canonical registry status is `seeded_not_certified`.


## M. P6 interchange / typed mapping recheck

Fresh recheck on current main `530df3dceb3ced165070af43a581784cf5738197` verified a coherent interchange boundary: XER project/resource-only/role-only, Primavera XML, XLS/XLSX, Microsoft Project XML and MPX codecs exist; `P6InterchangeMapper` preserves unknown/unsupported fields or rejects them rather than silently dropping them; and dedicated codec/typed-value round-trip tests exist.

The remaining parity gap is integration rather than absence of a typed contract. `P6InterchangeTypedValue` validates typed values independently, but the normal codec -> mapper -> canonical-field path still carries raw values. Mapping definitions retain source/canonical type metadata but do not yet enforce conversion against the canonical P6 field registry. Consequently the current typed-value tests do not by themselves prove real-file preservation of dates/timezones, duration units, Decimal precision, enums, codes/UDFs, calendars, baselines, relationships, resources/rates or financial-period data.

Issue #1227 records the required follow-up: connect interchange mappings to the canonical P6 field/type registry, enforce conversion at the shared interchange boundary, add representative independent typed round-trip fixtures, and explicitly map/classify the remaining P6 subject areas. This must not create a second field registry, conversion engine or scheduling engine.

**Interchange audit verdict:** architecture = sound foundation; P6 interoperability parity = partial and not yet certifiable. The no-silent-drop invariant is implemented at the interchange boundary, but complete P6 typed mapping coverage remains unverified.


## N. CPM relationship / constraint / Data Date / OOS recheck — current main 9da4be61981f87a8584641c1266e58592411fd37

Fresh source-and-test inspection of the scheduling core confirms that the reviewed CPM semantics are implemented in Shared Core and are covered by deterministic regression tests:

- RelationshipType implements FS/SS/FF/SF; working-day lag supports positive and negative values; relationship arithmetic is centralized and the forward-pass tests cover all four relationship types, lag signs, holidays, deterministic input ordering and cycle rejection.
- ActivityConstraint implements Start/Finish No Earlier Than, Start/Finish No Later Than, Mandatory Start and Mandatory Finish. Secondary P6 constraint values are represented explicitly; supported executable secondary values map into the existing primary constraint types, while documented-but-non-executable values are rejected rather than silently approximated.
- Constraint handling distinguishes early-date lower-bound semantics from late-date constraints, preserving P6-style float behavior. Regression tests cover conflicting windows, mandatory conflicts, relationship propagation, holidays, negative float and constrained ALAP behavior.
- Out-of-sequence scheduling is an explicit Shared Core policy with RETAINED_LOGIC, PROGRESS_OVERRIDE and ACTUAL_DATES. The policy preserves actual dates/remaining work and changes only how predecessor logic constrains progressed work. Regression tests exercise the four relationship types across the three OOS modes.
- Data Date is not merely a UI field: it participates in progressed-activity/OOS validation, SS lag calculation when actual progress changes the anchor, and the separate P6-style remaining-work-as-of-data-date calculation. This is correctly separated from explicit Remaining Duration, which remains authoritative.
- Relationship lag calendar selection is centralized through RelationshipLagCalendar and CalendarResolverRegistry, including predecessor, successor, project-default and 24-hour choices. No client-side lag arithmetic was found in the reviewed scheduling boundary.

### Important parity limitation

The reviewed scheduler is a strong CPM implementation, but P6 certification is still not justified. The typed ScheduleOptions surface contains several options whose calculation behavior is deliberately rejected by _validate_supported_schedule_options when enabled (for example resource-cost recalculation, external-project relationship handling, some leveling modes and scheduled-date preservation). This is preferable to silently ignoring an option, but it means the field/option contract is broader than the currently executable scheduler capability.

A second integration gap remains: the reviewed Relationship, ActivityConstraint, OOS policy and ScheduleOptions objects are authoritative Shared Core contracts, but this audit has not yet proven one-to-one mapping of every corresponding P6 field/option through the canonical Field Registry -> API -> Web/Desktop/Mobile -> interchange path. That traceability remains part of the existing P6 parity work and must be completed without duplicating the calculation engine.

CPM audit verdict: relationship arithmetic, constraints, OOS policy and Data Date support are real Shared Core behavior with regression evidence; full P6 option/field/interchange certification remains partial.

## O. Current-main integration status after UI merge

The current repository head is 9da4be61981f87a8584641c1266e58592411fd37, merge commit for PR #1225 (feat(cubi): professionalize responsive layout on exact current main). The UI work is presentation-only in the reviewed diff: responsive layout, typography, chart containers, print rules and navigation geometry. No Shared Core scheduling calculation change is present in that merge diff.

Fresh exact-head CI evidence is still not established by the connected status/run interface; therefore this audit continues to classify exact-head runtime verification as unverified, not green.

The current-main rule remains binding: future UI or parity PRs must rebuild/rebase from this head before merge, and no stale PR baseline should be treated as integrated work.


## P. Baseline / Resource-Assignment / Cost-EVM / Financial-Period traceability recheck — current main 78f6d157fcd1585f92b14577209094596ed03964

Fresh repository inspection on the actual current `main` confirms that these P6 persistence boundaries exist and are separated from Shared Core calculation semantics:

- **Baseline:** `p6_baseline_repository.py` + `p6_baseline_api.py` provide tenant/project/revision-scoped immutable baseline metadata for PRIMARY/SECONDARY/TERTIARY/USER_SELECTED, with SQLite/PostgreSQL persistence, transaction ownership and API authorization. The architecture document explicitly limits this slice to metadata/provenance; baseline activity date/unit/cost comparison, selection behavior and variance calculation remain open Shared-Core semantics.
- **Important baseline parity gap:** the repository already contains typed read-evidence for 11 primary, 11 secondary and 11 tertiary activity baseline fields, and those fields are seeded in the Field Registry, but the current baseline persistence model does **not** persist an activity-level baseline snapshot/value set. Therefore the existence of the metadata API must not be counted as full P6 baseline functionality. Writable/default/nullability/import-export and stored-vs-computed certification also remain open in the evidence artifacts.
- **Resource assignment:** `p6_resource_assignment_repository.py` persists assignment identity, activity/resource/role references, units, actual/remaining units, cost snapshots, unit/currency, calendar reference and deterministic period buckets. Decimal values are preserved without float conversion. This is correctly a persistence boundary and does not duplicate resource/calendar/leveling/scheduling calculation.
- **Resource-calendar parity gap:** the authoritative scheduling model carries activity calendar assignments, but a complete first-class resource-calendar precedence/assignment path is still not demonstrated. The legacy `resources/calendar.py` must remain outside the authoritative engine and must not be extended into a second calendar implementation.
- **Cost accounts:** `p6_cost_account_repository.py` provides immutable hierarchical cost-account definitions with SQLite/PostgreSQL parity. It deliberately does not calculate costs or assign cost accounts to activities/resources; those remain follow-up integration semantics.
- **Financial periods:** `p6_financial_period_repository.py` + `p6_financial_period_api.py` provide scoped immutable period metadata and OPEN/CLOSED state, with SQLite/PostgreSQL parity. They do not yet constitute financial-period value calculation, EVM periodization or complete import/export semantics.
- **EVM:** the repository has real Shared-Core earned-schedule/EVM-related calculation surfaces, while `resources/evm_bridge.py` is a small resource-to-EVM adapter. It must remain an adapter and must not become a second EVM authority. End-to-end traceability from canonical P6 cost/resource/financial-period fields through the Field Registry, API, persistence, all three clients and interchange is still incomplete.
- **Three-platform consumption:** the current Web/Desktop/Mobile app trees do not contain dedicated baseline/resource/cost/financial-period feature modules. This is not proof that generic project/sync contracts cannot carry these values, but it means dedicated cross-platform P6 consumption parity for these subject areas is not yet demonstrated. The existing Shared Core/API boundaries must remain authoritative; clients must not invent local calculation semantics.

### P6 field-registry finding

The canonical Field Registry contains the seeded Baseline1/2/3 activity fields, but the registry status remains `seeded_not_certified`. The typed evidence artifacts explicitly state that they certify read-side type/semantic evidence only and do not certify writable behavior, defaults, nullability, import/export or stored-vs-computed behavior. This is the correct conservative state and must not be upgraded without independent evidence.

### Audit verdict for this tranche

**Baseline:** persistence foundation = present; full P6 baseline semantics = **partial**.

**Resource/Assignment:** persistence foundation = present; full resource/calendar/rate/leveling/client parity = **partial**.

**Cost/EVM:** Shared-Core calculation foundations = present; canonical field/API/persistence/interchange/client traceability = **partial**.

**Financial Period:** metadata persistence/API = present; full P6 financial-period calculation/interchange/client parity = **partial**.

No second scheduling, calendar, formula or EVM calculation engine should be introduced to close these gaps.

### Current-main authority note

The repository branch endpoint currently identifies `78f6d157fcd1585f92b14577209094596ed03964` as the authoritative `main` head. Earlier sections of this document intentionally preserve historical audit checkpoints and their SHAs; they are not substitutes for this current-head value.


## Q. Canonical P6 Registry traceability — baseline/resource/cost/financial-period recheck

Direct inspection of the current Field Registry seed exposes two concrete cross-contract mismatches that prevent claiming canonical P6 parity:

1. **Financial Period contract mismatch:** `p6_financial_period_api.py` and `shared/contracts/p6-financial-period-api.v1.schema.json` expose `period_id`, `name`, `start_date`, `end_date`, and `status`. The canonical Field Registry currently contains only three Financial Period fields: `FinancialPeriodName`, `ActualThisPeriodCost`, and `ActualThisPeriodUnits`; it has no canonical registry fields for `start_date`, `end_date`, or `status`. This breaks the intended Registry → API trace for the contract itself.

2. **Cost Account registry gap:** `p6_cost_account_repository.py` and its persistence contract define a P6 Cost Account subject, but the canonical Field Registry contains **zero** Cost Account rows. Therefore Cost Account persistence exists, but its fields cannot yet participate in the authoritative Field → Registry → Layout/Formula → API → Interchange trace.

3. **Baseline representation remains split:** the Registry contains three generic Baseline selector fields (`PrimaryBaseline`, `SecondaryBaseline`, `TertiaryBaseline`) plus Activity baseline fields, while the baseline persistence boundary stores only baseline metadata/provenance. There is no demonstrated canonical activity-baseline value repository joining the persisted baseline identity to the per-activity baseline values described by the typed evidence artifacts.

4. **Resource/Assignment is grouped, not fully modeled as independent subject areas:** the Registry has 14 rows under `Resource/Assignment`, covering resource identity and a subset of assignment values. It does not establish a complete independent P6 field disposition for all Resource, Assignment, Role, rate, calendar and time-phased semantics represented elsewhere in contracts/repositories.

These are confirmed schema/registry facts, not inferred absences from code search. They should be resolved by extending the single canonical Registry and its mapping/contract validation, not by adding client-local catalogs.


## R. P6 subject-area/API layer recheck — current main

A direct repository-tree and source inspection of the remaining P6 subject areas confirms the following:

- **Relationships:** `relationship_master_repository.py` is an authoritative persistence boundary and stores FS/SS/FF/SF, signed Decimal lag, lag unit and optimistic record revision. The Shared Scheduling Core remains authoritative for relationship arithmetic. However, the current `src/construction_pm/p6_*_api.py` set contains no dedicated P6 Relationship API. The generic scheduling model therefore has persistence + calculation, but a complete versioned P6 transport contract is not yet demonstrated.
- **Roles:** the repository tree contains no dedicated P6 Role persistence/API boundary. Resource Assignment can store an optional `role_id`, and an XER role-only codec exists, but no canonical Role subject/field set or persistence contract was found. This is a concrete P6 parity gap, not a reason to duplicate role logic in clients.
- **UDF definitions:** P6 UDF definition persistence exists and `P6FieldRegistryAPI` exposes definition CRUD. Typed UDF value persistence also exists and validates DATE/DATETIME/Decimal/Percentage/Enum/Duration semantics. However, there is no dedicated P6 UDF-value API file in the current API surface. The Web client has only an authenticated metadata fetch for Activity UDF definitions. Thus end-to-end typed UDF value transport across all three clients is not demonstrated.
- **Expenses:** P6 Expense persistence exists with Decimal cost fields, Activity/WBS links and SQLite/PostgreSQL parity, but no dedicated `p6_expense_api.py` appears in the current API tree. Therefore persistence is present while an application/transport contract is incomplete.
- **Codes:** Code definition + assignment repositories and versioned APIs do exist. This is a stronger subject area than the previous gaps, but the canonical Registry currently exposes only two Codes fields while the code persistence contract also models scope, values, owners and assignments. Full field-level P6 mapping/interchange certification remains incomplete.
- **Activity Period Actuals / Financial Periods:** a dedicated `p6_activity_period_actual_api.py` exists, which correctly provides the activity-period actual transport boundary. This is evidence of a usable working-data layer, but it does not remove the previously identified Financial Period Registry mismatch or prove full P6 financial-period interoperability.
- **Documents / Issues / Risks / Notices / Work Products:** construction-specific document and field-issue product surfaces exist in Web/P0 contracts, but the canonical P6 Field Registry has no independent subject-area rows for Document, Issue, Risk, Notice or Work Product. Therefore product functionality must not be confused with P6 subject-area parity.

### Subject-area conclusion

The repository has substantial real P6 persistence/API foundations, but the architecture is currently uneven by subject area: Activities are heavily represented in the canonical Registry, while Relationships, Roles, UDF values, Cost Accounts, and P6 working-data/document-control subject areas are not yet represented with a uniform canonical Field → API → Persistence → Client → Interchange contract.

This reinforces Issue #389 as the umbrella P6 parity backlog and Issue #1227 for the interchange/type-validation integration. No new local client engine should be introduced to compensate for these gaps.


## S. P6 Field Registry quantitative coverage check — current main

A direct parse of the current canonical seed confirms **366 Registry rows** across these subject areas:

- Activity: 284
- ScheduleOptions: 33
- Project: 8
- WBS: 7
- Activity Step: 7
- Expense: 5
- Baseline: 3
- Financial Period: 3
- Resource/Assignment: 14
- Codes: 2

The current reference artifact `P6_ACTIVITY_FIELD_INVENTORY_2026-09-28.json` contains 275 Activity fields, and a direct name comparison confirms **275/275 are represented in the current Registry**. The Registry has additional Activity fields beyond that inventory, which is not itself a defect.

The material completeness problem is therefore not “the Activity catalog is absent.” It is that the Registry does not yet expose the required P6 subject areas as a uniform canonical model. The parity baseline explicitly calls for Relationships, Activity Resource Assignments, Resources, Roles, Cost Accounts, Work Products & Documents, Issues/Risks/Notices and User Defined Fields, while the current Registry lacks independent subject areas for those surfaces. Resource and Assignment are currently combined as `Resource/Assignment`, and Projects/EPS is represented as `Project`; these combinations must be deliberately dispositioned rather than assumed equivalent.

Most importantly, the global Registry status remains `seeded_not_certified`. The presence of 366 rows or complete Activity-name coverage must not be interpreted as P6 parity certification. Each applicable field still requires an evidence-backed disposition for identity, type, unit, writable/read-only, computed/stored, defaults/nullability, API/client context and import/export behavior.

**Quantitative audit verdict:** Activity-name coverage = strong evidence; subject-area parity = partial; certification = not complete.


## T. HTTP wiring recheck — current main

Direct inspection of `src/construction_pm/http/project_lifecycle_routes.py` shows that the Web HTTP boundary currently wires Field Registry, Layout, Formula Authority, Calendar read, Baseline, Financial Period, Mapping, Interchange, Resource read/write/spread and Code APIs. This is positive evidence that several P6 boundaries are not merely dead Python classes.

However, the current HTTP route constructor/import surface does **not** wire:
- `P6ActivityPeriodActualAPI`;
- a P6 Relationship API (none exists as a dedicated API file);
- a P6 Cost Account API (none exists as a dedicated API file);
- a P6 Expense API (none exists as a dedicated API file);
- a dedicated P6 UDF-value API (definition CRUD is wired through Field Registry API, value persistence is not exposed through an equivalent transport boundary);
- a full write-capable P6 Calendar API (only the read adapter is currently injected; this remains consistent with Issue #1209).

Therefore the current Web HTTP layer demonstrates partial P6 product wiring, not complete P6 subject-area transport parity. The generic sync system must not be counted as proof of P6 typed endpoint parity unless each subject's canonical contract, validation, persistence and client behavior are independently demonstrated.

The route file also currently contains a duplicated import of `P6UserDefinedFieldDefinition`. This is a small hygiene issue only; it has no evidence of affecting runtime behavior and is not being treated as a material product defect in this audit.


## U. Cross-platform offline mutation durability / P6 replay recheck — current main

Fresh inspection of the shared client-sync layer and all three platform runtimes found a material distinction between **conflict-safe synchronization** and **durable offline mutation storage**:

- `apps/client-sync/src/mutation-queue.ts` implements an in-memory `OfflineMutationQueue`. It correctly validates mutation contract/version, project identity, expected revision, idempotency reuse and authoritative stale-revision retry.
- Web `WebSyncRuntime`, Desktop `DesktopRuntime` and Mobile `MobileRuntime` each instantiate this in-memory queue directly. Their tests verify same-process enqueue/sync/conflict/retry behavior, but no restart/persistence restoration is exercised.
- The Python server/shared layer contains persistent/offline queue primitives (`SQLiteOfflineMutationQueue`, PostgreSQL sync state/idempotency persistence), but the current Web/Desktop/Mobile runtime wiring shown in the repository does not demonstrate a durable client-side queue adapter being used by those three runtimes.
- Consequently, **offline scheduling calculation itself is present for Mobile through Shared Core**, and workspace cache/stale-state behavior is tested, but **offline mutation durability across application/browser restart is not proven**. A queued P6 mutation may be lost when the runtime instance is recreated unless an external persistence layer exists outside the inspected runtime boundary.
- The generic `operation + payload` sync contract is intentionally transport-neutral, which is good architecture, but it is not by itself evidence of P6 typed domain mutation parity. P6 operations need canonical contract validation at the application boundary before being counted as complete three-platform P6 functionality.

### Severity / confidence

**Medium severity, high confidence:** this does not invalidate the Shared Scheduling Core or server-side idempotency design, but it prevents claiming full offline-first mutation durability for Web/Desktop/Mobile from the inspected runtime wiring.

**Required architectural direction:** use one durable client-sync persistence adapter behind the existing shared queue interface, and keep P6 mutation typing/validation at the Shared Core/application boundary. Do not create separate P6 sync engines per platform.


## V. Sync envelope contract fragmentation recheck — current main

Direct inspection found three overlapping mutation envelope schemas in the current repository:

- `offline-mutation.v1` in `docs/contracts/offline_mutation_v1.schema.json` / `offline_mutation_queue_v1.schema.json`, using nested `context` + `mutation` and nullable expected revision.
- `client-sync.v1` in `docs/contracts/client_sync_mutation_v1.schema.json`, also using nested `context` + `mutation`.
- `sync-mutation.v1` in `shared/contracts/sync-mutation.schema.json` and the active TypeScript `apps/client-sync/src/mutation-queue.ts`, using flat tenant/project identity, explicit `mutation_id` and `payload`.

The current Web/Desktop/Mobile runtime code uses the latter `sync-mutation.v1` contract. The older nested contracts and Python `OfflineMutation` model remain in the repository, creating a potential source of ambiguity for future implementers and import/sync adapters.

This is currently classified as **low-to-medium architectural hygiene risk, high confidence**, not as a demonstrated runtime defect. The correct remediation is a documented canonical contract + explicit legacy compatibility/migration policy, followed by removal or isolation of obsolete envelopes only after consumer evidence is established. Do not maintain multiple semantically equivalent sync engines or silently translate between envelopes without versioned contracts and lossless mapping tests.


## W. Resource/Cost legacy-module authority recheck — current main

A direct source inspection uncovered a concrete duplicate-calendar authority risk:

- `src/construction_pm/resources/calendar.py` defines a simplified `ResourceCalendar` (weekday set + fixed daily capacity).
- `src/construction_pm/scheduling/calendar.py` defines the Shared Core `WorkingCalendar` / `WorkingTimeResolver` authority with holidays, Jalali/Gregorian system identity, period factors and working-time semantics.
- Despite the earlier audit instruction not to promote the legacy seam, `src/construction_pm/p6_resource_capacity_contract.py` currently imports **`resources.calendar.ResourceCalendar` directly** and uses its `capacity_on()` method to build P6 resource-capacity slices.
- `src/construction_pm/resources/leveling.py` also imports the same legacy ResourceCalendar and `resources/__init__.py` exports its leveling functions publicly.

This means the resource-leveling capacity path is not yet cleanly connected to the authoritative versioned P6 CalendarMaster / Shared Scheduling calendar model. It also means a simplified weekday/fixed-capacity calendar can influence a P6 resource-capacity boundary independently of the richer Shared Calendar semantics.

**Severity: High architectural risk, high confidence.** This is not proof that current CPM activity scheduling is numerically wrong, but it violates the intended single-authority calendar boundary and can produce semantic divergence for resource capacity when holidays, time-of-day intervals, calendar inheritance, versions or Jalali/Gregorian behavior matter.

**Required direction:** route resource-capacity resolution through the authoritative Shared/P6 Calendar resolver and versioned Resource Calendar semantics. Retire the legacy `resources.calendar.ResourceCalendar` seam after consumers are migrated and regression evidence exists. Do not extend the legacy class or add another resource-calendar engine.

Existing issues #1209 and #1207 already cover the broader P6 calendar parity/inheritance work; this finding should be addressed within those boundaries rather than as a new parallel calendar subsystem.


## X. Resource / Rate / Cost authority recheck — current main

Fresh source inspection of `src/construction_pm/resources/` versus the P6 resource APIs found an important boundary mismatch:

- The `resources/models.py` + `resources/calculator.py` path contains the richer Resource, ResourceRate, ResourceAssignment and cost-control calculation model. `resources/control.py`, `performance.py` and related curves consume it, and these functions are publicly exported through `resources/__init__.py`.
- Separately, the P6 persistence/API path uses `P6ResourceAssignment` in `p6_resource_assignment_repository.py`, with `p6_resource_read_api.py` and `p6_resource_write_api.py`. The current P6 write API is focused on time-phased assignment-period values; it does not expose a complete create/update API for the underlying P6 Resource + Rate definition.
- Therefore the repository currently has **two resource data boundaries**: a legacy/richer domain resource model that performs cost calculations, and a P6 persistence model that stores assignment snapshots. They are not yet demonstrated as one canonical Resource/Rate contract.
- `ResourceEVMBridge` correctly derives ETC/EAC/VAC/CV/SV as an adapter and does not replace the central EVM engine. This is architecturally acceptable, but the bridge currently consumes values from the legacy resource-control model rather than a proven canonical P6 Resource/Assignment + financial-period data flow.
- The current P6 Field Registry has 7 Resource-related fields mixed into the combined `Resource/Assignment` subject and no independent Role or Cost Account subject. This prevents complete field-level traceability for resource rates, rate effective dates, calendars and role hierarchy.

### Authority verdict

**Cost calculator itself:** a real deterministic domain calculation, not proven dead code; it must not be duplicated by a second P6 cost engine.

**P6 Resource/Rate parity:** partial. The canonical integration from Resource definition/rates → assignment → calendar → cost → EVM → API → clients → interchange is not yet demonstrated.

**Required direction:** converge the richer resource/rate semantics and P6 persistence/API on one canonical Shared Core contract. Reuse existing calculations where appropriate; do not create a separate P6 calculator. Then expose the same canonical contract through Web/Desktop/Mobile and interchange.

Existing P6 backlog #389 / ownership track #393 already covers this family of work, so no duplicate issue is required.


## Y. EVM authority recheck — current main

Fresh current-main tree inspection searched the complete repository for the EVM/earned-value implementation surface. The evidence found is:

- `src/construction_pm/scheduling/earned_schedule.py` — real Shared Core Earned Schedule / SPI(t) / SV(t) calculation and reconciliation.
- `src/construction_pm/resources/evm_bridge.py` — Resource-to-EVM adapter deriving ETC/EAC/VAC/CV/SV from supplied PV/EV/AC/resource-remaining-cost inputs.
- P6 Activity typed semantic evidence artifacts for cost/EVM, actual cost/units, earned value/remaining and schedule performance/variance.
- `src/construction_pm/p6_activity_read_model.py` + `p6_activity_read_model_api.py` provide a read-only Activity Cost/Actual/Baseline aggregation boundary. Its implementation explicitly sets `evm.status = "unavailable"` until an authoritative computed Shared-Core EVM-result contract exists.
- No distinct current-main canonical EVM calculation module/API was identified for the full PV/EV/AC/BAC/ETC/EAC/CV/SV/SPI/SPI(t) lifecycle. The resource bridge is only an adapter and the Activity read model is only a stored-value/read boundary.
- The current HTTP route tree does not wire `P6ActivityReadModelAPI`, so even the read-model boundary is not demonstrated as a public Web route on current main.

The existing resource bridge is correctly designed as an adapter and its simple arithmetic is not a substitute for a complete project/WBS/activity EVM authority. Therefore the current repository evidence is insufficient to certify the previously intended full Progress/EVM/Schedule Performance engine as complete on current main.

### EVM verdict

Earned Schedule: implemented Shared Core behavior with deterministic tests.

Resource EVM bridge: implemented adapter, not the central EVM engine.

Full P6-compatible EVM authority and end-to-end API/client/interchange path: not demonstrated on current main; treat as a parity gap until a canonical implementation/evidence chain is found or restored.

No new EVM engine should be invented merely to satisfy this audit. The correct next action is to reconcile the intended EVM baseline against the actual current-main history/commits and, where necessary, restore or complete one canonical Shared Core implementation with regression evidence.


## Z. Resource cost/rate and time-phasing integrity — current main

Fresh code-level inspection adds the following concrete findings to the resource/cost audit:

- `resources/calculator.py::calculate_cost()` has a `hours_per_day` parameter but does not use it. `PER_UNIT`, `PER_HOUR`, and `PER_DAY` currently all execute `units * rate`. Therefore the declared rate basis is not yet semantically differentiated.
- `ResourceRate.is_effective_on()` allows overlapping validity windows, and `Resource.rate_on()` resolves an overlap by selecting the highest version. There is no explicit rate-interval conflict validation in `validate_resource()`.
- `validate_resource()` checks only negative rates; finite-value validation for Decimal rate inputs is not established at this boundary.
- `resources/loading.py::spread_units()` distributes planned units uniformly across every calendar date in the interval. It does not consult either the authoritative P6 CalendarMaster resolver or `WorkingTimeResolver`, so weekends/holidays can receive resource units and cost.
- `resources/capacity.py` and `resources/leveling.py` also directly consume the simplified `resources.calendar.ResourceCalendar`; the Shared Core scheduler uses the richer `WorkingCalendar`/`WorkingTimeResolver`. This reinforces the previously documented duplicate-calendar authority risk.
- Resource rates are genuinely persisted in `resources/persistence.py`, including basis, currency, effective dates and version, so this is not a missing-data problem. The remaining risk is semantic correctness and convergence with the canonical P6 resource/rate/calendar contract.
- Current tests cover basic effective-rate selection and total-preserving spread, but do not establish PER_DAY vs PER_HOUR semantics, rate-window conflict policy, working-calendar-aware spread, or cross-boundary equivalence with the P6 Resource/Assignment model.

### Severity

**High architectural/correctness risk, high confidence** for calendar-aware time-phased cost/resource calculations.

**Medium correctness/parity risk, high confidence** for rate-basis and effective-date semantics.

### Required disposition

Preserve `resources/calculator.py` as reusable domain logic where its semantics are valid, but bring rate basis, effective-date rules, and time-phased allocation under the canonical Shared Core/P6 Resource + Calendar contract. Do not create another cost calculator or another calendar implementation. Regression tests must prove the canonical result is identical across Web/Desktop/Mobile and import/export paths.


## AA. Cost Account / Expense / Financial Period integration — current main

Fresh current-main inspection of the persistence, API, HTTP wiring and Field Registry shows a second-level cost-integrity gap:

- `P6CostAccount` has SQLite/Postgres persistence and an application service, but no dedicated P6 Cost Account API or HTTP route was found. The registry has **zero** independent Cost Account rows.
- `P6Expense` has SQLite/Postgres persistence and an application service, but no dedicated `p6_expense_api.py` or HTTP route was found. The Activity Read Model can read expenses, but it is a read adapter rather than an Expense transport boundary.
- The Expense model stores `activity_id`, `wbs_id`, `expense_date`, currency and planned/actual/remaining cost, while the Field Registry independently registers only five Expense fields (`name`, `category`, planned/actual/remaining cost). This leaves important Expense identity/context semantics without canonical registry traceability.
- `P6FinancialPeriod` has a typed API and is wired into `project_lifecycle_routes.py`. However the Field Registry currently contains only three Financial Period fields (`name`, actual cost, actual units), while the API/domain contract contains `period_id`, `name`, `start_date`, `end_date`, and `status`. Start/end date ordering validation is also not established at the repository model boundary.
- `P6ActivityPeriodActual` has persistence and a typed API, but the HTTP route tree inspected does not wire that API. It carries `period_id`, so actuals have an explicit period link; Expense currently does not, which makes Financial Period attribution of expenses incomplete at the domain contract level.

### Cost/EVM impact

These components currently exist mostly as isolated typed persistence/read boundaries. They are not yet proven as one canonical chain:

`Cost Account / Expense / Financial Period → Activity Cost Inputs → Shared-Core EVM → P6 Field Registry → HTTP API → Web/Desktop/Mobile → Import/Export`.

This is **Medium-to-High architectural/parity risk, high confidence**. It does not imply existing stored values are numerically wrong; it means the end-to-end authoritative calculation and transport chain is incomplete/provisionally disconnected.

### Required disposition

Keep these persistence implementations; do not replace them with duplicate stores. Complete canonical Field Registry identities and API/HTTP wiring, add explicit Financial Period/Expense relationship semantics, and connect them to one Shared-Core EVM result contract. Preserve the separation between stored inputs and computed results.


## AB. Relationship authority / P6 registry seam — current main

Fresh current-main inspection of relationship persistence versus the Shared Core scheduler found:

- `relationship_master_repository.py` is a real authoritative persistence boundary for predecessor/successor relationships and stores `relationship_type`, signed `Decimal lag_value`, `DurationUnit lag_unit` and record revision.
- The Shared Core scheduler model in `scheduling/relationships.py` represents lag as an `int` and documents it as working-day lag. There is no inspected canonical adapter that proves lossless conversion from `LagQuantity` / `DurationUnit` into scheduler semantics for all supported P6 lag units.
- No dedicated Relationship API or HTTP route was found in the current source tree. Thus relationship persistence is present, but the end-to-end P6 transport path is not demonstrated.
- The Field Registry currently has no independent Relationship subject rows; only ScheduleOptions for relationship-lag-calendar and external-project handling are registered. This leaves relationship identity, endpoints, type, lag value and lag unit without independent registry traceability.
- No Role domain/persistence/API subject was found in the current source tree. `role_id` and `primary_role` appear as fields on adjacent resource/assignment structures, but this is not equivalent to a canonical P6 Role subject model.

### Verdict

**High parity/integration risk, high confidence** for Relationships because persistence and scheduling representations use different lag types/units without a proven canonical conversion/API chain.

**Medium parity risk, high confidence** for Roles because the independent P6 subject area is not represented as a canonical domain/API/registry surface.

Required direction: make one canonical Relationship/Lag contract shared by persistence, scheduling, API and interchange, preserving signed lag and explicit duration-unit semantics. Add independent Registry subject definitions and a Role domain boundary before declaring these P6 areas complete. Do not modify CPM arithmetic merely to hide the transport gap.


## AC. Document / RFI / Submittal versus UDF transport integrity — current main

Current-main subject-area inspection shows a useful contrast:

- Document/RFI/Submittal functionality has a real application boundary, Postgres persistence, versioning, idempotency, approval transitions and a `DocumentAPI`. This is a substantially complete transport pattern and should remain an example of the intended application/API separation.
- P6 UDF definitions have persistence and an application service, and typed UDF values have a revision-scoped persistence implementation with strict type validation and encode/decode checks.
- However no dedicated UDF Value API file was found in the current tree, and no independent HTTP route for UDF values was identified. The Web side has an authenticated metadata fetch boundary, but that does not establish full CRUD/transport parity for typed UDF values.
- UDF definitions themselves are scoped to `p6-field-registry.v1`, which is correct for registry coupling, but the value contract still depends on lookup of the definition before persistence. This should remain a single authority rather than be reimplemented by clients.

### Verdict

**Document/RFI/Submittal:** architecture pattern is sound at the inspected boundary; separate P6 field certification is still required where applicable.

**UDF typed values:** Medium parity/integration risk, high confidence because persistence exists without a dedicated transport path. This is not a calculation defect, but it can block full field/edit/export parity.

Required direction: add a typed UDF-value application/API/HTTP boundary over the existing persistence, reuse the Field Registry definition for validation, and expose the same contract to Web/Desktop/Mobile/import-export. Do not implement client-side UDF type engines.


## AD. Three-platform Shared Core consumption parity — current main

Current-main tree inspection shows unequal platform adapter surfaces:

- Mobile contains an explicit `shared-scheduling-adapter.ts` with a versioned scheduling request/result contract and an interface that deliberately contains no scheduling formulas. This is aligned with the single-authority Shared Core rule.
- Desktop currently has no corresponding P6/scheduling adapter source in `apps/desktop/src`; its runtime only handles project/sync/language/workspace concerns. Therefore a Desktop-specific schedule invocation boundary is not yet demonstrated.
- Web currently has concrete P6 Field Registry, Layout, Field Editor and Formula Grid Binding adapters, which is positive for presentation parity, but no dedicated Web scheduling adapter source was found in the current app tree. The authoritative scheduling invocation therefore remains outside these inspected client adapters.
- Mobile and Desktop both instantiate the same in-memory `OfflineMutationQueue`, preserving contract reuse but retaining the previously identified restart-durability gap.

### Verdict

**Medium cross-platform parity risk, high confidence.** The architecture intent is correct (clients should consume contracts, not calculate), but the current repository does not yet demonstrate equal scheduling-consumption boundaries across Web/Desktop/Mobile.

Required direction: define one shared scheduling invocation contract and have Web/Desktop/Mobile consume it through thin adapters. Do not implement a separate scheduler in Desktop or Web. Preserve the Mobile contract only as a migration-compatible adapter if it already maps exactly to the canonical contract.


## AE. Formula Core / Registry / client parity — current main

Fresh inspection of the current `main` formula stack confirms that the calculation architecture itself is healthy:

- `p6_formula_engine.py` implements tokenize → parse/AST → type inference → dependency discovery → deterministic evaluation using typed values and `Decimal`; no dynamic `eval` path was found.
- `p6_formula_authority_api.py` correctly builds its schema from the authoritative P6 Field Registry and delegates parsing/type/dependency semantics to the Shared Formula Core.
- `p6_formula_recalculation.py` only orchestrates dependency-safe recalculation; it does not redefine formula semantics.
- `p6_formula_definition_api.py` provides a versioned persistence/transport boundary for formula definitions and audit history.
- Web `p6-formula-editor.ts` and `p6-formula-grid-binding.ts` consume an injected `P6FormulaAuthority`; they do not calculate formulas locally. This is correct. The empty `apps/web/src/p6-formula-api.ts` is therefore not a second engine and should remain empty unless a thin transport adapter is actually required.

The remaining parity gap is type/surface coverage:

- `P6FormulaFieldAdapter` intentionally maps only the P6 field types that have a safe Formula Core representation. P6 types such as object-id-array, string-array, complex and spread currently reject from the formula schema instead of being silently coerced. This is the correct safety behavior, but it means full P6 formula-type coverage is not certified.
- `apps/web` has mature Formula/Field presentation adapters, while Desktop has no equivalent P6 Formula/Field adapter surface in the current tree and Mobile has no equivalent Formula surface. This supports the already-verified #1226 cross-platform parity gap.
- The Formula authority HTTP route is wired in the backend (`POST /api/projects/.../p6/formulas/...`), but an equivalent common client transport contract for all three platform clients is not yet demonstrated.

### Verdict

**Formula calculation authority:** structurally sound and single-source, high confidence.

**P6 formula type parity:** partial, medium risk.

**Cross-platform Formula/Field consumption parity:** medium-high risk, high confidence; tracked by existing issue #1226.

Required direction: keep the existing Shared Formula Core as the only formula engine; complete safe P6 type mappings where semantics can be certified, otherwise explicitly mark them unsupported; create one shared client transport contract consumed by Web/Desktop/Mobile rather than per-platform formula implementations.


## AF. Interchange typed values versus real canonical mappings — current main

Current-main tests confirm two different layers:

- `P6InterchangeTypedValue` has strong standalone JSON round-trip coverage for Date, timezone-aware DateTime, Decimal, Duration with explicit unit, Boolean, Enum, Integer and String, including fail-closed tests for invalid/coerced values.
- Real codec integration tests for XER and Primavera XML prove parsing + mapping composition, but the mapper currently copies mapped raw Python values directly into canonical fields. `P6MappingDefinition` stores `source_type` and `canonical_type` metadata, but `P6InterchangeMapper` does not enforce conversion against the canonical P6 Field Registry.
- Consequently a date field in a real XER/XML row is not yet proven to arrive at the canonical layer as a typed `date`; a duration/cost/enum has the same certification gap. The typed-value class alone does not establish this end-to-end property.
- Existing issue #1227 is the correct tracking item and already states the required outcome: connect mappings to the canonical Registry, enforce typed conversion at the shared boundary, and add representative round-trip evidence.

### Verdict

**Standalone typed interchange contract:** strong foundation.

**End-to-end typed canonical import/export:** incomplete; **High parity risk, high confidence** for P6 field certification, but not evidence of current data corruption because unsupported mappings are preserved/rejected rather than silently discarded.

Required direction remains exactly #1227; no new conversion engine should be created per codec or per client.


## AG. Baseline authority and comparison semantics — current main

Current-main inspection confirms that Baseline persistence is intentionally conservative but still incomplete for full P6 behavior:

- `P6Baseline` and `P6BaselineAPI` provide scoped, immutable baseline metadata with PRIMARY/SECONDARY/TERTIARY/USER_SELECTED roles and source-revision provenance.
- The architecture document explicitly states that baseline date/unit/cost comparisons, variance calculations, selection semantics and resource/cost/EVM calculations are non-goals of this persistence slice.
- P6 Activity baseline typed evidence exists, but remains `typed_read_evidence_only`; it does not certify writable/default/nullability/import-export semantics.
- No separate baseline snapshot/value repository was found in the inspected current tree that materializes activity/WBS/project baseline values independently of the live project data. Therefore baseline comparison cannot yet be certified as a complete authoritative P6 behavior from current main.
- This is intentionally not counted as a defect in the metadata persistence layer. The gap is that the later Shared Core comparison/selection contract has not been demonstrated end-to-end.

### Verdict

**Baseline metadata persistence:** structurally sound.

**Full baseline value snapshot + comparison + variance semantics:** incomplete / not certified; **High parity risk, high confidence** for P6 baseline completeness.

Required direction: preserve the existing immutable metadata boundary and add one canonical baseline snapshot/comparison contract in Shared Core. Baseline-derived fields exposed through Registry/API/clients/import-export must all consume that same contract; never calculate baseline variance separately in UI or persistence.


## AH. Change/Claim and payment/cash-flow completeness — current main

Current-main inspection distinguishes implemented foundations from product-level gaps:

- `change_claims.py` and `change_claim_api.py` provide a versioned Change/Variation/Notice/Claim domain and API with scope, actor, optimistic revision, idempotency and evidence references.
- The `control_intelligence.change_claim` layer adds explicit schedule/cost impact links and evidence requirements, which is structurally aligned with the construction-controls objective.
- However no direct Change/Claim HTTP route was found in `project_lifecycle_routes.py`; therefore the API is not yet proven as a complete Web transport path.
- The current source tree contains no dedicated Payment, Invoice/AR-AP, Commitment, or Cash Flow domain/API module. This matches the project backlog: issue #77 explicitly identifies commitments/payments/AP/AR and an ERP/accounting integration layer as P0 gaps.
- This should not be misclassified as a scheduler defect. It is a product-completeness gap that becomes important for the promised integrated construction Project Controls / Commercial Controls scope.

### Verdict

**Change/Claim domain:** meaningful foundation exists; HTTP/end-to-end integration remains incomplete.

**Payment / Cash Flow / Commitments:** not demonstrated on current main; **High product-completeness risk, high confidence** relative to the declared release scope.

Required direction: complete the Change/Claim transport path using the existing domain; then implement one canonical Commercial/Financial Controls layer for commitments, invoices/payments, cash flow and ERP interfaces. These modules must consume Shared Core cost/EVM/calendar results and must not create a parallel cost or schedule authority.


## AI. AI / Control Intelligence authority boundary — current main

Current-main inspection confirms a strong architectural boundary for AI-driven controls:

- `ai_action_boundary.py` models AI actions as proposals with explicit tool permission, human approval and audit recording. Approved actions require a human actor when the proposal requires approval.
- `control_intelligence/scenario.py` explicitly forbids a scenario from mutating authoritative project state (`authoritative_mutation_allowed=True` raises). This keeps AI scenario analysis separate from Shared Core calculation/state mutation.
- `control_intelligence/query.py` requires source references for answers, and source revisions must match the current project scope. This is appropriate for traceable AI assistance.
- `control_intelligence/risk_engine.py` consumes already-computed control indicators and explicitly states that it does not calculate CPM/P6 scheduling semantics. It uses a versioned deterministic risk score and revision-safe evidence.

### Verdict

**AI authority boundary:** structurally strong; no evidence found that the inspected AI/control modules replace CPM, Calendar, Formula or EVM calculation authority.

**Remaining product gap:** the inspected tree contains governance/analysis primitives rather than a demonstrated complete production AI assistant pipeline covering retrieval, grounded answers, action proposals, approvals, execution, audit and offline behavior across all three platforms. This is a completeness/integration question, not evidence of a second calculation engine.

Required direction: keep AI downstream of Shared Core authoritative results; expand AI through adapters/tools with source citations, revision checks and human approval for mutations. Never let an LLM recompute or overwrite authoritative P6 results.


## AJ. Persistence context / transaction authority consolidation — current main

Current-main inspection identifies legacy infrastructure that is structurally separate from the newer P6/P0 boundary:

- `resources/context.py` defines `ProjectContext(tenant_id, company_id, project_id)`, while the canonical backend/P6 model uses `BackendScope(tenant_id, project_id, project_revision)`.
- `resources/transactions.py` defines a separate transaction-manager family from `backend_p0/transactions.py`. The backend manager uses unique nested savepoint names; the resource manager uses a fixed savepoint name (`construction_pm_nested`). This is a latent nested-transaction collision risk if multiple nested resource transactions occur on one connection.
- `resources/idempotency.py` also has its own context-scoped mutation idempotency model keyed by tenant/company/project, separate from the newer P6/client-sync idempotency contracts.
- Current tree inspection did not find a dedicated HTTP route that consumes `resources.api.ResourceAPI`; therefore this resource stack appears to be a legacy/internal boundary rather than the public P6 resource transport path. It should not be expanded in parallel.
- The presence of this legacy stack does not by itself change current CPM calculations, but maintaining two context + transaction + idempotency authorities increases integration and maintenance risk.

### Verdict

**Medium architectural hygiene risk, high confidence.** The main concern is not immediate page speed; it is divergent semantics and duplicated infrastructure that can cause future data/concurrency inconsistencies.

Required direction: converge active production paths on the canonical `BackendScope`/application transaction/idempotency contracts. Migrate any still-required `resources/` consumers behind adapters, then retire the legacy duplicate infrastructure only after consumer and regression evidence. Do not silently delete it while consumers remain unknown.

### Dependency revision note

`DependencyLink.revision` and persisted `graph_revision` are intentionally distinct in the current implementation, but their semantic distinction is not self-evident from the public contract. Treat this as a low-confidence documentation/API clarity issue, not as a proven correctness defect, until the intended revision model is explicitly documented or certified.


## AK. Web workspace rerender / interaction performance — current main

Current-main inspection of `apps/web/src/main.ts` and `apps/web/src/workspace-view.ts` confirms the earlier shell-level optimization but reveals a remaining interaction-level cost:

- `main.ts::renderApp()` now preserves the application shell, which avoids rebuilding the outer DOM on every workspace change. This is good and should be retained.
- `workspace-view.ts::renderMainWorkspace()` still assigns a complete `container.innerHTML` for the entire workspace on every menu/WBS/activity/Gantt selection and after each P6 layout edit. This rebuilds the activity table, Gantt, control panels, procurement, field views and navigation surface even when only selection state changed.
- After the full DOM replacement, the renderer executes multiple `querySelectorAll(...).forEach(addEventListener)` passes over the newly-created subtree. This is repeated listener allocation and teardown work on every rerender.
- `createGanttScale()` scans every activity and parses each displayed start/finish date on each rerender; Gantt row geometry is then regenerated for every scheduled activity. This is deterministic and presentation-only, but unnecessarily repeated for selection-only interactions.
- Because the current declared beta scale is modest, this is not evidence of a current production failure. It is a **Medium performance risk, high confidence** as activity counts and richer control panels grow.

### Required optimization boundary

Keep all Shared Core/P6 calculations untouched. Optimize only presentation/state rendering:

1. retain the shell and static panels between interactions;
2. use event delegation on stable workspace containers rather than attaching many per-node listeners after every render;
3. cache Gantt scale/geometry when activity schedule data is unchanged;
4. update only affected selection/highlight/detail regions for selection changes;
5. preserve direct imports in `main.ts`; the barrel exports are not in the boot path and were not shown to cause bundle bloat.

Do not move CPM, Calendar, Formula or EVM calculations into the browser as part of this optimization.


## AL. Time-aware authoritative scheduling wiring — corrected

A concrete parity gap was verified and corrected in current main. `schedule_evaluator.py` previously sent `TIME_AWARE` snapshots only through `time_forward_pass()`, while the Shared Scheduling Core already contained the complete `time_schedule()` orchestration with forward pass, backward pass and time-float reconciliation.

The evaluator now delegates `TIME_AWARE` execution to that existing Shared Core `time_schedule()` implementation and retains `time_activities` as the early-activity compatibility projection while exposing the complete `TimeScheduleResult` through `time_result`. A regression test now certifies that authoritative time-aware evaluation exposes late dates and floats.

This is a wiring correction, not a new engine. The single Shared Scheduling Core remains authoritative.

**Finding status: Corrected in main.** Remaining work is end-to-end API/client projection of the full time-aware result where required; that is a transport/parity task, not a second calculation engine.


## AM. Legacy resource transaction savepoint collision — corrected

A concrete transaction-safety defect was verified in `src/construction_pm/resources/transactions.py`: nested transactions reused the fixed SQLite savepoint name `construction_pm_nested`. The transaction manager now allocates a monotonically unique savepoint name per nesting level, matching the safer pattern already used by `backend_p0`.

A regression test now exercises two nested resource transactions on one connection and verifies the final committed state. This change is infrastructure-only and does not alter P6/CPM/Calendar/Formula/EVM calculations.

**Finding status: Corrected in main.** Executable verification remains unconfirmed because current main has no GitHub workflow runs or commit statuses.


## AN. P6 Calendar multi-repository transaction atomicity — high-risk gap

Current-main inspection confirms a stronger transaction-boundary issue than the earlier legacy savepoint finding.

`P6CalendarAPI` orchestrates multi-step operations such as `copy()` and `replace()`. In the SQLite implementation, several Calendar repositories perform their own `connection.commit()` during mutation: `calendar_master_repository.py`, `calendar_exception_repository.py`, `calendar_snapshot_repository.py`, `calendar_work_hours_repository.py`, and the SQLite activity/relationship-lag calendar assignment repositories. The API itself does not expose one application-owned transaction spanning these writes.

This creates a concrete partial-commit risk. For example, a calendar copy can commit the target `CalendarMaster`, then commit the snapshot, then fail while copying an exception; the database may retain a partially copied calendar instead of rolling back the complete operation. `replace()` can similarly persist the target master before a later snapshot write fails.

This is **High severity, high confidence** for correctness of Calendar administration and recovery. It does not directly alter CPM arithmetic, but it can leave the authoritative calendar definition inconsistent, which can subsequently change scheduling results.

### Required direction

Make transaction ownership application-level for SQLite exactly as documented by the repository architecture: repository mutation methods must participate in the caller's transaction and must not commit/rollback independently. `P6CalendarAPI.copy/replace/delete` should execute their complete multi-repository mutation inside one transaction manager boundary. Initialization/schema setup may retain a separate initialization commit where necessary.

Add failure-injection tests that fail at each step of `copy()`/`replace()` and verify complete rollback, plus successful multi-step atomicity tests. Do not alter Shared Scheduling Core calculations as part of this repair.


## AO. SQLite Calendar schema migration default corruption risk

Current-main `SQLiteCalendarMasterRepository.__init__()` creates the modern table correctly with nullable `base_calendar_id` / `base_calendar_version`, but its compatibility migration adds missing columns using `TEXT NOT NULL DEFAULT 'project'` for all three new columns. For pre-existing databases that lack these inheritance columns, existing calendar rows can therefore be backfilled with `base_calendar_id='project'` and `base_calendar_version='project'` rather than `NULL`.

The model explicitly treats the base-calendar pair as optional; `None/None` represents no inheritance. The current migration default therefore can fabricate an inheritance reference in upgraded databases and change calendar-resolution behavior or make stored state fail later validation. Existing tests cover fresh in-memory schemas and normal round-trips, but no test was found that starts from the legacy schema and exercises the ALTER TABLE migration.

**High severity, high confidence** for upgrade correctness. The risk is conditional on upgrading an older SQLite database, but if triggered it can change the authoritative calendar definition and consequently future scheduling results.

### Required direction

Use nullable defaults for the optional inheritance columns during migration (or a backfill that explicitly establishes `NULL` for existing rows), preserve `calendar_type` default separately, and add a legacy-schema migration regression test that verifies old calendars remain non-inherited unless inheritance was explicitly stored. Migration must be tested before any production database upgrade.


## AP. P6 Calendar API/HTTP write-path exposure — confirmed gap

The source tree contains a substantial `P6CalendarAPI` with create/update/delete/copy/replace, exception and work-hour operations. However, `src/construction_pm/http/project_lifecycle_routes.py` wires only `P6CalendarReadAPI` for the `/api/projects/{project}/p6/calendars` GET catalog and snapshot reads; no `P6CalendarAPI` write dependency is constructed or routed there.

Therefore Calendar persistence and typed API code exist, but the Web HTTP boundary does not yet demonstrate an end-to-end Calendar write path. The same route-tree inspection also found no dedicated HTTP path for Relationship Master, Cost Account, or Expense persistence. This is an integration/completeness gap, not evidence of a missing domain implementation.

**Medium–High severity, high confidence.** For the declared Web-first beta, calendar administration cannot be considered end-to-end complete until the write API is exposed with tenant/project/revision authorization and one transaction boundary. No client-side calendar mutation engine should be introduced to compensate.


## AQ. Cross-client time-scheduling contract fragmentation — confirmed

The repository currently contains two distinct time-scheduling transport contracts:

- `shared/contracts/time-scheduling.schema.json` + `src/construction_pm/client_sync/time_api.py` use `contract_version = "1.0"` and a `calculation_context`-centric payload.
- `apps/mobile/src/shared-scheduling-adapter.ts` uses `MOBILE_SCHEDULING_CONTRACT_VERSION = "time-scheduling-portability.v1"` with a different request/result shape and a mobile-specific API type family.

The mobile contract exposes only a projection of the scheduling result (for example, early start/finish plus total/free float and criticality), while the canonical Shared Core has a richer result surface. More importantly, no equivalent Web/Desktop Scheduling adapter was found in the current tree.

This is **Medium–High architectural/integration risk, high confidence** against the V1 requirement that Web/Desktop/Mobile consume the same versioned API/Application contracts. It is not evidence of duplicate scheduling arithmetic; both designs explicitly delegate calculation authority elsewhere.

Required direction: establish one canonical cross-client scheduling transport contract or an explicitly versioned, lossless compatibility mapping. Web/Desktop/Mobile should each be thin adapters to that contract, with no scheduling formulas or calendar arithmetic locally. Preserve the existing richer Core semantics while defining which result projections each client may render.


## AR. Shared CPM Free-Float search complexity — performance risk

Current-main inspection of `src/construction_pm/scheduling/schedule.py` found a potentially material scheduling-performance bottleneck. `_free_float()` increments delay one working unit at a time up to 10,000 iterations for each outgoing relationship. `_relationship_free_float()` and `_relationship_total_float()` use the same linear 0..10,000 search pattern for relationship-level reconciliation; these functions are also invoked by the Multiple Float Paths algorithm when that option is enabled.

This preserves deterministic semantics but can become expensive on large construction networks or large float windows: relationship processing can approach 10,000 calendar-resolution probes per qualifying relationship, and Multiple Float Paths can repeat those probes across many path selections.

**High performance risk, high confidence** for large projects; no current functional error is proven. The algorithm is not UI-only: it affects Shared Core schedule calculation latency and therefore can affect Web/Desktop/Mobile response time when authoritative scheduling is invoked.

### Required optimization boundary

Replace the linear probe with a semantically equivalent bounded-search strategy (for example, monotonic bracket + binary search) only after independent regression fixtures prove identical Free Float/Total Float results across FS/SS/FF/SF, positive/negative lag, multiple calendars, exceptions, and open-ended activities. Preserve the existing 10,000 guard semantics or explicitly version any changed behavior. Do not approximate or move the calculation into client code.


## AS. Web P6 field-type projection loses semantic subtypes

`apps/web/src/p6-field-layout-foundation.ts` correctly models the full P6 type family, including `percentage`, `cost`, `unit`, `datetime`, `enum`, `object-id`, arrays, `complex` and `spread`. However, `apps/web/src/workspace-model.ts::toWorkspaceColumnDataType()` collapses these into a much smaller view-model type set: `percentage`, `cost` and `unit` all become `decimal`; `date` and `datetime` both become `date`; and object-id/array/complex/spread fall through to `text`.

This is not a calculation-engine duplication and it may be acceptable for a minimal display layer, but it is insufficient for full P6 column/type parity because formatting, filtering, sorting, editing, unit/currency display and semantic validation can depend on the original type. The Registry metadata is therefore richer than the Workspace column contract actually preserves.

**Medium risk, high confidence** for P6 UI parity. Required direction: preserve authoritative P6 `data_type`, unit and allowed-value metadata through the shared presentation model, with specialized rendering/editing behavior layered on top. Do not infer or recalculate business values in the client.


## AT. SQLite nested transaction manager binding — corrected

A follow-up verification of the resource transaction fix found a concrete implementation regression: _SQLiteTransaction.__enter__() referenced self.manager, but the context object did not receive or store the owning SQLiteTransactionManager. Therefore the newly added nested-savepoint regression would fail at runtime instead of exercising savepoint isolation.

Correction applied in commit 2212a3cbe8611484c27cec6b9a45c49943d60584:
- SQLiteTransactionManager.transaction() now passes its manager into _SQLiteTransaction.
- _SQLiteTransaction stores the manager and uses its monotonic savepoint counter.
- Existing nested-transaction test remains the regression boundary.

This is infrastructure-only and does not alter P6/CPM/Calendar/Formula/EVM calculations.

**Finding status: Corrected in main.** Exact-head CI remains unverified because GitHub currently reports no workflow runs for the corrected commit.


## AU. P6 Replace preflight — corrected

Audit of the merged P6 Calendar API found that `replace()` could update the target CalendarMaster first and only then fail in the immutable snapshot repository when the target already had a different snapshot. That created a partial mutation: the master revision/name/kind could change while the target snapshot remained unchanged.

Correction:
- `replace()` now preflights the target snapshot before mutating the CalendarMaster.
- A conflicting existing target snapshot raises `TARGET_CALENDAR_SNAPSHOT_IMMUTABLE_CONFLICT` before any master mutation.
- Regression verifies the target record remains unchanged after rejection.

Commits: `ec3a617ce61d3039a8d061ba81694eb0d658bb96`, `be1e191afa763a539cc88653dc4f1dac039ceb22`.

**Finding status: Corrected in main.** Exact-head CI must still verify the correction.


## AV. Legacy SQLite calendar migration regression — covered

Added a regression test proving that legacy `calendar_master` rows migrated to the current schema keep `base_calendar_id` and `base_calendar_version` as `NULL`, while `calendar_type` receives the intended `project` default. This locks the correction from `fac52509f9db253c2f35ee581cfb43afca0779e8` against future migration regressions.

Test commit: `bce9f92b9f0cb49807f5b11cb71cd35c00f902dc`.

**Finding status: corrected and regression-covered.** Exact-head CI is still absent for the current main commit chain.
