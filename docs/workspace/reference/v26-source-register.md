# Version 26 Documentation Source Register for CUBI

- Epic: [#1722 - Complete CUBI window build catalog and Version 26 requirements traceability](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1722)
- Baseline repository commit: 49201ddfbec83550e7147ce2fa3cc961e39eef55
- Purpose: use the official Version 26 documentation set as a controlled design and behavior reference for the single CUBI Visual Workspace.
- This file records source identity and applicability. It does not copy Oracle documentation or grant rights to redistribute it.

## 1. Authoritative official documents

| Priority | Official source | Document ID / date | Length | Use in CUBI |
|---|---|---|---:|---|
| Primary | [P6 Professional Help - PDF](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-help/p6-professional-help.pdf) | G57535-02 / 9 Oct 2026 | 815 PDF pages | Primary inventory for workspace, menus, command enablement, toolbars, windows, dialogs, operations, shortcut menus, layouts, tables, Gantt, networks, tracking, profiles, reports, global change and administration entry points. |
| Supporting | [P6 Professional User Guide - PDF](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/p6-professional-user-guide.pdf) | G57529-01 / Oct 2026 | 266 PDF pages | End-to-end project-management workflows, examples, project setup, WBS, activities, resources, progress, baselines, scheduling, grouping/filtering and layout usage. |
| Supporting | [P6 Professional Administration Guide - PDF](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-admin/p6-professional-administration-guide.pdf) | G57530-01 / 9 Oct 2026 | 84 PDF pages | Administrative preferences, limits/configuration, dictionaries/categories, currencies, financial periods, users, security profiles and resource security. |
| Supporting | [P6 Professional Reporting Guide - PDF](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-reports/p6-professional-reporting-guide.pdf) | G57532-01 / Oct 2026 | 47 PDF pages | Report authoring, data selection, layout, running and distribution behavior. |
| Supporting | [P6 Visualizer Help - PDF](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-viz-help/p6-visualizer-help.pdf) | G57536-01 / Oct 2026 | 77 PDF pages | Advanced Gantt, time-scaled logic diagrams and schedule comparisons. |

Official release index: [Version 26 - All Guides](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/books.html).

## 2. Source authority and precedence

1. Use the current Version 26 English Help as the primary source for window, menu, toolbar, dialog, command and interaction inventory.
2. Use the Version 26 User Guide to clarify the full user workflow and examples; it does not replace command-level Help coverage.
3. Use Administration, Reporting and Visualizer guides for their distinct areas. Do not assume that a capability described in a companion product is automatically part of the core Activities window.
4. When a Help feature is marked Professional-only, EPPM-only, database-only, role-dependent or connection-dependent, record that applicability. Do not silently treat it as universally available.
5. For calculation semantics, the relevant Version 26 Help/User Guide sections must be cross-checked against current Version 26 API/schema documentation and CUBI's own approved shared-core contract. A UI guide is not sufficient evidence of numeric calculation parity.
6. If official documents disagree, record both references, identify release/date, and resolve the conflict before implementation. Never use screenshots from older releases as proof of Version 26 behavior.

## 3. Help chapter map and implementation use

The primary Help contains a 24-page contents section and the following functional groups. Printed page numbers below refer to the page numbers printed within the named chapter, not the PDF viewer page counter.

| Help area | Principal coverage | CUBI work packages |
|---|---|---|
| Welcome / Getting Started | Workspace basics, symbols, main windows, hint help, status/layout bars, window details, shortcut menus, multi-selection, hot keys, menus/toolbars | Global shell, window lifecycle, command registry, context menus, keyboard behavior |
| Working with Toolbars and Menus | File, Edit, View, Project, Enterprise, Tools, Admin and Help menus; command descriptions, enabled windows, shortcut keys, matching toolbar icons; toolbar families and customization | Menu map, toolbar groups, command availability and icon inventory |
| Structuring Projects | EPS, WBS, OBS, project/resource/activity codes, code colors, UDFs, calendars, resources, roles and resource curves | Projects, Business Domains, WBS, responsibility structure, dictionaries, calendars, resources and roles |
| Working with EPS | Project identity, dates, defaults, status, leveling priority, activity defaults and critical threshold | Project Details and project defaults |
| Developing Projects | Activity creation/types/dates, activity table/network, relationships, resource/role assignment, curves, costs/expenses, steps, notebooks and global change | Activities, Gantt, Network, Activity Details, assignments, expenses and editing tools |
| Managing Projects | Budgeting, baselines, updating/progress, actuals, EVM, schedule, float/critical paths, constraints, resource leveling, issues, thresholds, risks and documents | Schedule, Progress, Baselines, Cost, Resources, Issues, Risks, Thresholds and Documents |
| Customizing Activity Layouts | Layout lifecycle, Activity Details customization, Activity Table columns/fonts/colors/row height, Gantt bars/timescale/labels/legend/relationships/data date, network and trace logic, usage charts and spreadsheets | Full per-window layout system and every Activities top/bottom view |
| Tracking Projects | Tracking layouts, sharing/import/export, top/bottom pane visibility, columns, filtering, Gantt charts, profiles and spreadsheets | Tracking and monitoring windows |
| Grouping, Filtering and Summarizing | Grouping by field/hierarchy/WBS path, sort levels, grouping band presentation, expand/collapse, filters, summaries and totals | Reusable filter/group/sort engine shared by every applicable window |
| Publishing Project Web Sites | Project site setup, content selection and publication | Map only where CUBI has an approved publishing/export requirement |
| Tools | External tools, reporting, visualizer, timesheets/status updates where applicable, summary services, jobs, global change and period performance | Tools menu and dedicated tool windows |
| Reference / Security / Integration | Multiple projects, remote projects, offline/online behavior, security and product-specific integrations | Import/export, offline, access control and interoperability boundaries |

## 4. Command catalog evidence

The Help explicitly states that its menu reference tables describe each command's function, the active windows in which it is enabled and the toolbar containing its corresponding icon. It identifies File, Edit, View, Project, Enterprise, Tools, Admin (where applicable) and Help menus.

The CUBI mapping must preserve the useful command capability while using CUBI product vocabulary:

| Reference command family | CUBI menu family | Required treatment |
|---|---|---|
| File | Workspace | Project lifecycle, open/close, import/export, print and recovery actions that are supported by CUBI services |
| Edit | Edit | Selection-aware add/edit/delete/copy/paste, assignments, relationship commands, find and bulk editing |
| View | View | Layouts, top/bottom panes, columns, filters, grouping/sorting, timescale, bars, zoom, expand/collapse, toolbars and tabs |
| Project | Project | Activities, WBS, assignments, baselines, documents, expenses, issues, risks and project-level views |
| Enterprise | Organization | Business Domains, portfolios, resources, roles, calendars, codes, UDFs, cost dictionaries and organization-level records |
| Tools | Tools | Schedule, resource leveling, reports, global change, period performance, validation and CUBI tools |
| Admin | Administration | Users, access profiles, permissions, system defaults, dictionaries, categories and audit/recovery controls |
| Help | Help | CUBI help, context help, keyboard shortcuts, documentation, release notes and About CUBI |

Do not expose vendor/product names, external logos, source URLs or trademarked labels in customer-facing CUBI menus, help or branding. Source citations stay inside engineering documentation.

## 5. Copyright and use boundary

The official PDFs contain restrictive copyright/licensing notices. This repository must store original CUBI requirements, paraphrased behavior descriptions, source document identifiers, links and page/section references only. Do not commit the PDF, extract and republish complete Help pages, reproduce proprietary screenshots, or translate substantial passages verbatim. Use screenshots only when the project has a lawful right to use them and they are clearly marked as internal reference evidence. CUBI's UI, labels, visual identity, icons and help content must be its own work.

## 6. Evidence record protocol

For each requirement in the build catalog, record:
- Source document ID and date.
- Chapter, section and printed page or page range.
- CUBI window key, view/layout and screen region.
- Component/control/dialog/command identifier.
- Expected appearance and behavior written in original CUBI language.
- Data source, service contract and permission condition.
- Empty, loading, error, disabled, dirty and conflict states.
- Unit/component/browser test identifiers.
- Screenshot/video evidence identifier and tested commit SHA.
- Status and reviewer decision.

No row may be marked complete from a title, icon, menu label, visual mock or passing isolated unit test alone.
