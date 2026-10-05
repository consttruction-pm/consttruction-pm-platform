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
