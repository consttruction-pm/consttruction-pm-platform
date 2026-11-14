# CUBI Enterprise Task API v1

**Status:** Implemented in the stacked Task API branch; exact-head CI and review required  
**Route root:** `/api/enterprise/tasks`

## Authentication and trust boundary

- Every route requires the existing authenticated `cp_session` session.
- State-changing requests pass through `ProductionWebApp` origin and CSRF verification before reaching the task middleware.
- Tenant and actor IDs are derived from the authenticated session. Client-supplied identity fields are ignored and never establish authority.
- Project task reads require `PROJECT_READ`; creates and updates require `PROJECT_WRITE`.
- Personal tasks are visible only to their authenticated creator/owner.
- Team assignment and Engineering object references are rejected until organization membership and cross-environment reference authorization are available.

## Routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/enterprise/tasks` | List the caller's personal tasks |
| GET | `/api/enterprise/tasks?project_id={id}` | List tasks in an authorized project |
| POST | `/api/enterprise/tasks` | Create a personal or project task; requires `Idempotency-Key` |
| GET | `/api/enterprise/tasks/{task_id}` | Read one authorized task |
| PATCH | `/api/enterprise/tasks/{task_id}` | Revision-checked update |

## Request contract

POST and PATCH bodies must include `contract_version: "cubi-enterprise-task.v1"`.

POST accepts `title`, optional `description`, `priority`, `project_id`, `assigned_user_id`, `due_at` and `dependency_ids`. Server-owned fields (tenant, creator, timestamps, task ID and revision) are derived by the service.

PATCH requires `expected_revision` and accepts `title`, `description`, `priority`, `status`, `assigned_user_id`, `due_at` and `dependency_ids`. Project, tenant, creator and creation time are immutable. Completion actor/time are assigned by the server.

## Pagination

The list response returns `next_cursor` when another page exists. Cursor fields are the composite `before_updated_at` and `before_task_id`; a null timestamp cursor is supported for the `NULLS LAST` partition.

## Error behavior

- 401: missing or invalid session.
- 403: project permission or assignment denied.
- 404: task missing or outside the caller's personal scope.
- 409: revision conflict or idempotency-key reuse.
- 400: invalid contract, unsupported fields, dependency scope or validation failure.

## Current limitations

- Team assignment is intentionally disabled until Organization & Access membership persistence is implemented and tested.
- Cross-environment Activity/WBS/Document/Risk references are intentionally disabled until an authorized, revision-pinned Engineering reference resolver exists.
- No UI is included in this backend vertical slice.
