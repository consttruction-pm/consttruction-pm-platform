# CUBI Global Administration (R2)

A system-level surface for the product owner, distinct from organization or project administration.

## Surface

- UI route `/admin` (authenticated; served by the same single shell, no second app).
- API prefix `/api/admin/*`.
- Contract `cubi-global-administration.v1`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/admin/dashboard` | users/tenants/sessions/audit summary + role catalogue |
| GET | `/api/admin/users?query=&status=&limit=&offset=` | list and filter users |
| POST | `/api/admin/users` | create a user (returns a one-time temporary password) |
| GET | `/api/admin/users/{id}` | one user |
| PATCH | `/api/admin/users/{id}` | profile, active, lock, expiry, roles |
| GET | `/api/admin/users/{id}/sessions` | session references (hashes truncated, never tokens) |
| POST | `/api/admin/users/{id}/revoke-sessions` | reauthentication required |
| POST | `/api/admin/users/{id}/password-reset` | reauthentication required; revokes sessions |
| GET | `/api/admin/audit?limit=&target_user_id=` | audit log |
| GET | `/api/admin/roles` | the eleven-role catalogue |

## Roles

Eleven catalogue roles map onto the four existing role tokens (`global_admin`, `project_admin`,
`planner`, `viewer`). No parallel permission model is introduced:

| Catalogue role | Token |
| --- | --- |
| Global Admin | `global_admin` |
| Organization Admin, Enterprise Admin, Engineering Admin | `project_admin` |
| Enterprise User, Engineering Planner, Engineering User | `planner` |
| Enterprise Viewer, Engineering Viewer, Guest | `viewer` |
| Test User | `viewer` + `test_user` |

`global_admin` is never a signup choice. Only this service can grant it, and granting or removing
it requires password reauthentication. An administrator cannot demote or disable themselves.

## Security controls

- Server-side gate on every request: the session is resolved and `global_admin` is required;
  401 when there is no session, 403 when the role is missing.
- CSRF: state-changing calls pass through `ProductionWebApp`, which verifies the signed double
  submit before the request reaches the admin middleware.
- Reauthentication (`confirm_password`) for role changes involving `global_admin`, password reset
  and session revocation.
- Locked, disabled and expired accounts cannot log in — enforced inside `IdentityService`, not in
  the UI.
- Temporary passwords are returned exactly once, stored only as scrypt hashes, never logged.
- Test users must live in a `test-` tenant and must carry an expiry.
- Every mutation writes an audit row: actor, target, tenant, reason, JSON detail, timestamp.

## Storage

Additive only, on the existing identity model:

- `identity_users` gains `locked_at`, `expires_at`, `must_change_password`, `last_login_at`,
  `is_test_user`, `locale`, `updated_at`, `role_keys_json` (`ADD COLUMN IF NOT EXISTS`).
  `role_keys_json` only disambiguates catalogue labels (seven roles share four tokens); the
  permission tokens in `roles_json` remain the sole authority.
- New table `global_admin_audit`.
- No second user store, no second auth system, no parallel schema.

## Verification

| Check | Result |
| --- | --- |
| `pytest tests/test_global_administration.py` (no DSN) | 5 passed, 1 skipped |
| same, with a real PostgreSQL 14 DSN | 6 passed — create → login → lock → disable → expire → reset → revoke → audit → non-admin denied → reauth enforced |
| `pytest tests/test_global_administration_http.py` with PostgreSQL | 1 passed — real `ProductionWebApp`: login cookie, CSRF missing → 403, create/edit/role change/test account, reauth required and wrong password → 403, non-admin → 403, reset/revoke → old sessions 401, audit rows, expired login → 401 |
| `npm test` (web) | 1206 passed, 0 failed |
| `npx tsc --noEmit` | clean |
| `npm run build` | bundle built |
| Local provisioning | `scripts/provision_workspace.py user --tenant platform-owner --roles global_admin --password-stdin` → login verified with `global_admin` |

## Production provisioning blocker

A production Global Admin cannot be created from this sandbox: no production PostgreSQL DSN,
deployment credentials, or owner password is available, and none is allowed in code, logs or
commits. The supported path is a single owner-run command with the production DSN supplied in the
environment:

```sh
CONSTRUCTION_PM_DATABASE_URL="postgresql://…" \
  python scripts/provision_workspace.py user --tenant platform-owner \
  --email <owner-email> --roles global_admin --password-stdin
```

The password is read from stdin, hashed with scrypt, and never echoed. The same command was run
against the local PostgreSQL 14 instance and the resulting account logged in with the
`global_admin` role.
