# Primavera P6 EPPM V26 vs P6 Professional V26 — Difference Audit

- **Status:** IN PROGRESS — initial official-Help comparison; not exhaustive and not an implementation authorization.
- **Baseline:** Oracle Primavera P6 EPPM Version 26 and P6 Professional Version 26.
- **Prepared:** 2026-11-14
- **Purpose:** Record product/surface differences so CUBI can distinguish Professional-compatible project-control behavior from EPPM web/enterprise capabilities.
- **Scope boundary:** This is a reference and product-analysis document only. It does not authorize changes to the current CUBI Project Control Workspace, scheduler, navigation, or UI. The Professional V26 parity mission remains separate.

## 1. Official source set

| Product | Official source | Use in this audit |
|---|---|---|
| P6 EPPM 26 Help | https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm | Main EPPM web/application help and topic tree |
| P6 Professional 26 Help | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm | Main Professional desktop help and topic tree |
| P6 EPPM 26 all guides | https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/books.html | Administration, integration, reporting, API, data dictionary and related guide discovery |
| P6 Professional 26 all guides | https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/books.html | Professional administration, user, reporting and Visualizer guide discovery |

### Important repository source correction

The existing CUBI Knowledge V26 ingestion identified in `docs/workspace/evidence/knowledge-multilingual-v26-2026-11-12/SOURCE_STATUS.md` contains the **Professional** help source `G48902_01/client_help/en_US/toc.htm` (982 topics) and Professional User Guide (557 topics). It does **not** establish that the EPPM help source `G48897_01/p6help/en/toc.htm` has been ingested or reviewed. Do not treat the existing 982-topic corpus as the EPPM manual. The EPPM help must be separately inventoried and compared against the Professional corpus.

The online EPPM TOC currently resolves to 825 TOC lines and the Professional TOC to 984 TOC lines. These are TOC line counts, not counts of unique topic pages. Any claimed page/topic totals must be calculated from the actual source inventory, not inferred from the TOC length or an approximate “815-page” description.

## 2. Classification rules

Every candidate difference must receive one of these classifications after its topic pages are opened and reviewed:

- **EPPM_ONLY_CONFIRMED** — Oracle explicitly identifies it as EPPM-only, or the full corresponding Professional help/topic set is checked and the capability is absent from Professional.
- **PROFESSIONAL_ONLY_CONFIRMED** — Oracle explicitly identifies it as Professional-only, or the full corresponding EPPM help/topic set is checked and the capability is absent from EPPM.
- **BOTH_DIFFERENT_SURFACE** — both products support the capability but the workflow, UI, role model, configuration or behavior differs.
- **BOTH_SHARED** — materially shared capability; not a differentiator.
- **EDITION_OR_DEPLOYMENT_DEPENDENT** — depends on licensing, deployment (cloud/on-premises), integration, module access or configuration.
- **NOT_YET_VERIFIED** — TOC/title evidence only or topic-level evidence incomplete.

A topic's absence from a TOC alone is not enough to prove product absence. Likewise, an item explicitly labelled “P6 EPPM Only” inside Professional Help is strong positive evidence for EPPM-specific behavior, but the corresponding EPPM topic must still be reviewed for exact semantics.

## 3. Initial findings from the Version 26 Help trees

The following are **candidate differences identified from the official TOCs**, not a final exhaustive verdict. The source topic pages and applicable administration/integration guides still need topic-by-topic review.

| ID | Area | EPPM Help evidence | Professional Help evidence | Initial classification | Review required |
|---|---|---|---|---|---|
| EPPM-DIFF-001 | Dashboards and portlets | Dedicated Dashboards, dashboard access/layout/filtering, portlets, custom portlets, portfolio portlets and document-review portlets | No corresponding web dashboard/portlet chapter in the Professional desktop TOC | NOT_YET_VERIFIED (strong EPPM web-surface candidate) | Open dashboard, portlet, access and custom-portlet topics; inspect licensing/admin requirements |
| EPPM-DIFF-002 | Portfolio analysis | Portfolios, portfolio views, scorecards, bubble/pie/histogram charts, What-if Analysis | Professional has portfolio creation and membership topics | BOTH_DIFFERENT_SURFACE | Compare analysis, scorecard, visualization, scenario and access behavior |
| EPPM-DIFF-003 | Capacity planning | Dedicated Capacity Planning page and role-allocation analysis | Professional has resource/role assignments and resource analysis; no same-named portfolio capacity-planning page in TOC | BOTH_DIFFERENT_SURFACE / NOT_YET_VERIFIED | Compare role demand, capacity calculations, project scope and time-phased behavior |
| EPPM-DIFF-004 | Team Member Web/Mobile and status updates | Team Member Web/Mobile, status-update reviews, reviewers, accept/reject/override/hold and history | Professional Help references EPPM-only Activity Owner and reflection/status-collection workflows; Professional desktop has its own resource feedback/discussion functions | BOTH_DIFFERENT_SURFACE | Compare Team Member product docs, permissions, status workflow and data ownership |
| EPPM-DIFF-005 | Activity Owner | EPPM Help has Activity Owners and assignment workflow | Professional Help labels “Designating an activity owner” as “P6 EPPM Only” | EPPM_ONLY_CONFIRMED (explicit Oracle label) | Verify assignment, ownership, reviewer and reflection semantics in linked topics |
| EPPM-DIFF-006 | Reflection + Activity Owner status collection | EPPM Help includes Team Member status updates and reviews | Professional Help labels “Using Reflection projects and Activity Owner features to collect and review activity status” as “P6 EPPM Only” | EPPM_ONLY_CONFIRMED (explicit Oracle label) | Review exact prerequisites and lifecycle; do not conflate generic reflections with EPPM workflow |
| EPPM-DIFF-007 | CBS assignment on activity | EPPM project/activity help includes project CBS / cost structures | Professional Help labels “Change an activity's cost breakdown structure assignment” as “P6 EPPM Only” | EPPM_ONLY_CONFIRMED (explicit Oracle label) | Verify CBS configuration, field behavior and XER/XML/API mapping |
| EPPM-DIFF-008 | Unifier integration | EPPM Help has project linking and schedule/summary/activity sheet exchanges with Unifier | Professional Help's EPPM-connected integration topic is labelled “P6 EPPM Only”; Professional also has separate integration configuration paths | EPPM_ONLY_CONFIRMED for the labelled workflow; other integrations remain separate | Review each sheet type, mapping, sync direction and supported deployment |
| EPPM-DIFF-009 | Timesheet approvals | EPPM Help has Timesheets and Team Member interfaces, approval/rejection and delegate workflows | Professional Help labels Tools > Approvals > Timesheets “P6 EPPM Only” | EPPM_ONLY_CONFIRMED (explicit Oracle label) | Compare EPPM web approvals vs Professional client connected to EPPM DB; inspect delegate and audit semantics |
| EPPM-DIFF-010 | Document content repository and reviews | EPPM Help has content repository, check-in/out, folders, templates and document reviews | Professional Help has Work Products and Documents with location references and project document library | BOTH_DIFFERENT_SURFACE | Compare managed repository vs document metadata/location records, versioning, check-in/out and review lifecycle |
| EPPM-DIFF-011 | Project scheduled services and publication | EPPM Help has Project Scheduled Services, Publication Services and publishing project/global/baseline data | Professional Help has Project Web Site Publisher, reports and layout publishing | BOTH_DIFFERENT_SURFACE | Compare service jobs, summarization, publication outputs, triggers and operational prerequisites |
| EPPM-DIFF-012 | Enterprise user administration | EPPM Help includes user accounts, module access, OBS/resource access, global/project security profiles and UI views | Professional has Admin menu and local/client administration topics, but its user TOC is not the same EPPM web user-management model | BOTH_DIFFERENT_SURFACE | Compare authentication modes, module access, OBS, resource access, UI views and security profile enforcement |
| EPPM-DIFF-013 | Audit | EPPM Help includes table auditing and viewing audit data | Professional Help has PI consent auditing and job alerts, but no equivalent enterprise table-audit section in its main TOC | NOT_YET_VERIFIED | Inspect EPPM audit configuration, audited tables, retention and access; inspect Professional connected-database limitations |
| EPPM-DIFF-014 | Resource/role teams and enterprise planning | EPPM Help includes Role Teams, Resource Teams, Resource Planning, Resource Analysis and future-period planning | Professional includes resources, roles, assignments, profiles and future-period planning | BOTH_DIFFERENT_SURFACE | Compare team entities, project staffing, planning spreadsheet and analysis |
| EPPM-DIFF-015 | Risk management | EPPM Help has risk enterprise data, scoring matrices, thresholds, categories, project risks and response plans | Professional Help labels the desktop Risks feature “P6 Professional Only” | BOTH_DIFFERENT_SURFACE (do not classify as simple EPPM-only) | Distinguish EPPM web risk module from Professional desktop risk feature; compare entity model, scoring and response plans |
| EPPM-DIFF-016 | Top-down estimation | Not identified as a corresponding EPPM web chapter in the reviewed TOC | Professional Help labels top-down estimation and saved-estimate application “P6 Professional Only” | PROFESSIONAL_ONLY_CANDIDATE | Check EPPM guide and release/licensing docs before final classification |
| EPPM-DIFF-017 | Job Services | EPPM has project scheduled services and server-side publication/summarization services | Professional Help labels Job Services “P6 Professional Only” | BOTH_DIFFERENT_SURFACE / NOT_YET_VERIFIED | Distinguish desktop Job Services from EPPM application/server scheduled services |
| EPPM-DIFF-018 | Reporting | EPPM guide set has a dedicated P6 EPPM Reporting guide and EPPM reporting services | Professional has a dedicated Professional Reporting Guide and desktop report authoring/printing | BOTH_DIFFERENT_SURFACE | Compare report catalogue, services, templates, scheduled delivery, permissions and output formats |
| EPPM-DIFF-019 | Import/export | EPPM Help includes XER, Primavera XML, MS Project XML, UN/CEFACT, IPMDAR, CPP, Excel and secure codes | Professional Help also includes XER/XML and Excel, with its own desktop import/export workflows | BOTH_DIFFERENT_SURFACE | Compare exact formats, supported fields, templates, round-trip behavior and version restrictions |
| EPPM-DIFF-020 | REST/SOAP/API and Data Dictionary | EPPM Version 26 guide set explicitly includes REST API, integration guides and Data Dictionary | Professional guide set is separately scoped; API/data-map contracts must not be inferred from desktop UI | EPPM_PLATFORM_CAPABILITY_CANDIDATE | Review EPPM REST/SOAP and Professional API/reference docs separately; map endpoint/field contracts |

## 4. Explicit reverse-direction markers found in Professional Help

The Professional Version 26 Help contains explicit product qualifiers that must be captured, rather than assuming all differences point from Professional toward EPPM:

- **P6 EPPM Only:** Activity Owner; Activity Cost Breakdown Structure assignment; using Reflection projects and Activity Owner features to collect/review status; Timesheet Approvals; selected Primavera Unifier project-linking workflow.
- **P6 Professional Only:** Top-down Estimation; Professional Risks; selected Job Services and global summarization configuration.

These labels are evidence about the specific feature/topic named, not a blanket statement that the broader domain is absent from the other product. Example: EPPM has a documented enterprise risk model even though Professional Help marks its own Risks feature “P6 Professional Only”.

## 5. Shared-core areas — not product differentiators by themselves

Both help trees document the core planning model: EPS/projects, WBS, activities, relationships, Gantt, calendars, resources/roles, baselines, schedule calculation, progress, costs and earned value. These areas still require detailed behavior-level comparison where the same concept is exposed through different clients, but must not be counted as EPPM-only solely because EPPM has a web page for them.

## 6. Required topic-by-topic audit workflow

1. Freeze exact official Version 26 source URLs and record retrieval date/content hashes.
2. Inventory every topic URL and breadcrumb from EPPM Help and Professional Help separately. Keep source IDs distinct.
3. Pair topics by semantic subject, not title alone. Record one-to-one, one-to-many and unmatched topics.
4. Open every paired/unmatched topic and capture the functional contract: purpose, UI path, actors, permissions, prerequisites, inputs, actions, outputs, validations, errors, deployment/licensing limits and integration dependencies.
5. Check the EPPM User Guide, Professional User Guide, Administration Guides, Reporting Guides, Integration Guides, API references and Data Dictionaries where Help topics point outside the main help.
6. Record each difference with exact Oracle URLs, topic titles, relevant quotations kept short, and a paraphrased behavioral summary.
7. Assign one of the classifications in section 2. An unmatched TOC topic remains NOT_YET_VERIFIED until the opposing product's complete source set is checked.
8. Cross-check the existing CUBI `p6_code_reference.py`, scheduling option reference, field/API registry, tests and product requirements. Reuse existing entries; do not duplicate the Professional parity register.
9. Create a trace from Oracle topic -> difference ID -> CUBI requirement/decision -> code/test only when the feature is in the approved scope.
10. Have an independent reviewer verify the source interpretation before any implementation decision.

## 7. Deliverables and acceptance criteria

- [ ] Source inventory for both products with exact topic counts and hashes.
- [ ] Complete EPPM-to-Professional topic pairing matrix.
- [ ] Every unmatched topic reviewed and classified; no inference from title-only absence.
- [ ] Every confirmed difference has exact Oracle source links and behavior notes.
- [ ] Reverse-direction Professional-only features are included.
- [ ] Deployment, license, module and integration dependencies are separately recorded.
- [ ] Existing CUBI references are cross-linked and duplicates avoided.
- [ ] Independent review and evidence log completed.
- [ ] Product owner approves any proposed CUBI scope separately.

**Current state:** the initial TOC comparison and explicit product qualifiers are recorded. The exhaustive topic-page comparison is not complete. No CUBI implementation work is authorized by this document.

## 8. Repository references

- Existing Professional compatibility registry: `src/construction_pm/p6_code_reference.py`
- Existing mapping matrix: `docs/workspace/architecture/p6-to-cubi-mapping-matrix.md`
- Existing Knowledge V26 source audit: `docs/workspace/evidence/knowledge-multilingual-v26-2026-11-12/SOURCE_STATUS.md`
- Existing documentation-first gate: Issue #1447
- EPPM V26 Help: https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm
- Professional V26 Help: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
