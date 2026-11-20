# CUBI — two-environment integration contract (v1)

**Status:** draft contract, partially implemented. Every endpoint below is either `CONNECTED` (observed by test or live probe at `0014928bf`) or `UNVERIFIED` (no route exists). Nothing in between is claimed.

## 1. Shared identity and session

| Concern | Contract | State |
|---|---|---|
| Session | `POST /api/session` sets `cp_session` + `cubi_csrf`; `GET /api/session` returns `{session_id,user_id,tenant_id,roles,expires_at}`; `DELETE` clears | CONNECTED |
| Reauthentication | Sensitive global-admin writes require `confirm_password` | CONNECTED |
| CSRF | Unsafe methods require origin match and `X-CSRF-Token` | CONNECTED |
| Tenant | `tenant_id` on every session; project records carry `tenant_id` | CONNECTED |

## 2. References (all revision-guarded)

| Reference | Shape | State |
|---|---|---|
| Project | `project_id`, `tenant_id`, `name`, `revision`, `status` | CONNECTED (`/api/projects`) |
| Activity / WBS | P6 contract with project revision and `expected_revision` on writes | CONNECTED (project-scoped `/api/projects/{id}/p6/...`) |
| Document | `documents` register scoped to project | CONNECTED (Engineering); Enterprise scope UNVERIFIED |
| Risk / Issue | Project risk and issue registers | CONNECTED (Engineering); Enterprise reference UNVERIFIED |
| Task (Enterprise) | `cubi-enterprise-task.v1`, `task_id`, `revision`, cursor paging | CONNECTED (`/api/enterprise/tasks`) |
| Portfolio read model | Not implemented | UNVERIFIED |
| Job / operation | Job infrastructure exists; no Enterprise route | UNVERIFIED |
| Notification | No API | UNVERIFIED |
| Workflow / approval | No API | UNVERIFIED |

## 3. Rules

1. Enterprise must not read Engineering operational tables directly. Cross-environment data is requested through the versioned, permission-checked HTTP contracts above.
2. Every write carries the revision (or `expected_revision`) it was based on; a stale revision is rejected, never silently merged.
3. Authorization is decided on the server for every request. The Workbench enables an environment only from a successful server response, never from a role string in the client.
4. Errors use stable codes (`SESSION_REQUIRED`, `AUTHORIZATION_DENIED`, `NOT_FOUND`, `CONFLICT`, `NO_UPDATES`) with HTTP status; no client-side reinterpretation.
5. No fabricated endpoint: a page that needs an unimplemented contract renders a permission/empty state and records `UNVERIFIED`.

## 4. Observed cross-environment behaviour at `0014928bf`

- `/workbench/` reads `/api/session`, `/api/projects` and `/api/enterprise/tasks`; all three returned 200 for an authenticated seeded owner.
- Unauthenticated `/workbench/` returns `302 /login?next=/workbench/` — the gate is server-side, not client-side.
- Engineering remains the only owner of schedule, cost and EVM calculations; Enterprise pages that will show KPIs must consume the portfolio read model, which does not exist yet.
