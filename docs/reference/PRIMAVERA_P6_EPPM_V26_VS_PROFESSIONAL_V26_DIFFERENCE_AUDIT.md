# Primavera P6 EPPM V26 vs P6 Professional V26 — Difference Audit

- **Status:** IN PROGRESS — initial official-Help comparison; not exhaustive and not an implementation authorization.
- **Baseline:** Oracle Primavera P6 EPPM Version 26 and P6 Professional Version 26.
- **Prepared:** 2026-11-14
- **Purpose:** Independently compare P6 EPPM V26 and P6 Professional V26 product capabilities, workflows, data contracts and integration boundaries using Oracle primary sources.
- **Scope boundary:** This is a product-documentation audit only. It is not a CUBI workspace, application, agent, implementation or feature-development task. No workspace/code/agent work is inspected or modified by this audit.

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
| EPPM-DIFF-008 | Unifier integration | EPPM owns initial project-link/configuration, CBS mapping, Gateway and scheduled-service setup | Professional V26 User Guide documents Schedule Sheet, Summary Sheet and Activity Sheet exchange actions after EPPM is configured; Activity Sheet's first exchange must originate from Unifier | BOTH_DIFFERENT_SURFACE; EPPM_ONLY_CONFIRMED for initial linking/setup, not for all exchange actions | Compare each sheet type, mapping, sync direction, setup privilege and Unifier version |
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
8. Keep the comparison independent of product implementation: do not inspect or modify any workspace, application code, agent-owned task, scheduler, menu or project data as part of this audit.
9. Record unresolved product/API/runtime questions explicitly; do not convert them into implementation tasks or assume missing documentation proves missing capability.
10. Have an independent reviewer verify the source interpretation before declaring the audit complete.

## 7. Deliverables and acceptance criteria

- [ ] Source inventory for both products with exact topic counts and hashes.
- [ ] Complete EPPM-to-Professional topic pairing matrix.
- [ ] Every unmatched topic reviewed and classified; no inference from title-only absence.
- [ ] Every confirmed difference has exact Oracle source links and behavior notes.
- [ ] Reverse-direction Professional-only features are included.
- [ ] Deployment, license, module and integration dependencies are separately recorded.
- [ ] All remaining product/API/runtime gaps are either closed with V26 evidence or explicitly retained as NOT VERIFIED.
- [ ] Independent review and evidence log completed.
- [ ] Any future implementation request is handled separately and is not part of this audit.

**Current state:** the initial TOC comparison and explicit product qualifiers are recorded. The exhaustive topic-page comparison is not complete. This document does not inspect or authorize any product/workspace implementation.

## 8. Audit tracking and official references

- Related audit Issue: https://github.com/consttruction-pm/consttruction-pm-platform/issues/1925
- Related documentation PR: https://github.com/consttruction-pm/consttruction-pm-platform/pull/1926
- EPPM V26 Help: https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm
- Professional V26 Help: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
- EPPM V26 All Guides: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/books.html
- Professional V26 All Guides: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/books.html

This audit does not cross-reference or validate implementation registries, application code, workspace files, tests or agent work. Those are outside the requested product-comparison scope.

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
| D-003 | Portfolio management | EPPM supports global, multiple-user and user portfolios, manual or filter-based membership, access control, portfolio views, scorecards, bubble/pie/histogram views and What-if analysis. | Professional supports manual and filtered portfolios; Help confirms projects cannot be manually added to a filtered portfolio. Its filter criteria/refresh details are less fully documented, and it does not document the same web portfolio-analysis/portlet surface. | BOTH / DIFFERENT SURFACE |
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
| D-040 | Unifier integration | EPPM owns initial project-linking/configuration, CBS mapping and Gateway setup. | Professional V26 supports Schedule Sheet, Summary Sheet and Activity Sheet exchange actions after EPPM is configured; Activity Sheet first exchange must originate from Unifier. | BOTH / DIFFERENT SURFACE |
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

## 13. Product-only scope boundary

This audit compares Oracle P6 EPPM V26 and P6 Professional V26 as products. It does not propose, design, implement or validate a third-party workspace or product. It does not inspect or modify any CUBI workspace, application code, scheduler, navigation, project data, tests or agent-owned work. Any implementation request must be separate, explicit and outside this comparison.

---

# Version 26 source-level comparison — expanded verified findings

**Review update:** 2026-11-14. This section records direct review of the two official Help topic trees, selected feature pages, and the official Version 26 guide catalogues. It supersedes any earlier implication that the initial 20 candidates constituted a complete review.

## A. Exact source inventory and documentation-set boundary

| Source | Oracle Version 26 evidence | What can be stated |
|---|---|---|
| EPPM Help topic tree | https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm — 825 rendered TOC lines | EPPM Help has a distinct web/application-oriented topic tree. TOC line count is not a page count. |
| Professional Help topic tree | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm — 984 rendered TOC lines | Professional Help has a distinct desktop/client-oriented topic tree. TOC line count is not a page count. |
| EPPM all-guides catalogue | https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/books.html | Includes EPPM Application Administration, Identity Management Administration, Data Dictionary, Extended Schema, EPPM Reporting, REST API, SOAP Web Services Programming and Reference, Team Member Help, Import/Export Data Maps and Integration guides. |
| Professional all-guides catalogue | https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/books.html | Lists Professional Administration, Help, Licensing, Reporting, User Guide and P6 Visualizer Help. |

**Counting rule:** 825 and 984 are rendered TOC line counts, not unique page/topic counts and not PDF page counts. The earlier “815-page” description is not validated by those numbers. The exact number of topic pages requires crawling each link target and deduplicating canonical URLs. This audit does not mislabel TOC lines as pages.

**Corpus correction remains in force:** the existing CUBI Knowledge V26 corpus described in SOURCE_STATUS is the Professional help/user-guide corpus, not an EPPM Help ingestion. EPPM source identity and ingestion need to be separate.

## B. Confirmed direction-specific markers in Professional Help

The Professional V26 Help itself explicitly labels the following topic groups. This is stronger evidence than absence from a TOC.

### B1. EPPM-only labels exposed in Professional Help

| Finding | Exact Professional Help topic label | Classification | Implication |
|---|---|---|---|
| EPPM-ONLY-01 | “Designating an activity owner (P6 EPPM Only)” | EPPM_ONLY_CONFIRMED | Activity ownership workflow is not a generic Professional desktop capability. |
| EPPM-ONLY-02 | “Change an activity's cost breakdown structure assignment (P6 EPPM Only)” | EPPM_ONLY_CONFIRMED | CBS assignment is an EPPM-specific activity workflow in this client help context. |
| EPPM-ONLY-03 | “Using Reflection projects and Activity Owner features to collect and review activity status (P6 EPPM Only)” | EPPM_ONLY_CONFIRMED | Reflection-based status collection/review must not be conflated with ordinary project copy/what-if workflows. |
| EPPM-ONLY-04 | Tools > Approvals; “Timesheets overview” and approve/reject/delegate actions under “Approvals (P6 EPPM Only)” | EPPM_ONLY_CONFIRMED | The EPPM approval workflow is explicitly distinguished in Professional Help. |
| EPPM-ONLY-05 | “Set the Industry Type (P6 EPPM Only)” | EPPM_ONLY_CONFIRMED | Industry-type administration is EPPM-specific in this documented context. |
| EPPM-ONLY-06 | “Working With Oracle Primavera Cloud (P6 EPPM Only)” and Gateway exchange | EPPM_ONLY_CONFIRMED | EPPM-specific product integration workflow; distinguish from general P6 data exchange. |
| EPPM-ONLY-07 | “Primavera Cache Service (P6 EPPM Only)” including cloud cache, offline work and synchronization | EPPM_ONLY_CONFIRMED | Cloud Connect local cache is a separate Professional deployment capability, not the EPPM browser UI. |
| EPPM-ONLY-08 | “Linking Primavera Unifier data (P6 EPPM only)” and project-link setup | EPPM_ONLY_CONFIRMED for initial linking/configuration | Professional V26 separately documents Schedule Sheet, Summary Sheet and Activity Sheet exchange actions after EPPM setup; do not label all exchange actions EPPM-only. |

Source: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (topic tree sections “Activities”, “Reflection”, “Tools”, “Administration”, and “Reference”).

### B2. Professional-only labels exposed in Professional Help

| Finding | Exact Professional Help topic group | Classification | Important caveat |
|---|---|---|---|
| PRO-ONLY-01 | Adding and Assigning Risks (P6 Professional Only) | PROFESSIONAL_ONLY_CONFIRMED for this desktop Risks feature | EPPM separately documents Enterprise Risk Data, Project Risks, scoring matrices, thresholds, categories and response plans. Risk as a business domain is not Professional-only. |
| PRO-ONLY-02 | Performing Top-down Estimation; prior-experience/function-point methods and saved estimates | PROFESSIONAL_ONLY_CONFIRMED | Do not confuse this with WBS top-down planning or cost/effort estimation in other products. |
| PRO-ONLY-03 | Job Services and configuring a job service (P6 Professional Only) | PROFESSIONAL_ONLY_CONFIRMED for this named Professional feature | EPPM has separate Project Scheduled Services and Publication Services; they are not automatically equivalent to desktop Job Services. |
| PRO-ONLY-04 | Administrative Preferences (including invalid upload types, global code separator, week start, default activity duration, hierarchy/code/baseline limits, default workhours and default EV settings) | PROFESSIONAL_ONLY_CONFIRMED for those named client administration settings | EPPM has Application Settings; compare each setting separately rather than assuming all admin settings are absent. |
| PRO-ONLY-05 | Administrative Categories (baseline types, expense categories, WBS categories, document categories/statuses, risk categories, notebook topics, units of measure) | PROFESSIONAL_ONLY_CONFIRMED for this Professional administration menu set | EPPM has Enterprise Data dictionaries; entity overlap does not prove identical administration surface. |
| PRO-ONLY-06 | Defining Currencies and Managing Financial Periods | PROFESSIONAL_ONLY_CONFIRMED for the documented Professional administration workflows | EPPM currency/time-period preferences and period-performance features are separate; compare data model and workflow. |
| PRO-ONLY-07 | Managing User Security, Resource Security and EPS-level Activity Code Security | PROFESSIONAL_ONLY_CONFIRMED for the Professional client administration workflows as labelled | EPPM has its own User Access, OBS, module access, resource access, global/project security profiles and UI views. Do not infer EPPM has no security model. |
| PRO-ONLY-08 | Admin Menu and Administrator Toolbar (P6 Professional Only) | PROFESSIONAL_ONLY_CONFIRMED for desktop UI surface | EPPM administration is delivered through web Administration pages and separate identity-management tooling. |
| PRO-ONLY-09 | Set global summarization options (P6 Professional Only) | PROFESSIONAL_ONLY_CONFIRMED for this Professional setting | EPPM Application Settings documents Summarization Periods; the controls and services differ. |

Source: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm (TOC topics labelled “P6 Professional Only”).

## C. Capability-by-capability product comparison

Legend:
- **EPPM web/enterprise** means a documented EPPM application capability; it does not necessarily mean Professional cannot access the same underlying EPPM database entity.
- **Professional desktop** means a documented Professional client workflow.
- **Different surface** means a related function exists in both products but actors, UI, configuration, service architecture or workflow differ.
- **Conditional** means licensing, deployment, configuration, connected services or modules must be checked.

| ID | Capability area | EPPM V26 Help / guide evidence | Professional V26 Help / guide evidence | Result |
|---|---|---|---|---|
| CMP-001 | Primary application surface | Browser-based P6 web application; EPPM Help has dashboard, portfolio, project and administration pages | Windows desktop client with windows, toolbars, menu customization, layouts and Visualizer | BOTH_DIFFERENT_SURFACE |
| CMP-002 | Dashboards | User, multi-user and global dashboards; dashboard creator controls content/layout/access; dashboard data appears in portlets | No equivalent EPPM-style dashboard-home/portlet model in the Professional desktop TOC | EPPM_WEB_CAPABILITY; exact client parity not established |
| CMP-003 | Portlets | Expandable themed windows; show data by association, ownership or filters; shared dashboards support centralized collaboration | Professional uses windows, layouts, tracking layouts and reports rather than the EPPM dashboard portlet container | EPPM_WEB_CAPABILITY |
| CMP-004 | Portfolio objects | User, multi-user and global portfolios; manual or filtered membership; summary/status of multiple projects; portfolio views and scorecards | Professional supports manual and filtered portfolios, adding/removing projects/users and portfolio details; filtered portfolios cannot be manually populated | BOTH_SHARED with DIFFERENT_SURFACE in analysis/visualization |
| CMP-005 | Portfolio analysis | Portfolio views include scorecards, bubble charts, pie charts, histograms and What-if Analysis | Professional supports what-if projects and portfolio membership; no same EPPM web portfolio-view analysis chapter in its TOC | BOTH_DIFFERENT_SURFACE |
| CMP-006 | Capacity Planning | Dedicated EPPM Capacity Planning page and role allocation analysis | Professional resource/role assignments and resource analysis; no same named EPPM capacity page in TOC | BOTH_DIFFERENT_SURFACE |
| CMP-007 | EPS / project structure | EPS and project management via web pages | EPS and project management via desktop windows | BOTH_SHARED |
| CMP-008 | WBS | EPPM WBS pages, milestones, categories and EV | Professional WBS chart/table, weighted milestones, categories and EV | BOTH_SHARED |
| CMP-009 | Activities and relationships | EPPM activity pages and browser interaction | Rich desktop Activity Table, Network, Gantt, trace logic and activity detail workflows | BOTH_SHARED; DIFFERENT_SURFACE |
| CMP-010 | Scheduling engine controls | EPPM scheduling page exposes general/advanced options and schedule actions | Professional schedule dialog exposes schedule options and desktop scheduling workflows | BOTH_SHARED; exact option-by-option parity needs a separate scheduler-options diff |
| CMP-011 | Multiple float paths / critical path | EPPM has critical activity and float topics | Professional has multiple critical float path, trace logic and critical path topics | BOTH_SHARED; verify calculation-option equivalence separately |
| CMP-012 | Resource and role assignments | EPPM assignment, staffing, resource teams, role teams and capacity/resource analysis | Professional assignment, rate type/source, curves, future period buckets, resource explorer and profiles | BOTH_SHARED; DIFFERENT_SURFACE |
| CMP-013 | Resource analysis | EPPM Resource Analysis, role/resource usage and unstaffed activity assignment | Professional Resource Analysis layouts, Project Gantt/Profile, Resource Explorer and dynamic leveling | BOTH_DIFFERENT_SURFACE |
| CMP-014 | Team Member Web/Mobile | Separate Team Member Web/mobile status and time reporting applications; own Help guide | Professional desktop is a full planning client, not the Team Member Web/mobile UI | EPPM_ECOSYSTEM_CAPABILITY; separate Team Member product documentation |
| CMP-015 | Email Statusing | EPPM email status service for activity updates and email notifications | Professional can participate in EPPM connected workflows; Help describes EPPM-only workflows in client context | EPPM_SERVICE_CAPABILITY; deployment-dependent |
| CMP-016 | Activity Owner | Explicit EPPM-only marker in Professional Help | Professional Help marks feature EPPM Only | EPPM_ONLY_CONFIRMED |
| CMP-017 | Reflection status review | EPPM status updates, reviewers, accept/reject/override/hold and history | Professional Help marks Reflection + Activity Owner status collection EPPM Only | EPPM_ONLY_CONFIRMED |
| CMP-018 | Timesheets | EPPM Timesheets, approvals/rejections, delegates, resource configuration and Team Member reporting | Professional Help marks Approvals/Timesheet approval workflow EPPM Only | EPPM_ONLY_CONFIRMED for approval workflow |
| CMP-019 | Issues | EPPM issue pages and project issue workflows | Professional issue creation, responsibility, tracking layouts, history and email | BOTH_SHARED; DIFFERENT_SURFACE |
| CMP-020 | Thresholds | EPPM performance thresholds and project health metrics | Professional thresholds and threshold-generated issues | BOTH_SHARED |
| CMP-021 | Risks | Enterprise risk data, scoring matrices, categories, thresholds, project risks, response plans and OPC sharing | Separate Professional Risks feature explicitly marked P6 Professional Only | BOTH_DIFFERENT_SURFACE; separate risk models |
| CMP-022 | Documents without repository | EPPM document records can be maintained without content repository | Professional Work Products and Documents stores records and location references | BOTH_SHARED; DIFFERENT_STORAGE_MODEL |
| CMP-023 | Managed document repository | EPPM Content Repository supports templates, document storage, check-in/out and document review flows | Professional Help describes document records and location references; not the same managed web repository/review model | EPPM_WEB_CAPABILITY; deployment/configuration-dependent |
| CMP-024 | Document reviews | EPPM document review workflows and dashboard portlets | No matching document-review workflow in Professional Help TOC | EPPM_WEB_CAPABILITY |
| CMP-025 | Project scheduled/publication services | EPPM Application Settings, publication services, project scheduled services and published reporting data | Professional has report publishing, Project Website Publisher and desktop Job Services | BOTH_DIFFERENT_SURFACE |
| CMP-026 | Desktop Job Services | EPPM has separate server-side scheduled/publication services | Job Services explicitly marked P6 Professional Only | PROFESSIONAL_ONLY_CONFIRMED for named feature |
| CMP-027 | Audit | EPPM has Table Auditing, audit settings and viewing audit data | Professional Help includes consent auditing and desktop administrative topics; does not show same EPPM table-audit workflow | EPPM_WEB/ADMIN CAPABILITY; inspect audit data model and retention |
| CMP-028 | Enterprise user access | EPPM creates accounts and assigns module access, OBS, resource access, global/project security profiles and UI views | Professional Help includes client user security, resource security, global/project profiles, and administrative access controls; some are Professional Only | BOTH_DIFFERENT_SURFACE |
| CMP-029 | Identity management | EPPM guide catalogue has separate Identity Management Administration Guide for users, personal info, companies and passwords | Professional guide catalogue has Professional Administration Guide; identity-management guide not listed in Professional set | EPPM_PLATFORM/DEPLOYMENT CAPABILITY |
| CMP-030 | User Interface Views | EPPM admin can create/configure UI Views and assign to users | Professional offers layouts, user preferences and menu/toolbar customization | BOTH_DIFFERENT_SURFACE |
| CMP-031 | REST API | Dedicated EPPM REST API Release 26 with endpoint catalogue | No Professional REST API guide in the published Professional Version 26 all-guides list | EPPM_DOCUMENTED_API_SURFACE; do not infer all client internals are API-only |
| CMP-032 | SOAP Web Services | Dedicated EPPM SOAP Web Services Programming and Reference Guides | No corresponding Professional SOAP guide in the Professional all-guides list | EPPM_DOCUMENTED_INTEGRATION_SURFACE |
| CMP-033 | Data Dictionary | Dedicated EPPM Data Dictionary | No corresponding Professional Data Dictionary guide listed in the Professional guide catalogue | EPPM_DOCUMENTED_DATA_REFERENCE |
| CMP-034 | Extended Schema | Dedicated EPPM Extended Schema guide for reporting views | Professional has its own reporting guide; no matching Extended Schema guide listed in Professional catalogue | EPPM_REPORTING_DATA_SURFACE |
| CMP-035 | Reporting | EPPM Reporting Guide covers sample reports, publication services and table auditing | Professional Reporting Guide covers configuring/running desktop reports; P6 Visualizer provides Gantt and Timescaled Logic Diagrams | BOTH_DIFFERENT_SURFACE |
| CMP-036 | Import/export | EPPM guides include XER Project/Resource/Role maps, XLSX, XML, MPX, UN/CEFACT, IPMDAR, CPP and Unifier Schedule Sheet maps | Professional Help has import/export workflows and Professional reporting/desktop tooling; guide catalogue has no equivalent list of EPPM mapping guides | BOTH_DIFFERENT_SURFACE; exact field maps differ |
| CMP-037 | Primavera Unifier integration | EPPM owns initial linking/configuration, CBS mapping, Gateway flows and Project Scheduled Services | Professional V26 User Guide documents Schedule Sheet, Summary Sheet and Activity Sheet exchange actions after EPPM setup; Activity Sheet's first exchange must originate from Unifier | BOTH_DIFFERENT_SURFACE; EPPM_ONLY_CONFIRMED for initial linking/setup |
| CMP-038 | Oracle Primavera Cloud integration | EPPM supports scope, tasks, enterprise risk and Gateway transfer; Help describes send/return workflows | Professional Help labels OPC/Gateway workflow P6 EPPM Only | EPPM_ONLY_CONFIRMED for documented integration flow |
| CMP-039 | Primavera Gateway | EPPM documents Gateway configuration and data flows for Unifier/OPC integrations | Professional reference topics mark the related EPPM integration paths as EPPM Only | EPPM_INTEGRATION_CAPABILITY |
| CMP-040 | Cloud cache/offline | EPPM has Team Member and web client services; it is not the Professional local cache feature | Professional Help documents Primavera Cache Service, offline work and Cloud Connect local synchronization as EPPM-only scoped reference feature | PROFESSIONAL_CLIENT_DEPLOYMENT_FEATURE within EPPM ecosystem |
| CMP-041 | Project templates | EPPM templates and project creation in browser | Professional templates and desktop project workflows | BOTH_SHARED; DIFFERENT_SURFACE |
| CMP-042 | Global Change | EPPM has web Global Search & Replace templates and enterprise global data search/replace | Professional has Global Change specifications, expressions, arithmetic, import/export | BOTH_DIFFERENT_SURFACE; do not equate Global Search & Replace and Global Change |
| CMP-043 | Store Period Performance | EPPM stores period performance via web workflow | Professional has Store Period Performance, post actuals and past-period editing | BOTH_SHARED; DIFFERENT_SURFACE |
| CMP-044 | Future Period Planning | EPPM has Future Period Planning layout and assignment period editing | Professional has manual future-period bucket planning and extensive FAQ/workflows | BOTH_SHARED; DIFFERENT_SURFACE |
| CMP-045 | Admin dictionaries | EPPM Enterprise Data pages include global dictionaries and user access configuration | Professional Administrative Categories menu and separate currencies/financial periods are explicitly Professional-only | BOTH_DIFFERENT_SURFACE |
| CMP-046 | Industry-specific field naming/type | EPPM Help supports industry-specific field names; Professional Help exposes Set Industry Type as EPPM Only | Professional can consume displayed names when connected but cannot use the EPPM-only administration control as a standalone feature | EPPM_ONLY_CONFIRMED for industry-type setting |
| CMP-047 | User preferences | EPPM global/view preferences, My Calendar, notifications and password/session settings | Professional client preferences include date/time/currency, email, startup, calculations and local UI settings | BOTH_DIFFERENT_SURFACE |
| CMP-048 | Consent / personal information | EPPM consent and auditing topics cover P6, Team Member and Professional clients | Professional has its own personal-information and consent topics | BOTH_SHARED; deployment-specific handling |
| CMP-049 | Visualizer | EPPM can provide visual/project information in web portlets and dashboards | Dedicated P6 Visualizer Help in Professional guide set, including Gantt and Timescaled Logic Diagrams | PROFESSIONAL_CLIENT_CAPABILITY |
| CMP-050 | Project Website Publisher | EPPM web publication/report services | Professional Help documents Project Website schemes and publishing reports to a website | BOTH_DIFFERENT_SURFACE |
| CMP-051 | Standalone / Cloud Connect modes | EPPM is server/web application deployment | Professional explicitly documents Standalone and Cloud Connect | PROFESSIONAL_DEPLOYMENT_CAPABILITY |
| CMP-052 | Remote project check-in/out | EPPM project access is server-side and browser-oriented | Professional Help documents remote projects, check out to XML/local database and check-in workflows | PROFESSIONAL_CLIENT_CAPABILITY |
| CMP-053 | Undo and local editing ergonomics | EPPM Help has undoing mistakes in web pages | Professional has Undo reference topic and extensive desktop clipboard/table/toolbar behavior | BOTH_DIFFERENT_SURFACE |
| CMP-054 | Desktop menu/toolbar customization | EPPM web interface is browser-based and uses preferences/views | Professional offers customizable menus, toolbars, icons and menu commands | PROFESSIONAL_CLIENT_CAPABILITY |
| CMP-055 | User-defined fields | EPPM has project/resource/activity/risk UDF workflows | Professional has UDFs in project/resource/activity and related areas | BOTH_SHARED; field support differs by entity/API |
| CMP-056 | Code dictionaries | EPPM has project/resource/role/assignment codes and values | Professional has project/resource/role/activity codes and values, including colors | BOTH_SHARED; compare scope and field support |
| CMP-057 | Cost Breakdown Structure | EPPM CBS assignment and Unifier cost integration | Professional Help marks activity CBS assignment EPPM Only | EPPM_ONLY_CONFIRMED for the named activity assignment operation |
| CMP-058 | Performance metrics / health | EPPM dashboards include project health, CPI/SPI/TCPI and thresholds | Professional has earned value and project analysis reports/profiles | BOTH_SHARED; DIFFERENT_PRESENTATION |
| CMP-059 | Email notifications | EPPM email notifications cover documents, issues, timesheets, managers/resources and status updates | Professional can configure email settings and send email about issues; several EPPM status services remain separate | BOTH_DIFFERENT_SURFACE |
| CMP-060 | Resource teams | EPPM has Resource Teams and dashboard/resource-team notification workflows | Professional has resource hierarchy/security and assignments, but not equivalent EPPM team-member distribution workflow in same surface | EPPM_WEB_CAPABILITY; compare exact entities |
 
## D. Corrections to the initial 30-item list

1. **Risk management is not simply EPPM-only.** EPPM has Enterprise Risk Management and project risk response plans; Professional labels its own desktop Risks feature Professional Only. The correct comparison is two related but different risk feature sets.
2. **Timesheets are not simply absent from Professional.** Professional Help contains EPPM-only Approvals/Timesheet workflow. The EPPM application and Team Member help describe timesheet submission and approvals. This is an EPPM workflow that can be surfaced in a Professional client connected to EPPM; it is not an isolated product database feature.
3. **Unifier is not a simple yes/no integration.** Professional V26 documents Schedule Sheet, Summary Sheet and Activity Sheet exchange actions, but the initial project-linking/setup topic is explicitly P6 EPPM Only. Professional requires EPPM configured and the project linked. For Activity Sheets, the first exchange must be initiated from Unifier; subsequent exchanges can be initiated from Professional. Schedule Sheet uses EPPM Integration & Allow Lists; Summary/Activity Sheets use Gateway configuration.
4. **Job Services are not equivalent to Project Scheduled Services.** Professional Job Services are explicitly Professional Only. EPPM uses server-side project scheduled/publication services.
5. **Documents are not binary.** Professional Work Products and Documents can reference document locations. EPPM additionally documents a managed Content Repository and review workflows. Both have document-related capability, but the storage/workflow models differ.
6. **Portfolios are not EPPM-only.** Professional documents portfolio objects and project membership. EPPM adds web portfolio analysis views, scorecards and portlets.
7. **P6 Professional is not the EPPM web UI.** A Professional client can connect to an EPPM database and invoke certain EPPM-backed functions, but that does not make browser dashboards, Team Member, server publication, web user administration or portlet functionality part of the desktop client.
8. **The guide catalogues are different evidence sets.** EPPM has separately published API, schema, Data Dictionary, Team Member, SOAP, data-map and identity-management guides. Professional has separate Administration, Reporting, User, Licensing and Visualizer guides. A guide not listed in the other catalogue is a documented-guide difference, not by itself proof that no underlying feature/API exists.

## E. EPPM guide inventory for integration and data contracts

The Version 26 EPPM catalogue explicitly lists:
- Identity Management Administration Guide
- P6 EPPM Application Administration Guide
- P6 EPPM Client System Requirements
- CPP Import/Export Data Map Guide
- P6 EPPM Data Dictionary
- P6 EPPM Extended Schema Guide
- P6 EPPM Help
- P6 EPPM Importing and Exporting Guide
- IPMDAR Import/Export Data Map Guide
- Licensing Information User Manual
- Microsoft Project MPX and XML Data Map Guides
- P6 EPPM Reporting Guide
- P6 EPPM REST API Release 26
- UN/CEFACT Import/Export Data Map Guide
- Unifier Schedule Sheet Data Map Guide
- P6 EPPM User Guide
- P6 EPPM Virtual Desktop User Guide
- P6 EPPM Web Services Programming Guide
- P6 EPPM Web Services Reference Guide
- XER Project, Resource Only and Role Only Data Map Guides
- XLSX Import/Export Data Map Guide
- P6 Team Member Help
- What's New

The Professional Version 26 catalogue lists:
- P6 EPPM Client System Requirements
- P6 Professional Administration Guide
- P6 Professional Help
- P6 Professional Licensing Information User Manual
- P6 Professional Reporting Guide
- P6 Professional User Guide
- P6 Visualizer Help

This catalogue comparison is verified at:
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/books.html
- https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/books.html

## F. Direct topic-page evidence reviewed

- EPPM “About Dashboards”: https://docs.oracle.com/cd/G48897_01/p6help/en/6608.htm — defines user, multi-user and global dashboards, ownership and access.
- EPPM “About Portlets”: https://docs.oracle.com/cd/G48897_01/p6help/en/36613_1.htm — portlets are dashboard-only expandable themed windows, with data based on association, ownership or filters.
- EPPM “About Portfolios”: https://docs.oracle.com/cd/G48897_01/p6help/en/6611.htm — portfolio grouping, sharing and summary/status analysis.
- EPPM “Working With Primavera Unifier”: https://docs.oracle.com/cd/G48897_01/p6help/en/78769.htm — schedule, summary and activity sheets; CBS; Gateway; prerequisites and caveats.
- EPPM “Working With Oracle Primavera Cloud”: https://docs.oracle.com/cd/G48897_01/p6help/en/88851.htm — scope, risk, task and portfolio integration and transfer-back flow.
- EPPM Application Administration Guide: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-app-admin/index.html
- EPPM Data Dictionary: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-dd/index.html
- EPPM Extended Schema: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-ext-schema/index.html
- EPPM Reporting Guide: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-reports/index.html
- EPPM REST API Release 26: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/
- EPPM SOAP Programming Guide: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-ws-prog/index.html
- EPPM SOAP Reference Guide: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-ws-ref/index.html
- EPPM Team Member Help: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-tm/index.html

## G. Status, completeness and acceptance

### Completed comparison slices

The following documentary slices are now present on this branch and linked from this parent register:

| Artifact | Rows / scope | Status |
|---|---:|---|
| Capability-level master register | 60 capability areas | Completed as a first-pass surface comparison; not a page-level census |
| Security / User Access / OBS / Dashboard | 26 | Evidence-backed child matrix; full checkbox-level privilege parity remains open |
| Team Member / Status / Timesheet | 36 | Evidence-backed lifecycle matrix; exhaustive API field parity remains open |
| Reporting / Publication / Scheduled Services / Audit | 32 | Evidence-backed service/reporting matrix; all parameter and service fields remain open |
| Scheduling Options / Calculation Semantics | 40 | Evidence-backed V26 options and calculation comparison; runtime parity/API gaps remain open |
| Data Dictionary / Extended Schema / API Field Surface | 44 | Evidence-backed field-surface comparison; Professional V26 API schema and physical-column mapping remain open |
| Import/Export XER/XML/XLSX | 61 | Evidence-backed mapping comparison; exhaustive parsing of all format maps and round-trip tests remain open |
| Document Repository / Review Lifecycle | 50 | Evidence-backed optional-repository and review lifecycle comparison; repository connector/API gaps remain open |
| Risk Model / Scoring / Response Plans | 53 |
| Portfolio / Capacity Planning / What-if | 42 |
| Resource/Role Planning / Teams / Assignments | 40 |
| Unifier / Gateway / Primavera Cloud Integration | 40 |
| Dashboards / Portlets / UI Views / Access | 40 | Evidence-backed risk-model comparison; Professional V26 API and runtime scoring parity remain open |

**Total technical child-matrix entries: 504 rows across twelve topic-specific matrices**, in addition to the 60 capability-level rows in the parent register. The child matrices cite Oracle Version 26 source pages and preserve NOT VERIFIED / PARTIALLY VERIFIED states where the source set does not support a definitive conclusion.

### Source inventory status — do not confuse line counts with topic counts

The existing read-only Professional V26 evidence corpus records the following exact source audit:

| Source | Exact URL | Topics | HTTP | SHA-256 |
|---|---|---:|---:|---|
| Professional V26 Help (ingested authoritative edition) | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm | 982 | 200 | `ef78a19c6f3f2a7797456af6d592d5474d0c054692bf75de1392d1d894f1c92e` |
| Professional V26 User Guide (ingested authoritative edition) | https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm | 557 | 200 | `c619051559bba3c0e7eb650a21c5b7910f46948ed7e457caa82ba1f252e4be89` |
| Professional alternate Help TOC (not ingested) | https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-help/toc.htm | 988 | 200 | `00602394c07597172b4f911a5e1ec93a99539627765d5404f017dee58fd52cbf` |
| Professional alternate User Guide TOC (not ingested) | https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/toc.htm | 527 | 200 | `0d2487c625a532daac46df83b647cf5ff55883389c579d4b046c96f8af168e5b` |

The 982/557 and 988/527 counts refer to different official Professional TOC editions and must not be merged under one source identity.

For EPPM V26, the official Help TOC was opened and structurally inspected at https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm. The web-rendered page reports **825 lines**, not 825 topics. An exact EPPM topic count, URL/breadcrumb export and SHA-256 content hash have **not** been captured in this audit. The EPPM Help is not present in the referenced Professional-only evidence database. Therefore, no EPPM ingestion, exact topic census, or EPPM source hash is claimed here.

### Remaining acceptance work — audit is not complete

The issue's full acceptance criteria remain open. In particular:

1. Inventory every topic URL and breadcrumb in the EPPM V26 Help tree, record the exact topic count and content hash, and keep the EPPM source identity separate from the Professional corpus.
2. Pair every topic across the two V26 Help trees semantically, including one-to-many matches and unmatched topics.
3. Open and compare every paired and unmatched topic; capture UI path, actors, permissions, prerequisites, inputs, actions, outputs, validation, errors, licensing and deployment constraints.
4. Review all relevant EPPM and Professional User, Administration, Reporting, Integration, API, Schema and Data Dictionary guides, not only the high-impact pages cited in the current child matrices.
5. Complete field-by-field API/schema comparisons where a version-matched Professional V26 contract is available; where it is not publicly established, retain the gap rather than infer parity or absence.
6. Parse all remaining V26 import/export maps and compare exact field, table, tag, enumeration and import-action behavior.
7. Perform controlled runtime tests only when authorized test environments and representative project data are available; none are claimed in this documentary audit.
8. Obtain an independent human review and record its disposition. No independent GitHub review has been recorded on PR #1926 yet.

**Completion rule:** This audit must not be marked complete, the issue must not be closed, and the PR must not be merged until the full topic inventory/pairing and independent acceptance requirements above are met. The eleven child matrices close their named topic slices only; they do not substitute for the full source-corpus audit.

## H. CUBI project boundary

This document is an approved **reference analysis artifact only**. It does not alter:
- current CUBI Project Control Workspace,
- Professional V26 compatibility implementation,
- scheduler/calculation core,
- existing menus/navigation,
- project/activity/WBS data flows,
- or current production behavior.

Any later EPPM-derived CUBI feature proposal must be a separate requirement, with owner approval, security model, API/data contract and regression plan.
