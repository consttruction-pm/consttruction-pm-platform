# CUBI Capability Consolidation & Help Parity Architecture V1

**Status:** Draft for product-owner review; registration/architecture only. No implementation or parity-completion claim.
**Parent program:** Issue #1990.
**Source register:** `docs/architecture/CUBI_MASTER_CAPABILITY_REGISTER_EPPM_V26_CLOUD_V1.md`.
**Related records:** Issue #1706 (19 Engineering engines), #1989 (Schedule Scenarios), #1990 (master program), PR #1988 (environment ownership), PR #2001 (Enterprise capability layering / ENT-13).
**Priority:** Engineering P1 / Qoder; Enterprise P2; Shared contracts P0 only where they unblock P1.

## 1. Decision summary

The 19 engines/modules originally catalogued in Issue #1706 and the 10 Cloud-origin capabilities are **not 29 independent engines**. Consolidate them as domain capabilities and sub-capabilities inside the existing canonical 37-family register (ENG-01..14, ENT-01..13 as introduced by PR #2001, SH-01..10). Do not create parallel menus, routes, entities, stores, calculation engines or workspaces.

The existing master register remains the source of truth for canonical capability IDs. This document is a mapping/disposition layer, not a replacement register. Preserve old IDs and issue references as aliases until all linked code, PRs, tests, documents and Qoder handoffs have been remapped and reviewed.

**No implementation work is authorized by this document alone.** Engineering implementation remains in the Qoder-owned canonical checkout after repository instructions, exact active PR/path ownership and source contracts are verified. Enterprise P2 work must not block Engineering P1.

## 2. Canonical architecture and single-owner rules

- **Engineering owns project execution facts and calculations:** project/EPS/WBS, activities, relationships, calendars, baselines, CPM, project resource assignments and leveling, project cost/progress/EVM, project risk and quantitative simulation, field commitments, activity status updates, project timesheets/actuals, technical delay analysis and engineering document links.
- **Enterprise owns organization and cross-project/commercial governance:** people/teams/skills, membership/entitlements, portfolio lifecycle and prioritization, enterprise capacity envelopes, cross-project allocation decisions, workflow definitions and approvals, contract/commercial records, claims/disputes, external stakeholder grants, integration governance, enterprise SLA policy and executive roll-ups.
- **Shared owns technical primitives, not business records:** identity/session enforcement, tenant boundaries, audit, idempotency, concurrency, event/job runtime, notification transport, data-quality framework, recovery/history primitives, command registry, localization, storage and sync.
- **Workbench is a non-owning projection:** navigation, contextual guidance, inbox, notifications and permission-filtered search. It does not own duplicate tasks, workflow records, project data or calculations.
- **One calculation authority:** CPM, calendars, project resource leveling, project cost, progress/EVM and project risk simulation must have one authoritative Engineering implementation. Scenario, risk, optimization, watchdog and reasoning modules call it; they do not fork it.
- **Cloud completeness and Professional compatibility are additive, not subtractive:** retain the complete applicable Cloud Help behavior and all applicable Professional/EPPM behavior. Where semantics differ, use context-aware adapters/permissions over one canonical domain model and document the resolution. Never silently drop either source's behavior.
- **No Oracle branding/code copying:** reproduce documented behavior and functional/visual structure in CUBI's own product identity, not Oracle logos, proprietary source assets, product names or external chrome.

## 3. Mapping: original 19 engines/modules from Issue #1706

The right-hand side uses canonical master-register families. Any sub-capability not explicitly represented by a current family must be added as a child capability in the register (or raised as a register change for approval), not hidden in an unrelated family.

| # | Original Issue #1706 engine/module | Disposition | Canonical owner / register mapping | Merge boundary and notes |
|---:|---|---|---|---|
| 1 | Engineering Reasoning & Root-Cause Engine | Retain as Engineering reasoning service; not a second calculation engine | Engineering; consumes ENG-02/03/05/07/08/09/10/14 and SH-05 facts | Reasoning/orchestration explains source-owned findings and proposes options. CPM, cost, EVM, risk and productivity formulas remain in their owning services. Cross-domain reasoning may be exposed through Workbench but project reasoning ownership remains Engineering. |
| 2 | Project Watchdog & Event Monitoring | Split event infrastructure from project monitoring policy | Engineering project rules; SH-05 event/job primitives; SH-02 notification projection | Watchdog subscribes to authoritative project events and computed facts. Shared runtime handles delivery/retry; Workbench only displays alerts. Do not create a second notification or event store. |
| 3 | Scenario Lab & Simulation | Merge with Schedule Scenarios, Comparison and Promotion/Merge | ENG-04; consumes ENG-03 and ENG-06/07 as needed | One scenario aggregate, immutable source snapshots, authoritative scheduler runs, comparison read models and separately gated promotion. No independent CPM. |
| 4 | Project & Portfolio Optimization | Split by optimization boundary | Engineering project optimization: ENG-06/07/09/10; Enterprise portfolio optimization: ENT-02/03/04 | Project resource assignment/leveling and project time-cost optimization stay Engineering. Portfolio selection, capacity envelopes and cross-project allocation stay Enterprise. One side must not write the other's records. |
| 5 | Risk & Uncertainty Analysis | Merge with project risk register and Monte Carlo | ENG-08 (qualitative/project risk) + ENG-09 (quantitative/Monte Carlo); Enterprise roll-up ENT-05 | One project Risk domain. Monte Carlo is a method/subsystem of ENG-09, not a parallel top-level engine. Enterprise consumes immutable exposure/confidence summaries only. |
| 6 | Schedule & Project Quality Audit | Merge with Schedule Health Score | ENG-05, using ENG-03 authoritative schedule runs and ENG-06/07 data where in scope | Rule catalogue, diagnostics, severity, explainability and health score belong together. Do not create a second audit engine or duplicate CPM checks in Watchdog. |
| 7 | Construction Production & Productivity Intelligence | Retain as Engineering execution/productivity capability; refine register child rows | Engineering; links ENG-02/03/06/07/10; proposed child capability under ENG-10/ENG-07 subject to register owner approval | Production quantities/rates, crew/equipment productivity, earned hours, production curves, bottleneck and takt/line-of-balance analytics must have explicit owner and source data. Do not force all productivity analytics into generic task management. |
| 8 | Contract, Change, Claims & Delay Analysis | Split decisively by commercial vs technical evidence | Enterprise contract/commercial/claims: ENT-13 (PR #2001); Engineering schedule/change/delay analysis: ENG-03/04/05/09 and an explicit child capability | Contract records, obligations, variations, notices, claims/disputes, entitlement, correspondence and settlement are Enterprise. TIA, windows, fragnet, as-planned/as-built, critical-path and schedule impact quantification are Engineering. Engineering supplies immutable schedule evidence; Enterprise owns the claim record. |
| 9 | Project Data Reconciliation | Shared reconciliation framework with domain adapters | SH-05 technical framework; Engineering adapter for ENG-01..14; Enterprise adapter for ENT-01..13 | Shared matching/diff/lineage machinery may be reused. Domain owners retain validation rules, authoritative writes and record ownership. Do not create one cross-domain mutable master record. |
| 10 | Workflow & Automation Engine | Split workflow governance from execution runtime and domain mutations | Enterprise ENT-08 owns Workflow Studio, definitions, delegation and approval policy; SH-05 owns event/job/retry runtime; source domain performs final mutation | No Engineering-specific parallel workflow studio. Engineering exposes typed commands/approval hooks and validates invariants. Enterprise workflow cannot directly mutate Engineering storage. |
| 11 | Portfolio Capacity & Cross-Project Allocation | Transfer commercial/product ownership to Enterprise | ENT-03/ENT-04; Engineering demand/assignment facts from ENG-06 | Enterprise owns people/skills/availability, capacity envelopes, allocation negotiation and cross-project priority. Engineering owns project resource assignments, leveling and schedule results. |
| 12 | Engineering Standards & Methods Library | Retain Engineering content ownership; share library infrastructure | Engineering-owned child capability; SH-09 shared forms/templates only where applicable; ENT-12 may publish governed PMO knowledge | Standards, construction methods, engineering procedures and technical acceptance criteria remain Engineering-controlled content. Enterprise can publish organization-wide policy and catalog metadata but cannot override engineering technical ownership. Register owner must add explicit child row if absent. |
| 13 | Project & Work-Method Templates | Split by template scope and submission owner | Engineering project/work-method templates under ENG-01/02/10; Enterprise organization/portfolio templates ENT-02/08/12; SH-09 shared Form Builder/template runtime | Shared schema/rendering/versioning can be reused. Engineering owns project/WBS/activity/work-method templates; Enterprise owns organization/portfolio/workflow templates. A template does not own submitted domain data. |
| 14 | Decision Register & Decision Support | Split by decision authority; share audit/history | Engineering project decisions linked to ENG-02/03/04/06/08/09/10; Enterprise portfolio/strategy/funding decisions ENT-02/04/05/13; SH-05 audit | Engineering decisions cover technical method, schedule, resource and risk choices. Enterprise decisions cover portfolio, capital, commercial and organization matters. Shared IDs/history do not imply shared business ownership. |
| 15 | Deadline, Reminder & SLA Control | Transfer policy ownership to Enterprise; share scheduling/notification runtime | ENT-08 policy/workflow SLA; SH-05 jobs/events; SH-02 Workbench projection; Engineering owns domain due dates | Enterprise defines organization-wide SLA calendars/escalation policy. Engineering owns activity/commitment due dates and schedule dates. No second reminder engine. |
| 16 | Data Quality Profiler | Merge as shared quality framework with domain-owned rule packs | SH-05 shared framework (or explicit SH child row); ENG/ENT domain rule packs | Profiling framework, sampling, lineage and result storage are shared. Engineering/Enterprise define rules and own remediation commands. Avoid cross-tenant leakage in profiles and samples. |
| 17 | Change Recovery, Undo & Decision History | Merge technical primitives into shared change-safety layer | SH-05; source domain owns reversible commands and business history | Shared revision, audit, idempotency and recovery orchestration. Undo must be a compensating command validated by the source domain, never arbitrary database rewind or silent last-write-wins. |
| 18 | User/Organization Command Dictionary | Merge into shared command registry with owner-scoped vocabulary | SH-01/SH-03 and shared command registry; ENT-01 owns organization/team terms; Engineering owns project/technical vocabulary | One command resolver and permission-aware search. Domain synonyms/commands are registered by their owners. Do not build separate Engineering and Enterprise parsers. |
| 19 | Contextual Smart Guide & Workspace Navigation | Move presentation ownership to Workbench | SH-01 navigation; SH-03 search; SH-02 inbox/help prompts | Workbench presents context-aware guidance and deep links; each specialist workspace owns its feature-specific help, validation and actions. No third business domain or duplicate workspace. |

## 4. Mapping: 10 Primavera Cloud capabilities approved for CUBI

| # | Cloud capability | Canonical owner / mapping | Consolidation decision | Required Cloud Help source topics (exact topic crosswalk still required) |
|---:|---|---|---|---|
| 1 | Schedule Scenarios | Engineering ENG-04 | Merge with Scenario Lab; one scenario lifecycle | Schedule Scenarios Overview; Add a Scenario; Open a Scenario; Manage a Scenario; Set a Scenario as the Current Schedule; scenario permissions |
| 2 | Schedule Comparison | Engineering ENG-04 | Comparison is a first-class sub-capability and read-only result of pinned versions, not a separate engine | Schedule Comparison Overview; Compare Two Versions of a Project Schedule; supported views/fields and comparison rules |
| 3 | Scenario Promotion / Merge | Engineering ENG-04 | Separate guarded command/release gate; never automatic or last-write-wins | Merge Overview; merge procedure; merge log; backup; conflict/permission behavior |
| 4 | Schedule Health Score | Engineering ENG-05 | Merge into Schedule & Project Quality Engine | Schedule Health Score Reference; View Schedule Health Score Results; every rule, threshold, status and drill-down topic |
| 5 | Monte Carlo Risk Analysis | Engineering ENG-09 | Merge into Risk & Uncertainty; separate async run/result subsystem, no duplicate CPM | Risk Analysis Prerequisites; Run a Risk Analysis; View Risk Iteration Analysis Results; distribution, iteration, convergence and sensitivity topics |
| 6 | Last Planner / Field Work Plan | Engineering ENG-10 | One schedule-linked field planning subsystem, distinct from Enterprise generic tasks and Team Member activity updates | Work Plan Overview; Manage Tasks on Work Plan; Pull Plan; all commitment, hand-off, constraint and work-plan board topics |
| 7 | Daily Huddle | Engineering ENG-10 | Child workflow within Field Work Plan, not a separate engine | Daily Huddle/meeting topics where present; if absent mark NOT PRESENT and verify application behavior; participants, agenda, commitments, notes and follow-up |
| 8 | PPC & Missed Commitment Analysis | Engineering ENG-10 | Child metrics/analysis within Field Work Plan; source commitments and reasons | PPC/Percent Plan Complete and missed-commitment history topics; formula, denominator, exclusions, reason codes, period and trend views |
| 9 | Constraint Management | Engineering ENG-10, linked to ENG-02 | Field constraint lifecycle is distinct from schedule activity constraints where semantics differ; reconcile shared references without conflating records | Constraint/Make Ready/Work Plan topics; responsible party, need-by date, status, release, activity/work-package link and blocker reasons |
| 10 | Resource-Loaded Scheduling | Engineering ENG-06 | Integrate with project resources/roles/assignments/spreads/leveling; no duplicate resource model | Resource assignments, role loading, resource curves/spreads, resource usage/analysis, resource leveling and schedule calculation topics |

**Important:** the Help topic names above are an inventory target. Every exact canonical URL, page/section/procedure, screenshot and option inventory must be captured before marking any row source-traced. Where a feature name is absent, record NOT PRESENT only after a documented TOC + guide + search pass. Never infer an exact Help topic URL from a title.

## 5. Enterprise transfer list and explicit non-transfer list

### Transfer / Enterprise ownership

1. Portfolio resource planning, enterprise capacity, cross-project allocation and portfolio optimization → ENT-03/ENT-04.
2. Contract & Commercial Management, contract lifecycle, obligations, variations, commercial claims/disputes, entitlement, notices and settlement → ENT-13 (as introduced by PR #2001; verify canonical register integration).
3. Workflow Studio, workflow definition, approval policy, delegation and enterprise SLA policy → ENT-08.
4. Portfolio/strategic/funding decisions and portfolio risk governance → ENT-02/ENT-05.
5. Enterprise organization, people, teams, skills and membership vocabulary → ENT-01.
6. Enterprise/portfolio templates, PMO knowledge and benefits → ENT-02/ENT-12 and SH-09 where a shared template/form runtime is used.

### Must remain Engineering

- Project Schedule Scenarios, comparison and promotion.
- CPM, calendars, baselines, schedule quality and project schedule health.
- Project resource assignment, resource loading, resource leveling and project resource costs.
- Project risk register and quantitative project risk/Monte Carlo.
- Field Work Plan, Last Planner, Daily Huddle, PPC, missed commitments and field constraints linked to activities/WBS.
- Project production/productivity and technical method analysis.
- Technical delay analysis, schedule impact and time-related evidence for claims.
- Engineering standards and work-method content.
- Project-level technical decision records.

### Shared / Workbench, not Enterprise business ownership

- Event/job/retry runtime, audit, idempotency, optimistic concurrency, recovery primitives, Data Quality Profiler framework, command registry, notification transport, navigation, contextual guide, search and inbox projection.
- Shared runtime does not grant a shared data owner. Source domains validate and commit their own commands.

## 6. Mandatory Help inheritance and exhaustive UI parity contract

The detailed universal gates already recorded in the master register §§2A, 2B and 2C are binding and incorporated by reference. This section makes their application to the consolidated capabilities explicit.

For every merged capability, inheritance must be documented **at the smallest user-visible behavior level**, not merely by linking a broad product guide. The implementation packet must include:

### 6.1 Topic-by-topic source ledger

One row per Help topic, subheading, procedure step, field, control, option, state, output and visual element. Required columns:

- Canonical source: P6 EPPM V26, P6 Professional V26 (supplementary collision audit), P6 Team Member V26 (where contributor workflow applies), Primavera Cloud HTML Help, or CUBI-native.
- Exact product/revision, canonical HTML URL, page title, section/subheading and procedure/step number.
- Source behavior, prerequisites, roles/privileges, input, expected result, errors and state transition.
- Surface: page/workspace/tab/dialog/wizard/panel/popover/context menu/toolbar/table/chart/report.
- Component/control type and exact label; icon semantics; default, selected/available values and dependencies.
- Form semantics: field order, requiredness, validation, formatting, unit, min/max, read-only/hidden/disabled conditions and save/cancel/reset.
- Visual semantics: hierarchy, layout, spacing, alignment, density, width/height, min/max dimensions, split ratio, scroll/resize and responsive breakpoints.
- Color semantics and status mapping; typography hierarchy; icon dimensions; border, radius, elevation and button variant/size/state.
- Grid/table: columns/order/width, row height, grouping, sorting, filters, totals, pagination, selection, row actions, export/print.
- Charts: type, series, axes, scale, units, labels, legend, thresholds, markers, colors, tooltip, drill-through, zoom, filters, export/print.
- Corresponding CUBI route/component/design token/API/domain object.
- Inheritance disposition: exact copy of behavior / reconciled behavior / additive Cloud extension / CUBI-native / NOT APPLICABLE / NOT PRESENT / MISSING-VERIFY, with reason.
- Test ID, screenshot/evidence reference, visual-diff result, implementation commit and reviewer.

### 6.2 UI implementation requirements

- **Pages and navigation:** same functional page taxonomy, workflow order, tab/panel/dialog roles, information hierarchy, entry/return paths and context switching. Do not introduce duplicate pages where a canonical CUBI page already exists.
- **Forms and selectable choices:** enumerate every field and every selectable value. Preserve default values, dependencies, validation, disabled/hidden conditions, permission-specific choices, multi-select semantics, date/time/unit behavior and error messages. A dropdown with fewer values is a parity failure.
- **Buttons and actions:** map every action to its correct button/menu/context-menu form, icon intent, hierarchy (primary/secondary/destructive), size, disabled/loading/hover/focus/pressed states, confirmation and resulting transition. Include bottom/action bars and modal footer actions.
- **Color and typography:** preserve source semantic meaning for status/severity/selection/series, but render with approved CUBI tokens. Record token mapping for background, surface, border, text, muted text, focus, selected, warning, danger, success, series and disabled. Typography, line height, font weight and density must be measured/recorded. Do not claim Oracle exact brand color copying.
- **Sizing and layout:** record actual reference dimensions when measurable; otherwise NOT SPECIFIED. Capture page, dialog, panel, grid row, column, button, field, chart and toolbar dimensions; responsive breakpoints; min/max; scroll behavior; resize and split-pane ratios. Do not invent exact sizes when Help does not specify them.
- **Filters and views:** include all filter dimensions/operators/value sets, saved filters, grouping, sorting, column selection, layout choices, chart selection, period/date ranges, clear/reset and permission restrictions.
- **Charts, reports and tables:** reproduce all applicable output types and configuration—not a generic placeholder. Compare data semantics and formulas as well as visual form. Include every chart selection option, legend/axis control, table column, report grouping, total, export/print output and empty/error state.
- **Responsive and localization:** test CUBI supported viewport sizes, FA/EN, RTL/LTR, Jalali/Gregorian date presentation and keyboard/focus behavior. Localization may change text direction and font metrics but must not drop a control or workflow.
- **Accessibility and interaction:** keyboard navigation, focus order, accessible names, contrast and state announcement are mandatory CUBI quality requirements, even where source Help is silent.

### 6.3 Professional/EPPM overlap and dual-environment preservation

For each source behavior, compare EPPM V26 and Professional V26. P6 EPPM remains the parity authority; Professional is a supplementary collision source and must not be used to claim EPPM web parity. Team Member Help is separately normative for contributor workflows.

Disposition rules:
1. Existing EPPM behavior → preserve in the canonical CUBI surface.
2. Professional behavior not present in EPPM → record as Professional-specific supplementary behavior; add only where the approved CUBI product scope requires it.
3. Cloud-only behavior → retain completely as an additive capability; do not remove it because EPPM/Professional lacks it.
4. Shared but different semantics → one canonical domain model plus explicit source/context adapter; no duplicated entities or engines.
5. CUBI-native behavior → label as such and do not falsely attribute it to Oracle Help.

Run regression journeys for both Professional-aligned and Cloud-aligned CUBI contexts. Cloud additions must not regress Professional-aligned behavior; Professional parity work must not remove Cloud-only additions.

### 6.4 Acceptance gate

A capability is **not source-traced** until every applicable topic and procedure has a complete ledger. It is **not UI-complete** until every applicable page, form, option, button, filter, chart, report, table, visual state and interaction has evidence. It is **not parity-complete** until:
- all source rows have a valid disposition;
- all applicable documented steps are replayed;
- no unexplained missing control/option/output remains;
- CUBI/reference screenshots and visual-diff checklist cover all principal states;
- browser tests cover success, validation, permissions, conflict, empty, loading and failure states;
- responsive, localization, RTL/LTR and keyboard checks pass;
- exact-head CI and fresh runtime/preview evidence are recorded;
- Professional/EPPM regression and duplicate-menu/route/API/entity/calculation scan pass;
- the product owner approves any explicit NOT APPLICABLE or source divergence.

No 100% claim may be inferred from a smoke test, green build, API presence, schema, mockup or partial screenshots. Unavailable source pages/screenshots remain MISSING / VERIFY and block full-parity acceptance.

## 7. Execution work packages

### WP-0 — Repository and collision audit (blocking precondition)
- Refresh main SHA, all open PR heads, changed paths, CI and ownership.
- Resolve actual-checkout root/nested AGENTS.md. Do not infer repository instructions from an API 404.
- Read current master register, blueprint, project-state ledger and existing issues.
- Confirm canonical 37-family register and ENT-13 addition from PR #2001; reconcile ID cardinality before changing IDs.
- Audit current implementation, tests and existing issue/PR ownership. No overlapping source edits.
- Output: signed owner/path matrix, exact baseline SHA, open risk list.

### WP-1 — Help source and UI inventory (per capability, before code)
- Qoder/assigned researcher opens each exact official Help topic and captures its linked subtopics.
- Complete EPPM V26 + Cloud topic ledger; Team Member where applicable; Professional V26 collision inventory.
- Capture screenshots/diagrams where officially available; if only live application can confirm a visual detail, mark Help NOT SPECIFIED and capture separate official application evidence.
- Inventory every page, field, option, filter, button, chart, table, report, color, size and workflow.
- Output: versioned source ledger + source screenshot index + unresolved questions. No implementation-ready status while rows are missing.

### WP-2 — Consolidation and contracts
- Map every old Issue #1706 item and every Cloud feature to one canonical register row and owner.
- Define aggregate/data/API/menu boundaries and source-of-truth per calculation.
- Specify shared-service reuse and non-interference tests.
- Output: approved contract, dependencies and executable acceptance tests.

### WP-3 — Engineering P1 implementation (Qoder)
- Deliver one vertical slice at a time, starting with active ENG-04 Scenario/Comparison contract without colliding with Issue #1989.
- Next sequence after owner review: ENG-05 Schedule Quality; ENG-09 Monte Carlo; ENG-10 Field Work Plan/Last Planner; ENG-06 Resource-Loaded Scheduling parity; then integrated reports/PPC.
- Reuse canonical CUBI components and Shared Calculation Core.
- Include full Help-to-component mapping and UI parity evidence in every PR.
- Do not change Jalal 5 weights or claim weighted progress without explicit approved rebaseline.

### WP-4 — Enterprise P2 integration
- Begin only when required Engineering contracts are stable.
- Enterprise owns ENT-13 contract/commercial/claims; consumes Engineering schedule/delay evidence read-only.
- Complete ENT-03/04 portfolio capacity and allocation; ENT-08 workflow governance; ENT-02/05 portfolio/decision/risk governance.
- Reuse Shared runtime and Workbench projections; no duplicate calculation or project records.

### WP-5 — Independent acceptance and release
- Reviewer independently checks source ledger, CUBI screens, UI behavior, data/API ownership and tests.
- Run exact-head CI, browser E2E, security/tenant tests, localization and visual regression.
- Release only after explicit product-owner approval; this document does not authorize merge or deploy.

## 8. Immediate child work items

1. Update Issue #1990 with this consolidation mapping and work-package dependencies.
2. Keep Issue #1989 as the existing ENG-04 execution child; add a non-interference note rather than opening a duplicate Scenario implementation issue.
3. Create a source/visual parity audit child covering ENG-04, ENG-05, ENG-09, ENG-10 and ENG-06; then expand to remaining register rows.
4. Reconcile PR #2001 ENT-13 with the master register and this mapping; do not duplicate contract/claims scope.
5. Qoder starts WP-0/WP-1 in canonical checkout and returns exact source ledger, current SHA, AGENTS instructions and active-path ownership before any source changes.

## 9. Current evidence and limitations

- The master capability register already contains mandatory visual parity, one-to-one Help conformity and non-subtractive dual-environment uplift gates (§§2A–2C). This document operationalizes those gates for the 19 + 10 consolidation.
- Issue #1989 states Schedule Scenario backend, UI wiring and E2E are not yet complete; its Phase 1 contract is DRAFTED / IN REVIEW.
- PR #2001 describes ENT-13 as source-mapped, not implementation-ready, and says its governance validator does not prove Help completeness or runtime parity.
- This document does not assert that every Help page, dropdown option, chart, exact dimension or screenshot has already been inspected. Those are explicit WP-1 evidence tasks and remain MISSING / VERIFY until completed.
- No production code, schema, CSS, UI or calculation engine was changed by this architecture registration.
