# CUBI Enterprise — page, field and Help matrix

**Generated from:** `docs/traceability/enterprise-v26.json` and `scripts/generate_master_page_matrices.py`
**Rows:** 16 · **Machine-readable twin:** `ENTERPRISE_PAGE_FIELD_HELP_MATRIX.json`

## Page and Help matrix

| Page ID | Page | Surface | Help topic | Direct HTML URL | Status | Evidence |
|---|---|---|---|---|---|---|
| ENT-HOME | /environments/ | Environment selection and Enterprise entry | Working with P6 | [Working with P6](https://docs.oracle.com/cd/G48897_01/p6help/en/6660.htm) | WIRED_READ | apps/web/src/enterprise-task-center.ts |
| ENT-DASHBOARDS | /enterprise/ | Dashboards | About Dashboards | [About Dashboards](https://docs.oracle.com/cd/G48897_01/p6help/en/6608.htm) | MISSING | src/construction_pm/enterprise_dashboard_application.py |
| ENT-PORTFOLIO | /enterprise/portfolio/ | Portfolio and executive center | About Portfolio Views | [About Portfolio Views](https://docs.oracle.com/cd/G48897_01/p6help/en/14087.htm) | MISSING | src/construction_pm/enterprise_dashboard.py |
| ENT-PROJECTS | /enterprise/projects/ | Project context and EPS | About the Enterprise Project Structure (EPS) | [About the Enterprise Project Structure (EPS)](https://docs.oracle.com/cd/G48897_01/p6help/en/6621.htm) | MISSING | src/construction_pm/enterprise_task_application.py |
| ENT-TEAM-TASKS | /enterprise/tasks/ | Team and task center | About P6 Team Member Status Updates | [About P6 Team Member Status Updates](https://docs.oracle.com/cd/G48897_01/p6help/en/50904.htm) | WIRED_WRITE | apps/web/src/enterprise-task-center.test.ts |
| ENT-FEEDBACK-APPROVAL | /enterprise/approvals/ | Feedback and approval center | Reviewing Team Member Status Updates | [Reviewing Team Member Status Updates](https://docs.oracle.com/cd/G48897_01/p6help/en/51331.htm) | MISSING | src/construction_pm/enterprise_task.py |
| ENT-OPERATIONS | /enterprise/operations/ | Operations and job center | About Project Scheduled Services | [About Project Scheduled Services](https://docs.oracle.com/cd/G48897_01/p6help/en/46217.htm) | MISSING | src/construction_pm/enterprise_dashboard_repository.py |
| ENT-WORKFLOW | /enterprise/workflows/ | Workflow studio | Configuring P6 Team Member Status Update Reviews | [Configuring P6 Team Member Status Update Reviews](https://docs.oracle.com/cd/G48897_01/p6help/en/50915.htm) | MISSING | src/construction_pm/enterprise_organization_access.py |
| ENT-ORG-ACCESS | /enterprise/organization/ | Organization and access center | About Users | [About Users](https://docs.oracle.com/cd/G48897_01/p6help/en/43794.htm) | MISSING | src/construction_pm/enterprise_identity.py |
| ENT-PORTAL | /enterprise/portal/ | Project portal | Publishing P6 Data | [Publishing P6 Data](https://docs.oracle.com/cd/G48897_01/p6help/en/48619.htm) | MISSING | src/construction_pm/enterprise_organization_access_repository.py |
| ENT-INTEGRATION | /enterprise/integrations/ | Integration hub | About Importing and Exporting Data | [About Importing and Exporting Data](https://docs.oracle.com/cd/G48897_01/p6help/en/6604.htm) | MISSING | apps/web/src/p6-interchange-api.ts |
| ENT-RESOURCES | /enterprise/resources/ | Resource capacity | Analyzing Role Allocation (Capacity Planning) | [Analyzing Role Allocation (Capacity Planning)](https://docs.oracle.com/cd/G48897_01/p6help/en/7855.htm) | MISSING | src/construction_pm/enterprise_dashboard_application.py |
| ENT-REPORTS | /enterprise/reports/ | Enterprise reporting | Configuring Report Settings | [Configuring Report Settings](https://docs.oracle.com/cd/G48897_01/p6help/en/78291.htm) | MISSING | src/construction_pm/enterprise_dashboard_application.py |
| ENT-ADMIN | /enterprise/admin/ | Enterprise administration | About Administration | [About Administration](https://docs.oracle.com/cd/G48897_01/p6help/en/6590.htm) | MISSING | src/construction_pm/enterprise_identity.py |
| ENT-DOCUMENTS | /enterprise/documents/ | Documents and reviews | About Documents | [About Documents](https://docs.oracle.com/cd/G48897_01/p6help/en/6620.htm) | MISSING | src/construction_pm/enterprise_organization_access_repository.py |
| ENT-RISKS-ISSUES | /enterprise/risks/ | Risks and issues | About Risks | [About Risks](https://docs.oracle.com/cd/G48897_01/p6help/en/6628.htm) | MISSING | src/construction_pm/enterprise_task.py |

## Field-level coverage

Only `/enterprise/` (Team & Task Center) currently has a wired form contract: title, description, project scope, priority, due date, status transitions and revision guard, all exercised by `apps/web/src/enterprise-task-center.test.ts` and the enterprise task HTTP tests. For the other fifteen surfaces the required field lists are enumerated in the product order but **not yet audited against code**; each is recorded as `NOT_AUDITED` rather than filled with placeholder rows. Enterprise documents, portal, workflow, approvals and risk registers have no implementation to extract fields from at this SHA.
