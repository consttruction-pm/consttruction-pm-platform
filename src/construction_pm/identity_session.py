"""Production identity, password verification and persisted login sessions.

The preview server authenticates fixed demo personas with in-memory sessions.
That is deliberately not usable here: this module verifies a real password
against a stored scrypt hash, writes an opaque session row to durable storage,
and resolves that row for the existing lifecycle service. The raw session
token and the raw password never leave this module.

Only the SHA-256 hash of a session token is stored. A database disclosure
therefore does not yield a usable cookie. CSRF tokens are derived from the
session token with a server-held secret and are never stored.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Protocol
from urllib.parse import quote

from .application.project_lifecycle import AuthenticatedSession

# scrypt parameters. n=2**14 uses 16 MiB and roughly 40 ms per verification on
# the deployment CPU, which is enough to make offline guessing expensive while
# keeping an interactive login responsive.
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
SCRYPT_MAXMEM = 64 * 1024 * 1024
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 256

# The HTTP route layer already reads this exact cookie name.
SESSION_COOKIE_NAME = "cp_session"
CSRF_COOKIE_NAME = "cubi_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"

DEFAULT_SESSION_TTL = timedelta(hours=12)
DEFAULT_IDLE_TIMEOUT = timedelta(hours=2)
DEFAULT_MAX_EMAIL_FAILURES = 5
DEFAULT_MAX_IP_FAILURES = 20
DEFAULT_FAILURE_WINDOW = timedelta(minutes=15)
TOUCH_INTERVAL = timedelta(seconds=60)

_ROLE_TOKEN = frozenset(
    "abcdefghijklmnopqrstuvwxyz0123456789_-"
)


class IdentityError(ValueError):
    """Stable, non-enumerating authentication failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _b64encode(value: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    import base64

    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Return a self-describing scrypt hash; parameters travel with the hash."""
    if not isinstance(password, str) or not password:
        raise IdentityError("PASSWORD_REQUIRED")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise IdentityError("PASSWORD_TOO_LONG")
    salt = secrets.token_bytes(16) if salt is None else salt
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
        maxmem=SCRYPT_MAXMEM,
    )
    return (
        f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}"
        f"${_b64encode(salt)}${_b64encode(derived)}"
    )


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time verification of a stored scrypt hash."""
    if not isinstance(password, str) or not isinstance(encoded, str):
        return False
    if len(password) > PASSWORD_MAX_LENGTH:
        return False
    parts = encoded.split("$")
    if len(parts) != 6 or parts[0] != "scrypt":
        return False
    try:
        n, r, p = int(parts[1]), int(parts[2]), int(parts[3])
        salt = _b64decode(parts[4])
        expected = _b64decode(parts[5])
    except (TypeError, ValueError):
        return False
    if n < 2**12 or n > 2**20 or r < 1 or p < 1:
        return False
    try:
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(expected),
            maxmem=SCRYPT_MAXMEM,
        )
    except (ValueError, MemoryError):
        return False
    return hmac.compare_digest(derived, expected)


def password_policy_error(password: str) -> str | None:
    """Return a stable policy code, or None when the password is acceptable."""
    if not isinstance(password, str) or not password:
        return "PASSWORD_REQUIRED"
    if len(password) < PASSWORD_MIN_LENGTH:
        return "PASSWORD_TOO_SHORT"
    if len(password) > PASSWORD_MAX_LENGTH:
        return "PASSWORD_TOO_LONG"
    return None


def validate_role_tokens(roles: Any) -> frozenset[str]:
    if not isinstance(roles, (list, tuple, set, frozenset)):
        raise IdentityError("INVALID_ROLES")
    normalized: set[str] = set()
    for role in roles:
        if not isinstance(role, str) or not role.strip():
            raise IdentityError("INVALID_ROLES")
        value = role.strip()
        if len(value) > 64 or any(char not in _ROLE_TOKEN for char in value):
            raise IdentityError("INVALID_ROLES")
        normalized.add(value)
    if not normalized:
        raise IdentityError("ROLES_REQUIRED")
    return frozenset(normalized)


def normalize_email(email: Any) -> str:
    if not isinstance(email, str):
        raise IdentityError("EMAIL_REQUIRED")
    value = email.strip().lower()
    if (
        not value
        or len(value) > 254
        or value.count("@") != 1
        or any(char.isspace() for char in value)
        or value.startswith("@")
        or value.endswith("@")
    ):
        raise IdentityError("EMAIL_INVALID")
    local, domain = value.split("@", 1)
    if "." not in domain or not local:
        raise IdentityError("EMAIL_INVALID")
    return value


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    if not isinstance(token, str) or not token:
        raise IdentityError("SESSION_TOKEN_INVALID")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def csrf_token(secret: str, token: str) -> str:
    if not isinstance(secret, str) or len(secret) < 32:
        raise IdentityError("CSRF_SECRET_MISSING")
    digest = hmac.new(
        secret.encode("utf-8"), f"csrf:{token}".encode("utf-8"), hashlib.sha256
    ).digest()
    return _b64encode(digest)


@dataclass(frozen=True)
class IdentityUser:
    user_id: str
    tenant_id: str
    email: str
    display_name: str
    roles: frozenset[str]
    password_hash: str
    active: bool = True


@dataclass(frozen=True)
class StoredSession:
    token_hash: str
    user_id: str
    tenant_id: str
    roles: frozenset[str]
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None


@dataclass(frozen=True)
class IssuedSession:
    token: str
    csrf_token: str
    user_id: str
    tenant_id: str
    roles: frozenset[str]
    created_at: datetime
    expires_at: datetime


class IdentityStore(Protocol):
    def initialize(self) -> None: ...

    def find_user_by_email(self, email: str) -> IdentityUser | None: ...

    def record_attempt(
        self,
        *,
        email: str,
        tenant_id: str | None,
        ip_hash: str,
        attempted_at: datetime,
        succeeded: bool,
    ) -> None: ...

    def count_failures(
        self, *, email: str, ip_hash: str, since: datetime
    ) -> tuple[int, int]: ...

    def save_session(self, session: StoredSession) -> None: ...

    def load_session(self, hashed: str, *, now: datetime) -> StoredSession | None: ...

    def touch_session(self, hashed: str, *, when: datetime) -> None: ...

    def revoke_session(self, hashed: str, *, when: datetime) -> bool: ...

    def delete_attempts_before(self, cutoff: datetime) -> None: ...


_DUMMY_HASH = hash_password("cubi-dummy-password-not-a-credential")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class IdentityService:
    """Authoritative login, logout and session resolution boundary."""

    def __init__(
        self,
        store: IdentityStore,
        *,
        csrf_secret: str,
        now: Any | None = None,
        session_ttl: timedelta = DEFAULT_SESSION_TTL,
        idle_timeout: timedelta = DEFAULT_IDLE_TIMEOUT,
        max_email_failures: int = DEFAULT_MAX_EMAIL_FAILURES,
        max_ip_failures: int = DEFAULT_MAX_IP_FAILURES,
        failure_window: timedelta = DEFAULT_FAILURE_WINDOW,
    ) -> None:
        if len(csrf_secret) < 32:
            raise IdentityError("CSRF_SECRET_TOO_SHORT")
        if session_ttl <= timedelta(0) or idle_timeout <= timedelta(0):
            raise IdentityError("SESSION_TTL_INVALID")
        self._store = store
        self._csrf_secret = csrf_secret
        self._clock = now or (lambda: datetime.now(timezone.utc))
        self._session_ttl = session_ttl
        self._idle_timeout = idle_timeout
        self._max_email_failures = max_email_failures
        self._max_ip_failures = max_ip_failures
        self._failure_window = failure_window

    @property
    def store(self) -> IdentityStore:
        return self._store

    def login(self, email: str, password: str, *, ip_hash: str = "") -> IssuedSession:
        attempted_at = _as_utc(self._clock())
        try:
            normalized = normalize_email(email)
        except IdentityError:
            # Never reveal whether the address exists or is malformed.
            verify_password(password if isinstance(password, str) else "", _DUMMY_HASH)
            raise IdentityError("AUTHENTICATION_FAILED") from None
        since = attempted_at - self._failure_window
        email_failures, ip_failures = self._store.count_failures(
            email=normalized, ip_hash=ip_hash, since=since
        )
        if email_failures >= self._max_email_failures or ip_failures >= self._max_ip_failures:
            raise IdentityError("AUTHENTICATION_THROTTLED")
        user = self._store.find_user_by_email(normalized)
        valid = False
        if user is not None and user.active:
            valid = verify_password(password, user.password_hash)
        else:
            # Spend comparable time on an unknown account so response timing
            # does not disclose account existence.
            verify_password(password if isinstance(password, str) else "", _DUMMY_HASH)
        self._store.record_attempt(
            email=normalized,
            tenant_id=user.tenant_id if user is not None else None,
            ip_hash=ip_hash,
            attempted_at=attempted_at,
            succeeded=valid,
        )
        if not valid or user is None:
            raise IdentityError("AUTHENTICATION_FAILED")
        token = new_session_token()
        session = StoredSession(
            token_hash=token_hash(token),
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            roles=user.roles,
            created_at=attempted_at,
            last_seen_at=attempted_at,
            expires_at=attempted_at + self._session_ttl,
        )
        self._store.save_session(session)
        # Opportunistic retention keeps the attempt table bounded without a
        # separate scheduler.
        self._store.delete_attempts_before(attempted_at - (self._failure_window * 8))
        return IssuedSession(
            token=token,
            csrf_token=csrf_token(self._csrf_secret, token),
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            roles=user.roles,
            created_at=attempted_at,
            expires_at=session.expires_at,
        )

    def logout(self, token: str) -> bool:
        try:
            hashed = token_hash(token)
        except IdentityError:
            return False
        return self._store.revoke_session(hashed, when=_as_utc(self._clock()))

    def resolve(self, token: str) -> AuthenticatedSession | None:
        """Resolve an opaque cookie token, enforcing absolute and idle expiry."""
        try:
            hashed = token_hash(token)
        except IdentityError:
            return None
        now = _as_utc(self._clock())
        stored = self._store.load_session(hashed, now=now)
        if stored is None:
            return None
        if stored.revoked_at is not None or now >= stored.expires_at:
            self._store.revoke_session(hashed, when=now)
            return None
        if now - stored.last_seen_at >= self._idle_timeout:
            self._store.revoke_session(hashed, when=now)
            return None
        if now - stored.last_seen_at >= TOUCH_INTERVAL:
            self._store.touch_session(hashed, when=now)
        return AuthenticatedSession(
            session_id=token,
            user_id=stored.user_id,
            tenant_id=stored.tenant_id,
            roles=stored.roles,
            expires_at=stored.expires_at,
        )

    def csrf_for(self, token: str) -> str:
        return csrf_token(self._csrf_secret, token)

    def verify_csrf(self, token: str, candidate: str | None) -> bool:
        if not isinstance(candidate, str) or not candidate:
            return False
        expected = csrf_token(self._csrf_secret, token)
        return hmac.compare_digest(expected, candidate)


class IdentitySessionRepository:
    """SessionRepository adapter backed by the persisted identity sessions.

    The lifecycle service receives the cookie token as its session id; this
    adapter hashes it, enforces expiry and writes the idle-touch timestamp.
    """

    def __init__(self, identity: IdentityService) -> None:
        self._identity = identity

    def get(self, session_id: str) -> AuthenticatedSession | None:
        return self._identity.resolve(session_id)


class _SqlIdentityStore:
    """Shared SQL behaviour for the SQLite and PostgreSQL identity stores."""

    placeholder = "?"
    now_type = "text"

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    # -- DDL ---------------------------------------------------------------
    def initialize(self) -> None:
        raise NotImplementedError

    # -- queries -----------------------------------------------------------
    def _one(self, sql: str, params: tuple[Any, ...]) -> Any:
        return self.connection.execute(sql, params).fetchone()

    def _all(self, sql: str, params: tuple[Any, ...]) -> list[Any]:
        return list(self.connection.execute(sql, params).fetchall())

    def find_user_by_email(self, email: str) -> IdentityUser | None:
        row = self._one(
            "SELECT user_id, tenant_id, email, display_name, roles_json, "
            f"password_hash, active FROM identity_users WHERE lower(email)={self.placeholder}",
            (email.lower(),),
        )
        if row is None:
            return None
        roles = json.loads(row[4])
        if not isinstance(roles, list):
            raise IdentityError("INVALID_ROLES")
        return IdentityUser(
            user_id=str(row[0]),
            tenant_id=str(row[1]),
            email=str(row[2]),
            display_name=str(row[3] or ""),
            roles=validate_role_tokens(roles),
            password_hash=str(row[5]),
            active=bool(row[6]),
        )

    def record_attempt(
        self,
        *,
        email: str,
        tenant_id: str | None,
        ip_hash: str,
        attempted_at: datetime,
        succeeded: bool,
    ) -> None:
        self.connection.execute(
            "INSERT INTO identity_login_attempts "
            "(email, tenant_id, ip_hash, attempted_at, succeeded) "
            f"VALUES ({self.placeholder}, {self.placeholder}, {self.placeholder}, "
            f"{self.placeholder}, {self.placeholder})",
            (email, tenant_id, ip_hash, attempted_at.isoformat(), succeeded),
        )

    def count_failures(
        self, *, email: str, ip_hash: str, since: datetime
    ) -> tuple[int, int]:
        email_row = self._one(
            "SELECT COUNT(*) FROM identity_login_attempts "
            f"WHERE email={self.placeholder} AND succeeded={self.placeholder} "
            f"AND attempted_at>={self.placeholder}",
            (email, False, since.isoformat()),
        )
        ip_row = self._one(
            "SELECT COUNT(*) FROM identity_login_attempts "
            f"WHERE ip_hash={self.placeholder} AND succeeded={self.placeholder} "
            f"AND attempted_at>={self.placeholder}",
            (ip_hash, False, since.isoformat()),
        )
        return int(email_row[0] if email_row else 0), int(ip_row[0] if ip_row else 0)

    def save_session(self, session: StoredSession) -> None:
        self.connection.execute(
            "INSERT INTO identity_sessions "
            "(token_hash, user_id, tenant_id, roles_json, created_at, last_seen_at, expires_at) "
            f"VALUES ({self.placeholder}, {self.placeholder}, {self.placeholder}, "
            f"{self.placeholder}, {self.placeholder}, {self.placeholder}, {self.placeholder})",
            (
                session.token_hash,
                session.user_id,
                session.tenant_id,
                json.dumps(sorted(session.roles), separators=(",", ":")),
                session.created_at.isoformat(),
                session.last_seen_at.isoformat(),
                session.expires_at.isoformat(),
            ),
        )

    def load_session(self, hashed: str, *, now: datetime) -> StoredSession | None:
        row = self._one(
            "SELECT user_id, tenant_id, roles_json, created_at, last_seen_at, "
            "expires_at, revoked_at FROM identity_sessions "
            f"WHERE token_hash={self.placeholder}",
            (hashed,),
        )
        if row is None:
            return None
        roles = json.loads(row[2])
        if not isinstance(roles, list):
            raise IdentityError("INVALID_ROLES")
        return StoredSession(
            token_hash=hashed,
            user_id=str(row[0]),
            tenant_id=str(row[1]),
            roles=validate_role_tokens(roles),
            created_at=_parse_time(row[3]),
            last_seen_at=_parse_time(row[4]),
            expires_at=_parse_time(row[5]),
            revoked_at=_parse_time(row[6]) if row[6] else None,
        )

    def touch_session(self, hashed: str, *, when: datetime) -> None:
        self.connection.execute(
            "UPDATE identity_sessions SET last_seen_at="
            f"{self.placeholder} WHERE token_hash={self.placeholder}",
            (when.isoformat(), hashed),
        )

    def revoke_session(self, hashed: str, *, when: datetime) -> bool:
        row = self.connection.execute(
            "UPDATE identity_sessions SET revoked_at="
            f"{self.placeholder} WHERE token_hash={self.placeholder} "
            "AND revoked_at IS NULL RETURNING token_hash",
            (when.isoformat(), hashed),
        ).fetchone()
        return row is not None

    def delete_attempts_before(self, cutoff: datetime) -> None:
        self.connection.execute(
            "DELETE FROM identity_login_attempts WHERE attempted_at<"
            f"{self.placeholder}",
            (cutoff.isoformat(),),
        )


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return _as_utc(value)
    return _as_utc(datetime.fromisoformat(str(value)))


class SQLiteIdentityStore(_SqlIdentityStore):
    """SQLite identity store used by unit tests and the local preview harness."""

    def initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS identity_users (
                user_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                email TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT '',
                roles_json TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                password_changed_at TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS identity_users_email_unique
                ON identity_users (lower(email));
            CREATE TABLE IF NOT EXISTS identity_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                roles_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT
            );
            CREATE INDEX IF NOT EXISTS identity_sessions_user
                ON identity_sessions (user_id);
            CREATE TABLE IF NOT EXISTS identity_login_attempts (
                attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                tenant_id TEXT,
                ip_hash TEXT NOT NULL DEFAULT '',
                attempted_at TEXT NOT NULL,
                succeeded INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS identity_attempts_email
                ON identity_login_attempts (email, attempted_at);
            """
        )
        self.connection.commit()

    def upsert_user(self, user: IdentityUser) -> None:
        self.connection.execute(
            "INSERT INTO identity_users "
            "(user_id, tenant_id, email, display_name, roles_json, password_hash, "
            "active, created_at, password_changed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now')) "
            "ON CONFLICT(user_id) DO UPDATE SET tenant_id=excluded.tenant_id, "
            "email=excluded.email, display_name=excluded.display_name, "
            "roles_json=excluded.roles_json, password_hash=excluded.password_hash, "
            "active=excluded.active, password_changed_at=datetime('now')",
            (
                user.user_id,
                user.tenant_id,
                user.email,
                user.display_name,
                json.dumps(sorted(user.roles), separators=(",", ":")),
                user.password_hash,
                1 if user.active else 0,
            ),
        )
        self.connection.commit()


class PostgresIdentityStore(_SqlIdentityStore):
    """Durable identity store for the production (Vercel) runtime."""

    placeholder = "%s"

    def initialize(self) -> None:
        for statement in (
            """
            CREATE TABLE IF NOT EXISTS identity_users (
                user_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                email TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT '',
                roles_json TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                password_changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """,
            "CREATE UNIQUE INDEX IF NOT EXISTS identity_users_email_unique "
            "ON identity_users (lower(email))",
            """
            CREATE TABLE IF NOT EXISTS identity_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                roles_json TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                last_seen_at TIMESTAMPTZ NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                revoked_at TIMESTAMPTZ
            )
            """,
            "CREATE INDEX IF NOT EXISTS identity_sessions_user "
            "ON identity_sessions (user_id)",
            "CREATE INDEX IF NOT EXISTS identity_sessions_expiry "
            "ON identity_sessions (expires_at)",
            """
            CREATE TABLE IF NOT EXISTS identity_login_attempts (
                attempt_id BIGSERIAL PRIMARY KEY,
                email TEXT NOT NULL,
                tenant_id TEXT,
                ip_hash TEXT NOT NULL DEFAULT '',
                attempted_at TIMESTAMPTZ NOT NULL,
                succeeded BOOLEAN NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS identity_attempts_email "
            "ON identity_login_attempts (email, attempted_at)",
            "CREATE INDEX IF NOT EXISTS identity_attempts_ip "
            "ON identity_login_attempts (ip_hash, attempted_at)",
        ):
            self.connection.execute(statement)

    def upsert_user(self, user: IdentityUser) -> None:
        self.connection.execute(
            "INSERT INTO identity_users "
            "(user_id, tenant_id, email, display_name, roles_json, password_hash, active) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT(user_id) DO UPDATE SET tenant_id=excluded.tenant_id, "
            "email=excluded.email, display_name=excluded.display_name, "
            "roles_json=excluded.roles_json, password_hash=excluded.password_hash, "
            "active=excluded.active, password_changed_at=now()",
            (
                user.user_id,
                user.tenant_id,
                user.email,
                user.display_name,
                json.dumps(sorted(user.roles), separators=(",", ":")),
                user.password_hash,
                user.active,
            ),
        )


def hash_client_ip(secret: str, client_ip: str) -> str:
    """Pseudonymous key for throttling; raw addresses are not stored."""
    if not client_ip:
        return ""
    return hmac.new(
        secret.encode("utf-8"), client_ip.encode("utf-8"), hashlib.sha256
    ).hexdigest()[:32]


def session_cookie_header(
    *,
    name: str,
    value: str,
    max_age: int,
    secure: bool,
    same_site: str = "Lax",
) -> str:
    parts = [f"{name}={value}", "Path=/", "HttpOnly", f"SameSite={same_site}"]
    if secure:
        parts.append("Secure")
    parts.append(f"Max-Age={max_age}")
    return "; ".join(parts)


def csrf_cookie_header(
    *, name: str, value: str, max_age: int, secure: bool
) -> str:
    parts = [f"{name}={quote(value)}", "Path=/", f"SameSite=Lax"]
    if secure:
        parts.append("Secure")
    parts.append(f"Max-Age={max_age}")
    return "; ".join(parts)


def clear_cookie_header(*, name: str, secure: bool) -> str:
    parts = [f"{name}=", "Path=/", "HttpOnly", "SameSite=Lax", "Max-Age=0"]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def clear_csrf_cookie_header(*, name: str, secure: bool) -> str:
    parts = [f"{name}=", "Path=/", "SameSite=Lax", "Max-Age=0"]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def load_identity_settings(environment: Mapping[str, str]) -> dict[str, Any]:
    """Read and validate the non-secret production identity settings."""
    secret = environment.get("CONSTRUCTION_PM_SESSION_SECRET", "").strip()
    origin = environment.get("CONSTRUCTION_PM_PUBLIC_ORIGIN", "").strip().rstrip("/")
    # An HTTPS deployment can never be talked into an insecure cookie: the
    # escape hatch below exists only for a loopback HTTP harness.
    secure = True
    if not origin.startswith("https://"):
        secure = environment.get("CONSTRUCTION_PM_INSECURE_COOKIES", "").strip() not in {
            "1",
            "true",
            "yes",
        }
    return {
        "csrf_secret": secret,
        "secure_cookies": secure,
        "public_origin": origin,
    }
