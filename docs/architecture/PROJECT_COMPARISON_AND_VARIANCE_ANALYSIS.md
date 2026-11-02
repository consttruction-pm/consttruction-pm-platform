# CUBI Project Comparison and Variance Analysis

**Status:** Approved product and architecture requirement; implementation is not certified by this specification.
**Requirement ID:** CMP-01
**Registration baseline:** \`codex/jalal/resource-dependent-core-20261102\` at inspected HEAD \`66072977b9fe893de842d2668ad96157bb8c08af\`.
**Authority:** This specification elaborates Principle 12 in \`PRODUCT_PRINCIPLES.md\`. It is additive to all existing CUBI requirements.

## 1. Purpose

CUBI must provide a first-class Project Comparison and Variance Analysis capability. Users must be able to select two project data sets, compare them deterministically, identify what was added, removed, changed, moved or left unchanged, inspect exact field-level differences, and produce a traceable report.

This capability is broader than comparing the current project with one baseline. It must ultimately support:

1. **Project vs. Baseline:** compare a current project revision or schedule snapshot with a selected saved baseline.
2. **Revision vs. Revision:** compare two saved revisions/snapshots of the same project.
3. **Project vs. Project:** compare two independent projects, including a project imported from a supported exchange file after successful validation and normalization.

The comparison engine is a read-only analysis capability. It does not silently update, merge, overwrite or re-baseline either source project.

## 2. Architectural invariants

- The comparison domain and variance semantics belong to the shared application/domain boundary. Web, Desktop and Mobile are clients of the same versioned comparison contract.
- All schedule-derived values must be obtained from the single authoritative Shared Domain/Calculation Core. Do not implement a second CPM, calendar, resource, cost or EVM engine inside the comparison service or a client.
- A comparison operates on immutable, revision-bound source snapshots. It must not read a mixture of values from different project revisions.
- Each side retains its own source project, revision, baseline identity (when applicable), calculation context and provenance.
- Comparison is deterministic: the same two normalized snapshots, matching map, comparison options and calculation versions produce the same result.
- Comparison never mutates either source. Any future "apply selected changes" operation is a separate, explicitly approved workflow with preview, authorization, revision checks, transactionality, idempotency and audit history.
- Missing, unsupported, ambiguous or incompatible information must be shown explicitly. It must never be silently treated as zero, unchanged, deleted, or equal.
- A project comparison is not complete merely because a menu item, screen, schema or basic baseline-diff function exists.

## 3. Source selection and supported comparison modes

The user must be able to select:

- Source A and Source B;
- a current project revision, saved historical revision, saved baseline, or supported imported snapshot for each side;
- the comparison scope (whole project or explicitly selected WBS/activity/resource subsets);
- the data domains to compare;
- the matching strategy or an approved mapping profile;
- the schedule/calculation output set and reporting options.

The UI must clearly label which side is the reference and which side is the compared/candidate side. Swapping sides must reverse directional variance signs and added/removed interpretation consistently.

A supported import format is a source for comparison only after it has passed the existing typed import/mapping/validation boundary. A file name or project name alone is not sufficient provenance.

## 4. Snapshot identity and comparison provenance

Each side of a comparison must retain at least:

- tenant and project identity, with the exact project revision;
- source kind (live revision, archived revision, baseline, or imported package);
- baseline ID and baseline role when applicable;
- package format, source file hash and import/mapping profile version when imported;
- source snapshot ID/hash and capture time;
- Data Date and schedule calculation timestamp where applicable;
- schedule-engine/calculation semantic version;
- project, activity, resource and lag calendar IDs and immutable versions;
- relevant scheduling options, constraints and progress interpretation settings;
- timezone, stored calendar system and unit/currency context;
- selected comparison scope and filters;
- identity-matching rules and any user-approved identity map.

The result must preserve references to both source snapshots and the comparison options. Re-running a comparison must either reuse the exact immutable snapshots or create a new, separately identified run. A later edit to a project must not silently rewrite an earlier comparison result.

## 5. Entity identity and matching rules

Matching is a critical correctness boundary, especially for two independent projects.

Use this order where the relevant identity exists and is unique:

1. stable shared/external source identity explicitly preserved by import/export;
2. an approved cross-project identity map;
3. a unique, explicitly selected Activity ID or WBS code within the selected comparison scope;
4. another documented stable business key approved for that entity type.

Activity ID, WBS code, name or row position must not be assumed globally unique across projects. Duplicate identifiers, conflicting mappings and one-to-many or many-to-one matches must be reported as ambiguous and require user resolution.

Names, descriptions, WBS paths, codes and structural similarity may be used to suggest candidate matches. AI may explain or rank candidate matches, but it must never silently establish authoritative identity or hide uncertainty. User-confirmed mapping must be persisted with its scope and version so the comparison can be reproduced.

The system must distinguish:

- matched and unchanged;
- matched and modified;
- added on the compared side;
- removed from the compared side;
- moved to another WBS/parent;
- renamed or recoded;
- ambiguous/unmatched identity;
- not comparable because source data is incomplete or incompatible;
- outside the selected comparison scope.

A missing row may be classified as added or removed only when both source snapshots declare complete coverage for the relevant entity type and selected scope. Selective exports, filtered imports, permission-limited views and partial snapshots must never cause false deletion claims.

## 6. Comparison domains and field-level differences

The comparison contract must be extensible by domain. At minimum, the product scope includes:

### 6.1 Project and configuration
Project identity/code, description, project dates, Data Date, project-level settings, time zone, calendar system, units and currency context.

### 6.2 EPS/WBS structure
WBS/EPS identity and code, parent/child relationships, hierarchy path, descriptions, sequence/order where meaningful, additions, removals, moves and renames.

### 6.3 Activities and milestones
Activity identity, Activity ID/code, name, type, duration type, original/planned/remaining duration, planned/current/actual dates, status, percent-complete type and value, remaining units/duration, milestone type and WBS assignment.

### 6.4 Relationships and logic
Predecessor/successor identities, relationship type (FS, SS, FF, SF), lag value, lag unit, lag calendar, relationship additions/removals/changes and invalid or unresolved references.

### 6.5 Calendars and scheduling options
Project/activity/resource/relationship-lag calendar assignments, calendar version, weekly work periods, shifts, hours per day/week/month, holidays, exceptions, inheritance/overrides, constraints, schedule options, criticality method and relevant progress/out-of-sequence settings.

### 6.6 Resources and assignments
Resource identity/type, labor/material/equipment classification, assignment identity, budgeted/actual/remaining units, units/time, rate type, effective-dated rates, resource curves where supported, driver designation, calendars, availability/capacity and assignment start/finish windows.

### 6.7 Cost, expenses and earned value
Budgeted/actual/remaining costs, assignment costs, expenses, currency, cost accounts, selected baseline sources, PV, EV, AC, BAC, CV, SV, CPI, SPI, ETC, EAC and VAC when the necessary source facts and compatible calculation context exist.

### 6.8 Other approved project-control domains
Additional domains such as risks, issues, changes, claims, procurement or documents may be added through versioned comparison adapters. They must not be represented as compared until their entity identity, scope, permissions and field semantics are defined.

For each changed field, the result must retain the field key, display label, typed old value, typed new value, unit, comparison status, variance (when meaningful), and an explanation of why it is or is not comparable.

## 7. Calculated schedule and cost comparison

Comparison must separate **input/data differences** from **calculated-result differences**.

Where calculated outcomes are requested:

1. Resolve each side from its own complete, immutable, revision-bound input snapshot.
2. Calculate each side through the authoritative Shared Core using that side's actual calendar and scheduling settings.
3. Persist the calculation identity/version and input snapshot hash with each result.
4. Compare corresponding outputs only after verifying their semantics and units are comparable.
5. Show the source values, the normalized values, the difference and the calculation context.

Where applicable, compare planned/current/actual/early/late start and finish, original and remaining duration, Total Float, Free Float, criticality/longest-path membership, progress, resource units/capacity, assignment windows, cost and EVM outputs.

Date variances must state their sign convention. For this specification, directional date/amount variances use **compared side minus reference side**; positive date variance means later, and positive cost/quantity variance means higher. Any field whose established contract uses a different convention must declare it explicitly rather than silently changing its meaning.

Duration and lag comparisons must respect their typed units and calendar basis. Do not subtract ordinary calendar dates and label the result a working-day variance. If the two sides use different calendars, working-time definitions, currencies, units, Data Dates, calculation versions or incompatible settings, the comparison must either:
- calculate each side in its own context and mark the result as context-dependent; or
- normalize through an explicit, versioned, valid conversion rule; or
- report the field as not comparable with a concrete reason.

Never invent an exchange rate, calendar conversion, rate, missing baseline value or zero default to force a numerical comparison.

A critical-path difference must identify the relevant activities and logic changes. Matching only the final project finish date is insufficient evidence of schedule equivalence.

## 8. Results, review and reporting

The comparison result must provide:

- a project-level summary of added, removed, changed, moved, unchanged, ambiguous and incomparable entities;
- WBS-grouped, filterable activity and resource comparison tables;
- field-level before/after values and directional variances;
- side-by-side schedule/Gantt presentation with changes highlighted;
- relationship/network changes where supported;
- filters for WBS, activity ID/code, status, change type, date, resource and cost;
- drill-through from each difference to its source record and source revision;
- a traceable comparison run ID and reproducible source metadata;
- Excel export for detailed analysis and PDF/print output for review, where reporting services support them.

The UI must not present color alone as the meaning of a change; labels/icons and accessible text are also required. Filters and selected scope must be visible in the report header so a partial comparison cannot be mistaken for a whole-project result.

## 9. Interchange and portability

Use the existing typed interchange architecture and supported codecs (including applicable XER, Primavera XML, Microsoft Project XML/MPX, XLS and XLSX paths) rather than creating a comparison-only file parser.

Preserve stable IDs, source IDs, mapping profiles, data types, units, nulls, calendar definitions/versions, scheduling options and project revisions wherever the format supports them. Unsupported or lossy mappings must be reported before the comparison is treated as complete.

Import → validate → normalize → compare must be reproducible. A round-trip export/import must not silently change values, identity mappings, dates, calendars or comparison semantics.

## 10. Security, authorization and audit

- Enforce tenant, project and revision scope for both comparison inputs and outputs.
- The default policy is to deny cross-tenant comparison. Any explicitly supported cross-tenant/portfolio capability requires a separate authorization contract and auditable grant.
- A user must have read permission for both sources and for each selected data domain.
- A comparison result may reveal information from either source; access to the result must therefore be no broader than the intersection of the applicable source permissions unless an explicit authorized policy says otherwise.
- Exports must enforce the same permission boundary and record actor, time, scope and result identity.
- Comparison runs and approved identity maps must be auditable and versioned.
- The compare operation is read-only. No source project, baseline, schedule, assignment, cost or resource record may be changed by running it.

## 11. Acceptance criteria

The capability is not complete until all relevant criteria below have implementation and test evidence:

1. Users can select two valid source snapshots in each supported comparison mode.
2. Source completeness, revision, scope, permissions and calculation context are validated before comparison.
3. Stable identity matching works deterministically; duplicates, ambiguous matches and unresolved references fail closed or remain visibly unresolved.
4. Added, removed, changed, unchanged, moved, renamed, out-of-scope and incomparable cases are represented distinctly.
5. Selective/partial packages cannot produce false additions or deletions.
6. WBS, activity, relationship, calendar, constraint and schedule-option differences are identified at field level.
7. Dates, durations, lags, units, currencies and decimals preserve typed semantics and correct variance direction.
8. Calculated outputs are sourced only from the authoritative Shared Core and are bound to immutable input/result identities.
9. Resource, cost and EVM comparisons reconcile to their source records without double counting or fabricated conversion.
10. Comparison execution does not mutate either source and is tenant/project/revision isolated.
11. Results are reproducible, auditable, filterable and exportable through supported reporting contracts.
12. The same versioned contract is consumed by Web, Desktop and Mobile; localization, RTL/LTR and Jalali/Gregorian display do not alter comparison results.
13. Unit, contract, integration, persistence, security, interchange round-trip and UI/runtime tests cover positive, negative and boundary cases.
14. Unsupported fields and calculation contexts are explicitly disclosed; no parity or completion claim is made without evidence.

## 12. Delivery phases

The complete product requirement is all three comparison modes. Phasing controls implementation order; it does not remove later scope.

- **Phase 1 — Baseline and same-project revision comparison:** complete the baseline snapshot/variance contract; compare current and historical revisions; establish stable IDs, typed field differences, result provenance and exportable reports.
- **Phase 2 — Independent project comparison:** compare two distinct projects and validated imported projects; implement approved identity mapping, WBS/activity/relationship/calendar/constraint/resource structural diffs and user resolution of ambiguous matches.
- **Phase 3 — Full calculated and commercial comparison:** compare schedule-derived outputs, critical/float paths, resource/capacity windows, time-phased costs and EVM, with detailed filters, side-by-side visualizations and final reports.

The phases must reuse the same comparison contract and result model. Do not build separate comparison engines for Baseline, Revision and independent Project modes.

## 13. Current repository evidence at registration

The following are foundations, not proof of a complete Project Comparison capability:

- \`src/construction_pm/p6_baseline_update.py\` contains selective baseline update planning and a baseline-to-current activity comparison for a limited set of values/statuses.
- \`tests/test_p6_baseline_update.py\` covers the current baseline update/comparison slice.
- \`docs/workspace/architecture/workspace-navigation-map.md\` lists an Additional Activities View described as a project/baseline comparison surface.
- \`apps/web/src/workspace-desktop-shell.ts\` currently exposes a Compare Baselines command as unavailable/disabled.
- The typed interchange adapters/codecs provide reusable import/export infrastructure, but interchange support alone does not implement semantic comparison between independent project snapshots.

At registration, **full CMP-01 is a product/architecture requirement, not an implemented feature**. The existing baseline comparator must be preserved and extended; it must not be relabeled as the complete independent Project Comparison engine.
