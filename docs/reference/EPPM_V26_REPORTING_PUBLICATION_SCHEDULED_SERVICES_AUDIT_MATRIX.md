# P6 EPPM V26 vs P6 Professional V26 — Reporting, Publication, Scheduled Services and Audit Matrix

- **Status:** Topic-level comparison completed for the cited Version 26 guides/pages; exhaustive report-field and audit-table mapping remains open.
- **Prepared:** 2026-11-14
- **Parent audit:** `PRIMAVERA_P6_EPPM_V26_VS_PROFESSIONAL_V26_DIFFERENCE_AUDIT.md`
- **Scope:** Documentation/product comparison only. No CUBI Workspace, scheduler, menu, API, schema or Professional V26 implementation changes.

## 1. Evidence model

Distinguish four different mechanisms:
1. **Professional report authoring and execution** — Report Wizard/Editor, report groups/batches, print/export and Project Web Site Publisher.
2. **EPPM Reports page and Enterprise Reporting** — browser-based report catalogue, run/schedule/delivery and history.
3. **EPPM Publication Services** — publish project/global data into reporting tables (Extended Schema) used by reports and other EPPM pages.
4. **Table auditing** — capture insert/update/delete events into audit data, then publish audit data for reporting/viewing.

These are related but not interchangeable. In particular, P6 Professional Job Services and EPPM Project Scheduled Services are not the same scheduler.

## 2. Comparison matrix

| ID | Area | EPPM V26 | Professional V26 | Classification / conclusion |
|---|---|---|---|---|
| REP-001 | Guide scope | Dedicated EPPM Reporting Guide includes reports, Publication Services and Table Auditing. | Dedicated Professional Reporting Guide focuses on configuring/running Professional reports, Report Wizard/Editor, report groups and batches. | BOTH / DIFFERENT GUIDE AND SURFACE — CONFIRMED |
| REP-002 | Report authoring | EPPM uses reporting software/catalogue and shared report definitions; web users run/schedule available reports. | Professional provides Report Wizard and Report Editor for custom reports and graphics. | BOTH / DIFFERENT SURFACE — CONFIRMED |
| REP-003 | Report catalogue access | EPPM Reports page is exposed based on Enterprise Reports module access; administrators grant this module access. | Professional exposes Tools > Reports and desktop report catalogue, controlled by Professional/EPPM global report privileges depending on database. | BOTH / DIFFERENT AUTHORIZATION SURFACE — CONFIRMED |
| REP-004 | On-demand execution | EPPM Reports page can run a report with template, output format, delivery type and parameters; output can be file or email. | Professional can run/print/export reports using desktop report tools. | BOTH / DIFFERENT DELIVERY — CONFIRMED |
| REP-005 | Scheduled reports | EPPM Reports page supports schedules, recurring runs, email recipients, enabled/suspended state, status and history. | Professional has report batches and command-line batch execution; this is not the same browser scheduled-report catalogue. | BOTH / DIFFERENT SCHEDULING MODEL — CONFIRMED |
| REP-006 | Report schedule history | EPPM Schedules tab exposes scheduled run history and statuses including Completed, Failed, Pending and Suspended. | Professional report batch execution/logging differs; equivalent EPPM Reports Schedules page is not a Professional desktop feature. | EPPM WEB CAPABILITY — CONFIRMED |
| REP-007 | Delivery types | EPPM on-demand report can be delivered by email or file; scheduled reports are delivered by email. | Professional can print/save/export and publish files; report output workflows are desktop-oriented. | BOTH / DIFFERENT SURFACE — CONFIRMED |
| REP-008 | Long-running report | EPPM file-delivered reports taking more than 20 seconds run as a job service and notify user when complete. | Professional batch report execution is available via command line; no claim of same 20-second EPPM behavior in Professional. | EPPM SERVICE BEHAVIOR — CONFIRMED |
| REP-009 | Report groups | EPPM report folder arrangement is determined in P6 reporting software; access and catalogue are managed centrally. | Professional supports report groups, hierarchy and report-group editing. | BOTH / DIFFERENT ADMINISTRATION — CONFIRMED |
| REP-010 | Report batches | Professional Reporting Guide documents report batches, printing and command-line execution. | EPPM scheduled reports are separate from Professional batch definitions; do not map them one-to-one. | PROFESSIONAL DESKTOP FEATURE / EPPM ALTERNATIVE DIFFERENT — CONFIRMED |
| REP-011 | Command-line batch | Professional supports command-line batch reports; its V26 guide gives distinct actions/configuration when connected to Professional DB versus EPPM DB. | EPPM also has server-side scheduled services, but those are not the same command-line batch mechanism. | PROFESSIONAL CLIENT FEATURE WITH DB-CONDITIONAL BEHAVIOR — CONFIRMED |
| REP-012 | Report definition export | Professional exports report definitions as .ERP files. | EPPM reporting software has separate report catalogue/template mechanisms; .ERP is not a universal cross-product report interchange guarantee. | PROFESSIONAL FORMAT — CONFIRMED; cross-product portability NOT VERIFIED |
| REP-013 | Default report headers/footers | EPPM database supports global default report headers, footers and labels through EPPM privileges. | Professional Reporting Guide marks this capability “P6 EPPM Only”. | EPPM DB FEATURE — CONFIRMED |
| REP-014 | Project Web Site Publisher | EPPM has browser dashboards/reports and publication services; this is not the same as static Project Web Site Publisher. | Professional can publish project plans/layouts/reports as HTML web sites and transfer to intranet/FTP. | PROFESSIONAL DESKTOP PUBLISHER — CONFIRMED |
| REP-015 | Personal information in published website | EPPM reporting data is subject to P6 security and published data scope. | Professional Project Web Site Publisher warns personal information may be exposed; publisher controls detail of activity and resource personal information. | DIFFERENT SECURITY RISK / OUTPUT — CONFIRMED |
| REP-016 | Project Scheduled Services | EPPM can schedule Apply Actuals, Export, Import, Level, Project Checker, Publish, Schedule, Summarize and Send to Schedule Sheet for selected projects/EPS/code/portfolio scope. | Professional has Job Services (Professional Only) and other desktop automation; not identical to EPPM project scheduled service catalogue. | BOTH / DIFFERENT SERVICE MODELS — CONFIRMED |
| REP-017 | Project service targeting | EPPM project services target selected projects, EPS nodes, project code values or portfolios; project templates cannot be scheduled. | Professional Job Services target Professional desktop jobs/configuration and have distinct constraints. | EPPM SERVICE — CONFIRMED |
| REP-018 | Global publication services | EPPM schedules global data publication including enterprise, summary, resource management, security and audit data. | Professional does not expose the same EPPM global publication service administration surface in the desktop client. | EPPM PLATFORM SERVICE — CONFIRMED |
| REP-019 | Publication source tables | EPPM publishes project data (including baselines, summaries, calculations and audit data) and global data (enterprise, resource, security and audit data) into reporting tables / Extended Schema. | Professional report tools can query database data; this is not equivalent to EPPM Extended Schema publication pipeline. | EPPM PLATFORM DATA PIPELINE — CONFIRMED |
| REP-020 | Automatic publication | EPPM can publish automatically based on intervals and change thresholds; project priority can be configured from 1 (highest) to 100 (lowest). | Professional does not provide the same EPPM web Publication Services administration workflow. | EPPM PLATFORM SERVICE — CONFIRMED |
| REP-021 | On-demand publication | EPPM can queue enabled projects for publication; service status can be checked from User > View Service Status. | Professional does not provide the same EPPM on-demand publish queue surface. | EPPM PLATFORM SERVICE — CONFIRMED |
| REP-022 | Baseline publication | EPPM baseline publication requires project data publication for relevant projects and baseline publication enabled. | Professional baseline/report calculations are handled through its desktop report/summarization mechanisms. | BOTH / DIFFERENT DATA PIPELINE — CONFIRMED |
| REP-023 | Published vs live values | EPPM reports use published/summarized data; Earned Value reports use project baseline for calculations, which can differ from live areas using the project's Earned Value baseline preference. | Professional desktop reports can operate on its database/reporting context and live/project data; no automatic equivalence with EPPM published report results. | BOTH / DATA FRESHNESS AND CALCULATION DIFFERENCE — CONFIRMED |
| REP-024 | Security propagation to reporting | EPPM documentation warns a WBS-level cost privilege does not necessarily expose cost in reports if published data is available only at project level. | Professional report access is governed by Professional/EPPM global and project security; do not infer EPPM published-data visibility from desktop screen access. | EPPM REPORT SECURITY SEMANTIC — CONFIRMED |
| REP-025 | Publication service failure notification | EPPM Services can enable notification email when publication services fail. | Professional batch/report failures are handled through desktop/command-line execution behavior, not this EPPM publication alert. | EPPM PLATFORM SERVICE — CONFIRMED |
| REP-026 | Table audit configuration | EPPM Application Settings > Audit allows retention intervals and selecting tables plus Insert/Update/Delete operations. | Professional has audit-related reporting support in its guide set; exact database-context parity of every audit table and UI control must be checked. | EPPM TABLE AUDIT — CONFIRMED; full Professional parity NOT VERIFIED |
| REP-027 | Audit persistence | EPPM table audit writes changes to PAUDIT; enabling table auditing alone is insufficient to view audit data unless Publish Audit Data service is configured/enabled. | Professional Reporting Guide references table auditing, but does not establish identity of EPPM PAUDIT/publication service behavior in every DB context. | EPPM DATA PIPELINE — CONFIRMED |
| REP-028 | Audit viewing | EPPM EPS Audit panel can filter by subject area/table and date range, customize columns and print. | Professional's report tooling can produce database reports; an equivalent EPS Audit panel was not established in Professional Help. | EPPM WEB SURFACE — CONFIRMED; Professional equivalent NOT VERIFIED |
| REP-029 | Audit performance/retention | EPPM warns table auditing increases interaction with database and may affect performance; login/audit retention intervals are configurable. | Professional reporting/audit behavior is database/configuration-dependent; no exact matching retention control confirmed from the reviewed pages. | EPPM OPERATIONAL CONSTRAINT — CONFIRMED |
| REP-030 | Security data publication order | EPPM recommends running Publish Security first when services are chained with Run After Previous so security restrictions are updated before report generation. | Professional desktop reporting does not define the same EPPM global publication sequencing. | EPPM SECURITY-CRITICAL PIPELINE — CONFIRMED |
| REP-031 | Reporting permissions | EPPM Reports visibility depends on Enterprise Reports module access; publication/audit administration requires corresponding global scheduled-service/audit privileges. | Professional report edit/group/delete operations depend on Professional database or EPPM global report privileges. | BOTH / DIFFERENT PRIVILEGE MODEL — CONFIRMED |
| REP-032 | EPPM vs Professional Job Services | EPPM Project Scheduled Services and Publication Services are server/application services; Professional Job Services are explicitly Professional Only in the Professional Help TOC. | Professional Job Services automate desktop-side processes; they must not be renamed or treated as EPPM publication scheduler. | DIFFERENT SERVICES — CONFIRMED |

## 3. Operational and data-consistency conclusions

1. **Report data may be stale by design.** EPPM reports can consume published/summarized tables rather than live transactional values. A dashboard/report count must not be assumed identical to a live activity view.
2. **Security is part of publication correctness.** Oracle recommends publishing security data before other chained publication services so restrictions reach reporting tables before reports run.
3. **WBS privilege does not guarantee report visibility.** Oracle explicitly describes a case where WBS-level financial privilege is insufficient because the published financial data exists only at project level.
4. **Audit requires both capture and publication.** Selecting tables/operations and enabling auditing writes to PAUDIT; Publish Audit Data must also be configured for audit data to be available through reporting/viewing.
5. **Publication and audit are separate from Team Member histories.** PAUDIT table auditing, activity Update History and timesheet audit are different evidence sources and must not be combined into one generic audit log.
6. **Project service jobs and global publication services have different scope.** Project services can target selected project sets; global services publish enterprise/security/audit datasets.
7. **Professional has substantial report authoring.** Report Wizard/Editor, groups, batches, command-line batch execution and Project Web Site Publisher are not EPPM-exclusive.
8. **Professional and EPPM publishing are not the same.** A static HTML Project Website is not an EPPM dashboard, portlet, Reports page or Extended Schema publication pipeline.
9. **Professional on EPPM DB inherits context-specific behavior.** Global report privileges and EPPM-only defaults can apply through the Professional client, but the browser reporting and publication administration surfaces remain distinct.
10. **Do not equate Job Services with Project Scheduled Services.** Their product ownership, runtime, scope and outputs differ.

## 4. Direct Oracle Version 26 sources

### EPPM
- EPPM Reporting Guide (V26, October 2026): https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-reports/index.html
- Creating Project Scheduled Services: https://docs.oracle.com/cd/G48897_01/p6help/en/44525.htm
- Configuring Project Scheduled Services: https://docs.oracle.com/cd/G48897_01/p6help/en/44526.htm
- Publishing P6 Data: https://docs.oracle.com/cd/G48897_01/English/Admin/p6_eppm_reporting/48619.htm
- Configuring Publication Service Settings for Projects: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-reports/configuringpublicationservicesettingsforprojects-49606a.html
- Enabling Automatic Publishing of P6 Project Data: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-reports/enablingautomaticpublishingofce-product-names_p6-web__projectdata-48877a.html
- Enabling Automatic Publishing of P6 Global Data: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-reports/enablingautomaticpublishingofce-product-names_p6-web__globaldata-48684a.html
- Reports Page: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/46163.html
- Reports Tab: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/44328.html
- Schedules Tab: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/45579.html
- Configuring Audit Settings: https://docs.oracle.com/cd/G48897_01/English/Admin/p6_eppm_reporting/89307.htm
- Viewing Audit Data: https://docs.oracle.com/cd/G48897_01/p6help/nl/102814.htm
- Publishing P6 Global Data On Demand: https://docs.oracle.com/cd/G48897_01/p6help/en/48709.htm
- Running Reports On-Demand: https://docs.oracle.com/cd/G48897_01/English/Admin/p6_eppm_reporting/44322.htm

### Professional
- Professional Reporting Guide V26 TOC: https://docs.oracle.com/cd/G48902_01/English/admin/p6_pro_reporting/toc.htm
- Professional Reporting Guide — Export a report (.ERP): https://docs.oracle.com/cd/G48902_01/English/admin/p6_pro_reporting/export_a_report.htm
- Professional Reporting Guide — Report field data cells: https://docs.oracle.com/cd/G48902_01/English/admin/p6_pro_reporting/add_a_field_data_or_field_title_cell_to_a_report.htm
- Professional Reporting Guide — command-line batch reports: https://docs.oracle.com/cd/G48902_01/English/admin/p6_pro_reporting/run_a_report_batch_from_the_command_line.htm
- Professional Help TOC (Project Web Site Publisher and EPPM-only report/approval labels): https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
- Project Web Site Publisher: https://docs.oracle.com/cd/G18296_01/client_help/en_US/project_web_site_publisher.htm
- Publish reports on a Project Website: https://docs.oracle.com/cd/F74771_01/client_help/en_US/publish_reports_on_a_project_website.htm

## 5. Open evidence gaps

- Enumerate every EPPM scheduled-service type, parameter, frequency, retry, concurrency, failure and status field.
- Enumerate every publication threshold and project/global data object, including exact Extended Schema tables/columns.
- Map report templates, parameters, recipients, schedules, output formats and permissions field-by-field between EPPM and Professional.
- Compare all Professional report data sources and report fields with EPPM report definitions and Extended Schema.
- Verify every audit table/operation, retention semantics, PAUDIT schema, publish order and permission.
- Determine exact differences in Professional table auditing when connected to Professional DB versus EPPM DB.
- Review report data freshness, baseline selection and security filtering for each report family.
- Independent review of all interpretations and exact source versions.

These are explicitly NOT VERIFIED. This matrix is topic-level service/report/audit comparison, not complete report-field or Extended Schema parity.

## 6. CUBI boundary

Reference analysis only. No CUBI Project Control Workspace, scheduler, menu, schema, API, report engine, or Professional V26 implementation was changed. Any future implementation proposal requires separate approval, authorization, security design and regression evidence.
