# CUBI Enterprise — P6 EPPM V26 per-page traceability

**Help baseline:** P6 EPPM V26 (G48897-01, May 2026)
**Rows:** 16 · **Generated from:** `docs/traceability/enterprise-v26.json`

Every CUBI Enterprise page is mapped to its P6 EPPM V26 Help topic and to an owning canonical module. The EPPM Help set is HTML-only; it has no page-numbered PDF baseline. This document is internal traceability: no Oracle, Primavera or P6 name may appear in customer-facing UI.

## Status legend

- `PUBLISHED` — منتشرشده / Published
- `IMPLEMENTED` — پیاده‌سازی‌شده / Implemented
- `PARTIAL` — جزئی / Partial
- `PLANNED` — برنامه‌ریزی‌شده / Planned
- `CUBI_OWNED` — مخصوص CUBI / CUBI-owned
- `LEGAL` — حقوقی / Legal

## Per-page traceability

| ID | Page | Surface | Help topic | PDF | CUBI evidence | Status |
|---|---|---|---|---|---|---|
| ENT-HOME | `/environments/` | Environment selection and Enterprise entry | [Working with P6](https://docs.oracle.com/cd/G48897_01/p6help/en/6660.htm) | — | `apps/web/src/enterprise-task-center.ts` | PARTIAL |
| ENT-DASHBOARDS | `/enterprise/` | Dashboards | [About Dashboards](https://docs.oracle.com/cd/G48897_01/p6help/en/6608.htm) | — | `src/construction_pm/enterprise_dashboard_application.py` | PARTIAL |
| ENT-PORTFOLIO | `/enterprise/portfolio/` | Portfolio and executive center | [About Portfolio Views](https://docs.oracle.com/cd/G48897_01/p6help/en/14087.htm) | — | `src/construction_pm/enterprise_dashboard.py` | PARTIAL |
| ENT-PROJECTS | `/enterprise/projects/` | Project context and EPS | [About the Enterprise Project Structure (EPS)](https://docs.oracle.com/cd/G48897_01/p6help/en/6621.htm) | — | `src/construction_pm/enterprise_task_application.py` | PARTIAL |
| ENT-TEAM-TASKS | `/enterprise/tasks/` | Team and task center | [About P6 Team Member Status Updates](https://docs.oracle.com/cd/G48897_01/p6help/en/50904.htm) | — | `apps/web/src/enterprise-task-center.test.ts` | IMPLEMENTED |
| ENT-FEEDBACK-APPROVAL | `/enterprise/approvals/` | Feedback and approval center | [Reviewing Team Member Status Updates](https://docs.oracle.com/cd/G48897_01/p6help/en/51331.htm) | — | `src/construction_pm/enterprise_task.py` | PLANNED |
| ENT-OPERATIONS | `/enterprise/operations/` | Operations and job center | [About Project Scheduled Services](https://docs.oracle.com/cd/G48897_01/p6help/en/46217.htm) | — | `src/construction_pm/enterprise_dashboard_repository.py` | PARTIAL |
| ENT-WORKFLOW | `/enterprise/workflows/` | Workflow studio | [Configuring P6 Team Member Status Update Reviews](https://docs.oracle.com/cd/G48897_01/p6help/en/50915.htm) | — | `src/construction_pm/enterprise_organization_access.py` | PLANNED |
| ENT-ORG-ACCESS | `/enterprise/organization/` | Organization and access center | [About Users](https://docs.oracle.com/cd/G48897_01/p6help/en/43794.htm) | — | `src/construction_pm/enterprise_identity.py` | PARTIAL |
| ENT-PORTAL | `/enterprise/portal/` | Project portal | [Publishing P6 Data](https://docs.oracle.com/cd/G48897_01/p6help/en/48619.htm) | — | `src/construction_pm/enterprise_organization_access_repository.py` | PLANNED |
| ENT-INTEGRATION | `/enterprise/integrations/` | Integration hub | [About Importing and Exporting Data](https://docs.oracle.com/cd/G48897_01/p6help/en/6604.htm) | — | `apps/web/src/p6-interchange-api.ts` | PARTIAL |
| ENT-RESOURCES | `/enterprise/resources/` | Resource capacity | [Analyzing Role Allocation (Capacity Planning)](https://docs.oracle.com/cd/G48897_01/p6help/en/7855.htm) | — | `src/construction_pm/enterprise_dashboard_application.py` | PARTIAL |
| ENT-REPORTS | `/enterprise/reports/` | Enterprise reporting | [Configuring Report Settings](https://docs.oracle.com/cd/G48897_01/p6help/en/78291.htm) | — | `src/construction_pm/enterprise_dashboard_application.py` | PARTIAL |
| ENT-ADMIN | `/enterprise/admin/` | Enterprise administration | [About Administration](https://docs.oracle.com/cd/G48897_01/p6help/en/6590.htm) | — | `src/construction_pm/enterprise_identity.py` | PARTIAL |
| ENT-DOCUMENTS | `/enterprise/documents/` | Documents and reviews | [About Documents](https://docs.oracle.com/cd/G48897_01/p6help/en/6620.htm) | — | `src/construction_pm/enterprise_organization_access_repository.py` | PLANNED |
| ENT-RISKS-ISSUES | `/enterprise/risks/` | Risks and issues | [About Risks](https://docs.oracle.com/cd/G48897_01/p6help/en/6628.htm) | — | `src/construction_pm/enterprise_task.py` | PLANNED |

## Behaviour notes

- **ENT-HOME** — Signed-in environment choice; Enterprise never reuses Engineering calculations.
- **ENT-DASHBOARDS** — Role-based dashboards and configurable portlets.
- **ENT-PORTFOLIO** — Authorized project list, health and KPIs.
- **ENT-PROJECTS** — Project selection constrained by read authorization.
- **ENT-TEAM-TASKS** — Personal/project tasks with status, priority and due date.
- **ENT-FEEDBACK-APPROVAL** — Proposed vs approved records with decision history.
- **ENT-OPERATIONS** — Job status, failures and controlled retry.
- **ENT-WORKFLOW** — Configurable stages, transitions and deadlines.
- **ENT-ORG-ACCESS** — Members, roles, teams and server-side authorization.
- **ENT-PORTAL** — Approved status and documents with revocable access.
- **ENT-INTEGRATION** — Versioned APIs, webhooks and controlled import/export.
- **ENT-RESOURCES** — Role and resource capacity read models.
- **ENT-REPORTS** — Organization-level performance reporting.
- **ENT-ADMIN** — Security profiles, preferences and audit.
- **ENT-DOCUMENTS** — Document repository and review participation.
- **ENT-RISKS-ISSUES** — Authorized risk/issue references without duplicating Engineering data.
