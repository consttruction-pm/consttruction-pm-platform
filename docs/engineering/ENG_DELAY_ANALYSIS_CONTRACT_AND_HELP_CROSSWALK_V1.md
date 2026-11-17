# ENG — Technical Delay Analysis Contract & Help Crosswalk (V1)

**Status:** Research / product contract proposal; not implemented.  
**Capability owner:** Engineering (technical schedule and time-impact analysis).  
**Commercial consumer:** Enterprise ENT-13 Claims & Disputes.  
**Source baseline:** P6 EPPM Version 26 HTML Help; Primavera Cloud V26 Help is additive; P6 Professional is comparison-only.  
**Repository baseline inspected:** `main` at `20e8b6509704c8225bba81e722a835b5b1bb1ea0` (2026-11-17).

## 1. Executive decision and ownership boundary

CUBI needs a first-class, auditable **Technical Delay Analysis** capability. It is not the same thing as a baseline variance report, a schedule-health check, a disruption/productivity study, or a commercial claim determination.

The correct ownership split is:

| Concern | Owner | System responsibility |
|---|---|---|
| Current schedule, activities, relationships, calendars, actuals, data date, baseline and CPM calculations | Engineering | Authoritative schedule facts and immutable schedule snapshots |
| Technical delay analysis | Engineering | Reproducible analysis of schedule impact, critical/near-critical paths, windows, concurrency and technical time findings |
| Disruption / productivity analysis | Engineering evidence + specialist productivity method | Compare planned/earned/actual quantities and resource productivity; keep distinct from critical-path time analysis |
| Claim notices, party submissions, response, objection, counterclaim, determination, settlement | Enterprise ENT-13 | Bilateral contract workflow and private party working papers |
| Contract entitlement, notice compliance, liability, LD rates/caps, prolongation valuation, damages and final quantum | Authorized human/contract/legal process in ENT-13 | Record contract-grounded determinations; do not infer from schedule variance |
| Workbench | Non-owning projection | Notifications, assigned actions and due dates only |

**Non-negotiable:** Enterprise must consume a versioned, immutable Engineering result. It must not calculate CPM, recalculate float, determine critical path, run a second time-impact engine, or infer legal entitlement. Engineering findings are technical evidence, not a legal decision.

This split is consistent with #2009 (technical Delay Analysis is a separately owned Engineering capability) and #2016/#2002 (ENT-13 owns claims, bilateral submissions and evidence archive). This document does not take over Hasan's ENT-13 implementation.

## 2. What the official product Help establishes

### 2.1 P6 EPPM V26 — normative native behavior

| Official topic | Native behavior evidenced by Help | CUBI disposition | Acceptance trace |
|---|---|---|
| [P6 EPPM V26 Help TOC](https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm) | The exact V26 TOC contains baseline, scheduling, float, critical activities, progress, relationships, earned value and schedule-check topics; it contains no topic titled Delay Analysis, Time Impact Analysis, EOT entitlement or Claim Digger. | Normative inventory. Absence is stated narrowly as a TOC/topic review finding, not a claim that no external/custom implementation can exist. | DA-17; DA-18 |
| [Oracle P6 EPPM / Primavera Cloud feature comparison matrix](https://docs.oracle.com/cd/E80480_01/English/admin/p6_eppm_migration_guide/246421.htm) — product-family cross-check, not a V26 Help topic | Matrix distinguishes (a) an Activities feature row named Schedule Comparison marked available in P6 EPPM Web and Cloud, from (b) the combined Claim Digger and Schedule Comparison capability marked for P6 EPPM Client, P6 Professional and Cloud but not EPPM Web; Project Differences Report is client/Professional, while point-in-time comparison and interactive scorecard/Gantt/drill-down are Cloud. | Do not overstate either direction: EPPM Web has baseline/variance fields and an Activities-level Schedule Comparison entry, but not the client/Professional Claim Digger + Project Differences Report workflow or Cloud's point-in-time comparison page. Validate the exact deployed EPPM build and UI surface before parity claims. | DA-18; DA-19 |
| [Working with Baselines](https://docs.oracle.com/cd/G48897_01/p6help/en/6687.htm) | Defines a baseline as a copy/snapshot used to track cost, schedule and performance; baseline types, Project Baseline and User's Primary Baseline are described. EPPM permits at most two baselines for comparisons at a time. Baselines can be updated or restored; the Help also notes up to three user baselines in P6 Professional. | Freeze a separate CUBI analysis input snapshot and hash. Do not treat a native P6 baseline as inherently immutable: its update/restore lifecycle must be captured. Do not import Professional's three-baseline note into EPPM behavior.  DA-02; DA-03a |
| [Creating Baselines](https://docs.oracle.com/cd/G48897_01/p6help/en/7961.htm) and [Updating Baselines](https://docs.oracle.com/cd/G48897_01/p6help/en/93166.htm) | Create/name/type baselines, assign Project Baseline/User's Primary Baseline, convert projects to baselines, restore baselines and update selected data. | Record baseline ID/type/designation, last update date and the exact frozen export/snapshot hash. A later update creates a new analysis input revision.  DA-02; DA-03a |
| [Scheduling Projects](https://docs.oracle.com/cd/G48897_01/p6help/en/7878.htm) | Schedule projects with Schedule (F9); privileges can disable scheduling; multiple open projects can be scheduled together using the chosen project's advanced options. | Record exact project set, scheduler run, data date and effective scheduling options. Do not reschedule a historical source in place for forensic reconstruction.  DA-01; DA-03b |
| [Schedule Project Log Dialog Box](https://docs.oracle.com/cd/G48897_01/p6help/en/99347.htm) and [Scheduling Settings Section](https://docs.oracle.com/cd/G48897_01/p6help/en/99348.htm) | Log exposes read-only settings, statistics, errors, warnings, results and exceptions. Settings include out-of-sequence progress logic (Retained Logic / Progress Override / Actual Dates), critical float threshold, Total Float calculation (Start Float / Finish Float / Smallest Value), relationship-lag calendar and multiple float paths. | Capture the full log and settings as analysis provenance; these are not optional metadata because they can change dates, criticality and float.  DA-01; DA-03b |
| [About Float](https://docs.oracle.com/cd/G48897_01/p6help/en/46930.htm) | Defines Free Float and Total Float; Total Float uses CPM and is calculated from early/late dates, with scheduling constraints also relevant. | Record the selected float method and calendar/constraint context. Do not equate activity float with contractual delay days.  DA-03b; DA-04; DA-06 |
| [Working with Critical Activities](https://docs.oracle.com/cd/G48897_01/p6help/en/6679.htm) and [Configuring Advanced Scheduling Options](https://docs.oracle.com/cd/G48897_01/p6help/en/37940.htm) | EPPM can identify critical activities by a maximum total-float threshold or longest path and can calculate multiple float paths using Total Float or Free Float; sub-critical paths can be displayed. | Analysis must preserve criticality rule and path-end activity. A total-float threshold alone can flag activities not driving project completion; path status is not proof of causation or responsibility.  DA-03b; DA-04; DA-06 |
| [Check Schedule Dialog Box](https://docs.oracle.com/cd/G48897_01/p6help/en/91574.htm) and [Check Schedule Settings Tab](https://docs.oracle.com/cd/G48897_01/p6help/en/101232.htm) | Checks include missing logic/dangling starts and finishes, negative/long lags, relationship types, hard/soft constraints, large/negative float, large durations, invalid progress dates, missing resources/costs, late activities and Baseline Execution Index (BEI). | Preserve each enabled check, threshold, denominator/exclusion and result. These are schedule-quality diagnostics, not forensic method selection or a pass/fail entitlement rule.  DA-03; DA-03a |
| [Available Columns of the Activities Page](https://docs.oracle.com/cd/G48897_01/p6help/en/47261.htm) | Exposes actual/baseline activity fields, critical and longest-path flags, predecessors/successors and relationship details, Float Path/Float Path Order, baseline dates, durations and percent-complete values. | Use as native source fields; preserve exact baseline identity, activity identity and source revision.  DA-04; DA-06 |
| [Available Columns of the EPS Page](https://docs.oracle.com/cd/G48897_01/p6help/en/47274.htm) | Defines Data Date, Last Scheduled Date, baseline start/finish/duration, Total Float, start/finish variance and EV measures. Published/summarized EV always uses Project Baseline and can differ from live-data areas. | Preserve data date, schedule freshness, selected baseline and live vs published/summarized mode. Do not mix unlike calculation bases.  DA-01; DA-02; DA-17 |
| [Defining Earned Value Calculations for WBS Elements](https://docs.oracle.com/cd/G48897_01/p6help/en/48063.htm) | EVM compares planned and actual cost/work; EV = Performance % Complete × BAC, with configurable WBS techniques for performance percent complete and ETC. | EV/SPI/SV are performance measures, not time-impact or critical-path delay findings; retain the selected WBS technique and baseline basis.  DA-17 |
| [Variance Report — P6 EPPM Reporting Guide](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-reports/variancereport-81320a.html) | Sample report lists activities with schedule variance relative to data date, including baseline/current dates, variance and Total Float. This is a Reporting Guide artifact, not a forensic analysis topic in HTML Help. | Useful screening evidence only; it does not prove event causation, critical delay, concurrency, entitlement or damages.  DA-06; DA-17 |

**Source interpretation and scope of the negative finding:** the EPPM V26 TOC and the topic-level sources above establish native schedule facts, baseline lifecycle, CPM scheduling, criticality/float, schedule quality checks, earned-value and variance reporting. A targeted review of that TOC and these exact V26 topics did not identify a native topic/workflow for forensic Delay Analysis, TIA, windows analysis, EOT entitlement, contractual concurrency adjudication, disruption valuation or damages calculation. This is a documented Help-scope finding, not a universal assertion about every Oracle add-on, partner product, integration or customer customization.

**Important product nuance:** EPPM Web does support baseline-related activity fields, critical/longest-path indicators, multiple float paths, schedule checks and schedule logs. Therefore CUBI should reuse these authoritative facts and not falsely claim EPPM has no baseline comparison at all. What is absent from the reviewed native Help set is the governed forensic method workflow and contract determination layer.

**Snapshot integrity rule:** Oracle Help explicitly permits updating and restoring baselines. Accordingly, the analysis engine must freeze a separate immutable copy/export of the selected schedule and baseline inputs (including their hashes) at analysis creation. Merely storing a mutable P6 baseline ID is insufficient for reproducibility.

### 2.2 P6 EPPM Client / Professional V26 — comparison-only surfaces, not EPPM Web parity

- [Comparing Current and Baseline Schedules — P6 Professional V26](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/62723.htm) documents the Professional client workflow for current/baseline bars, baseline fields and variance bars. Acceptance trace: DA-19.
- The EPPM V26 [Working with Baselines](https://docs.oracle.com/cd/G48897_01/p6help/en/6687.htm) topic explicitly says EPPM can select at most two baselines for comparisons and separately notes up to three user baselines in P6 Professional. Keep this distinction explicit. Acceptance trace: DA-02, DA-03a, DA-19.
- Oracle's product-family matrix has two similarly named rows that must not be conflated (acceptance trace: DA-18 and DA-19): it marks an Activities-level **Schedule Comparison** feature as available in EPPM Web and Cloud; separately, the combined **Claim Digger and Schedule Comparison** feature is not marked for EPPM Web, and the **Project Differences Report** is listed for P6 EPPM Client / P6 Professional. The Cloud page provides its own point-in-time comparison interface. The matrix is a product-family cross-check, not a replacement for the V26 Help TOC.
- Therefore CUBI must preserve EPPM Web's native baseline/variance/Activities comparison surface where present, but must not claim that the P6 Professional Claim Digger / Project Differences Report workflow is available in EPPM Web. Likewise, Cloud's point-in-time comparison, interactive variance panel and merge mode are additive Cloud behavior, not EPPM Web parity.

### 2.3 Primavera Cloud V26 — additive comparison

| Official topic | Cloud behavior | CUBI disposition | Acceptance trace |
|---|---|---|---|
| [Schedule Comparison Overview](https://primavera.oraclecloud.com/help/en/user/191095.htm) | Compares current schedule, baseline, scenario or historical point; identifies added/deleted/changed activities and values; may initiate merge of selected activities. The comparison view is read-only except view settings; source schedule merge is a separate mutating workflow. | Candidate for a separate schedule-version comparison capability. Keep merge disabled from forensic analysis; never mutate frozen analysis inputs. | DA-18; DA-19 |
| [Schedule Comparison](https://primavera.oraclecloud.com/help/en/user/193627.htm) | Cloud feature entry lists comparison of baselines, scenarios, current schedule and history, with Merge Mode. | Additive Cloud-only feature reference; not EPPM Web parity and not forensic delay analysis. | DA-18; DA-19 |
| [Compare Two Versions of a Project Schedule](https://primavera.oraclecloud.com/help/en/user/191096.htm) | Comparison is read-only; schedule versions should be scheduled for accurate calculated-value comparison; date variance uses project calendar. | Record exact schedule versions, calendar basis and scheduling status. Do not assume calendar treatment is identical to EPPM activity variance. | DA-18; DA-19 |
| [Schedule Health Score Overview](https://primavera.oraclecloud.com/help/en/user/149130.htm) | Quality checks run on current schedule, baseline or scenario and produce metric scores; criteria, weights and settings are configurable and results can be exported/reported. | Additive quality diagnostic only; never a forensic delay conclusion. | DA-03 |
| [Baselines Overview](https://primavera.oraclecloud.com/help/en/user/89344_1.htm) | Cloud supports up to five project baselines, with original/current/supplementary/unofficial categories, past baseline dates and three user baseline preferences; baselines can be opened and updated. | Useful comparative model; do not overwrite EPPM's baseline-as-separate-project lifecycle, two-baseline comparison limit or update/restore semantics with Cloud-specific behavior. | DA-02; DA-03a; DA-18 |

Cloud comparison may improve the CUBI user experience, but it is not a substitute for a forensic method, a legal determination or a separate analysis record.

## 3. Methodology boundary: delay is not disruption

The [SCL Delay and Disruption Protocol, 2nd edition](https://www.scl.org.uk/sites/default/files/documents/SCL_Delay_Protocol_2nd_Edition_Final.pdf) distinguishes delay (time impact, especially critical delay to completion) from disruption (disturbance/hindrance/interruption to planned working methods and productivity). It also explains that the monetary consequences may overlap but require different substantiation. The [AACE RP 29R-03 Forensic Schedule Analysis](https://web.aacei.org/docs/default-source/rps/29r-03.pdf) is a technical reference for CPM-based forensic schedule analysis. Its scope guidance emphasizes method categorization/evaluation and professional judgment; the recommended practice is not a universal prescriptive entitlement rule.

Therefore:

- **Delay analysis** asks what happened to time, milestones and completion, and whether an event affected the critical or near-critical path in the relevant analysis window.
- **Disruption analysis** asks whether productivity/efficiency was reduced relative to a defensible plan or benchmark, even when the affected activity is not critical to project completion.
- A late activity is not automatically critical delay, compensable delay or employer/contractor responsibility.
- A schedule variance is an observation, not proof of causation, notice compliance, entitlement or liability.
- Time impact and money valuation must remain linked but separate: delay findings may support EOT or time-related cost inputs; disruption findings may support productivity/loss inputs; contract terms determine what is recoverable.
- Do not combine delay, disruption, acceleration, prolongation and direct damages into one opaque “claim amount”.

## 4. Proposed Engineering analysis lifecycle

1. **Register event:** identify event, event type, affected work, start/end/known dates, source evidence, notifier and confidence. Link to existing project/contract/claim references without copying evidence bytes.
2. **Freeze analysis inputs:** choose the schedule revision, data date, approved baseline, analysis window(s), calendars, actuals cut-off, relationship logic, float settings, schedule run and relevant event/evidence revisions.
3. **Quality gate:** run EPPM Check Schedule and capture the selected options/thresholds, report and scheduler log. Record missing predecessors/successors, dangling starts/finishes, negative/long lags, relationship type mix, hard/soft constraints, large/negative float, large remaining durations, invalid progress dates, missing resources/costs, late activities and BEI. Record exclusions and denominators because Oracle's checks do not include every activity category. Analyst must explain any method limitation.
4. **Select method:** analyst chooses the method appropriate to available contemporaneous records and contract/project circumstances; record why alternatives were rejected. Never auto-select a method solely from data availability.
5. **Run analysis:** execute against immutable schedule snapshots and immutable event/evidence references. No source schedule mutation.
6. **Review and challenge:** second-person technical review, assumptions/limitations, opposing-party observations and response references. Re-run creates a new analysis revision; it never overwrites a prior result.
7. **Publish technical result:** immutable result with input/output hashes, method/version, findings, confidence, limitations and sign-off.
8. **Consume in ENT-13:** Enterprise links the result to claim submissions, EOT requests, responses, counterclaims, determinations and settlements. Contract/legal decision remains human and contract-grounded.

## 5. Method catalogue and selection controls

The following are method families to support through a governed analysis engine, not an instruction to implement all methods at once or to declare one universally correct:

| Method family | Typical use / required inputs | Key limitations to record |
|---|---|---|
| Time Impact Analysis (TIA) | Contemporaneous update immediately before/at event; validated fragnet; logic ties; calendars; data date; accepted assumptions. | Results depend on update quality, fragnet logic, status cut-off, float and method conventions. |
| Windows / time-slice analysis | Multiple reliable schedule updates and contemporaneous progress records; analyse each window separately. | Update frequency/quality, changing critical path and missing periods can bias results. |
| As-Planned vs As-Built | Reliable approved plan plus actual start/finish/progress chronology. | Planned logic may not reflect actual execution; actual dates alone do not establish cause or responsibility. |
| Impacted As-Planned | Baseline plus modeled event fragnets. | May be weak where actual progress, resequencing or mitigation materially changed the plan. |
| Collapsed As-Built / But-For | Reliable as-built logic and transparent removal of selected delay events. | Highly assumption-sensitive; must disclose logic reconstruction, event selection and counterfactual limitations. |
| Time-slice / contemporaneous critical path | Statused schedule snapshots and event chronology per window. | Requires consistent updates and explicit treatment of changing critical/near-critical paths. |

Every method selection must record: method identifier/version, analyst, selection rationale, schedule quality score/diagnostics, schedule and baseline revisions, analysis windows, event/fragnet assumptions, calendars, data date, actuals status, relationship logic, total-float and criticality definition, out-of-sequence progress treatment, concurrency approach, mitigation/acceleration treatment, exclusions and limitations.

## 6. Proposed versioned Engineering request/result contract (conceptual only)

### 6.1 Request envelope

| Field | Requirement |
|---|---|
| `tenant_id`, `project_id` | Derived from authenticated context; never trusted from a client payload as authorization authority. |
| `analysis_id`, `analysis_revision` | Stable identity and immutable revision; idempotent request key for retries. |
| `event_refs[]` | Event IDs plus exact revisions; event records remain owned by their canonical source. |
| `schedule_snapshot_ref` | Immutable schedule snapshot ID/revision and content hash. |
| `baseline_snapshot_ref` | Explicit baseline ID/revision/type and hash; missing baseline is a declared limitation, not silently substituted. |
| `data_date`, `analysis_windows[]` | Canonical instant/date, project timezone and window boundaries. Preserve timezone and working-calendar semantics. |
| `method` | Approved method ID/version, not arbitrary user code or free-form executable expression. |
| `assumptions[]` | Typed, versioned and attributable assumptions with rationale and approver. |
| `schedule_settings_ref` | Scheduler run/settings snapshot: calendars, relationship lag calendar, float calculation, critical path definition, out-of-sequence progress mode, constraints and relevant options. |
| `evidence_refs[]` | Authorized document/daily-report/evidence object IDs, exact revisions and hashes; do not duplicate original bytes. |
| `requested_by`, `requested_at` | Server-authenticated actor and UTC timestamp; preserve actor's organization/party role as an attributed fact. |

### 6.2 Result envelope

- Stable `analysis_id`, revision, status, created/completed timestamps and source input hashes.
- Project, schedule snapshot, baseline snapshot, data date, analysis windows and schedule settings references.
- Method ID/version, analyst/reviewer identities, rationale, assumptions and sign-off.
- Schedule quality diagnostics and limitations.
- Event-by-event technical findings: affected activities/WBS, before/after dates, durations, float, critical/near-critical path membership, milestone/completion movement, path changes and evidence references.
- Concurrency findings by window with the exact definition and approach used; distinguish true concurrent delay from mere overlapping calendar periods.
- Mitigation/acceleration observations and any modeled effect, with provenance.
- Separate delay and disruption result sections; no conflated totals.
- Reproducibility manifest: engine/build version, calculation configuration, input hash, output hash and deterministic rerun identity.
- Explicit disclaimer/state: technical analysis only; no contractual entitlement, liability, notice validity or final monetary quantum determined.

### 6.3 State model

`requested → validating → blocked_on_input | ready → running → completed | failed`

A completed analysis is immutable. Corrections or new evidence produce a new revision linked by `supersedes_analysis_id`; never mutate the original result. Failed runs preserve diagnostics but do not publish partial findings as completed. Re-run and retry are idempotent for the same request key and exact input hashes.

## 7. Neutral two-sided commercial outputs

The Engineering result should expose the same technical facts to authorized Employer and Contractor representatives, subject to project/contract/party/object access. The commercial layer may organize those facts into different claim positions without changing the underlying analysis.

| Output category | Engineering provides | ENT-13 / contract process decides |
|---|---|---|
| Extension of Time | Technical completion/milestone impact and supported duration range, with concurrency/criticality and limitations. | Contractual EOT entitlement, notice compliance, granted days and determination. |
| Liquidated damages exposure | Relevant completion date and technically supported delay windows. | Contract rate, caps, grace periods, excusable/compensable treatment and actual LD assessment. |
| Prolongation / time-related cost | Delay windows and time-related resource/overhead evidence references. | Contract recoverability, allowable rates, proof, causation, mitigation and quantum. |
| Disruption / loss of productivity | Measured productivity, benchmark, affected work and method limitations. | Recoverability, causation, contractual valuation and quantum. |
| Acceleration / mitigation | Recorded actions, resource/time changes and schedule effect. | Instruction/authorization, recoverability, reasonableness and cost entitlement. |
| Employer counterclaim | Technical event/time facts and relevant records. | Contractual breach, responsibility, LD or damages decision. |
| Contractor claim | Technical event/time facts and relevant records. | Notice, entitlement, relief and monetary valuation. |

Do not calculate a single combined “employer loss” or “contractor claim amount” from schedule variance alone. Currency, contract rates, taxes, caps, mark-ups, exclusions, interest and legal rules are controlled by the relevant contract and authorized commercial process.

## 8. Security, evidence and audit constraints

- Every operation is tenant-, project-, object- and permission-scoped; never trust caller-supplied actor, tenant or party identity.
- Schedule facts and calculations are read from Engineering's authoritative store. Enterprise only receives the permitted result projection.
- Claim party membership does not confer access to another party's private draft, working paper, evidence classification or undisclosed attachment.
- Every event/evidence link resolves to an authorized object and exact revision; preserve source hashes and retention controls.
- Revoke access for future reads/exports/downloads without deleting historical audit evidence or rewriting immutable analysis.
- Analysis result publication, audit append and revision creation must be atomic.
- Export includes actor, timestamp, method/version, source references, hash manifest and limitations; no hidden data leakage across parties.
- No arbitrary SQL, formulas, scripts, external URLs or user-provided executable analysis methods.
- No result can mutate a schedule, baseline, actual, cost, progress or source evidence record.

## 9. Acceptance scenarios

| ID | Scenario | Expected outcome |
|---|---|---|
| DA-01 | Run TIA against a frozen, quality-checked update and approved baseline. | Result reproduces from exact snapshot refs and records method, data date, windows and hashes. |
| DA-02 | Baseline is missing or changed after request. | Request blocks or explicitly records missing/changed baseline; no silent fallback to current schedule. |
| DA-03 | Schedule contains open ends, dangling starts/finishes, negative/long lags, non-FS relationships, hard/soft constraints, large/negative float, invalid progress dates, late activities or weak BEI. | EPPM Check Schedule settings, targets, exclusions and report are preserved; method selection requires documented analyst rationale. |
| DA-03a | EPPM baseline is updated after an analysis request. | Analysis uses its frozen input copy/hash; later native baseline update does not alter prior analysis evidence. |
| DA-03b | Critical activities are configured by total-float threshold vs longest path; multiple float paths enabled/disabled. | Result records criticality rule, float calculation method and multiple-path configuration; subcritical paths are not omitted silently. |
| DA-04 | Critical path changes across windows. | Each window reports path membership and milestone movement separately; no single static path assumption. |
| DA-05 | Two events overlap in calendar time. | System does not automatically declare concurrency; analyst documents path effect, causation assumptions and method. |
| DA-06 | Delay exists on a non-critical activity. | Report distinguishes activity delay from project completion delay. |
| DA-07 | Productivity drops while completion date is unchanged. | Disruption analysis remains separate and may exist without critical delay. |
| DA-08 | New evidence is submitted after a completed analysis. | New analysis revision is created; prior result and evidence manifest remain immutable. |
| DA-09 | Employer and Contractor access the same published technical result. | Both see authorized common technical facts; neither can enumerate the other's private claim workpapers. |
| DA-10 | User lacks permission for a source activity, cost or evidence object. | Source values are withheld; no inference or direct-ID/export bypass. |
| DA-11 | ENT-13 requests analysis for a claim. | Engineering receives versioned request; Enterprise stores only result reference/projection, not a second CPM calculation. |
| DA-12 | Technical report is exported for a determination. | Report carries source snapshot refs, method, assumptions, limitations, review and reproducibility manifest. |
| DA-13 | Retry same request with same idempotency key and inputs. | No duplicate completed analysis; same result identity returned. |
| DA-14 | Same request key is reused with different input hashes. | Conflict is rejected and audited. |
| DA-15 | Analyst changes method or assumptions. | New revision with explicit supersedes link; prior report remains retrievable. |
| DA-16 | A party's membership/disclosure is revoked. | Future reads/exports/downloads are denied; immutable audit and frozen submission evidence remain preserved under retention rules. |
| DA-17 | A reviewer treats SPI, Schedule Variance (EV minus PV), or a variance-report row as days of critical delay or as causation proof. | Reject the inference; preserve EVM/report metrics as performance indicators only and require CPM/path/window evidence for time-impact findings. |
| DA-18 | A user requests P6 Professional Claim Digger / Project Differences Report behavior inside EPPM Web, or Cloud point-in-time comparison/merge behavior inside the analysis record. | Reject product-family conflation while retaining the EPPM Web Activities-level Schedule Comparison and baseline/variance capabilities that Oracle documents. Keep source/analysis snapshots immutable. |
| DA-19 | A parity reviewer equates EPPM Web's baseline/variance fields or Activities-level Schedule Comparison with the Professional Claim Digger / Project Differences Report or Cloud's full point-in-time Schedule Comparison page. | Record each product-family surface separately; no unsupported equivalence, menu promise or migration of Cloud/Professional-only behavior. |

## 10. Explicit non-goals / deferred decisions

- This is not a legal advice or automatic contract entitlement engine.
- No automatic responsibility allocation, concurrency apportionment, EOT grant, LD imposition, damages award or settlement recommendation.
- No duplicate CPM/scheduler, resource leveling, EVM or project cost engine.
- No direct copy of P6 Professional Claim Digger into EPPM Web.
- No Cloud schedule merge behavior in the first technical analysis slice.
- No duplicate evidence/document storage or second Form Builder.
- No coding, API, database schema, migration, UI, menu or production route is authorized by this document.

## 11. Source and governance references

### Product Help
- [P6 EPPM Version 26 HTML Help TOC](https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm)
- [Working with Baselines](https://docs.oracle.com/cd/G48897_01/p6help/en/6687.htm); [Creating Baselines](https://docs.oracle.com/cd/G48897_01/p6help/en/7961.htm); [Updating Baselines](https://docs.oracle.com/cd/G48897_01/p6help/en/93166.htm)
- [Scheduling Projects](https://docs.oracle.com/cd/G48897_01/p6help/en/7878.htm); [Schedule Project Log](https://docs.oracle.com/cd/G48897_01/p6help/en/99347.htm); [Scheduling Settings in Log](https://docs.oracle.com/cd/G48897_01/p6help/en/99348.htm)
- [About Float](https://docs.oracle.com/cd/G48897_01/p6help/en/46930.htm); [Working with Critical Activities](https://docs.oracle.com/cd/G48897_01/p6help/en/6679.htm); [Configuring Advanced Scheduling Options](https://docs.oracle.com/cd/G48897_01/p6help/en/37940.htm)
- [Check Schedule Dialog](https://docs.oracle.com/cd/G48897_01/p6help/en/91574.htm); [Check Schedule Settings](https://docs.oracle.com/cd/G48897_01/p6help/en/101232.htm)
- [Available Columns of Activities](https://docs.oracle.com/cd/G48897_01/p6help/en/47261.htm); [Available Columns of EPS](https://docs.oracle.com/cd/G48897_01/p6help/en/47274.htm); [Defining Earned Value Calculations for WBS](https://docs.oracle.com/cd/G48897_01/p6help/en/48063.htm)
- [P6 Professional V26 Comparing Current and Baseline Schedules](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/62723.htm) — comparison only.
- [Oracle P6 EPPM vs Primavera Cloud feature comparison](https://docs.oracle.com/cd/E80480_01/English/admin/p6_eppm_migration_guide/246421.htm) — product-family matrix; distinguish the Activities Schedule Comparison row from Claim Digger / Project Differences Report and Cloud point-in-time comparison.
- [Primavera Cloud V26 Help TOC](https://primavera.oraclecloud.com/help/en/user/toc.htm)

### Forensic methodology references
- [Society of Construction Law — Delay and Disruption Protocol, 2nd Edition (2017)](https://www.scl.org.uk/sites/default/files/documents/SCL_Delay_Protocol_2nd_Edition_Final.pdf)
- [AACE International RP 29R-03 — Forensic Schedule Analysis](https://web.aacei.org/docs/default-source/rps/29r-03.pdf)

### Repository governance
- [#2009 — Engineering contracts, menu/access placement and non-interference queue](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2009)
- [#2016 — ENT-13 party-specific claim forms and bilateral workflow](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2016)
- [#2002 — ENT-13 Claim Day Archive and immutable evidence packages](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2002)
- [#2041 — this research work package](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2041)

## 12. Verification and status

- Main SHA at original preflight: `20e8b6509704c8225bba81e722a835b5b1bb1ea0`; refreshed main SHA before this V26 crosswalk correction remained the same.
- V26 Help links were checked against the official Oracle TOC and exact topic pages on 2026-11-17. The EPPM topic IDs/URLs above use the `G48897_01/p6help/en` release-26 Help namespace; no V23 topic is used as authority.
- Exact target path was absent from the main recursive tree.
- No root or nested `AGENTS.md` was present in the main recursive tree at preflight.
- Open PR path preflight sampled the active Engineering/Enterprise documentation and implementation PRs; none of the checked PRs modified this exact target path. PR #2008 touches adjacent ENG-10/ENG-11/ENG-12 documents, not this new file.
- This is a documentation-only artifact. No tests, API, schema, runtime behavior, browser behavior or deployment were changed or claimed.
- Crosswalk corrections specifically clarify EPPM's native baseline/variance fields, two-baseline comparison limit, mutable baseline update lifecycle, exact critical-path/float settings, Check Schedule diagnostics and EVM semantics.
- Product-family comparison was tightened after reviewing Oracle's feature matrix: EPPM Web's Activities-level Schedule Comparison is not the same thing as the combined Claim Digger / Schedule Comparison capability and Project Differences Report in the client/Professional columns, nor Cloud's point-in-time Schedule Comparison page. This avoids a false-negative parity claim.
- Cloud Schedule Comparison's read-only Compare Mode is distinguished from its separate Merge Mode; Cloud baseline categories and count are not imported into EPPM semantics.


## 13. Repository implementation boundary verified against current main

The following existing components were inspected at main SHA `20e8b6509704c8225bba81e722a835b5b1bb1ea0`:

| Existing component | Verified responsibility | Delay Analysis implication |
|---|---|---|
| `src/construction_pm/schedule_input_snapshot_repository.py` | Persists canonical authoritative schedule-input payload, immutable snapshot ID/hash, calculation identity and revision-bound scope. | Reuse its immutable snapshot identity/provenance. Do not create a competing schedule snapshot format or trust a client-supplied hash. |
| `src/construction_pm/p6_baseline_repository.py` and `docs/architecture/P6_BASELINE_PERSISTENCE_V1.md` | Persist baseline metadata and source revision identity; this repository does not own comparison calculations. | Reuse baseline identity and source-revision provenance. |\n| `src/construction_pm/p6_baseline_activity_repository.py` and `src/construction_pm/p6_baseline_activity_api.py` | Persist/read immutable baseline activity planned start/finish, budgeted cost, currency, WBS and EVM technique, with tenant/project scope and immutable batch semantics. | This is a useful baseline-date/EVM subset, but not a frozen CPM network: it lacks baseline relationships, constraints, resolved calendars, full schedule options, baseline scheduler outputs/float and critical-path provenance. Use it for date-variance evidence only; do not infer TIA capability. |
| `src/construction_pm/delay_analysis/baseline_snapshot_binding.py` (proposed in PR #2045) | Binds a P6 baseline ID/source revision to an existing immutable `ScheduleInputSnapshot` and verifies its hash/calculation identity when resolved. | This provides the full frozen schedule-input network through the canonical snapshot contract when a source-revision snapshot exists; it does not yet persist a baseline scheduler run/log or event fragnet. |
| `src/construction_pm/scheduling/p6_activity_scheduler_outputs.py` | Projects early/late dates and remaining float exclusively from the authoritative Shared Core `ScheduleResult`. | Consume scheduler outputs; do not independently calculate float, criticality, calendars or CPM dates. |
| `docs/architecture/TIME_AWARE_BACKWARD_PASS_AND_FLOAT.md` | Records time-aware backward-pass/float semantics and explicitly notes remaining parity/runtime gates. | Analysis methods must record the exact scheduler/calculation version and supported time semantics; do not imply every P6 scheduling behavior is already runtime-certified. |
| `docs/architecture/ACTIVITY_AND_LAG_CALENDAR_RESOLUTION.md` | Defines versioned project/activity/relationship-lag calendar resolution and inheritance. | Freeze resolved calendar identities and versions per analysis input. |

**Verified gap and implementation path:** the inspected main tree had no dedicated `src/construction_pm/delay_analysis/` domain package or `tests/delay_analysis/` suite. Baseline persistence is not metadata-only: `p6_baseline_activity_repository.py` stores immutable planned-date and selected EVM activity facts, but those rows alone are not a complete baseline network. PR #2045 adds a binding from the baseline ID/source revision to the existing immutable `ScheduleInputSnapshot`, whose canonical payload contains the full authoritative schedule inputs (activities, relationships, calendars, constraints and schedule options). This is the correct non-duplicating path to recover a frozen baseline network when a snapshot exists at the baseline source revision. Remaining forensic prerequisites are a reproducible baseline scheduler run/log, event/fragnet semantics, method-specific analysis persistence and expert review.



## 15. Data-date, evidence revision and independent review governance — V26 aligned

### Oracle EPPM V26 source semantics

| Native EPPM concept | Help-defined behavior | CUBI control / implementation boundary |
|---|---|---|
| Updating progress in a browser | Progress can be entered manually for activities/resources, or computed/applied through Auto-Compute Actuals and Apply Actuals. | Each analysis revision must identify the exact statused source snapshot and the evidence supporting the reported progress. A date alone is not proof that progress was statused contemporaneously. |
| Applying Actuals | Apply Actuals updates the selected project(s) as of a specified New Data Date and uses a selected Remaining Duration Calculation option. | Persist the selected data date, source snapshot/hash, update evidence hash and calculation context. Do not silently move the cut-off or recompute historical actuals during analysis. |
| Updating Baselines | Updating a baseline changes only selected data types and can be previewed before committing. | Baseline ID alone is insufficient. Bind the baseline source revision to its immutable schedule snapshot and hash; a later native baseline update must not rewrite a prior analysis revision. |
| Schedule Project Log | Native sections are Scheduling Settings, Statistics, Errors, Warnings, Scheduling Results and Exceptions. | CUBI records only sections emitted by Shared Core and labels its envelope PARTIAL. Missing native sections are explicit unavailable evidence, never synthesized as empty or successful. |
| Check Schedule | The report includes relationship/open-end, dangling start/finish, large duration, invalid progress dates, resource/cost, late activity and BEI checks; exclusions and targets are part of the semantics. | Preserve exact evaluator findings and settings that exist. A missing evaluator check is marked unsupported/not run; it is not represented as passed. |
| Activity relationships and calendars | FS/SS/FF/SF relationship types, lag, activity calendars and typed constraints affect scheduling. | Reuse canonical typed Shared Core inputs and version-pinned calendar resolution. Unsupported activity types or schedule modes fail closed. |

Official V26 HTML Help topics:
- [Working with Updating Progress in a Browser Running P6](https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/6681.htm)
- [Applying Actuals to a Project](https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/7995.htm)
- [Working with the Apply Actuals Feature](https://docs.oracle.com/cd/G48897_01/p6help/en/32048.htm)
- [Updating Baselines](https://docs.oracle.com/cd/G48897_01/p6help/en/93166.htm)
- [Update Baseline Preview](https://docs.oracle.com/cd/G48897_01/p6help/en/100466.htm)
- [Schedule Project Log](https://docs.oracle.com/cd/G48897_01/p6help/en/99347.htm)
- [Check Schedule Report](https://docs.oracle.com/cd/G48897_01/p6help/en/101231.htm)
- [Check Schedule Settings](https://docs.oracle.com/cd/G48897_01/p6help/en/101232.htm)

### New implementation in PR #2045

The isolated Engineering package now adds `analysis_records.py` and `test_analysis_records.py`:

1. **Case idempotency:** tenant/project-scoped immutable case identity; reuse of an idempotency key with a different request hash is rejected.
2. **Append-only revisions:** monotonically increasing revision number, immutable revision key, exact baseline/current snapshot IDs and SHA-256 hashes, method, result hash, event evidence-manifest hash and statused-update evidence hash.
3. **Data-date gate:** baseline/current data dates are explicit; current date cannot precede baseline or be in the future relative to record creation. A reconstructed data date requires a written rationale. The `APPROVED_CONTEMPORANEOUS_UPDATE` label is a CUBI governance attestation, not a claim that Oracle P6 provides this exact approval workflow.
4. **Independent review:** author self-review is rejected; each reviewer has one immutable decision per revision; a rejection blocks approval status for that revision. A changed method, assumption, data date, source or evidence requires a new revision rather than editing the reviewed record.
5. **Persistence:** SQLite and PostgreSQL repository adapters are provided. SQLite and PostgreSQL database triggers reject UPDATE/DELETE against case, revision and review records; production database roles must additionally be denied direct DDL/trigger bypass privileges.

These records are governance primitives only. They do not yet provide an authenticated application/API route, reviewer identity resolution from the production authorization layer, a publication service, or an ENT-13 result reference. No client may supply trusted tenant identity or snapshot provenance. Those integration steps require the protected application owner and security review; this PR does not create a parallel access boundary.

### Acceptance and honest parity status

- Implemented in this slice: immutable snapshot/run provenance, inserted-fragnet what-if execution through the authoritative scheduler, analysis case/revision/review persistence primitives, data-date validation and evidence hash binding.
- Still PARTIAL: native Schedule Project Log parity (Shared Core does not emit every native section), complete native Check Schedule settings/targets and exclusions, resource-dependent fragnet semantics, TIME_AWARE execution, window analysis and concurrency diagnostics.
- Not implemented / not claimed: contractual causation, responsibility allocation, entitlement, EOT, damages, cost determination, formal forensic expert opinion, authenticated reviewer workflow, publication to ENT-13, production browser acceptance.

The V26 Help is the semantic authority for P6 behavior; SCL Delay and Disruption Protocol / AACE RP 29R-03 govern forensic-method choices. Neither source authorizes CUBI to infer legal entitlement from schedule movement alone.

## 14. Implementation sequencing and release gates

The implementation follow-on is tracked separately in [#2044 — governed Technical Delay Analysis vertical slice](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2044). Its sequencing is deliberate:

1. Reuse `P6Baseline` plus immutable `P6BaselineActivity` rows for baseline metadata and native date/EVM facts. PR #2045 adds an immutable binding to the canonical `ScheduleInputSnapshot` at `source_revision`, avoiding a second schedule-network store. Require the baseline snapshot and its exact calculation identity before TIA/windows analysis.
2. The first read-only implementation slice is tracked in PR #2045: schedule movement comparison, baseline planned-date variance over existing `ScheduleResult` outputs, and baseline-to-snapshot binding/verification. It is intentionally not a forensic delay method. Next add reproducible baseline/current scheduler-run records and immutable analysis request/revision/result persistence without modifying Shared Core scheduler internals.
3. Deliver one method-specific, read-only vertical slice (TIA or a justified window method) only after its event/fragnet semantics and source evidence are validated.
4. Add reviewer sign-off, immutable publication and a narrow result reference for ENT-13.
5. Add further method families only with their own method contracts and acceptance evidence.

The follow-on is blocked while Qoder owns the active P0 scheduling-core optimization and until the shared-path coordinator confirms a clean handoff. It is intentionally unassigned; it must not be redirected into Hassan's ENT-13 or #2028 Dashboard/Portlet paths. No public route, menu, duplicate scheduler, or legal/financial determination is authorized by this research artifact.

**Completion rule:** documentation and a technical contract are not implementation credit. The feature remains not implemented until #2044's exact-head unit/integration/security tests, PostgreSQL coverage where applicable, deterministic replay evidence and any required browser/runtime checks pass. A Vercel rate-limit failure is infrastructure-blocked, not a passing check.
