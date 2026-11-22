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

Nothing in this document writes to a database. Persistence happens later through
the canonical Engineering and Enterprise services only.

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
