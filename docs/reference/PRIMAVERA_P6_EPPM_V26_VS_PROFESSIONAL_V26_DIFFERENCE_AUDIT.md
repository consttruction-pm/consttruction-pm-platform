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


---

## 9. Full product-model correction — what “EPPM Only” actually means

This is the most important interpretation rule in the comparison.

Oracle's P6 Professional Version 26 Help explicitly states that P6 Professional can connect to either:
1. a **P6 Professional database**, or
2. a **P6 EPPM database**.

The same guide says topics marked **P6 Professional Only** apply when Professional is connected to a Professional database, while topics marked **P6 EPPM Only** apply when Professional is connected to an EPPM database. Unqualified topics generally apply to both database types. Some topics contain conditional behavior for each database type. Cloud/on-premises qualifiers also apply.

Official explanation: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/62783.htm

Therefore, this audit distinguishes three different things that must never be conflated:

- **P6 Professional client surface** — the Windows desktop application and its own UI, menus, layouts, Visualizer, report editor, and local/standalone administration.
- **P6 EPPM web/platform surface** — browser application, dashboards, portfolios, Team Member interfaces, application administration, publication/reporting services, REST/SOAP services and EPPM data/schema.
- **P6 Professional connected to an EPPM database** — the desktop client is still Professional, but EPPM-database-specific functions and privileges become available. A topic labelled “P6 EPPM Only” may be used through this connected Professional client; it does not mean the desktop client itself becomes the EPPM web application.

**Correction to previous wording:** “EPPM Only” must not be interpreted as “not accessible from P6 Professional at all.” It means the documented feature/topic is specific to the EPPM database/deployment context, and may be exposed through Professional when connected to that database.

## 10. V26 guide-set inventory — source coverage boundary

Oracle's current Version 26 documentation landing pages were inspected:

- EPPM All Guides: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/books.html
- Professional All Guides: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/books.html

The EPPM set lists distinct application administration, identity management, client requirements, data dictionary, extended schema, EPPM Help, import/export and multiple data maps, reporting, REST API, SOAP programming/reference, user guide, virtual desktop, Team Member Help, What's New, Primavera Administration and Primavera Data Service REST API guides. The Professional set lists Professional Administration, Help, Licensing, Reporting, User Guide and Visualizer Help, plus EPPM client requirements.

This is not a simple “one 815-page book vs one Professional book” comparison. The EPPM documentation set is a multi-guide suite. The main Help TOCs resolve to 825 rendered TOC lines for EPPM and 984 rendered TOC lines for Professional. **Those are line counts, not verified page counts or topic counts.** The user's “815 pages” description is not used as a measured source count.

## 11. Expanded comparison matrix — confirmed from V26 TOCs and topic-level source pages

Classification key:
- **EPPM PLATFORM**: EPPM web/platform-specific capability or service.
- **EPPM DB CONTEXT**: Oracle explicitly labels the Professional-client workflow “P6 EPPM Only”; available in the Professional client when connected to an EPPM database.
- **PRO DB CONTEXT**: Oracle explicitly labels the Professional-client workflow “P6 Professional Only”; applies to Professional database context.
- **BOTH / DIFFERENT SURFACE**: both products have the domain, but the workflows, depth, UI or service model differ.
- **SHARED CORE**: common project-control concept; not a differentiator by itself.
- **CONDITIONAL**: exact behavior depends on deployment, licensing, privileges or configuration.

| ID | Functional area | EPPM Version 26 evidence | Professional Version 26 evidence | Result |
|---|---|---|---|---|
| D-001 | Browser dashboards | EPPM has dashboards with private/shared/global dashboard options, content, layout, filters and access controls. Creating a dashboard is a browser workflow. | Professional Help is a desktop client guide; no equivalent web dashboard authoring surface in its main TOC. | EPPM PLATFORM |
| D-002 | Portlets | Portlets can be arranged on shared dashboards; project/portfolio filters, status/performance, custom content, document-review and resource-related portlets are documented. | Professional has desktop windows/layouts and tracking layouts, not the same dashboard/portlet container. | EPPM PLATFORM |
| D-003 | Portfolio management | EPPM supports global, multiple-user and user portfolios, manual or filter-based membership, access control, portfolio views, scorecards, bubble/pie/histogram views and What-if analysis. | Professional has portfolio creation and project membership, but its Help does not document the same web portfolio-analysis/portlet surface. | BOTH / DIFFERENT SURFACE |
| D-004 | What-if analysis | EPPM explicitly documents what-if projects to assess cost/investment scenarios and business-goal impacts. | Professional supports what-if project workflows; the detailed portfolio analysis workflow is not the same. | BOTH / DIFFERENT SURFACE |
| D-005 | Capacity planning | EPPM Capacity Planning analyzes role allocation over time across selected projects/portfolios, with role hierarchy/team grouping and chart waterlines. | Professional has resource/role assignment, resource profiles, spreadsheets and resource analysis; not the same portfolio Capacity Planning page. | BOTH / DIFFERENT SURFACE |
| D-006 | Activity Owner | Professional Help explicitly labels “Designating an activity owner” as P6 EPPM Only. EPPM Help has Activity Owners and assignment. | Not available for a Professional-only database workflow. | EPPM DB CONTEXT |
| D-007 | CBS assignment | Professional Help explicitly labels changing an activity's cost breakdown structure assignment as P6 EPPM Only. | Not available for a Professional-only database workflow. | EPPM DB CONTEXT |
| D-008 | Reflection-based status collection | Professional Help explicitly labels using Reflection projects and Activity Owner features to collect/review activity status as P6 EPPM Only. | Reflection itself exists in Professional; the EPPM-specific activity-owner/status-collection integration is the differentiator. | EPPM DB CONTEXT |
| D-009 | Team Member Web | EPPM includes a separate Team Member Web experience for assigned activities and timesheets, with work-distribution filters and configurable status fields. | Not a Professional desktop screen. | EPPM PLATFORM |
| D-010 | Team Member mobile | EPPM documentation includes P6 mobile app status updates and Team Member mobile interfaces. | Professional is a Windows desktop client; this is not its native mobile UI. | EPPM PLATFORM / CONDITIONAL |
| D-011 | Email Statusing Service | EPPM supports email distribution of assigned activities and email-based status updates. | Not the Professional desktop's native project-planning workflow. | EPPM PLATFORM |
| D-012 | Team Member status review | EPPM documents status reviewers at WBS level, selecting activities for review, accept/reject/override/hold and status history. | Professional has update/progress workflows; the Team Member review lifecycle is EPPM-context-specific. | EPPM PLATFORM / EPPM DB CONTEXT |
| D-013 | Timesheet approval | Professional Help explicitly labels Tools > Approvals > Timesheets as P6 EPPM Only, including approve/reject, delegates and notes. | Not applicable to a Professional-only database. | EPPM DB CONTEXT |
| D-014 | Resource and role teams | EPPM documents Resource Teams and Role Teams as first-class enterprise structures and assignment operations. | Professional has resource/role dictionaries and assignments; the same team-management surfaces are not mirrored in its desktop TOC. | BOTH / DIFFERENT SURFACE |
| D-015 | Resource planning | EPPM has Resource Planning at project/WBS level, allocation over time, splitting assignments and planning spreadsheet export. | Professional has future-period bucket planning, assignments and resource analysis layouts. | BOTH / DIFFERENT SURFACE |
| D-016 | Resource analysis | EPPM Resource Analysis supports allocation analysis and role/resource usage views. | Professional has Resource Explorer, profiles, spreadsheets and dynamic resource leveling. | BOTH / DIFFERENT SURFACE |
| D-017 | Enterprise risk data | EPPM has enterprise risk dictionaries, scoring matrices, thresholds, categories, risk UDFs and sharing enterprise risk data with Primavera Cloud. | Professional has a separate “Risks (P6 Professional Only)” feature. | BOTH / DIFFERENT DATA MODEL |
| D-018 | Project risk workflows | EPPM documents project risks, detailed/high-level risks, activity risk assignments, risk response plans and action items. | Professional documents create/assign/respond/modify/delete risks as a Professional-only database feature. | BOTH / DIFFERENT DATA MODEL |
| D-019 | Document content repository | EPPM supports documents stored in a Content Repository, templates, check-in/check-out, folders, searching, viewing/downloading and document review. | Professional WPs & Docs primarily manages document/work-product records and location references; when connected to EPPM it can surface EPPM document records. | EPPM PLATFORM / BOTH DIFFERENT |
| D-020 | Document review workflow | EPPM documents document reviews, participants, termination and dashboard review portlets. | Professional WPs & Docs records do not constitute the same managed review workflow. | EPPM PLATFORM |
| D-021 | Budget change requests | EPPM supports budget log entries at EPS/project/WBS level, responsible party, status, reason and approval/denial workflow. | Professional has budgeting and cost controls; the EPPM web request/approval workflow must be treated as a distinct surface. | BOTH / DIFFERENT SURFACE |
| D-022 | Project scheduled services | EPPM provides server-side scheduled project services and configuration. | Professional Help separately documents Job Services as P6 Professional Only. | BOTH / DIFFERENT SERVICE MODEL |
| D-023 | Publication services | EPPM provides project/global/baseline data publication, publication periods, automatic/on-demand publication and service settings. | Professional has Project Web Site Publisher and desktop publishing layouts/reports. | BOTH / DIFFERENT SERVICE MODEL |
| D-024 | Summarization | EPPM has server-side summarizer service and project summarization settings. | Professional has summary service; global summarization settings are explicitly Professional Only in the Professional Help. | BOTH / DIFFERENT SERVICE MODEL |
| D-025 | Enterprise user administration | EPPM web administration includes user accounts, module access, global profiles, OBS assignment, resource access, associated resources and UI views. | Professional Administration Guide/Help includes user/security administration for Professional database context. | BOTH / DIFFERENT ADMIN MODEL |
| D-026 | Security profiles | EPPM has global and project security profiles, module access, OBS and resource scoping, and UI views. | Professional has global/project profiles and resource security; the exact privileges and administration path are database-context-dependent. | BOTH / DIFFERENT ADMIN MODEL |
| D-027 | User Interface Views | EPPM documents creating/configuring User Interface Views and assigning them to users. | No equivalent first-class web UI-view administration surface is identified in the Professional Help TOC. | EPPM PLATFORM |
| D-028 | Table auditing | EPPM application settings configure audit settings and allow viewing table audit data; Reporting Guide includes table-auditing context. | Professional Help includes consent auditing and local administrative controls; do not equate those with EPPM table auditing. | EPPM PLATFORM |
| D-029 | REST API | EPPM Version 26 has a dedicated REST API guide with endpoints, authentication/security, entity operations and task workflows. | Professional's guide set does not list a matching Professional-specific REST API guide; Professional can connect to an EPPM database. | EPPM PLATFORM / INTEGRATION |
| D-030 | SOAP Web Services | EPPM has separate Web Services Programming and Web Services Reference guides documenting operations and fields. | No equivalent Professional-specific SOAP guide appears in the Professional V26 all-guides list. | EPPM PLATFORM / INTEGRATION |
| D-031 | Data Dictionary | EPPM publishes a Version 26 Data Dictionary for fields. | Professional all-guides set does not list a parallel Professional Data Dictionary. | EPPM PLATFORM / DATA CONTRACT |
| D-032 | Extended Schema | EPPM publishes a separate Extended Schema Guide for reporting views and their population. | No parallel Professional Extended Schema Guide appears in the Professional V26 guide list. | EPPM PLATFORM / REPORTING DATA |
| D-033 | Reporting | EPPM Reporting Guide covers sample BI Publisher reports, report schedules/delivery, publication services and table auditing. | Professional Reporting Guide covers desktop Report Wizard/Editor, report groups, preview/print/import/export and graphics. | BOTH / DIFFERENT REPORTING STACK |
| D-034 | Report header/footer defaults | Professional Reporting Guide explicitly marks default global report headers, footers and custom labels as P6 EPPM Only. | Not available in Professional-only database context. | EPPM DB CONTEXT |
| D-035 | XER exchange | Both document XER project import/export. | Professional also documents XER import/export. | SHARED CORE / FORMAT DETAILS DIFFER |
| D-036 | Primavera XML | Both document Primavera XML project import/export. | Professional also documents Primavera XML workflows. | SHARED CORE / FORMAT DETAILS DIFFER |
| D-037 | Microsoft Project exchange | Both guide sets document Microsoft Project exchange; EPPM also publishes separate MPX/XML data-map guides. | Professional has desktop import/export/template workflows. | BOTH / DIFFERENT DATA MAP |
| D-038 | UN/CEFACT, IPMDAR, CPP | EPPM has separate Version 26 data-map guides and Help workflows for these formats. | No corresponding dedicated data-map guides appear in the Professional V26 all-guides list. | EPPM PLATFORM / FORMAT SUPPORT |
| D-039 | XLSX data maps | EPPM has a dedicated XLSX Import/Export Data Map Guide and Help workflows. | Professional Help documents Excel import/export/templates but not a parallel published data-map guide. | BOTH / DIFFERENT CONTRACT DETAIL |
| D-040 | Unifier integration | EPPM documents schedule, summary and activity sheet linking/exchange, with integration privileges and Gateway deployment. | Professional Help identifies EPPM-specific Unifier linking workflows; the desktop client may initiate exchange after initial Unifier-side setup. | EPPM DB CONTEXT / INTEGRATION |
| D-041 | Primavera Cloud integration | EPPM Help documents OPC scope, tasks, enterprise risk sharing, project linking and transfer/update workflows. | Professional has no equivalent web integration workspace in its own UI; it may be used as the connected client for shared project data. | EPPM PLATFORM / INTEGRATION |
| D-042 | Primavera Gateway | EPPM Help includes Gateway linking/configuration workflows. | Not a native Professional-only desktop service. | EPPM PLATFORM / INTEGRATION |
| D-043 | Industry Type | Professional Help explicitly marks “Set the Industry Type” as P6 EPPM Only. | Not a Professional-only database workflow. | EPPM DB CONTEXT |
| D-044 | Top-down estimation | Professional Help explicitly marks estimation using prior experience/function points and applying saved estimates as P6 Professional Only. | Not an EPPM database workflow. | PRO DB CONTEXT |
| D-045 | Professional Risks | Professional Help explicitly marks its Risks feature P6 Professional Only. | EPPM has a distinct enterprise/project risk model; the two risk features must not be treated as identical. | PRO DB CONTEXT / BOTH DIFFERENT DATA MODEL |
| D-046 | Job Services | Professional Help explicitly labels Job Services and job configuration P6 Professional Only. | EPPM has its own project scheduled/publication/summarizer services. | PRO DB CONTEXT / BOTH DIFFERENT SERVICE MODEL |
| D-047 | Admin Preferences | Professional Help labels the Administrative Preferences area and many settings P6 Professional Only. | EPPM manages corresponding enterprise settings in browser Application Settings and administration. | BOTH / DIFFERENT ADMIN SURFACE |
| D-048 | Admin Categories | Professional Help labels categories such as baseline types, expense categories, WBS categories, document categories/statuses, risk categories, notebook topics and units of measure as Professional Only. | EPPM maintains corresponding enterprise dictionaries under Enterprise Data, with a different web workflow and privilege model. | BOTH / DIFFERENT ADMIN SURFACE |
| D-049 | Currencies and financial periods | Professional Help labels currency and financial-period administration P6 Professional Only. | EPPM has enterprise currencies and financial periods in its browser Enterprise Data. | BOTH / DIFFERENT ADMIN SURFACE |
| D-050 | Professional toolbar/menu customization | Professional Help documents desktop toolbar/menu creation, movement, command editing and customization. | EPPM uses a browser navigation/context interface rather than the same desktop menu/toolbar customization model. | PRO CLIENT SURFACE |
| D-051 | Professional Visualizer | Professional V26 includes P6 Visualizer Help for customizable Gantt charts and Timescaled Logic Diagrams. | EPPM web provides its own views/charts/portlets; no equivalent Visualizer guide is listed in the EPPM guide set. | PRO CLIENT SURFACE |
| D-052 | Professional project website publishing | Professional has Project Web Site Publisher to publish layouts, reports and project web sites. | EPPM's server publication services publish enterprise/project/baseline data for EPPM reporting and web application consumption. | BOTH / DIFFERENT PUBLISHING PURPOSE |
| D-053 | Professional desktop layouts | Professional has detailed desktop Activity Table, Gantt, Activity Network, Trace Logic, profiles, spreadsheets, tracking layouts and custom toolbars. | EPPM has browser Activity/EPS views, grids, portlets and dashboard layouts. | BOTH / DIFFERENT CLIENT UX |
| D-054 | Global Change | Both help sets document Global Change and related operations. | Both help sets document Global Change and related operations. | SHARED CORE |
| D-055 | EPS, OBS, WBS, activities, relationships | Both help sets document the core project structures and activity network/schedule concepts. | Both help sets document the core project structures and activity network/schedule concepts. | SHARED CORE |
| D-056 | Calendars, baselines, constraints, CPM/scheduling | Both help sets document calendars, baselines, relationships, constraints, scheduling and leveling. | Both help sets document calendars, baselines, relationships, constraints, scheduling and leveling. | SHARED CORE; verify behavior parity separately |
| D-057 | Resources, roles, assignments, curves, future period planning | Both help sets document resource/role assignments, curves and future period planning, with distinct web/desktop planning views. | Both help sets document resource/role assignments, curves and future period planning, with distinct web/desktop planning views. | BOTH / DIFFERENT SURFACE |
| D-058 | Earned Value | Both help sets document Earned Value; Professional has standalone-database default settings that are explicitly Professional Only, while EPPM has enterprise application settings. | Both products expose Earned Value; configuration path/context differs. | BOTH / DIFFERENT ADMIN MODEL |
| D-059 | Issues and thresholds | Both help sets document issues/thresholds, though the Professional TOC includes its own desktop issue navigator and tracking-layout workflows. | EPPM includes browser issue pages and enterprise issue-code data. | BOTH / DIFFERENT SURFACE |
| D-060 | Notebooks and UDFs | Both help sets document notebooks and user-defined fields, including EPPM enterprise UDF types. | Professional also documents user-defined fields and notebook topics; scope/type coverage must be checked field-by-field before declaring equivalence. | BOTH / FIELD-LEVEL REVIEW REQUIRED |

### Topic-level source pages opened during this pass

- EPPM dashboard creation: https://docs.oracle.com/cd/G48897_01/p6help/en/7826.htm
- EPPM portlets: https://docs.oracle.com/cd/G48897_01/p6help/en/47039.htm
- EPPM portfolio creation/access: https://docs.oracle.com/cd/G48897_01/p6help/en/7858.htm
- EPPM What-if Analysis: https://docs.oracle.com/cd/G48897_01/p6help/en/36491.htm
- EPPM Capacity Planning role allocation: https://docs.oracle.com/cd/G48897_01/p6help/en/7855.htm
- EPPM Budget Change Requests: https://docs.oracle.com/cd/G48897_01/p6help/en/7962.htm
- EPPM Unifier Activity Sheet integration: https://docs.oracle.com/cd/G48897_01/p6help/en/89593.htm
- Professional database-context qualifier: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/62783.htm
- Professional Reporting Guide EPPM-only report defaults: https://docs.oracle.com/cd/G48902_01/English/admin/p6_pro_reporting/p6_pro_reporting.pdf
- Professional V26 Admin Guide TOC: https://docs.oracle.com/cd/G48902_01/English/admin/p6_pro_admin/toc.htm
- Professional V26 Reporting Guide TOC: https://docs.oracle.com/cd/G48902_01/English/admin/p6_pro_reporting/toc.htm
- EPPM V26 REST API TOC: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/toc.htm
- EPPM V26 Team Member Help: https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/toc.htm

## 12. What is now established vs what is not

Established from official Version 26 TOCs, product-qualified topic titles, guide-set listings and opened topic pages:
- The distinct three-surface product model in section 9.
- The explicit EPPM-database-only and Professional-database-only qualifiers recorded in D-006 to D-008, D-013, D-034, D-043 to D-046.
- The existence and functional scope of dashboards/portlets, portfolio analysis, capacity planning, budget-change logging, Unifier sheet integration, Team Member workflows, EPPM reporting/API/schema and Professional desktop-only workflows in the matrix.
- The distinction between EPPM enterprise risk management and the Professional-only Risks feature.
- The distinction between EPPM content repository/reviews and Professional WPs & Docs location-reference workflows.

Not established, and therefore not claimed:
- A page-by-page reading of every single topic in both 825-line and 984-line Help TOCs.
- A complete one-to-one semantic pairing of every Help topic.
- Every field-level difference in the EPPM Data Dictionary vs Professional data map/database schema.
- Every REST/SOAP endpoint vs Professional Integration API operation and all version-specific payload/field differences.
- Every licensing entitlement, deployment-specific option and integration prerequisite.
- Full test-backed behavioral parity or absence for all shared-core functions.

These remaining items require full guide-topic ingestion and an automated/manual topic-pairing pass. This artifact is now a substantially expanded product-level difference register, but must not be marked as an exhaustive page-by-page source audit until those evidence items are produced.

## 13. CUBI product implications — reference only, no implementation authorization

For the future EPPM MENU concept, the most relevant EPPM enterprise capabilities to model as candidate modules are:

1. Personal and shared dashboards / portlet-style widgets.
2. My assigned activities, status submissions and review state.
3. Timesheets, approvals, delegates and history.
4. Issues, project risks, risk response plans and document reviews.
5. Portfolio/project performance and capacity indicators.
6. Notifications, email status, resource-team communications.
7. Documents and managed repository/review references.
8. Reports, report run history and published project data.
9. User access, module entitlements, OBS/resource scoping and UI-view permissions.
10. API-backed integrations and data provenance.

This is a product-design input only. Do not implement these modules, alter the current Project Control Workspace, or modify Professional V26 parity work under this audit. Any future EPPM MENU scope requires separate explicit approval and a dedicated implementation plan.
