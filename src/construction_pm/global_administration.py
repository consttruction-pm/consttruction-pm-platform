"""CUBI Global Administration.

A system-level administration surface for the product owner. It is **not** an
organization or project administration panel: it manages who exists, which
roles they hold, whether they can sign in, and what was done, across tenants.

Design rules enforced here:

* One identity model. Users live in ``identity_users``; this module adds state
  columns and an audit table, never a second user store.
* One permission model. The eleven catalogue roles map onto the existing role
  tokens (``viewer``, ``planner``, ``project_admin``, ``global_admin``) that the
  application authorization policy already understands.
* Server-side gate. Every request resolves the session and requires the
  ``global_admin`` token; hiding UI is never the control.
* Every mutation is audited with actor, target, tenant and a JSON detail.
* ``global_admin`` is never a signup choice: this module is the only writer that
  can grant it, and only an existing global admin can do so.
"""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from .identity_session import (
    IdentityError,
    IdentityService,
    hash_password,
    normalize_email,
    validate_role_tokens,
    verify_password,
)

GLOBAL_ADMIN_ROLE = "global_admin"
CONTRACT_VERSION = "cubi-global-administration.v1"
TEST_TENANT_PREFIX = "test-"


class GlobalAdministrationError(ValueError):
    """A request that must be refused, with a stable machine code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class RoleDefinition:
    key: str
    label_en: str
    label_fa: str
    token: str
    scope: str
    description: str


# Eleven roles from the brief. Seven share four existing tokens on purpose:
# creating new permission semantics would be a parallel model.
ROLE_CATALOG: tuple[RoleDefinition, ...] = (
    RoleDefinition("global_admin", "Global Admin", "مدیر کل سامانه", GLOBAL_ADMIN_ROLE, "system", "Product owner; user, role and test management across tenants."),
    RoleDefinition("organization_admin", "Organization Admin", "مدیر سازمان", "project_admin", "organization", "Tenant administration through the existing project_admin grants."),
    RoleDefinition("enterprise_admin", "Enterprise Admin", "مدیر سازمانی", "project_admin", "enterprise", "Enterprise environment administration."),
    RoleDefinition("enterprise_user", "Enterprise User", "کاربر سازمانی", "planner", "enterprise", "Enterprise planning and task work."),
    RoleDefinition("enterprise_viewer", "Enterprise Viewer", "بازدیدکننده سازمانی", "viewer", "enterprise", "Read-only Enterprise access."),
    RoleDefinition("engineering_admin", "Engineering Admin", "مدیر مهندسی", "project_admin", "engineering", "Engineering environment administration."),
    RoleDefinition("engineering_planner", "Engineering Planner", "برنامه‌ریز مهندسی", "planner", "engineering", "Schedule and cost planning."),
    RoleDefinition("engineering_user", "Engineering User", "کاربر مهندسی", "planner", "engineering", "Day-to-day schedule maintenance."),
    RoleDefinition("engineering_viewer", "Engineering Viewer", "بازدیدکننده مهندسی", "viewer", "engineering", "Read-only Engineering access."),
    RoleDefinition("guest", "Guest / Read-only", "مهمان / فقط خواندن", "viewer", "organization", "Read-only guest."),
    RoleDefinition("test_user", "Test User", "کاربر آزمایشی", "viewer", "test", "Disposable account bound to a test tenant."),
)

ROLE_TOKENS = frozenset(role.token for role in ROLE_CATALOG) | {GLOBAL_ADMIN_ROLE}
ROLE_BY_KEY = {role.key: role for role in ROLE_CATALOG}


def role_catalog_payload() -> list[dict[str, str]]:
    return [
        {
            "key": role.key,
            "label_en": role.label_en,
            "label_fa": role.label_fa,
            "token": role.token,
            "scope": role.scope,
            "description": role.description,
        }
        for role in ROLE_CATALOG
    ]


def tokens_for(role_keys: Any) -> frozenset[str]:
    """Translate catalogue keys to the persisted role tokens."""
    if not isinstance(role_keys, (list, tuple, set, frozenset)) or not role_keys:
        raise GlobalAdministrationError("ROLES_REQUIRED")
    tokens: set[str] = set()
    for key in role_keys:
        if not isinstance(key, str) or key not in ROLE_BY_KEY:
            raise GlobalAdministrationError("ROLE_NOT_IN_CATALOG")
        tokens.add(ROLE_BY_KEY[key].token)
        if key == "test_user":
            tokens.add("test_user")
    try:
        return validate_role_tokens(sorted(tokens))
    except IdentityError as error:
        raise GlobalAdministrationError(error.code) from None


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise GlobalAdministrationError("TIMESTAMP_INVALID") from None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class AdminActor:
    user_id: str
    tenant_id: str
    roles: frozenset[str]

    @property
    def is_global_admin(self) -> bool:
        return GLOBAL_ADMIN_ROLE in self.roles


@dataclass(frozen=True)
class ManagedUser:
    user_id: str
    tenant_id: str
    email: str
    display_name: str
    roles: frozenset[str]
    active: bool
    locked_at: datetime | None
    expires_at: datetime | None
    must_change_password: bool
    is_test_user: bool
    locale: str
    created_at: datetime | None
    last_login_at: datetime | None
    role_keys: tuple[str, ...] = ()
    session_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "email": self.email,
            "display_name": self.display_name,
            "roles": sorted(self.roles),
            "role_keys": sorted(self.role_keys) if self.role_keys else sorted(
                key for key, role in ROLE_BY_KEY.items() if role.token in self.roles
            ),
            "active": self.active,
            "locked": self.locked_at is not None,
            "expires_at": _iso(self.expires_at),
            "must_change_password": self.must_change_password,
            "is_test_user": self.is_test_user,
            "locale": self.locale,
            "created_at": _iso(self.created_at),
            "last_login_at": _iso(self.last_login_at),
            "sessions": self.session_count,
        }


class PostgresGlobalAdministrationStore:
    """Additive store over ``identity_users`` plus the administration audit log."""

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def initialize(self) -> None:
        for statement in (
            "ALTER TABLE identity_users ADD COLUMN IF NOT EXISTS is_test_user "
            "BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE identity_users ADD COLUMN IF NOT EXISTS locale TEXT NOT NULL DEFAULT 'en'",
            "ALTER TABLE identity_users ADD COLUMN IF NOT EXISTS updated_at "
            "TIMESTAMPTZ NOT NULL DEFAULT now()",
            # Catalogue labels chosen in the admin UI. Permission tokens remain
            # authoritative; this column only disambiguates roles that share a token.
            "ALTER TABLE identity_users ADD COLUMN IF NOT EXISTS role_keys_json "
            "TEXT NOT NULL DEFAULT '[]'",
            """
            CREATE TABLE IF NOT EXISTS global_admin_audit (
                audit_id BIGSERIAL PRIMARY KEY,
                actor_user_id TEXT NOT NULL,
                actor_tenant_id TEXT NOT NULL,
                action TEXT NOT NULL,
                target_user_id TEXT,
                target_tenant_id TEXT,
                reason TEXT NOT NULL DEFAULT '',
                detail_json TEXT NOT NULL DEFAULT '{}',
                occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """,
            "CREATE INDEX IF NOT EXISTS global_admin_audit_occurred "
            "ON global_admin_audit (occurred_at DESC)",
            "CREATE INDEX IF NOT EXISTS global_admin_audit_target "
            "ON global_admin_audit (target_user_id)",
        ):
            self.connection.execute(statement)

    # -- reads -----------------------------------------------------------
    def get(self, user_id: str) -> ManagedUser | None:
        row = self.connection.execute(
            "SELECT user_id, tenant_id, email, display_name, roles_json, active, "
            "locked_at, expires_at, must_change_password, is_test_user, locale, "
            "created_at, last_login_at, role_keys_json, "
            "(SELECT count(*) FROM identity_sessions s WHERE s.user_id=u.user_id "
            " AND s.revoked_at IS NULL AND s.expires_at > now()) "
            "FROM identity_users u WHERE user_id=%s",
            (user_id,),
        ).fetchone()
        return None if row is None else self._map(row)

    def list_users(self, *, query: str = "", status: str = "", limit: int = 50, offset: int = 0) -> tuple[list[ManagedUser], int]:
        where = ["TRUE"]
        params: list[Any] = []
        if query:
            where.append("(lower(email) LIKE %s OR lower(display_name) LIKE %s OR user_id=%s)")
            like = f"%{query.lower()}%"
            params.extend([like, like, query])
        if status == "active":
            where.append("active AND locked_at IS NULL")
        elif status == "disabled":
            where.append("NOT active")
        elif status == "locked":
            where.append("locked_at IS NOT NULL")
        elif status == "test":
            where.append("is_test_user")
        clause = " AND ".join(where)
        total = int(
            self.connection.execute(
                f"SELECT count(*) FROM identity_users u WHERE {clause}", tuple(params)
            ).fetchone()[0]
        )
        rows = self.connection.execute(
            "SELECT user_id, tenant_id, email, display_name, roles_json, active, "
            "locked_at, expires_at, must_change_password, is_test_user, locale, "
            "created_at, last_login_at, role_keys_json, "
            "(SELECT count(*) FROM identity_sessions s WHERE s.user_id=u.user_id "
            " AND s.revoked_at IS NULL AND s.expires_at > now()) "
            f"FROM identity_users u WHERE {clause} ORDER BY created_at DESC, user_id "
            "LIMIT %s OFFSET %s",
            (*params, limit, offset),
        ).fetchall()
        return [self._map(row) for row in rows], total

    def dashboard(self) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT count(*), "
            "count(*) FILTER (WHERE active AND locked_at IS NULL), "
            "count(*) FILTER (WHERE NOT active), "
            "count(*) FILTER (WHERE is_test_user), "
            "count(DISTINCT tenant_id), "
            "count(*) FILTER (WHERE last_login_at > now() - interval '7 days') "
            "FROM identity_users"
        ).fetchone()
        sessions = self.connection.execute(
            "SELECT count(*) FROM identity_sessions WHERE revoked_at IS NULL AND expires_at > now()"
        ).fetchone()[0]
        recent = self.list_audit(limit=10)
        return {
            "contract_version": CONTRACT_VERSION,
            "users_total": int(row[0]),
            "users_active": int(row[1]),
            "users_disabled": int(row[2]),
            "users_test": int(row[3]),
            "tenants": int(row[4]),
            "users_logged_in_7d": int(row[5]),
            "active_sessions": int(sessions),
            "roles_defined": len(ROLE_CATALOG),
            "recent_actions": recent,
            "database": "connected",
        }

    def list_audit(self, *, limit: int = 50, target_user_id: str = "") -> list[dict[str, Any]]:
        sql = (
            "SELECT audit_id, actor_user_id, actor_tenant_id, action, target_user_id, "
            "target_tenant_id, reason, detail_json, occurred_at FROM global_admin_audit"
        )
        params: tuple[Any, ...] = ()
        if target_user_id:
            sql += " WHERE target_user_id=%s"
            params = (target_user_id,)
        sql += " ORDER BY occurred_at DESC, audit_id DESC LIMIT %s"
        rows = self.connection.execute(sql, (*params, limit)).fetchall()
        return [
            {
                "audit_id": int(row[0]),
                "actor_user_id": row[1],
                "actor_tenant_id": row[2],
                "action": row[3],
                "target_user_id": row[4],
                "target_tenant_id": row[5],
                "reason": row[6],
                "detail": json.loads(row[7] or "{}"),
                "occurred_at": _iso(row[8]),
            }
            for row in rows
        ]

    def list_sessions(self, user_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT token_hash, created_at, last_seen_at, expires_at, revoked_at "
            "FROM identity_sessions WHERE user_id=%s ORDER BY created_at DESC LIMIT 50",
            (user_id,),
        ).fetchall()
        return [
            {
                "session_ref": str(row[0])[:12],
                "created_at": _iso(row[1]),
                "last_seen_at": _iso(row[2]),
                "expires_at": _iso(row[3]),
                "revoked": row[4] is not None,
            }
            for row in rows
        ]

    def password_hash(self, user_id: str) -> str:
        row = self.connection.execute(
            "SELECT password_hash FROM identity_users WHERE user_id=%s", (user_id,)
        ).fetchone()
        if row is None:
            raise GlobalAdministrationError("USER_NOT_FOUND")
        return str(row[0])

    # -- writes ----------------------------------------------------------
    def create(
        self,
        *,
        user_id: str,
        tenant_id: str,
        email: str,
        display_name: str,
        roles: frozenset[str],
        password_hash: str,
        must_change_password: bool,
        expires_at: datetime | None,
        is_test_user: bool,
        locale: str,
        role_keys: tuple[str, ...] = (),
    ) -> None:
        self.connection.execute(
            "INSERT INTO identity_users (user_id, tenant_id, email, display_name, "
            "roles_json, password_hash, active, must_change_password, expires_at, "
            "is_test_user, locale, role_keys_json) "
            "VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s, %s, %s, %s, %s)",
            (
                user_id,
                tenant_id,
                email,
                display_name,
                json.dumps(sorted(roles), separators=(",", ":")),
                password_hash,
                must_change_password,
                expires_at,
                is_test_user,
                locale,
                json.dumps(sorted(role_keys), separators=(",", ":")),
            ),
        )

    def update(self, user_id: str, fields: Mapping[str, Any]) -> None:
        allowed = {
            "display_name",
            "email",
            "roles_json",
            "active",
            "locked_at",
            "expires_at",
            "must_change_password",
            "locale",
            "role_keys_json",
        }
        assignments = [f"{name}=%s" for name in fields if name in allowed]
        values = [value for name, value in fields.items() if name in allowed]
        if not assignments:
            raise GlobalAdministrationError("NO_UPDATES")
        self.connection.execute(
            f"UPDATE identity_users SET {', '.join(assignments)}, updated_at=now() "
            "WHERE user_id=%s",
            (*values, user_id),
        )

    def set_password(self, user_id: str, password_hash: str) -> None:
        self.connection.execute(
            "UPDATE identity_users SET password_hash=%s, password_changed_at=now(), "
            "must_change_password=TRUE, updated_at=now() WHERE user_id=%s",
            (password_hash, user_id),
        )

    def revoke_sessions(self, user_id: str, *, when: datetime) -> int:
        result = self.connection.execute(
            "UPDATE identity_sessions SET revoked_at=%s WHERE user_id=%s AND revoked_at IS NULL",
            (when, user_id),
        )
        return int(getattr(result, "rowcount", 0) or 0)

    def audit(
        self,
        actor: AdminActor,
        action: str,
        *,
        target_user_id: str | None = None,
        target_tenant_id: str | None = None,
        reason: str = "",
        detail: Mapping[str, Any] | None = None,
    ) -> None:
        self.connection.execute(
            "INSERT INTO global_admin_audit (actor_user_id, actor_tenant_id, action, "
            "target_user_id, target_tenant_id, reason, detail_json) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                actor.user_id,
                actor.tenant_id,
                action,
                target_user_id,
                target_tenant_id,
                reason[:500],
                json.dumps(dict(detail or {}), separators=(",", ":")),
            ),
        )

    @staticmethod
    def _map(row: Any) -> ManagedUser:
        return ManagedUser(
            user_id=str(row[0]),
            tenant_id=str(row[1]),
            email=str(row[2]),
            display_name=str(row[3] or ""),
            roles=frozenset(json.loads(row[4])),
            active=bool(row[5]),
            locked_at=row[6],
            expires_at=row[7],
            must_change_password=bool(row[8]),
            is_test_user=bool(row[9]),
            locale=str(row[10] or "en"),
            created_at=row[11],
            last_login_at=row[12],
            role_keys=tuple(json.loads(row[13] or "[]")),
            session_count=int(row[14] or 0),
        )


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_LOCALE = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")
_TENANT = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")


class GlobalAdministrationService:
    """Authorization, validation and audit around the store."""

    def __init__(self, store: PostgresGlobalAdministrationStore, identity: IdentityService, *, now: Callable[[], datetime] | None = None) -> None:
        self._store = store
        self._identity = identity
        self._now = now or (lambda: datetime.now(timezone.utc))

    # -- gate ------------------------------------------------------------
    def actor(self, token: str) -> AdminActor:
        session = self._identity.resolve(token) if token else None
        if session is None:
            raise GlobalAdministrationError("SESSION_REQUIRED")
        actor = AdminActor(session.user_id, session.tenant_id, frozenset(session.roles))
        if not actor.is_global_admin:
            raise GlobalAdministrationError("GLOBAL_ADMIN_REQUIRED")
        return actor

    def _reauth(self, actor: AdminActor, password: str) -> None:
        if not password:
            raise GlobalAdministrationError("REAUTHENTICATION_REQUIRED")
        if not verify_password(password, self._store.password_hash(actor.user_id)):
            raise GlobalAdministrationError("REAUTHENTICATION_FAILED")

    # -- read surface ----------------------------------------------------
    def dashboard(self, token: str) -> dict[str, Any]:
        actor = self.actor(token)
        payload = self._store.dashboard()
        payload["viewer"] = {"user_id": actor.user_id, "tenant_id": actor.tenant_id}
        payload["role_catalog"] = role_catalog_payload()
        return payload

    def users(self, token: str, *, query: str = "", status: str = "", limit: int = 50, offset: int = 0) -> dict[str, Any]:
        self.actor(token)
        users, total = self._store.list_users(query=query, status=status, limit=limit, offset=offset)
        return {
            "contract_version": CONTRACT_VERSION,
            "total": total,
            "limit": limit,
            "offset": offset,
            "users": [user.as_dict() for user in users],
        }

    def user(self, token: str, user_id: str) -> dict[str, Any]:
        self.actor(token)
        user = self._store.get(user_id)
        if user is None:
            raise GlobalAdministrationError("USER_NOT_FOUND")
        return {"contract_version": CONTRACT_VERSION, "user": user.as_dict()}

    def sessions(self, token: str, user_id: str) -> dict[str, Any]:
        self.actor(token)
        return {"contract_version": CONTRACT_VERSION, "sessions": self._store.list_sessions(user_id)}

    def audit(self, token: str, *, limit: int = 50, target_user_id: str = "") -> dict[str, Any]:
        self.actor(token)
        return {
            "contract_version": CONTRACT_VERSION,
            "limit": limit,
            "entries": self._store.list_audit(limit=limit, target_user_id=target_user_id),
        }

    # -- mutations -------------------------------------------------------
    def create_user(self, token: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        actor = self.actor(token)
        email = self._email(payload.get("email"))
        tenant = self._tenant(payload.get("tenant_id"))
        display = self._display(payload.get("display_name"))
        role_keys = payload.get("roles") or ["engineering_viewer"]
        tokens = tokens_for(role_keys)
        chosen_keys = tuple(sorted({str(key) for key in role_keys}))
        is_test = bool(payload.get("is_test_user")) or tenant.startswith(TEST_TENANT_PREFIX)
        locale = self._locale(payload.get("locale", "en"))
        expires = _parse(payload.get("expires_at")) if payload.get("expires_at") else None
        if is_test and not tenant.startswith(TEST_TENANT_PREFIX):
            raise GlobalAdministrationError("TEST_USER_REQUIRES_TEST_TENANT")
        if is_test and expires is None:
            raise GlobalAdministrationError("TEST_USER_REQUIRES_EXPIRY")
        if GLOBAL_ADMIN_ROLE in tokens and not actor.is_global_admin:
            raise GlobalAdministrationError("GLOBAL_ADMIN_REQUIRED")
        password = self._temporary_password()
        user_id = f"usr-{secrets.token_hex(8)}"
        self._store.create(
            user_id=user_id,
            tenant_id=tenant,
            email=email,
            display_name=display,
            roles=tokens,
            password_hash=hash_password(password),
            must_change_password=True,
            expires_at=expires,
            is_test_user=is_test,
            locale=locale,
            role_keys=chosen_keys,
        )
        self._store.audit(
            actor,
            "user.create",
            target_user_id=user_id,
            target_tenant_id=tenant,
            reason=str(payload.get("reason") or ""),
            detail={"roles": sorted(tokens), "is_test_user": is_test, "expires_at": _iso(expires)},
        )
        created = self._store.get(user_id)
        return {
            "contract_version": CONTRACT_VERSION,
            "user": created.as_dict() if created else None,
            "temporary_password": password,
        }

    def update_user(self, token: str, user_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        actor = self.actor(token)
        target = self._store.get(user_id)
        if target is None:
            raise GlobalAdministrationError("USER_NOT_FOUND")
        fields: dict[str, Any] = {}
        if "display_name" in payload:
            fields["display_name"] = self._display(payload.get("display_name"))
        if "email" in payload:
            fields["email"] = self._email(payload.get("email"))
        if "locale" in payload:
            fields["locale"] = self._locale(payload.get("locale"))
        if "active" in payload:
            if target.tenant_id == actor.tenant_id and target.user_id == actor.user_id and not payload.get("active"):
                raise GlobalAdministrationError("CANNOT_DISABLE_SELF")
            fields["active"] = bool(payload.get("active"))
        if "locked" in payload:
            fields["locked_at"] = self._now() if payload.get("locked") else None
        if "expires_at" in payload:
            fields["expires_at"] = _parse(payload.get("expires_at")) if payload.get("expires_at") else None
        if "roles" in payload:
            tokens = tokens_for(payload.get("roles"))
            if GLOBAL_ADMIN_ROLE in tokens and GLOBAL_ADMIN_ROLE not in target.roles:
                self._reauth(actor, str(payload.get("confirm_password") or ""))
            if GLOBAL_ADMIN_ROLE in target.roles and GLOBAL_ADMIN_ROLE not in tokens:
                if target.user_id == actor.user_id:
                    raise GlobalAdministrationError("CANNOT_DEMOTE_SELF")
                self._reauth(actor, str(payload.get("confirm_password") or ""))
            fields["roles_json"] = json.dumps(sorted(tokens), separators=(",", ":"))
            fields["role_keys_json"] = json.dumps(
                sorted({str(key) for key in payload.get("roles")}), separators=(",", ":")
            )
        if not fields:
            raise GlobalAdministrationError("NO_UPDATES")
        self._store.update(user_id, fields)
        self._store.audit(
            actor,
            "user.update",
            target_user_id=user_id,
            target_tenant_id=target.tenant_id,
            reason=str(payload.get("reason") or ""),
            detail={key: _iso(value) if isinstance(value, datetime) else value for key, value in fields.items()},
        )
        updated = self._store.get(user_id)
        return {"contract_version": CONTRACT_VERSION, "user": updated.as_dict() if updated else None}

    def reset_password(self, token: str, user_id: str, *, confirm_password: str, reason: str = "") -> dict[str, Any]:
        actor = self.actor(token)
        self._reauth(actor, confirm_password)
        target = self._store.get(user_id)
        if target is None:
            raise GlobalAdministrationError("USER_NOT_FOUND")
        password = self._temporary_password()
        self._store.set_password(user_id, hash_password(password))
        revoked = self._store.revoke_sessions(user_id, when=self._now())
        self._store.audit(
            actor,
            "user.password_reset",
            target_user_id=user_id,
            target_tenant_id=target.tenant_id,
            reason=reason,
            detail={"sessions_revoked": revoked},
        )
        return {
            "contract_version": CONTRACT_VERSION,
            "temporary_password": password,
            "must_change_password": True,
            "sessions_revoked": revoked,
        }

    def revoke_sessions(self, token: str, user_id: str, *, confirm_password: str, reason: str = "") -> dict[str, Any]:
        actor = self.actor(token)
        self._reauth(actor, confirm_password)
        target = self._store.get(user_id)
        if target is None:
            raise GlobalAdministrationError("USER_NOT_FOUND")
        revoked = self._store.revoke_sessions(user_id, when=self._now())
        self._store.audit(
            actor,
            "user.sessions_revoked",
            target_user_id=user_id,
            target_tenant_id=target.tenant_id,
            reason=reason,
            detail={"sessions_revoked": revoked},
        )
        return {"contract_version": CONTRACT_VERSION, "sessions_revoked": revoked}

    # -- validation helpers ---------------------------------------------
    @staticmethod
    def _email(value: Any) -> str:
        try:
            email = normalize_email(value)
        except IdentityError as error:
            raise GlobalAdministrationError(error.code) from None
        if not _EMAIL.match(email):
            raise GlobalAdministrationError("EMAIL_INVALID")
        return email

    @staticmethod
    def _tenant(value: Any) -> str:
        if not isinstance(value, str) or not _TENANT.match(value.strip().lower()):
            raise GlobalAdministrationError("TENANT_INVALID")
        return value.strip().lower()

    @staticmethod
    def _display(value: Any) -> str:
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > 120:
            raise GlobalAdministrationError("DISPLAY_NAME_INVALID")
        return value.strip()

    @staticmethod
    def _locale(value: Any) -> str:
        if not isinstance(value, str) or not _LOCALE.match(value):
            raise GlobalAdministrationError("LOCALE_INVALID")
        return value

    @staticmethod
    def _temporary_password() -> str:
        # Shown once to the administrator; never logged or stored in clear.
        return "Cubi-" + secrets.token_urlsafe(12)
