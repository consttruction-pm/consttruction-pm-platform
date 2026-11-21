# CUBI Enterprise — V26 entry routing and operational evidence

Date: 2026-11-21. Branch: `feat/cubi-entry-enterprise-operational` (PR #2089).
Baseline re-verified: `main` at `b2b20793c` (PR #2088 merge) after PR #2087
`6ea2e4215`.

This record covers the **entry path** and the **operational controls** of the
Enterprise Workbench. It does not claim full P6 EPPM V26 parity; the page-level
parity matrices remain the authority for scope.

## 1. Canonical entry path

```
/ (public site)
  → /login                     canonical sign-in (preview alias: /preview/login)
  → /workbench/                POST-login default destination
  → /workbench/#environments   environment selection (Engineering | Enterprise)
      ├─ /app?view=live        Engineering (only when the server authorizes it)
      └─ /cubi/enterprise/dashboard
```

Rules enforced by the server and the clients:

| Rule | Implementation | Evidence |
| --- | --- | --- |
| Successful login lands on `/workbench/` | `_safe_next` fallback is `/workbench/`; role and personal sign-in redirect there | 5/5 personas landed on `/workbench/` |
| A valid requested deep link is preserved | `/login?next=/cubi/enterprise/dashboard` and `/app?project=…&view=live` survive; `_safe_next` canonicalizes `/app?project=…` to `&view=live` | Unit and HTTP tests |
| An invalid or hostile `next` never becomes Engineering | non-local, protocol-relative, backslash, control-character and fragment values fall back to `/workbench/` | `_safe_next` matrix tests |
| `/enterprise` is retired as an Engineering route | answers `308` to `/cubi/` and never serves `app.html` | HTTP tests and probe |
| Enterprise is gated by Enterprise roles | `/cubi/enterprise/*` requires `enterprise_admin`/`enterprise_user`/`enterprise_viewer` (or `global_admin`); other roles get `303 /workbench/` | Planner, Project administrator, Viewer and New account all redirected |
| Enterprise entitlement is independent of Engineering projects | the workbench probe reads the Enterprise tier, not project membership | `probeEnterprise` 2xx / 403 / other states |
| Transient probe failure is not a permanent denial | 5xx/network → `server_unknown`, card shows retry and the explanation; only 403 maps to `no_server_grant` | `personal-workbench.test.ts` |
| Sign-out ends the session and returns to sign-in | `DELETE /api/session` revokes the preview session; `/preview/logout` and `/logout` redirect to `/login` | Session 401 after sign-out; re-login succeeds |

Preview note: port 4180 was occupied by an unrelated stale
`/tmp/repo/apps/web/e2e/production-login-server.py` process, so this evidence
run used the same shared preview on port **4191** with
`/tmp/preview-2090.sqlite3`. No parallel preview implementation was added.

## 2. Persona matrix (real browser run)

Every persona signed in from `/login?next=%2Fworkbench%2F`:

| Persona | Session roles | Landing | Enterprise direct URL | Sign-out | Re-login |
| --- | --- | --- | --- | --- | --- |
| Enterprise administrator | `enterprise_admin`, `project_admin` | `/workbench/` | `200` `/cubi/enterprise/dashboard/` | `/login`, session 401 | `/workbench/` |
| Project administrator | `project_admin` | `/workbench/` | `303` → `/workbench/` | `/login`, session 401 | `/workbench/` |
| Planner | `planner` | `/workbench/` | `303` → `/workbench/` | `/login`, session 401 | `/workbench/` |
| Viewer | `viewer` | `/workbench/` | `303` → `/workbench/` | `/login`, session 401 | `/workbench/` |
| New account (no projects) | `project_admin` | `/workbench/` | `303` → `/workbench/` | `/login`, session 401 | `/workbench/` |

The Personal Workbench now carries a sign-out control in all ten locales; the
Enterprise shell sign-out returns to `/login` as well.

## 3. Route and refresh matrix

All 20 data routes served under `/cubi/enterprise/<segment>/` opened by direct
URL and kept the same `h1` after a hard refresh:

`dashboard`, `portfolio`, `projects`, `access`, `tasks`, `workflows`,
`approvals`, `resources`, `reports`, `knowledge`, `risks`, `documents`, `eps`,
`member-activities`, `timesheets`, `notifications`, `settings`, `forms`,
`audit`, `directory`.

Browser back/forward restored the previously visited Portfolio and Approvals
pages with the correct `h1`.

## 4. Operational controls

- **Registers (risks, documents, EPS, timesheets, notifications, settings,
  forms, directory)**: toolbar with search (server `q`, 250 ms debounce),
  status filter, project filter, include-deleted, refresh, CSV export and
  print; sortable headers with `aria-sort`; multi-select; detail panel; row
  context menu (Open details, Edit, Delete/Restore, Refresh); keyboard
  `ArrowUp/ArrowDown`, `Enter`, `Space`, `Shift+F10`/ContextMenu; revision
  conflicts surfaced from the server; soft delete and restore.
- **Portfolio and Projects**: search, status filter and locale-aware sort over
  the `/api/projects` register; selected project portal.
- **Dashboard**: dashboard selector, project scope, portlet text filter,
  designer add/remove/reorder/resize/visibility; layout create/update on
  `/api/enterprise/dashboards`; server-sync badge survived reload.
- **Tasks**: project/status/priority/search filters, create with
  `Idempotency-Key`, revision-checked status update.
- **Approvals**: New approval creates a real queue item; Review fills the exact
  revision; decision accepted by the server; stale/duplicate 409 messages.
- **Workflow studio**: draft create and publish with server graph validation.
- **Member activities**: first authorized project auto-selected, activities read
  from the Engineering route, search over returned rows, read-only by design.
- **Top bar**: global search over the routes this build serves and the projects
  the session can read (`Ctrl/Cmd+K`), notification indicator fed by
  `/api/enterprise/notifications` (unread count only when the server says
  `unread`; failures go to the tooltip, never to a fake zero), language
  selector, Help, Workbench link and Engineering switch when authorized.

## 5. Localization and layout

| Check | Result |
| --- | --- |
| Persian (`fa`) | `dir=rtl`, `lang=fa`, localized `h1` `داشبورد و پورتلت‌های سازمانی` |
| English (`en`) | `dir=ltr`, localized `h1` |
| 1440×1000 | no horizontal overflow |
| 1366×768 | no horizontal overflow (fa and en) |
| 1280×720 | no horizontal overflow (fa and en) |

Ten locales are present in `i18n.ts` and the Personal Workbench. English is the
fallback; a locale is not reported as fully translated unless its dictionary is
complete.

## 6. API behaviour used by this increment

- `GET /api/enterprise/{kind}` with `q`, `status`, `project_id`,
  `include_deleted`, `limit`.
- `POST /api/enterprise/{kind}` (Idempotency-Key), `PATCH`/`DELETE` with
  `expected_revision`, `POST …/{id}/restore`.
- `/api/enterprise/tasks` (v1), `/api/enterprise/approvals/{id}/decisions`,
  `/api/enterprise/workflows/{id}/publish`, `/api/enterprise/dashboards`.
- `GET /api/session`, `DELETE /api/session`, `GET /api/projects`.
- Engineering read models (`/api/enterprise/portlets/*`,
  `/api/enterprise/portfolio/*`, `/api/enterprise/evm/capability`) answer
  `503 ENGINEERING_SOURCE_NOT_CONNECTED`; the UI reports that verbatim and
  substitutes nothing.

## 7. Known limits (not claimed complete)

- The production composition still mounts only `EnterpriseTaskHttpMiddleware`;
  `/api/enterprise/{kind}` for dashboards, risks, documents, etc. is mounted in
  the preview runtime, not in the production runtime (PR #2068 is open).
- Dashboard portlet values that belong to Engineering remain unavailable until
  the official read models are connected; no number is derived in Enterprise.
- Notification delivery to external channels is a record, not a proven send.
- Document binary storage and invitation acceptance are not implemented.
- Workflow publish validates its own graph; it does not schedule or approve
  Engineering work.
- Screenshots in `artifacts/enterprise-preview/v26/` are from the shared
  preview on port 4191; the committed build artefacts in the repository are the
  source of those pages.
