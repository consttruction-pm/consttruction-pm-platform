# Production deployment — CUBI Workspace on Vercel

This document describes the real production path, not the local preview:

```
Browser
  → Vercel domain (cubi-web-preview)
  → Vercel Python function (api/index.py, api/shell.py)
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

- Root directory: repository root.
- Framework preset: none (`"framework": null`).
- Install command: `npm --prefix apps/web ci --no-audit --no-fund`.
- Build command: `bash scripts/vercel_build.sh` (builds the Web bundle and
  assembles `public/`).
- Output directory: `public`.
- Functions: `api/index.py` (python3.12, 1024 MB, 30 s) and `api/shell.py`
  (python3.12, 512 MB, 15 s), both with `src/**` and `requirements.txt`
  included.
- Rewrites, headers and ignored paths: `vercel.json`, `.vercelignore`.
- Python dependencies: root `requirements.txt` (`psycopg[binary]`).

The rewrites map `/api/:path*` to `/api/index?__path=:path*`; the WSGI entry
restores `PATH_INFO` before dispatch. `/app` is rewritten to `/api/shell`,
which forces `PATH_INFO=/app` and runs the same production app.

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

Nothing below is a Vercel-gateway claim. See the status note at the end.

| Layer | Command | Result |
| --- | --- | --- |
| Python unit (identity) | `PYTHONPATH=src python -m pytest tests/test_production_identity_session.py` | 21 passed |
| Python unit (HTTP boundary) | `PYTHONPATH=src python -m pytest tests/test_production_web_app.py` | 25 passed |
| Live PostgreSQL, real WSGI | `CONSTRUCTION_PM_POSTGRES_DSN=… PYTHONPATH=src python -m pytest tests/integration/test_production_login_postgres_live.py` | 10 passed (login, session, projects, open, workspace v2, refresh, logout, viewer/planner/admin, cross-tenant, stale revision, 429) |
| Browser (headless Chrome) | `CONSTRUCTION_PM_POSTGRES_DSN=… node apps/web/e2e/production-login-e2e.mjs` | 10 checks, 3 screenshots, zero exceptions/console errors/5xx |

The browser run drives the exact WSGI callable exported by `api/index.py`
(`apps/web/e2e/production-login-server.py` composes `ProductionRuntime`) and
asserts: anonymous `/app` redirect, rejected wrong password, real login,
authorized project workspace render, real `/api/session` and `/api/projects`,
refresh continuity, 1280×720 and 1366×768 renders, logout revocation,
post-logout rejection, Persian RTL login. Evidence JSON is written to
`apps/web/e2e/artifacts/production-login-e2e.json`.

## Deployment status and the remaining external input

The existing Vercel deployments (`cubi-web-preview.vercel.app` and the
immutable `…-qkm0lkylp-…` URL) still serve only the static bundle: `/api/*`
returns 404, so no login is possible there yet. This repository now contains the
complete runtime, configuration and tests, but publishing requires one of:

1. Vercel access for this project (a token or dashboard/CLI session), or
2. a Git integration that redeploys `main` automatically, plus
3. a reachable PostgreSQL instance and its DSN, and
4. the first production user's password (entered through provisioning, never
   shared in Git or chat).

Until a deployment built from this branch serves `POST /api/session` and a real
login succeeds **on the Vercel domain**, LIF-06 remains unverified at the
gateway level and must be reported as `BLOCKED_EXTERNAL`, not `VERIFIED`.
