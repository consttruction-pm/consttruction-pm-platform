# Production deployment — CUBI Workspace on Vercel

This document describes the real production path, not the local preview:

```
Browser
  → Vercel domain (cubi-web-preview)
  → Vercel Python function (api/index.py, api/shell.py in the project root)
  → construction_pm.deployment.ProductionRuntime
  → PostgreSQL (identity, sessions, projects, workspace data)
```

Render is not part of this path and is not a fallback. The preview server,
preview personas and demo data are never used by the production composition.

## What the deployment serves

| Path | Handler | Behaviour |
| --- | --- | --- |
| `/` | static | landing page from `public/` |
| `/login` | `login.html` | anonymous sign-in page (en/fa, RTL) |
| `/app` | `api/shell.py` | session-gated workspace; `302 /login?next=…` without a session |
| `/api/session` | `api/index.py` | `POST` login, `DELETE` logout, `GET` current session |
| `/api/projects`, `/api/projects/{id}`, `/api/projects/{id}/open` | `api/index.py` | authorized project lifecycle |
| `/api/v2/workspace/control-room/read` | `api/index.py` | canonical workspace read (v2 contract) |
| `/api/projects/{id}/p6/fields/…`, `/api/projects/{id}/p6/layouts/…` | `api/index.py` | field registry and layout presentation |
| `/api/health/live`, `/api/health/ready` | `api/index.py` | liveness vs. database readiness |

Everything else returns 404. Unsafe methods require both a same-origin
`Origin`/`Referer` and `X-CSRF-Token` derived from the caller's own session.

## Required environment variables

Set on the Vercel project (Production, and Preview only if a separate database
is used). Values are never committed.

| Name | Required | Purpose |
| --- | --- | --- |
| `CONSTRUCTION_PM_DATABASE_URL` | yes | PostgreSQL DSN (`postgresql://…`). Use a pooled/serverless endpoint if the provider offers one; the runtime also keeps a small in-instance pool. |
| `CONSTRUCTION_PM_SESSION_SECRET` | yes | ≥ 32 characters. Used for CSRF derivation and pseudonymous IP hashing. Rotating it invalidates CSRF tokens and IP hashes, not sessions. |
| `CONSTRUCTION_PM_PUBLIC_ORIGIN` | yes | Exact HTTPS origin, e.g. `https://cubi-web-preview.vercel.app`. Login/logout/mutations are rejected when `Origin` does not match. |
| `CONSTRUCTION_PM_DB_POOL_SIZE` | no | Idle connections per warm instance (1–8, default 2). |
| `CONSTRUCTION_PM_DB_CONNECT_TIMEOUT` | no | Connect timeout seconds (2–30, default 10). |
| `CUBI_WEB_ROOT` | no | Override for the built Web root; by default `public/` next to the function bundle. |
| `CONSTRUCTION_PM_INSECURE_COOKIES` | never in production | Disables the `Secure` cookie flag. Only the loopback E2E harness avoids it by constructing settings directly. |

Secrets are read at request time from the environment; nothing is written to
logs, the repository or response bodies. Database errors are never returned to
the browser (generic `500 INTERNAL_ERROR`).

## Vercel project configuration

The deployed project is `cubi-web-preview` (`prj_E1psnPyPs9doA82oZ4OcmiIqarle`).
Vercel reports its **root directory as `apps/web`**, so the project only reads
configuration and functions inside that directory. Two equivalent entrypoint
layouts exist in the repository:

| Layout | Used when | Files |
| --- | --- | --- |
| Project root = repository root | a project is created with no root directory | `vercel.json`, `api/index.py`, `api/shell.py`; build `scripts/vercel_build.sh`, output `public/` |
| Project root = `apps/web` (the live project) | Vercel project rooted at `apps/web` | `apps/web/vercel.json`, `apps/web/api/index.py`, `apps/web/api/shell.py`; build `apps/web/scripts/vercel-project-build.mjs`, output `apps/web/vercel-site/` |

In the live layout the build:

1. runs `npm run build` for the TypeScript client;
2. assembles the same public site the Pages workflow validates
   (`scripts/assemble-pages-site.mjs`), with `SITE_BASE_URL` defaulting to
   `https://$VERCEL_PROJECT_PRODUCTION_URL`, and deliberately **without**
   `CUBI_WORKSPACE_URL`, so `/app` is never redirected to Render;
3. removes the static `app/` mirror so `/app` always reaches the gate;
4. copies the login document into the static output;
5. stages an unmodified copy of the repository `src/` into
   `apps/web/vercel-runtime/src`, which the functions import (the project root
   cannot see `../../src` at function packaging time).

`includeFiles` is a single glob (`vercel-runtime/**`): the Vercel schema types
it as a string, and an array makes the whole configuration invalid.

Python dependencies come from `apps/web/requirements.txt` (`psycopg[binary]`).
Per-function `memory`/`maxDuration` are intentionally not set; plan defaults
apply.

The rewrites map `/api/:path*` to `/api?__path=:path*`; the WSGI entry restores
`PATH_INFO` before dispatch. `/app`, `/app/` and `/app.html` are rewritten to
`/api/shell`, which forces `PATH_INFO=/app` and runs the same production app.
`/login` is the static sign-in document.

If the runtime configuration is missing, liveness still answers
`{"status":"ok"}`; readiness, login and `/app` answer
`503 CONFIGURATION_REQUIRED`. This is deliberate: the function is observable
without ever faking a session or serving workspace HTML.

## First-run provisioning

The runtime creates missing tables (`initialize_production_schema`) without
dropping or rewriting rows. Create the first real identity and project:

```bash
export CONSTRUCTION_PM_DATABASE_URL='postgresql://…'

# 1. Schema only
python scripts/provision_workspace.py init

# 2. A real user; the password is read from stdin (or CUBI_PROVISION_PASSWORD)
python scripts/provision_workspace.py user \
  --tenant your-tenant --email you@example.com \
  --roles project_admin --user-id you --display-name "Your Name" \
  < /path/to/password.txt

# 3. An authorized project with the curated field registry and layout
python scripts/provision_workspace.py project \
  --tenant your-tenant --project-id your-project \
  --name "Your Project" --member you@example.com --seed-presentation
```

The password must be at least 12 characters. It is hashed with scrypt
(n=2^14, r=8, p=1) and never printed.

## Session and security model

- Session cookie `cp_session`: opaque 256-bit token, `HttpOnly`, `SameSite=Lax`,
  `Secure` in production, 12-hour absolute lifetime, 2-hour idle timeout,
  idle touch at most once per minute.
- Only the SHA-256 of the token is stored in `identity_sessions`; the raw token
  is returned once to the browser and never echoed in JSON.
- CSRF cookie `cubi_csrf` is readable JavaScript and holds
  `HMAC-SHA256(session_secret, "csrf:" + token)`. Mutations must send it in
  `X-CSRF-Token`; the server recomputes and compares in constant time.
- Login failures are generic (`401 AUTHENTICATION_FAILED`), throttled per email
  (5) and per hashed IP (20) in 15 minutes, and return `429` with
  `Retry-After`. Unknown accounts spend comparable scrypt time.
- Every project read/write re-derives tenant and user from the session; the
  browser cannot select a tenant. A mismatched `X-Tenant-Id` on the workspace
  read returns `403 CROSS_SCOPE_ACCESS`, and a stale revision returns
  `409 STALE_WORKSPACE_READ_SCOPE`.
- Viewer/planner/project_admin permissions come from the stored session roles;
  `viewer` lacks `PROJECT_WRITE`/`PROJECT_ADMIN`.

## Verification (what was actually run)

| Layer | Command | Result |
| --- | --- | --- |
| Python unit (identity) | `PYTHONPATH=src python -m pytest tests/test_production_identity_session.py` | 21 passed |
| Python unit (HTTP boundary) | `PYTHONPATH=src python -m pytest tests/test_production_web_app.py` | 26 passed |
| Python unit (Vercel entrypoints) | `PYTHONPATH=src python -m pytest tests/test_vercel_entrypoints.py` | 6 passed |
| Full Python suite | `PYTHONPATH=src python -m pytest -q tests` | 4176 passed, 188 skipped |
| Live PostgreSQL, real WSGI | `CONSTRUCTION_PM_POSTGRES_DSN=… PYTHONPATH=src python -m pytest tests/integration/test_production_login_postgres_live.py` | 10 passed, repeated twice against the same database |
| Browser (headless Chrome) | `CONSTRUCTION_PM_POSTGRES_DSN=… node apps/web/e2e/production-login-e2e.mjs` | 10 checks, 3 screenshots, zero exceptions/console errors/5xx |
| Vercel build (real gateway) | push `e8999339` to `feat/production-vercel-login` | `Vercel – cubi-web-preview` **success**; preview alias issued |

The browser run drives the exact WSGI callable exported by `api/index.py`
(`apps/web/e2e/production-login-server.py` composes `ProductionRuntime`) and
asserts: anonymous `/app` redirect, rejected wrong password, real login,
authorized project workspace render, real `/api/session` and `/api/projects`,
refresh continuity, 1280×720 and 1366×768 renders, logout revocation,
post-logout rejection, Persian RTL login. Evidence JSON is written to
`apps/web/e2e/artifacts/production-login-e2e.json`.

The staged `apps/web/vercel-runtime` layout was additionally driven directly
over WSGI against PostgreSQL: `/api/health/live` 200, `/api/health/ready` 200
with `database` healthy, anonymous `/app` `302 /login?next=/app`, real login
200, `GET /api/session` 200, `GET /api/projects` 200 with the authorized
project, and `/app` 200 with the shell HTML.

## Deployment status and the remaining external input

Observed on the Vercel preview origin
`https://cubi-web-preview-git-feat-producti-c31a74-foroughichamshir-7811.vercel.app`
on 2026-11-13 16:54 UTC (commit `e8999339`):

| Request | Response |
| --- | --- |
| `GET /` | 200 HTML (landing page) |
| `GET /login` | 200 HTML, title `CUBI Workspace — Sign in`, bilingual form present |
| `GET /app` | 503 configuration page (gate reached, not faked) |
| `GET /api/health/live` | 200 `{"status":"ok"}` |
| `GET /api/health/ready` | 503 `{"status":"not_ready","code":"CONFIGURATION_REQUIRED"}` |
| `POST /api/session` | 503 `CONFIGURATION_REQUIRED` |
| `GET /dist/web/src/main.bundle.js` | 200 JavaScript |

The Python function is deployed and reachable through the Vercel gateway. It
cannot authenticate anyone yet because the project has no runtime environment
variables. The complete and exact input needed is:

1. **A reachable PostgreSQL database** and its DSN in
   `CONSTRUCTION_PM_DATABASE_URL` (Vercel Postgres / Neon / Supabase pooled
   endpoint, or any reachable PostgreSQL 12+).
2. `CONSTRUCTION_PM_SESSION_SECRET` — at least 32 random characters
   (e.g. `python -c "import secrets;print(secrets.token_urlsafe(48))"`).
3. `CONSTRUCTION_PM_PUBLIC_ORIGIN=https://cubi-web-preview.vercel.app`
   (and the preview origin if preview login is wanted).
4. The first real user's password, passed to `scripts/provision_workspace.py`
   on stdin; it is hashed locally and never stored in Git or chat.

Set these for the project (Production scope; Preview too if preview data is
intended), redeploy, then provision the user and project. No code change is
required after that: `/api/health/ready` becomes 200 and login works on the
same domain.

The other two Vercel projects connected to this repository
(`consttruction-pm-platform-public`, `consttruction-pm-platform-web`) report
`There is no GitHub account connected to this Vercel account.` on every
deployment, including main. That failure is pre-existing account/project state,
is unrelated to this code, and is not used by the CUBI workspace path.

Until the environment above is provided and a real login succeeds **on the
Vercel domain**, LIF-06 stays `BLOCKED_EXTERNAL`, not `VERIFIED`. Render is not
used, is not a fallback, and is not referenced by the Vercel build.
