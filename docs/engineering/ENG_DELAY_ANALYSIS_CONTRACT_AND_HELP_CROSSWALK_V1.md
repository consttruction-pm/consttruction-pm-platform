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

| Official topic | Native behavior evidenced by Help | CUBI disposition |
|---|---|---|
| [P6 EPPM V26 Help TOC](https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm) | Product navigation and feature inventory; includes baselines, activities, scheduling, float, critical path, progress, relationships, earned value, issues and publication. | Normative inventory. A forensic Delay Analysis / EOT entitlement workflow was not identified in the reviewed EPPM Help topic set; do not label ordinary variance tools as forensic analysis. |
| [Working with Baselines](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/WorkingwithBaselines-6687a-1-reuse.html) | Baseline is a schedule snapshot used to track cost, schedule and performance; baseline types, project/user baseline designation, comparison limits, publishing and restore/update behavior are documented. | Baseline provenance and snapshot lifecycle are mandatory inputs. A baseline comparison is not by itself a delay-causation finding. |
| [Creating Baselines](https://docs.oracle.com/cd/G48897_01/p6help/en/7961.htm) | Define Baselines from Activities/EPS; set name/type; choose project or user's primary baseline; convert/restore baseline. | Capture exact baseline identity/type and authority; no silent baseline substitution. |
| [Scheduling Projects](https://docs.oracle.com/cd/G48897_01/p6help/en/7878.htm) | Schedule projects using Schedule (F9); scheduling privileges affect availability; multiple open projects and scheduling options are relevant. | Every analysis records schedule run identity, schedule revision and selected scheduling options. Do not reschedule a historical source silently. |
| [Check Schedule Dialog Box](https://docs.oracle.com/cd/G48897_01/p6help/en/91574.htm) | Schedule quality checks include logic, negative lags and relationship lags (with other checks in the dialog). | Run and preserve quality diagnostics before selecting a forensic method; quality defects become explicit limitations, not hidden assumptions. |
| [Check Schedule Settings Tab](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/101232.html) | Defines checks/targets including out-of-sequence progress, large float, negative float, late activities and BEI. | Record enabled checks, thresholds and results. A failed threshold is a warning/limitation, not an automatic rejection or entitlement conclusion. |
| [Scheduling Settings Section of Schedule Project Log](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/99348.html) | Schedule log records read-only settings including progressed-activity logic (Retained Logic / Progress Override / Actual Dates), lag calendar and total-float method. | Preserve these settings with every schedule snapshot and analysis run; they materially affect calculated dates/float. |
| [Available Columns of Activities Page](https://docs.oracle.com/cd/G48897_01/p6help/en/47261.htm) | Documents earned-value fields such as BAC, CPI and related cost/work measures. | Use existing authoritative fields; do not recreate EV formulas in Enterprise. |
| [Available Columns of EPS Page](https://docs.oracle.com/cd/G48897_01/p6help/en/47274.htm) | Defines cost/schedule variance and EV measures and warns that summarized/published data can differ from live data; published/summarized EV uses project baseline. | Preserve source mode and freshness (live vs summarized/published) and the baseline basis. Never mix unlike data modes without labeling. |
| [Variance Report](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-reports/variancereport-81320a.html) | Lists activities with schedule variance relative to data date, including baseline/current dates, variance and total float. | Useful monitoring/reporting evidence, not a forensic method or a proof of cause/critical delay. |

**Source interpretation:** EPPM Help provides the underlying schedule facts, baseline management, schedule-quality checks, schedule settings, float/critical path and performance/variance reporting. In the reviewed EPPM V26 Help set, no dedicated forensic delay-analysis workflow, contractual EOT determination, concurrency adjudication, disruption valuation or damages calculator was found. Those must be specified as a CUBI capability with explicit method governance, not represented as a native P6 screen.

### 2.2 P6 Professional V26 — comparison-only, not EPPM Web parity

- [Comparing Current and Baseline Schedules — P6 Professional V26](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/62723.htm) documents a Professional user workflow for current/baseline bar and field comparisons.
- P6 Professional's Schedule Comparison / Claim Digger must not be described as an EPPM Web feature. The product-family distinction is also visible in Oracle's [P6 / Primavera Cloud feature comparison](https://docs.oracle.com/cd/E80480_01/English/admin/p6_eppm_migration_guide/246421.htm), which places Claim Digger and Schedule Comparison in the P6 client/Professional columns and Schedule Comparison in Primavera Cloud.
- CUBI may provide its own version-to-version comparison only under an approved Engineering contract; it must not silently inherit a Professional-only menu or behavior into the EPPM parity claim.

### 2.3 Primavera Cloud V26 — additive comparison

| Official topic | Cloud behavior | CUBI disposition |
|---|---|---|
| [Schedule Comparison Overview](https://primavera.oraclecloud.com/help/en/user/191095.htm) | Compares current schedule, baseline, scenario or historical point; identifies added/deleted/changed activities and values; supports compare and merge workflows. | Candidate for a separate schedule-version comparison capability. Merge is not forensic delay analysis and must not mutate historical snapshots. |
| [Compare Two Versions of a Project Schedule](https://primavera.oraclecloud.com/help/en/user/191096.htm) | Comparison is read-only; schedule versions should be scheduled for accurate calculated-value comparison; date variance uses project calendar. | Record exact schedule versions, calendar basis and scheduling status. Do not assume calendar treatment is identical to EPPM activity variance. |
| [Schedule Health Score Overview](https://primavera.oraclecloud.com/help/en/user/149130.htm) | Quality metrics can be run on current schedule, baseline or scenario and surfaced in reports/charts. | Additive quality diagnostic only; never a forensic delay conclusion. |
| [Baselines Overview](https://primavera.oraclecloud.com/help/en/user/89344_1.htm) | Defines original/current/supplementary/unofficial baseline categories and historical baseline date behavior. | Useful comparative model; do not overwrite EPPM baseline semantics or import Cloud-specific category assumptions into the EPPM core. |

Cloud comparison may improve the CUBI user experience, but it is not a substitute for a forensic method, a legal determination or a separate analysis record.

## 3. Methodology boundary: delay is not disruption

The [SCL Delay and Disruption Protocol, 2nd edition](https://schdc.cl/web2021/wp-content/uploads/2023/10/SCL_Delay_Protocol_2nd_Edition_Final.pdf) distinguishes delay (time impact, especially critical delay to completion) from disruption (disturbance/hindrance/interruption to planned working methods and productivity). It also explains that the monetary consequences may overlap but require different substantiation. The [AACE RP 29R-03 Forensic Schedule Analysis](https://web.aacei.org/docs/default-source/toc/toc_29r-03.pdf) is a technical reference for CPM-based forensic schedule analysis and explicitly requires professional judgment in selecting methods based on contract, facts, applicable law and contemporaneous records.

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
3. **Quality gate:** run applicable schedule-health checks; record open ends, out-of-sequence progress, constraints, negative/large float, missing logic, calendar inconsistencies, missing actuals and baseline quality. Analyst must explain any method limitation.
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
| DA-03 | Schedule contains open ends, negative lags, out-of-sequence progress or extreme float. | Diagnostics and limitations are attached; method selection requires documented analyst rationale. |
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
- [P6 Professional V26 Comparing Current and Baseline Schedules](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/62723.htm) — comparison only.
- [Oracle P6 EPPM vs Primavera Cloud feature comparison](https://docs.oracle.com/cd/E80480_01/English/admin/p6_eppm_migration_guide/246421.htm)
- [Primavera Cloud V26 Help TOC](https://primavera.oraclecloud.com/help/en/user/toc.htm)

### Forensic methodology references
- [Society of Construction Law — Delay and Disruption Protocol, 2nd Edition (2017)](https://schdc.cl/web2021/wp-content/uploads/2023/10/SCL_Delay_Protocol_2nd_Edition_Final.pdf)
- [AACE International RP 29R-03 — Forensic Schedule Analysis (Table of Contents / scope)](https://web.aacei.org/docs/default-source/toc/toc_29r-03.pdf)

### Repository governance
- [#2009 — Engineering contracts, menu/access placement and non-interference queue](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2009)
- [#2016 — ENT-13 party-specific claim forms and bilateral workflow](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2016)
- [#2002 — ENT-13 Claim Day Archive and immutable evidence packages](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2002)
- [#2041 — this research work package](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2041)

## 12. Verification and status

- Main SHA at preflight: `20e8b6509704c8225bba81e722a835b5b1bb1ea0`.
- Exact target path was absent from the main recursive tree.
- No root or nested `AGENTS.md` was present in the main recursive tree at preflight.
- Open PR path preflight sampled the active Engineering/Enterprise documentation and implementation PRs; none of the checked PRs modified this exact target path. PR #2008 touches adjacent ENG-10/ENG-11/ENG-12 documents, not this new file.
- This is a documentation-only artifact. No tests, API, schema, runtime behavior, browser behavior or deployment were changed or claimed.
