# Workbench Architecture

## 1. Position inside the platform

The Workbench is a second **presentation document** inside the Engineering
environment, not a second application. It shares:

- the same session cookie (`cp_session`) and identity service;
- the same API composition (`build_project_lifecycle_wsgi_app`) and error codes;
- the same client transport (`FetchApiTransport`) for cookies, CSRF and timeouts;
- the same localization catalogs and locale direction rules;
- the same project, tenant and revision scope.

```
Browser
  ├─ /app                         Engineering workspace (app.html + main bundle)
  ├─ /ai-workbench                Workbench document (ai-workbench.html + own bundle)
  │    ├─ GET  /api/projects/{id}/workbench/context
  │    ├─ POST /api/projects/{id}/workbench/command
  │    ├─ GET|POST /api/projects/{id}/risks
  │    ├─ GET  /api/projects/{id}/ai/actions/proposals
  │    ├─ POST /api/projects/{id}/ai/actions/proposals/{pid}/decision
  │    ├─ POST /api/projects/{id}/ai/actions/proposals/{pid}/execute
  │    └─ GET  /api/v2/workspace/control-room/read
  └─ /cubi/*                      Enterprise Workbench (enterprise.html)
```

The Workbench bundle imports only its own `src/workbench/*` modules plus the
shared `client.ts` and `workspace-localization.ts`. It does not mount the
Engineering workspace and cannot be mounted inside it.

## 2. Server boundary

`src/construction_pm/ai_workbench/http.py` implements a WSGI middleware,
`AIWorkbenchHttpMiddleware`, that owns exactly:

- `/api/projects/<project_id>/workbench/context`
- `/api/projects/<project_id>/workbench/command`

Any other path is passed through unchanged. The middleware is installed:

- in `src/construction_pm/preview/runtime.py` (local full-stack preview);
- in `src/construction_pm/deployment/production_runtime.py` (deployment).

Because it sits inside the composed API chain, in production it runs behind the
`ProductionWebApp` origin/CSRF checks and `IdentityService`; in preview it runs
behind the preview session and cookie handling. It never creates a second
authentication path.

## 3. Command flow

```
command panel
  → POST workbench/command {command, locale, correlation_id}
  → _Scope (session, tenant, project, revision, roles)
  → CommandEnvelope (source_revision = project revision)
  → resolve_intent() → studios() → plan_command()
  → plan JSON (facts / calculated / assumptions / recommendations / questions)
  → renderCommandPlan() (four separated blocks, explicit empty text)
  → optional single studio switch when can_open is true
```

`plan_command` is pure: it performs no write and opens no surface by itself.
Only the browser switches studios, and only when the server says `can_open`.

## 4. Shell layout

The shell is rendered once, then panels are updated in place so typing in the
command textarea never loses focus.

| Region | Width | Behaviour |
|---|---|---|
| Header | full | project name/id, revision, data date, access, locale selector, back link |
| Command panel | 340 px (300 px < 1180 px) | context chips, plan region, command form, recent plans |
| Workspace | remaining, ≥ 65 % at desktop | studio tabs and the active studio |
| Inspector | 320 px (280 px < 1180 px) | selected record or command evidence, Help |
| Status bar | full | revision, data date, calculation state, selection, jobs, connected |
| Fallback notice | full | visible whenever a non-English catalog lacks a label |

At ≤ 980 px the columns stack: command panel, workspace, inspector. At ≤ 620 px
the facts grid becomes a single column. This is a responsive document, not a
desktop-only floating window.

## 5. Studio rendering rules

- `can_open === false` → `renderBlockedStudio`: status, canonical service,
  blocked reason, Help topic. No controls.
- `PARTIAL` studio → `renderPartialStudio`: status, service, reason. Only
  server-backed parts would be added; none are faked.
- Risk studio → table and 5×5 matrix built **only** from stored records.
- Analysis studio → record counts from the workspace read model and stored
  control metrics. EVM and resource/forecast sections are explicitly `PLANNED`.
- Decision studio → proposals read from the canonical AI action runtime. A
  pending proposal offers approve/reject; an approved one offers execution; a
  stale proposal shows only its warning. No proposal is created by the studio.
- A failed read renders the server error code with a retry control; it never
  falls back to sample data.

## 6. Ownership boundaries

- Do not add a CPM, leveling, cost, EVM, import, scenario or approval engine
  inside `ai_workbench/`. It resolves, plans and presents.
- Do not change `scheduling/` or the schedule composer to make a studio pass.
- Do not add a second risk store; use `risk_api` / `risk_application`.
- Do not let the client compute a score, variance, forecast or permission.
