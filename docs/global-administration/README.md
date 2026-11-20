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
  `is_test_user`, `locale`, `updated_at` (`ADD COLUMN IF NOT EXISTS`).
- New table `global_admin_audit`.
- No second user store, no second auth system, no parallel schema.

## Verification

| Check | Result |
| --- | --- |
| `pytest tests/test_global_administration.py` (no DSN) | 5 passed, 1 skipped |
| same, with a real PostgreSQL 14 DSN | 6 passed — full flow: create → login → lock → disable → expire → reset → revoke → audit → non-admin denied → reauth enforced |
| `npm test` (web) | 1200 passed, 0 failed |
| `npx tsc --noEmit` | clean |
| `npm run build` | bundle built |

Remaining: the production deployment still needs a Global Admin account provisioned with
`scripts/provision_workspace.py user --roles global_admin` (owner action, requires the production
DSN). The UI currently renders the dashboard, summary and recent audit actions; the user editor
form is the next increment.
