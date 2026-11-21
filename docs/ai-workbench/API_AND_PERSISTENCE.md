# API and Persistence

## 1. Workbench endpoints

### `GET /api/projects/<project_id>/workbench/context`

Returns the pinned scope for the document.

```json
{
  "contract_version": "cubi-ai-workbench.v1",
  "environment": "engineering",
  "project": {
    "project_id": "preview-rps-01",
    "name": "Riverside Pump Station Upgrade",
    "revision": 7,
    "settings_revision": 0,
    "start_date": "2026-09-21",
    "status": "active",
    "date_system": "gregorian"
  },
  "data_date": null,
  "actor": { "user_id": "…", "roles": ["planner"] },
  "permissions": { "can_read": true, "can_propose": true },
  "studios": [
    {
      "id": "risk-analysis",
      "status": "WIRED_WRITE",
      "service": "Risk register API",
      "intent": "risk",
      "can_open": true,
      "can_execute": true,
      "blocked_reason": null,
      "help_topic": "Risk register",
      "help_status": "HELP_REFERENCE_PENDING"
    }
  ]
}
```

`data_date` is `null` when the project schedule settings do not define one.
The middleware reads it through a provider:

- preview: `repositories.settings.get(BackendScope(tenant, project, revision))`;
- production: `PostgresProjectScheduleSettingsRepository`.

`can_propose` is derived from the session roles; it is never sent by the
client.

### `POST /api/projects/<project_id>/workbench/command`

See `COMMAND_CONTRACT.md`. The response always includes `contract_version`,
`correlation_id`, `project` and `resolved_at` alongside the plan.

## 2. Studio endpoints (canonical, reused)

| Studio | Endpoint | Contract |
|---|---|---|
| Risk read | `GET /api/projects/{id}/risks` | `p6-risk-api.v1` list |
| Risk create | `POST /api/projects/{id}/risks` + `Idempotency-Key` | single risk DTO |
| Risk update | `PUT /api/projects/{id}/risks/{risk_id}` + `expected_revision` | single risk DTO |
| Risk history | `GET /api/projects/{id}/risks/{risk_id}/history` | audit events, newest revision included |
| Analysis read | `GET /api/v2/workspace/control-room/read` + `X-Tenant-Id`, `X-Project-Id`, `X-Project-Revision` | workspace rows + `control_intelligence` |
| Baselines | `GET /api/projects/{id}/p6/baselines` | `p6-baseline-api.v1` entries (`baseline.baseline_id` …) |
| Earned value | `POST /api/projects/{id}/p6/earned-value` | baseline, data date, currency; values from persisted facts |
| Proposals | `GET /api/projects/{id}/ai/actions/proposals` | `ai-action-runtime.v1`; requires project write access |
| Decision | `POST /api/projects/{id}/ai/actions/proposals/{pid}/decision` + `expected_revision` | `approved` boolean; canonical approval policy and audit |
| Execution | `POST /api/projects/{id}/ai/actions/proposals/{pid}/execute` + `expected_revision` | reauthorizes the exact tool grant, then applies atomically |
| Register exchange | `GET/POST /api/projects/{id}/exchange/*` | not surfaced as project import |

All requests use the shared `FetchApiTransport`, which sends
`X-Tenant-Id`, `X-Project-Id`, `X-Project-Revision`, the CSRF header on
mutations, and a bounded timeout.

## 3. Persistence

| Capability | Store | Notes |
|---|---|---|
| Risk | `SQLiteRiskStore` (preview) / PostgreSQL risk store (production) | revisioned, audited, idempotent |
| Project / revision | `ProjectLifecycleAPI` | the Workbench never writes it |
| Workspace read | read-only composition of schedule rows | no Workbench write path |
| Proposal / approval | canonical `AIActionRuntime` store (preview SQLite; production composition when mounted) | proposals, decisions, executions and their audit are owned by the runtime |
| Command plan | none | computed per request; never persisted as project fact |
| Studio statuses | code registry (`studios.py`) | a capability flag, not tenant data |

The Workbench has **no database table of its own**. A plan is evidence, not a
stored record. This avoids a second state authority.

## 4. Read-back and idempotency

- Every risk create sends one `Idempotency-Key` per draft. A retry with the
  same key returns the stored record; a conflict triggers `loadRisks()` and a
  fresh read instead of a duplicate.
- After a successful write the studio re-reads the full list and re-groups the
  matrix from the server rows. The row shown is the row stored.
- A risk update sends the revision that was rendered. On `409` the client
  re-reads instead of overwriting a newer record; the success notice shows the
  revision the server returned. The inspector's history view reads the audit
  events for the selected risk and never reconstructs them locally.
- The analysis studio reads with the pinned revision header. `409
  STALE_WORKSPACE_READ_SCOPE` is surfaced as the server code with a retry.
- No optimistic local mutation is displayed before the server confirms.

## 5. Limits

| Limit | Value | Enforced by |
|---|---|---|
| Workbench request body | 64 KiB | middleware |
| Command text | 2 000 characters | middleware + input |
| Risk title | 160 characters | client input; server validates presence |
| Risk ID | 40 characters | client input; server validates presence |
| Owner | 80 characters | client input; server validates presence |

Oversized or malformed bodies return a stable error code, not a partial write.

## 6. Document delivery

| Runtime | Route | Gate |
|---|---|---|
| Preview | `/ai-workbench` | session cookie; redirect to `/login?next=…` |
| Production | `/ai-workbench` | `IdentityService.resolve`; redirect to `/login?next=…` |
| Static | `ai-workbench.html`, `ai-workbench.css`, `dist/web/src/ai-workbench-entry.bundle.js` | served from the web root |

The document is `Cache-Control: no-store`. Unknown query parameters are dropped
by `_safe_next`; only `project`, `lang` and `studio` survive sign-in.
