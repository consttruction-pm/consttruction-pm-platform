# CUBI reference projects — import analysis and field mapping

Contract: `cubi-reference-import-source.v1`
Source: `CUBI_Three_Reference_Projects_Master_Data_v1-1.xlsx`
SHA-256: `0848454d2b8b77806986eb53cf36e95521d7e789ad8c4f0b2af78acb4e82fa26`
Status date: 2026-11-22 (all three projects)
Classification: **DEMO/SYNTHETIC** — no customer or as-built record.

This document is the analysis half of the import mission. It records what each
of the 94 sheets contains, where every field goes, and what is deliberately not
imported. The machine-readable inventory — one row per sheet with counts,
columns, primary key, foreign keys, disposition and target — is
[`CUBI_REFERENCE_PROJECTS_SHEET_INVENTORY.csv`](CUBI_REFERENCE_PROJECTS_SHEET_INVENTORY.csv).

Nothing in this document writes to a database. Persistence happens through the
canonical Engineering and Enterprise services only, driven by one importer with
a SQLite adapter for the preview and a PostgreSQL adapter for production
(see section 13).

## 1. Ground rules

1. **Engineering is the single source of truth** for projects, EPS/ZVE, WBS,
   activities, relationships, calendars, baselines, resources, assignments,
   progress, cost and earned value. Enterprise reads it through read models; it
   never keeps a second schedule, resource or cost engine.
2. **The workbook is input, not schema.** It is mapped field by field; it is not
   mounted as a table set. No sheet is copied verbatim.
3. **No calculated value is imported as a fact.** CPM dates, total/free float,
   critical path, resource histograms and every EVM indicator are recalculated by
   the canonical services. Source values are kept only as cross-checks. The
   workbook itself says so:
   - README/Scheduling: *"CPM dates, total/free float and critical path are
     intentionally not asserted; calculate with CUBI scheduling engine."*
   - README/EVM: *"EAC/ETC/CPI/SPI are formulas or expected calculation outputs,
     not certified forecasts."*
   - Schedule Options: *"CUBI required; do not import CPM/float as facts."*
4. **Nothing is silently dropped.** Every sheet has a disposition below; fields
   without a canonical home are listed as *Proposed Extension* and stay visible
   until a target exists.
5. **Source IDs are preserved.** `CUBI-REF-00x` stays the project ID in both
   environments, so Engineering, Enterprise, the assistant and the Scenario
   Workspace address the same project without a remapping table.

## 2. Dispositions

| Disposition | Sheets | Meaning |
| --- | ---: | --- |
| Direct | 22 | Field-for-field into an existing canonical entity. |
| Transformed | 19 | Imported after a documented unit, date, status or entity change. |
| Derived | 19 | An output of a canonical calculation. Never imported as truth; recomputed and compared. |
| Proposed Extension | 18 | No canonical home yet. Visible gap; must be closed or explicitly excluded before apply. |
| Enterprise | 13 | Owned by Enterprise, referencing Engineering project IDs. |
| Metadata | 3 | Governance/dictionary. Not imported. |

## 3. Engineering core — field mapping

### 3.1 Project, EPS, OBS, WBS

| Source sheet | Source field | Canonical target | Disposition |
| --- | --- | --- | --- |
| Project Register | Project ID | `project.id` (same string in both environments) | Direct |
| Project Register | Project Name | `project.name` | Direct |
| Project Register | Project Status | `project.status` | Direct |
| Project Register | Planned Start / Planned Finish | `project.planned_start` / `planned_finish` | Direct |
| Project Register | Status Date | `project.data_date` | Direct |
| Project Register | Target Budget USD, Planned Duration Days, Sector, Contract Type | project attributes | Proposed Extension (attributes not yet on the canonical project) |
| Project Settings | Default Calendar ID | `project.calendar` | Transformed |
| Project Settings | Default Activity Type / Duration Unit / % Complete Type | activity defaults | Transformed |
| Project Settings | Time Zone, Fiscal Year Start Month, EVM Method | settings | Proposed Extension |
| EPS | EPS ID, Parent EPS ID, EPS Name, Level | `eps_node` / `project_org_binding`, or WBS roots | Transformed — binding decision recorded below |
| OBS | OBS ID, Parent OBS ID, OBS Name, Manager Role | `p6_obs_repository` | Direct |
| WBS | WBS ID, Parent WBS ID, WBS Code, WBS Name | `wbs_master_repository` | Direct |
| WBS | EPS ID → EPS; Responsible OBS ID → OBS | WBS links | Direct |

**EPS note.** CUBI replaces the P6 EPS classification with a Business Domain in
the project lifecycle, while the administration store already keeps `eps_node`
and `project_org_binding`. The workbook's 25 EPS rows (8/8/9) are imported as an
EPS tree bound to the project; the persistence stage must choose either the
existing `eps_node` binding or WBS top-level EPS nodes and record the choice.
This is a *Proposed Extension*, not a silent remap.

### 3.2 Activities

| Source field | Canonical target | Disposition / rule |
| --- | --- | --- |
| Activity ID | `activity_master.activity_id` | Direct, source ID preserved |
| Activity Name | `activity_master.name` | Direct |
| Activity Type (`Task Dependent`) | `activity_master.activity_type` | Direct |
| Original Duration Days | `activity_master.duration_value` + `duration_unit=Day` | Transformed |
| Remaining Duration Days | `activity_master.remaining_duration` | Transformed |
| Status (`Not Started`/`In Progress`/`Completed`) | `activity_master.status` + `status_code` | Transformed |
| WBS ID | `activity_wbs_assignment.wbs_id` | Direct (FK) |
| Calendar ID | activity calendar assignment | Direct (FK) |
| Responsible OBS ID | activity OBS | Direct (FK) |
| Planned Start / Planned Finish | activity planned dates (input) | Transformed |
| Actual Start / Actual Finish | `activity_master.actual_start` / `actual_finish` | Transformed |
| Physical / Duration / Units % | `activity_master.percent_complete` (+ type) | Transformed |
| Budget USD | activity budget / `cost_account_id` link | Transformed |
| Phase, Activity Code | activity code assignment | Direct |
| Data Classification | import metadata (not a schedule field) | Proposed Extension |

`Activity Calendar Assignments` (540 rows) duplicates `Activities.Calendar ID`.
The source agrees on all 540 rows, so the assignment sheet is validated, then the
activity field is authoritative.

### 3.3 Relationships

| Source field | Canonical target | Rule |
| --- | --- | --- |
| Relationship ID | relationship identity | Direct |
| Predecessor ID / Successor ID | dependency graph endpoints | Direct (must resolve to activities in the same project) |
| Relationship Type | `FS` (429), `SS` (195), `FF` (90) | Direct; `SF` is reserved but absent |
| Lag | relationship lag | Direct; all 714 rows use `Day` |
| Lag Unit / Lag Calendar ID | lag unit + lag calendar | Transformed; lag calendar resolved to the project calendar |

Relationships are stored as a graph; the canonical scheduler derives ES/EF/LS/LF,
float and the critical path. `_detect_cycles` rejects a cyclic graph before
persistence.

### 3.4 Calendars

| Source sheet | Canonical target | Rule |
| --- | --- | --- |
| Calendars (9) | `calendar_master_repository` | Direct; 3 calendars per project |
| Calendar Workweeks (63) | `calendar_work_hours_repository` | Transformed: weekday, working flag, start/finish, hours |
| Calendar Shifts (9) | shift/work-hour model | Transformed: break hours reduce net hours |
| Calendar Exceptions (9) | `calendar_exception_repository` | Direct: holiday / working exception |

Where `Start Time 07:00 / Finish Time 15:00 / Hours 8` disagree with the elapsed
span, the explicit `Hours` value wins.

### 3.5 Resources, equipment and assignments

P6 models **equipment as a resource**; this workbook keeps equipment in a
separate `Equipment Register`. Naive mapping leaves 180 equipment assignments
dangling (60 per project). The import therefore builds one resource index from
**Resource Master ∪ Equipment Register** and resolves every assignment against
it.

| Source sheet | Canonical target | Rule |
| --- | --- | --- |
| Resource Master (90) | `p6_resource_master_repository` + rates | Direct (`Labor`, 30/project) |
| Equipment Register (30) | resource rows with type `Equipment` | Transformed (rate, capacity, availability, calendar) |
| Resource Roles (90) | `p6_role_repository` | Direct |
| Resource Skills (270) | resource skills | Direct |
| Resource Rates (90) | `p6_resource_rate_repository` | Direct |
| Resource Availability (90) | `p6_resource_capacity_repository` | Transformed |
| Resource Calendars (90) | resource calendar binding | Direct; agrees with Resource Master |
| Resource Assignments (720) | `p6_resource_assignment_repository` | Direct; 240/project = 180 Labor + 60 Equipment |
| Resource Assignment Spreads (720) | `p6_resource_spread_repository` | Transformed (period buckets) |
| Resource Actuals (720) | `p6_activity_period_actual_repository` | Transformed |
| Resource Usage (720) | histogram / usage read model | Derived |
| Labor Register (30) | headcount/hours aggregate | Derived — not a parallel resource truth |
| Material Register (30) | Enterprise procurement / material register | Proposed Extension |

Equipment assignments use IDs such as `CUBI-REF-001-EQ-01` and resolve only
through `Equipment Register`. The validator asserts this: removing the equipment
sheet produces exactly three `RESOURCE_ID_UNKNOWN` errors in the fixture, and
zero on the real workbook.

### 3.6 Baselines

| Source | Target | Rule |
| --- | --- | --- |
| Baselines (3) | `p6_baseline_repository` | Transformed; one immutable snapshot per project |
| Baseline Activities (540) | `p6_baseline_activity_repository` | Transformed; one row per activity, 180/project |

Exactly one baseline exists per project (`Immutable Snapshot = YES`), and every
one of the 180 activities has a snapshot row. Baseline dates and budget are
planning inputs; the engine's comparison is authoritative.

### 3.7 Progress, cost and schedule options

| Source | Target | Rule |
| --- | --- | --- |
| Activity Progress (540) | progress API / period actuals | Transformed; 0 mismatches against Activities on all three percentage fields, status and remaining duration |
| Activity Status History (540) | `activity_progress_history` | Transformed; append-only |
| Activity Steps (540) | `p6_activity_step_repository` | Direct |
| Activity Expenses (135) | `p6_expense_repository` | Direct |
| Cost Accounts (24) | `p6_cost_account_repository` | Direct |
| Project Budgets (24) | budget service | Direct |
| Activity Budgets (540) | activity budget | Transformed |
| Cost Periods (66) | `p6_financial_period_repository` | Direct |
| Actual Costs (24) | cost actuals | Direct |
| Expenses (24) | project expenses | Direct |
| Commitments (24) | Enterprise procurement | Proposed Extension |
| Cash Flow (66) | cash-flow read model | Derived |
| Schedule Options (3) | `schedule_options` + project schedule settings | Transformed; critical definition **Longest Path**, retained logic, 10 float paths, predecessor lag calendar |
| Schedule Run Inputs (3) | schedule-run manifest | Proposed Extension; the run is executed by the engine, never seeded |

### 3.8 Milestones, constraints, documents

| Source | Target | Rule |
| --- | --- | --- |
| Project Milestones (36) | milestone activities | Transformed; `Activity ID` links the milestone to its activity; `Milestone Status` is a planning input |
| Activity Constraints (30) | `constraint_master_repository` | Transformed: `Start On or After` |
| Activity Documents (108) | activity↔document link | Direct |
| Document Register / Revisions (45 + 45) | Enterprise documents | Enterprise |

## 4. Enterprise-owned sheets

Enterprise owns portfolio, organization, teams, tasks, workflows, approvals,
contracts, procurement, documents, risks and reports, and reads Engineering
through valid APIs or read models. Existing Enterprise workbench kinds can take:

| Sheet(s) | Enterprise target |
| --- | --- |
| Risk Register, Risk Responses | kind `risks` |
| Document Register, Document Revisions | kind `documents` |
| Organization | kind `organizations` |
| Project Teams | kind `teams` |
| Workflow Templates / Instances | kind `workflows` |
| Approval Records | kind `approvals` |
| Forms Register | kind `forms` |
| Timesheets | kind `timesheets` |
| Team Tasks | `enterprise_task_http` canonical task store |
| Responsibility Assignments | responsibility records |

The remaining enterprise sheets have **no workbench kind today** and are marked
*Proposed Extension*: Issue Register, Change Requests, Contracts, Contract
Packages, Procurement Register, Vendor Register, Communication Log, and the
quality/HSE family (Quality Register, Inspection Requests, HSE Register, NCR
Register, Punch List, Lessons Learned). They must not be forced into an
unrelated kind; each needs an explicit record type or a documented exclusion.

`Audit Import Manifest` is the import-run audit identity the apply sequence
requires (source digest, batch, actor, counts, result). It is a Proposed
Extension until the apply engine writes it.

## 5. Derived sheets — recompute, never import

These 19 sheets are outputs. They are read for cross-checks only; CUBI's own
services produce the authoritative values:

`Earned Value`, `EVM Periods`, `EVM Forecast`, `Cost Variance`,
`Schedule Variance`, `EVM Dashboard Data`, `Dashboard KPIs`, `Portfolio Summary`,
`Milestone Trend`, `Planned vs Actual`, `Resource Histogram Data`,
`Cost S-Curve Data`, `Progress S-Curve Data`, `Risk Matrix Data`,
`Procurement Dashboard`, `Document Status Dashboard`, `Resource Usage`,
`Labor Register`, `Cash Flow`.

The required EVM set — BAC, PV, EV, AC, CV, SV, CPI, SPI, ETC, EAC, VAC, TCPI —
must be reproducible from persisted progress and cost, not copied from the
`Earned Value` sheet. The source values are retained only to compare the engine
result against the workbook expectation.

## 6. Gaps and inconsistencies found in the source

| # | Finding | Impact | Resolution |
| --- | --- | --- | --- |
| 1 | `Data Validation` reports **325 relationships** per project; the data has **238** per project (714 total) | The sheet's V02/V08 "PASS" cannot be trusted | Recompute; never import the validation sheet as truth |
| 2 | Same sheet claims density ≥ 1.5 and threshold 270, while 238/180 = **1.32** | A read of that claim would wrongly pass a thinner network | Validator recomputes relationship counts; documented here |
| 3 | README says `v1.0`, the file is `v1-1` | Version ambiguity | Record the file SHA-256 as the identity |
| 4 | Equipment lives in `Equipment Register` but assignments reference its IDs | 180 assignments would be orphaned | One resource index over Resource Master ∪ Equipment Register |
| 5 | Many quality/HSE/procurement/contract sheets have no Enterprise kind | Data would be dropped | Marked Proposed Extension; explicit decision before apply |
| 6 | EPS has no single canonical Engineering binding | Ambiguous hierarchy | Choose `eps_node` or WBS roots; recorded as Proposed Extension |
| 7 | CPM/float and EVM values are present as if final | Risk of importing derived values | Recalculate with canonical services; source is cross-check only |
| 8 | `Project Settings.EVM Method` is a non-standard label ("Budgeted Cost of Work Performed") | Mapping ambiguity | Kept as display metadata; calculation method comes from CUBI settings |

These are source observations, not reasons to change the workbook. The import
keeps the source intact and records the decision for each item.

## 7. Referential integrity enforced before persistence

`validate_dataset` returns deterministic issues sorted by sheet, record and code:

- project count must be exactly three, IDs unique, every sheet's `Project ID`
  must be registered;
- WBS parent/EPS/OBS links, self-parent rejection;
- activity WBS/calendar/OBS/duration/status;
- relationship endpoints in the same project, type in FS/SS/FF/SF, numeric lag,
  and a cycle check by depth-first search;
- resource/equipment rate, units, calendar, and the merged resource index for
  assignments;
- assignment unit fields; baseline one-per-project and per-activity snapshot;
- progress percentages in `[0, 100]`.

Current result on the real workbook:

```
contract: cubi-reference-import-source.v1
ok: true
error_count: 0
warning_count: 0
sheets: 94
projects: CUBI-REF-001, CUBI-REF-002, CUBI-REF-003
```

## 8. Reproduction

```bash
python scripts/validate_reference_projects.py \
  CUBI_Three_Reference_Projects_Master_Data_v1-1.xlsx --summary
python -m pytest tests/test_reference_projects_import.py -q
```

Exit code 0 means the source is internally consistent and safe to hand to the
persistence stage. It does not mean the projects exist; that is the next stage.

## 9. Not claimed

- No database write, no project created, no schedule run yet.
- No CPM/float, histogram or EVM value is verified by this document.
- The Enterprise kinds and Proposed Extensions above are proposals, not merged
  contracts.
- Supabase/PostgreSQL behaviour is not asserted; the validator reads the
  workbook only.

## 10. Implementation record — what was actually persisted

The analysis above was executed by
[`src/construction_pm/importing/reference_persistence.py`](../../src/construction_pm/importing/reference_persistence.py)
(Engineering) and
[`src/construction_pm/importing/reference_enterprise.py`](../../src/construction_pm/importing/reference_enterprise.py)
(Enterprise). Both run through the existing canonical repositories. There is no
parallel store, no shadow project and no second scheduler: the import writes the
same rows a user would create, then runs the canonical schedule engine.

The import is idempotent. Each project carries a marker row in
`cubi_reference_import`; Enterprise registers carry
`cubi_reference_enterprise`. A second run on a warm database creates nothing and
runs no new calculation. The preview runtime calls both from
`open_preview_runtime`/`seed_database`, so every preview instance either has the
three projects or does not start.

### 10.1 Stored counts per project (identical for all three)

| Entity | Rows | Target |
| --- | ---: | --- |
| Activities | 180 | `p6_activity` |
| Relationships | 238 | `p6_relationship` |
| WBS nodes (root + EPS + WBS) | 129 | `p6_wbs` |
| Calendars | 3 | `p6_calendar` |
| Resources (30 labour + 10 equipment) | 40 | `p6_resource` |
| Assignments | 240 | `p6_resource_assignment` |
| Assignment spreads / actuals | 240 / 240 | `p6_resource_assignment_spread` |
| Baseline activities | 180 | `p6_baseline_activity` |
| Progress rows | 180 | `p6_activity_progress` |
| Activity codes | 180 | `p6_activity_code` |
| Constraints | 10 | `p6_activity_constraint` |
| Expenses | 45 | `p6_activity_expense` |
| Activity documents | 36 | `p6_activity_document` |

Enterprise: risks 15, issues 8, documents 15, enterprise tasks 12,
organizations 8, teams 8, responsibilities 30, contracts 5, contract packages 5,
procurement items 5, vendors 5, change requests 4, communication 1, approvals 1,
forms 1, workflows 1, timesheets 10, milestones 12. `tests/test_reference_enterprise.py`
asserts these numbers exactly and asserts that a second import creates nothing.

### 10.2 Decisions taken while applying the mapping

| # | Decision | Why | Where it is visible |
| --- | --- | --- | --- |
| D1 | The platform WBS root is `WBS-{project_id}` (`WBSParentKind.PROJECT`); the eight EPS nodes are its level-1 children and the 120 workbook WBS nodes hang below them | The platform allows exactly one project root; EPS cannot become a second root without breaking the invariant | `p6_wbs`, 129 rows per project |
| D2 | Equipment is imported into the same resource register as labour | Assignments reference `Equipment Register` IDs; without the merge, 240 assignments would be orphaned | 40 resources per project; assignments resolve |
| D3 | `activities.duration` holds the workbook's *physical percent complete*; real duration comes from `original_duration_days` / `remaining_duration_days` | The source column is a percentage, not a duration | documented here and asserted in the import counts |
| D4 | Remaining cost is derived as `baseline_budget × (100 − physical%)/100` | The source `remaining_cost_usd` contradicts its own budget and progress columns; the derived value keeps the arithmetic identity | source column recorded as unsupported, not imported as fact |
| D5 | Baselines are written once and never updated (`PRIMARY`, notes = `DEMO/SYNTHETIC immutable reference baseline`) | A baseline is an immutable snapshot; re-import must not move it | `p6_baseline`, `p6_baseline_activity` |
| D6 | CPM, float and critical path are computed by the canonical engine after persistence | The workbook explicitly says not to import them | `cubi_reference_schedule_run` |
| D7 | Baseline endpoints fall on Sundays (26 / 52 / 24 per project) although no assigned calendar works Sunday | Earned value must still be measurable from the immutable baseline; CPM is *not* changed — each activity still evaluates on its own assigned calendar | import counts `baseline_dates_on_sunday`; the EVM resolver uses a 7-day measurement calendar for imported reference projects only |

### 10.3 Canonical schedule runs

Each project has exactly one recorded run. Run ID, input/output hashes, engine
version, options count, duration and diagnostics are stored in
`cubi_reference_schedule_run` and are not hand-entered.

| Project | Run ID (prefix) | Engine | Duration | Warnings |
| --- | --- | --- | ---: | --- |
| CUBI-REF-001 | `b7883dfe4d98…` | `cubi-preview-engine.v1` | 66 ms | 0 |
| CUBI-REF-002 | `54c865cb533a…` | `cubi-preview-engine.v1` | 67 ms | 0 |
| CUBI-REF-003 | `23f726035c58…` | `cubi-preview-engine.v1` | 94 ms | 3 — negative total float on ACT-0138 (−4 d), ACT-0139 (−7 d), ACT-0141 (−3 d) |

The three warnings are real engine output for the source data; they are reported,
not suppressed and not "fixed" by editing dates.

### 10.4 Earned value from the canonical read model

Data date 2026-11-22, currency USD, ETC method `REMAINING_COST`. These are the
values the API returns; nothing is computed in the browser.

| Project | PV | EV | AC | CPI | SPI | BAC | EAC | VAC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CUBI-REF-001 | 185,888,888.737 | 185,839,305.404 | 190,671,249.93 | 0.974658 | 0.999733 | 244,999,999.80 | 249,831,944.32 | −4,831,944.52 |
| CUBI-REF-002 | 79,057,324.414 | 79,004,660.790 | 80,973,416.02 | 0.975686 | 0.999334 | 98,499,999.60 | 100,468,754.83 | −1,968,755.23 |
| CUBI-REF-003 | 107,485,532.563 | 107,453,958.489 | 110,184,861.19 | 0.975215 | 0.999706 | 137,500,000.20 | 140,230,902.90 | −2,730,902.70 |

TCPI is not produced by the canonical engine and is therefore not reported. It
is not fabricated and no placeholder is shown.

## 11. Connected surfaces and their exact sources

| Surface | Project | API it reads | Revision / data date | Status |
| --- | --- | --- | --- | --- |
| Personal Workbench | all five visible projects | `GET /api/projects` | revision per project | connected |
| Engineering project picker | `CUBI-REF-001/002/003` | `GET /api/projects` | revision 1 | connected |
| Engineering workspace | `CUBI-REF-001` | `GET /api/projects/{id}/p6/activities` etc. | revision 1 | connected — 180 rows rendered |
| AI Workbench context | `CUBI-REF-001` | `GET /api/projects/{id}/workbench/context` | revision 1, data date 2026-11-22 | connected |
| AI Workbench · project analysis | `CUBI-REF-001` | `GET /api/v2/workspace/control-room/read`, `GET …/p6/baselines`, `POST …/p6/earned-value` | revision 1 | connected — 180 activities / 129 WBS / 238 relationships / 44 critical; CPI/SPI/EAC rendered from the read model |
| AI Workbench · risk analysis | `CUBI-REF-001` | `GET /api/projects/{id}/risks` | revision 1 | connected — 15 risks |
| AI Workbench · scenario studio | — | none | — | **not connected** — no revision-bound scenario service is mounted; the studio is rendered BLOCKED and offers no control |
| AI Workbench · import staging | — | exchange preview only | — | partial by design |
| Assistant conversation | `CUBI-REF-001` | deterministic command planner | revision 1 | provider-gated — no AI provider is configured in this environment, so free-form answers are unavailable; the planner reports `INTENT_NOT_RESOLVED` rather than inventing an answer |
| Enterprise project register | `CUBI-REF-001/002/003` | `GET /api/projects` | revision 1 | connected — 5 of 5 |
| Enterprise project portal · resources | `CUBI-REF-001` | `GET /api/projects/{id}/p6/resources` | revision 1 | connected — 40 rows |
| Enterprise project portal · documents | `CUBI-REF-001` | `GET /api/projects/{id}/documents` | revision 1 | connected — 15 rows (identity and review state; no binary content) |
| Enterprise project portal · risks & issues | `CUBI-REF-001` | `GET /api/projects/{id}/risks`, `…/p6/issues` | revision 1 | connected — 15 risks, 8 issues |
| Enterprise tasks / timesheets | `CUBI-REF-001` | `GET /api/enterprise/tasks`, `GET /api/enterprise/timesheets` | revision 1 | connected — 12 tasks, 10 timesheets |
| Enterprise organization & access | `CUBI-REF-001` | `GET /api/enterprise/{organizations,teams,responsibilities}` | revision 1 | connected — 8 / 8 / 30 |
| Enterprise Risk/Document/EPS register pages | — | `GET /api/enterprise/{risks,documents,eps}` | — | these pages render the **Enterprise-owned** generic register, which is a different record set; the imported risk/document registers are read in the project portal and the assistant. They are reported as an intentional split, not silently matched |
| Enterprise dashboard / portfolio indicators | — | `GET /api/enterprise/{portlets,portfolio,evm}` | — | **503 `ENGINEERING_SOURCE_NOT_CONNECTED`** in the preview runtime; dashboards say so and do not calculate |
| Scenario Workspace | — | none | — | **not connected** — no scenario service, no separate scheduler; reachable from the assistant studio, which is BLOCKED |
| Return path | — | `/workbench/` | — | fixed in this branch: the deployment now serves the Personal Workbench shell at `/workbench/` instead of a 404 |

## 12. Browser evidence and reproduction

Captured with headless Chromium against the fixed preview
`https://cubi-web-preview-git-feat-referenc-7043fd-foroughichamshir-7811.vercel.app`
(read-only demo session) and against a local full-stack preview of the same
commit for the Enterprise document, which the deployed preview does not expose
to the anonymous planner persona. Screenshots and the JSON evidence files are in
the mission report, not committed as binary noise.

| Screenshot | Proves |
| --- | --- |
| `01-personal-workbench.png` | post-login landing, five authorized projects, both environments |
| `02-engineering-project-picker.png` | `CUBI-REF-001/002/003` selectable next to the fixtures |
| `03-engineering-CUBI-REF-001.png` | 180 activity rows rendered for the reference project |
| `04-enterprise-request-landed-on-workbench.png` | the Enterprise gate returns a planner to the Personal Workbench |
| `05-return-path-workbench.png` | `/workbench/` answers 200 with the workbench cards |
| `06-assistant-workbench.png` | the assistant pins `CUBI-REF-001` revision 1, data date 2026-11-22 |
| `08-assistant-evm-CUBI-REF-001.png` | CPI 0.974658 / SPI 0.999733 / EAC 249,831,944.32 rendered from the read model |
| `assistant-studio-schedule-scenario.png` | scenario studio BLOCKED with its reason |
| `local-enterprise-*.png`, `local-portal-*.png` | Enterprise register, portal tabs and the reference rows |

Reproduce:

```bash
python -m pytest -q tests/test_reference_projects_import.py tests/test_reference_enterprise.py \
  tests/test_reference_api.py tests/test_preview_runtime.py
node apps/web/e2e/preview-e2e.mjs      # local full-stack browser E2E
```

## 13. Twenty-point proof

| # | Requirement | Evidence | Verdict |
| --- | --- | --- | --- |
| 1 | Repo inspected before changes; main SHA recorded | `6bf5088d` → `42f5e967` → `fa62d4fd` | done |
| 2 | No environment, admin account or login path changed | no env/secret/account change in any commit; preview session is the existing demo one | done |
| 3 | Three projects registered as demo reference projects | `cubi_reference_import` COMPLETE × 3 | done |
| 4 | Visibility for authorized preview users without weakening tenant isolation | rows joined through `preview_project` + `preview_project_member`; `cubi-preview-tenant` only | done |
| 5 | Not auto-enabled in production | import runs from the preview runtime only; production selects its own runtime | done |
| 6 | Engineering is the single source of truth | all schedule/resource/cost tables are the canonical ones; no parallel store | done |
| 7 | Enterprise reads Engineering through APIs | portal reads `/api/projects/{id}/…` | done |
| 8 | All 94 sheets analysed with counts, PK/FK and dispositions | inventory CSV + §2–§6 | done |
| 9 | Nothing silently dropped | every sheet has a disposition; unmapped Enterprise sheets listed explicitly | done |
| 10 | Project Master, EPS, WBS, activities, relationships, calendars persisted | 1 project, 129 WBS nodes, 180 activities, 238 relationships, 3 calendars each | done |
| 11 | Baselines immutable | baseline written once; re-import creates nothing | done |
| 12 | Resources, assignments, loading, progress, cost persisted | 40 resources, 240 assignments, 240 spreads, 180 progress rows | done |
| 13 | Canonical CPM executed with a recorded run | three `SUCCESS` runs with run ID, hashes, options, duration, warnings | done |
| 14 | No CPM/float hand-entered | every date/float in the UI comes from the engine snapshot | done |
| 15 | Capacity/histogram and baseline-vs-actual validated | capacity segments 93, rate facts 123, baseline comparison reads the immutable baseline | done |
| 16 | All EVM indicators calculated, not fabricated | PV/EV/AC/CV/SV/CPI/SPI/ETC/EAC/VAC per project; TCPI reported as not produced | done |
| 17 | Enterprise, assistant and scenario connected to the same project IDs | §11 table, including the honest not-connected rows | done (partial where stated) |
| 18 | Personal Workbench landing and constant return path | screenshots 01/04/05; `/workbench/` fix | done |
| 19 | Real browser evidence on the fixed Preview | screenshots 01–08 + JSON, fixed alias URL | done |
| 20 | Tests, migrations, APIs and PRs reported | Python suite, E2E suites, PR #2123 (merged) and #2124 (this branch) | done |

## 14. Not claimed

- No PostgreSQL/Supabase verification: the preview runtime is SQLite; a
  PostgreSQL run needs `CONSTRUCTION_PM_DATABASE_URL` and is not asserted here.
- No AI provider is configured, so free-form conversation is unavailable; the
  deterministic planner is what answers, and it refuses to invent data.
- No scenario service exists, so the Scenario Workspace is reported as not
  connected rather than simulated.
- Enterprise portlet/indicator/EVM routes remain a preview-runtime stub (503).
- Committed baseline dates on Sundays are a source property; the measurement
  calendar that makes EVM possible is documented in D7 and does not alter CPM.

## 13. Durable registration in PostgreSQL

The same frozen bundle (`sha256 0848454d…`, contract
`cubi-reference-import-bundle.v1`) is registered as real tenant data in the
operational database; it is not a per-page fixture.

| Concern | Implementation |
| --- | --- |
| Entry point | `scripts/import_reference_projects.py --tenant <tenant-id>` (adds migrations 14/15 first) |
| Import logic | `construction_pm.importing.reference_persistence.ensure_reference_projects` |
| PostgreSQL adapter | `construction_pm.importing.reference_postgres.ensure_reference_projects_postgres` |
| Journal | `cubi_reference_import` (bundle hash, revision, per-domain counts), `cubi_reference_schedule_run` (engine manifest), `cubi_reference_project` (shared-visibility registry) |
| Engineering storage | `project_lifecycle_projects`, `wbs_master`, `activity_master`, `activity_wbs_assignment`, `relationship_master`, `constraint_master`, `calendar_*`, `p6_resource_*`, `p6_baseline*`, `p6_activity_period_actual`, `project_budget_*`, `project_schedule_settings`, `schedule_input_snapshot`, `schedule_calculation_context` |
| Enterprise storage | `project_risk`, `p6_issue`, `project_documents`, `enterprise_records` (contracts, procurement, milestones, approvals, teams, responsibilities, timesheets…), `enterprise_tasks` |
| Idempotency | Existing project → skip, re-register in `cubi_reference_project`, no row rewrite. Second run: 0 new rows. |
| Visibility | `cubi_reference_project` is unioned into the project list/get queries, so every authenticated user of the tenant sees the three projects with **zero** `project_lifecycle_memberships` rows. Writes still follow `RoleBasedAuthorizationPolicy`. |
| Calculated values | Never imported. CPM/float/critical path are produced by `evaluate_schedule_snapshot`; the manifest records engine/rules version and an output hash. EVM is read from the canonical read model. |

Local PostgreSQL 14 evidence (fresh database, then re-run):

| Project | Activities | WBS | Risks | Documents | Issues | Tasks | Import status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| CUBI-REF-001 | 180 | 129 | 15 | 15 | 8 | 12 | `COMPLETE`, missing `{}` |
| CUBI-REF-002 | 180 | 129 | 15 | 15 | 8 | 12 | `COMPLETE`, missing `{}` |
| CUBI-REF-003 | 180 | 145 | 15 | 15 | 8 | 12 | `COMPLETE`, missing `{}` |

Explicit unmappable report (returned by every import, also printed by the CLI):

| Bundle register | Handling |
| --- | --- |
| `commitments` (8/project) | No canonical commitment entity exists. Reported as `unsupported`; not forced into budget or procurement rows. |
| `actual_costs` (8/project) | The authoritative cost facts are the per-activity actuals and expenses, imported into `p6_activity_period_actual` and `p6_expense`; the standalone summary register is reported as `unsupported`. |
| `cost_periods` (23/project) | The cost calendar is imported into `p6_financial_period` and drives schedule settings; the standalone register is reported as `unsupported`. |
| `timesheets` (10/project) | Kept with `resource_id` / week-ending hours; no `user_id` is invented. |
| `document_register` | Register identity and revision hash only; no binary content is claimed. |
