# Command Contract

Contract version: `cubi-ai-workbench.v1`.

The command layer is deterministic. It is a typed envelope, a rule-based intent
resolver, a studio registry and a pure planner. It does not call a model
provider, embedding service or inference runtime.

## 1. Request

`POST /api/projects/<project_id>/workbench/command`

```json
{
  "command": "Show the project risks",
  "locale": "en",
  "correlation_id": "wb-3f4d5e6a7b8c9d0e1f2a"
}
```

| Field | Rule |
|---|---|
| `command` | non-empty, ≤ 2 000 characters, trimmed |
| `locale` | `^[a-z]{2,3}(-[A-Za-z0-9]{2,8})?$`; anything else is `LOCALE_INVALID` |
| `correlation_id` | `^[A-Za-z0-9][A-Za-z0-9._:-]{7,63}$`; reused for evidence, never for authorization |
| body | JSON object, ≤ 64 KiB; larger is `REQUEST_TOO_LARGE` |

Tenant, actor, roles, environment and project come from the **session and
route**, never from the body.

## 2. Envelope

`CommandEnvelope` carries: `tenant_id`, `actor_id`, `roles`, `environment`
(`engineering`), `locale`, `correlation_id`, optional `project_id`,
`source_revision` (the resolved project revision), `data_date`, and
`selected_object`. Invalid values raise `EnvelopeError` and the HTTP boundary
returns `400` with the stable code. `can_propose` is derived from the session
roles (`project_admin`, `planner`, `global_admin`, `scheduler`).

## 3. Intents

Resolution is ordered by specificity; the first matching rule wins, and the
matched text is returned as `evidence`.

| Intent | English examples | Studio |
|---|---|---|
| `decision` | approve, reject, apply, execute, promote, defer | decision-approval |
| `import` | import, stage, ingest, ورود، بارگذاری | import-staging |
| `scenario` | scenario, what-if, reschedule, recover, delay | schedule-scenario |
| `risk` | risk, risks, threat, exposure, ریسک | risk-analysis |
| `compare` | compare, versus, better | scenario |
| `analysis` | analyse, forecast, why, performance, trend, EVM | project-analysis |
| `export` | export, download, report | scenario |
| `explain` | explain, describe | project-analysis |
| `unknown` | anything else | none; one clarifying question |

Every command returns exactly one studio or `null`. A command that mentions an
approval of an import reaches `decision`, not `import`.

## 4. Plan response

```json
{
  "contract_version": "cubi-ai-workbench.v1",
  "correlation_id": "wb-…",
  "command": "Show the project risks",
  "intent": "risk",
  "studio": "risk-analysis",
  "status": "WIRED_WRITE",
  "can_open": true,
  "can_execute": true,
  "refusal": null,
  "reason": null,
  "missing_inputs": [],
  "questions": [],
  "facts": ["environment=engineering", "actor=…", "project=…", "source_revision=7"],
  "calculated": [],
  "assumptions": [],
  "recommendations": [],
  "objective": null,
  "constraints": [],
  "evidence": "risks",
  "project": { "project_id": "…", "revision": 7 },
  "resolved_at": "2026-11-21T…Z"
}
```

The four evidence blocks are always present and separated:

- **Facts** — server-known scope only (`actor`, `project`, `revision`, data date).
- **Calculation** — empty unless a canonical calculation service produced a
  value. The Workbench never computes CPM, cost or EVM in the browser.
- **Assumptions** — explicit, never silent.
- **Recommendations** — advisory; never executed automatically.

`can_open` is `false` for `BLOCKED` studios. `can_execute` is `true` only for
`LIVE_VERIFIED` and `WIRED_WRITE`. A refusal, missing input or unknown intent
produces at most one structured question with `options` and `allow_unknown`.

## 5. Errors

| Code | HTTP | Cause |
|---|---|---|
| `SESSION_INVALID` / `SESSION_REQUIRED` | 401 | no valid session |
| `PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED` | 403 | project not in this tenant or not visible to the actor |
| `COMMAND_REQUIRED` | 400 | empty or whitespace command |
| `COMMAND_TOO_LONG` | 400 | over 2 000 characters |
| `REQUEST_JSON_INVALID` | 400 | body is not a JSON object |
| `LOCALE_INVALID` | 400 | locale outside the pattern |
| `CORRELATION_ID_INVALID` / `CORRELATION_ID_REQUIRED` | 400 | bad or missing correlation |
| `REQUEST_TOO_LARGE` | 413 | body over the limit |
| `ROUTE_NOT_FOUND` | 404 | path not owned by the middleware |
| `METHOD_NOT_ALLOWED` | 405 | wrong verb |

## 6. No side effects

`POST /workbench/command` never writes a project, creates a risk, changes a
schedule or opens a studio server-side. It resolves and plans. All writes go
through their canonical endpoint with idempotency, revision and audit.
