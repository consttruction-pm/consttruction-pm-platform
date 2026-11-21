# Security and Authorization

## 1. Document gate

| Runtime | Mechanism |
|---|---|
| Preview | `_workbench_shell` requires a valid `cp_session`; otherwise `302 /login?next=<safe target>` |
| Production | `ProductionWebApp._workbench` resolves the session via `IdentityService.resolve`; otherwise `302 /login?next=<safe target>` |

The gate only decides whether the document HTML is served. Every API call is
authorized again; the gate is never the authorization boundary.

## 2. API authorization

`AIWorkbenchHttpMiddleware`:

1. reads the session ID from the `cp_session` cookie (HttpOnly);
2. calls `ProjectLifecycleAPI.open_project(session, project_id, now)`;
3. resolves the session again with `get_session` to obtain current roles;
4. builds a `_Scope` from **server** values (tenant, actor, project, revision);
5. rejects an empty role set with `ROLES_REQUIRED`.

`open_project` enforces tenant and project visibility. A project outside the
tenant or not visible to the actor raises `PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED`
and the response is `403` with that stable code. This is the IDOR guard: the
URL's project id is never trusted on its own.

The router validates the project id **after** percent-decoding: a decoded
`/`, `\`, control character, `.`/`..` segment or an id longer than 200
characters is rejected with `400 PROJECT_ID_INVALID` before any lifecycle
lookup. An encoded separator cannot add a second path segment. Every scope
field in the command body (`tenant_id`, `project_id`, `revision`, `actor_id`,
`roles`) is ignored; the envelope is built only from the resolved session and
URL project.

## 3. Request forgery

- In production, `ProductionWebApp._api` rejects a mutating API request when:
  - the `Origin`/`Referer` is not the configured public origin
    (`CSRF_ORIGIN_MISMATCH`), or
  - the signed double-submit cookie `cubi_csrf` does not match
    `X-CSRF-Token` (`CSRF_TOKEN_INVALID`).
- The Workbench client uses the shared transport, which attaches the CSRF
  header on `POST`/`PUT`/`PATCH`/`DELETE`.
- The preview runtime has no password authentication by design; it is bound to
  loopback unless `CUBI_PREVIEW_ALLOW_LAN=1` is explicitly set.
- The Workbench document sets `Cache-Control: no-store` and the platform adds
  `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: no-referrer` and a restrictive permissions policy.

## 4. Client permission display

`permissions.can_propose` is computed on the server from session roles
(`project_admin`, `planner`, `global_admin`, `scheduler`). The client only hides
or shows controls. If a read-only actor calls the risk write endpoint directly,
the risk service rejects it with its own authorization error. Hiding a control
is never the security control.

## 5. Writes

The Workbench itself performs no write in Phase 1. Studio writes use canonical
services:

- risk create: idempotency key, revisioned record, audit event, server-side
  validation, response read back by a fresh list read;
- risk update: canonical `PUT /api/projects/{id}/risks/{risk_id}` with
  `expected_revision`; a `409 RISK_REVISION_CONFLICT` triggers a fresh list read
  and the client never retries with a stale token; the audit history is read
  from `/risks/{risk_id}/history`;
- risk delete is not exposed in the studio; the canonical endpoint remains the
  only authority if it is added later;
- analysis is read-only and sends the pinned `X-Project-Revision`; a stale
  revision returns `409 STALE_WORKSPACE_READ_SCOPE`.

## 6. Audit

- Every resolved command emits a structured log record:
  `tenant`, `project`, `revision`, `actor`, `correlation_id`, `intent`,
  `studio`, `status`, `can_open`, `can_execute`.
- Denials emit `workbench_denied reason=<code> path=<api path>`; the command
  text is **not** logged.
- Domain writes keep their own audit trail in the canonical service (risk
  history endpoint `/api/projects/{id}/risks/{risk_id}/history`).
- There is no Workbench-specific audit table; adding one would duplicate the
  domain audit authority.

## 7. Data exposure

- Responses contain server-resolved scope and studio metadata only.
- No raw SQL, repository internals, secrets or model/provider identifiers are
  returned.
- Error codes are stable constants; unexpected exceptions are not reflected.
- The public preview health endpoint stays minimal (`status`, `production`,
  `demo_data`, `public_demo`, `read_only`).

## 8. Localization and direction

The document sets `lang` and `dir` from the resolved locale (`fa`, `ar` → RTL).
Direction affects layout only; it never changes authorization or data.
