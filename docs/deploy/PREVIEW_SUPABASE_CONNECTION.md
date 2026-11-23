# Preview → Supabase connection runbook

This is the exact procedure to point the CUBI Vercel **Preview** deployment at
the existing Supabase project and prove the full chain: login → project → save →
form → assistant proposal → approval → logout → re-login → restore.

It does **not** create a database, copy data to a new project, or reset
anything. The target is the existing reference database.

## The immutable target

| Fact | Value |
| --- | --- |
| Supabase project | `CUBI-Platform-Core-DB` |
| Project ref | `pbgosszuzemljgoccppk` |
| Region | Frankfurt (`eu-central-1`) |
| Vercel project | `cubi-web-preview` (`prj_E1psnPyPs9doA82oZ4OcmiIqarle`) |
| Vercel root directory | `apps/web` |
| Target environment | Vercel **Preview** (Production only with separate approval) |

Prohibited: a second Supabase project, a parallel test database, a local
database presented as success, deleting or resetting the current database,
changing existing rows without a backup/migration plan, or committing a DSN,
password, session secret or service-role key.

## Baseline rows to preserve

Before any change, record these counts. They must not decrease.

| Table | Expected baseline |
| --- | --- |
| `knowledge_source` | 9 |
| `knowledge_topic` | 353 |
| `knowledge_card` | 360 |
| `knowledge_audit` | 9 |
| everything else | 0 |

```sql
-- read-only, run in the Supabase SQL editor
select 'knowledge_source' as tbl, count(*) from knowledge_source
union all select 'knowledge_topic', count(*) from knowledge_topic
union all select 'knowledge_card',  count(*) from knowledge_card
union all select 'knowledge_audit', count(*) from knowledge_audit;
```

Take a logical backup before the first migration. From a machine that holds the
DSN (never from this repository):

```bash
pg_dump --no-owner --no-privileges --schema=public \
  "$CONSTRUCTION_PM_DATABASE_URL" > cubi-core-db-$(date +%Y%m%dT%H%M%SZ).sql
```

## Step 1 — build the connection string

The runtime uses `psycopg` and needs TLS. Two Supabase endpoints work:

- **Session pooler** (recommended for this runtime), port `5432`:
  `postgresql://postgres.<ref>:<password>@aws-0-eu-central-1.pooler.supabase.com:5432/postgres?sslmode=require`
- **Direct connection**, port `5432`:
  `postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres?sslmode=require`

Do not use the transaction pooler on port `6543` unless prepared statements are
disabled. The runtime keeps a small per-instance connection pool and psycopg
prepares statements after repeated use, which a transaction pooler does not
guarantee across requests.

Set `connect_timeout` via `CONSTRUCTION_PM_DB_CONNECT_TIMEOUT` (default 10s) and
keep `CONSTRUCTION_PM_DB_POOL_SIZE` low (1–2) for serverless.

## Step 2 — set Vercel Preview environment variables

In the Vercel project → Settings → Environment Variables, add these for the
**Preview** scope only (Production is out of scope without explicit approval):

| Name | Value |
| --- | --- |
| `CONSTRUCTION_PM_DATABASE_URL` | the DSN from Step 1 (marked *Sensitive*) |
| `CONSTRUCTION_PM_SESSION_SECRET` | ≥ 32 random chars: `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
| `CONSTRUCTION_PM_PUBLIC_ORIGIN` | the exact preview origin, e.g. `https://cubi-web-preview-git-<branch>-<team>.vercel.app` |
| `CONSTRUCTION_PM_DB_POOL_SIZE` | `2` (optional) |
| `CONSTRUCTION_PM_DB_CONNECT_TIMEOUT` | `10` (optional) |
| `CONSTRUCTION_PM_DB_SCHEMA` | leave unset for the real `public` schema (optional; only used to isolate test schemas) |
| `CUBI_AI_ENABLED` | `1` only if a server-side provider is configured (see Step 6) |
| `CUBI_AI_ACTIONS_ENABLED` | `1` to allow proposals/execution |
| `CUBI_AI_REQUIRE_DISTINCT_APPROVER` | `1` to require a second human approver |

`CONSTRUCTION_PM_PUBLIC_ORIGIN` must match the host the browser actually opens.
A mismatch makes login and every mutation return `403 ORIGIN_MISMATCH` by
design. Vercel branch previews get a unique host per branch, so set the origin
for the branch you will test, or promote a fixed preview alias.

Do not set `CONSTRUCTION_PM_INSECURE_COOKIES`; it is ignored on HTTPS.

## Step 3 — deploy the preview

1. Push the branch and let Vercel build, or redeploy with the new variables:
   `vercel --preview --cwd apps/web` (or trigger Redeploy in the dashboard after
   changing env vars — existing deployments do not pick up new values).
2. Record the **Deployment ID** and the **Preview URL** from the deployment.
3. Confirm the function sees configuration:

```bash
curl -sS "https://<preview-host>/api/health/live"
# {"status":"ok","schema":null}   (or schema omitted)

curl -sS "https://<preview-host>/api/health/ready"
# 200 {"status":"ready","components":[{"name":"database","healthy":true}],
#      "schema":{"version":15,"tables":94,"drift":null}}
```

The runtime applies pending migrations on first request through
`initialize_production_schema`, records them in `cubi_schema_migration`, and
reports the ledger version and table count in readiness. A first cold start on
an empty schema applies 15 steps and creates 94 tables. Re-running applies
zero steps.

If readiness returns `503 not_ready` with `database` unhealthy, the DSN, TLS
mode, network allow-list or password is wrong. If it returns
`schema.drift`, read the next section before proceeding.

## Step 4 — apply migrations explicitly (optional but preferred)

Applying at startup is safe and repeatable, but running it once from an
operator machine makes the first failure visible without a cold-start timeout:

```bash
export CONSTRUCTION_PM_DATABASE_URL='postgresql://…?sslmode=require'
PYTHONPATH=src python scripts/provision_workspace.py init
# prints: schema ready
```

This runs the same versioned registry. It is additive: `CREATE TABLE IF NOT
EXISTS`, `ALTER TABLE … ADD COLUMN IF NOT EXISTS`, no `DROP`, `TRUNCATE` or
`RESET`. The knowledge tables and their rows are untouched.

## Step 5 — provision the real test tenant

```bash
# real admin
PYTHONPATH=src python scripts/provision_workspace.py user \
  --tenant cubi-acceptance --email owner@example.com --roles project_admin \
  --display-name "Acceptance Admin" --password-stdin < /secure/password.txt

# real project with the curated field registry and layout
PYTHONPATH=src python scripts/provision_workspace.py project \
  --tenant cubi-acceptance --project-id acceptance-project \
  --name "Acceptance Project" --member owner@example.com --seed-presentation
```

Then create the planner and viewer memberships through the real API (or the
Enterprise organization-access routes), not by editing rows. The acceptance
needs Admin, Planner and Viewer roles to prove permissions.

## Step 6 — configure the assistant (optional, needed for P0-G)

The assistant is server-only and HTTPS-only. Providers are configured by
environment, never in the browser:

| Name | Purpose |
| --- | --- |
| `CUBI_AI_ENABLED` | instantiate the OpenAI-compatible provider |
| `CUBI_AI_BASE_URL` | provider base URL (HTTPS) |
| `CUBI_AI_API_KEY` | provider key (Sensitive) |
| `CUBI_AI_MODEL` | model name |
| `CUBI_AI_ACTIONS_ENABLED` | enable proposals and execution |
| `CUBI_AI_REQUIRE_DISTINCT_APPROVER` | forbid self-approval |

Without a provider the deterministic planner still runs; the assistant returns
an honest `BLOCKED`/`PARTIAL` capability instead of a fabricated answer. Do not
claim AI verification until a real model response is observed.

## Step 7 — verify the deployment

Run the evidence script. It is read-only by default and never prints secrets:

```bash
python scripts/verify_preview_runtime.py \
  --base-url "https://<preview-host>" \
  --email owner@example.com \
  --password-stdin \
  --project-id acceptance-project \
  --out preview-evidence.json < /secure/password.txt
```

Add `--write` to also create one risk and one AI proposal (it never approves or
executes them). The script checks, in order: liveness, readiness with schema
version, login, `GET /api/session`, `GET /api/projects`, project open, workspace
read v2, risks, AI proposals, organization form templates, knowledge coverage,
optional writes with read-back, logout `204`, revoked session `401`, re-login,
and project restore. Exit code 0 means every required check passed; a recorded
`BLOCKED` capability does not fail the run.

Then run the manual browser journey on the same origin:

1. Open `/login`, sign in as the admin.
2. Create or open the acceptance project.
3. Add a WBS node and an activity; reload and confirm it persisted.
4. Design a form, submit it, review and approve it (Planner → Admin).
5. Ask the assistant for an activity proposal, approve it, execute it.
6. Log out, sign in again in the same or a new browser, and confirm the
   project, activity, form approval and audit history are intact.
7. Sign in as Viewer and confirm writes return `403`; sign in as another tenant
   and confirm the project is invisible.

## Drift policy and rollback

- Default drift policy is `report`: a legacy database may legitimately differ;
  readiness still succeeds and the structured drift summary is logged.
- Set `fail` only after an audit confirms the expected fingerprint, so a real
  structural change stops readiness instead of being ignored.
- A migration failure aborts the whole bootstrap transaction; no partial step
  is recorded in the ledger.
- Rollback of schema is by restoring the `pg_dump` taken in the baseline step.
  The ledger is append-only; never edit it by hand.

## Counts after acceptance

Re-run the baseline query. Expected additions: identity users/sessions for the
acceptance tenant, one organization and memberships, one project with WBS,
activities, relationships, calendar, assignments, baseline, one or more forms
and submissions, one or more risks, AI proposals and their audit events. The
four knowledge counts must remain exactly 9 / 353 / 360 / 9.

## External blockers (what cannot be done from this sandbox)

This environment has **no Supabase credentials and no Vercel token**. It cannot
read the reference database, set its environment variables, deploy a Preview,
or observe the deployed origin. Therefore:

- Migration registry, storage adapters, security and the full save/restore
  chain are verified on a **real local PostgreSQL 14** with disposable schemas
  (`tests/integration/test_cubi_database_operationalization_postgres_live.py`,
  12 tests).
- `VERIFIED_ON_SUPABASE` and `VERIFIED_ON_PREVIEW` remain **BLOCKED** until an
  owner runs Steps 1–7 above and returns the deployment ID, preview URL,
  readiness payload and `preview-evidence.json`.

No part of this runbook requires a code change: the deployment becomes live as
soon as the environment variables are set and the preview is redeployed.
