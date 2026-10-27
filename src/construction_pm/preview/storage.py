from __future__ import annotations

"""Guarded SQLite storage and demo-session lifecycle for the local preview.

The preview database is deliberately identifiable. A reset never guesses: it
refuses unknown files, backs up a recognised preview database first, and then
atomically replaces it with a freshly seeded database.
"""

import json
import os
import secrets
import shutil
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable, Mapping

from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectSummary,
)
from construction_pm.backend_p0.models import BackendScope

PREVIEW_APPLICATION_ID = 0x43554249  # "CUBI"
PREVIEW_SCHEMA_VERSION = 1
PREVIEW_SEED_VERSION = "cubi-preview-seed.v1"
PREVIEW_APPLICATION_MARKER = "cubi-local-preview"
PREVIEW_TENANT_ID = "cubi-preview-tenant"
PREVIEW_SESSION_TTL = timedelta(hours=8)


class PreviewDatabaseError(ValueError):
    """Raised when a preview database cannot be safely opened or reset."""

    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True)
class DemoUser:
    user_id: str
    label_en: str
    label_fa: str
    role: str
    roles: frozenset[str]


DEMO_USERS: tuple[DemoUser, ...] = (
    DemoUser(
        "preview-planner",
        "Planner",
        "برنامه‌ریز",
        "planner",
        frozenset({"planner"}),
    ),
    DemoUser(
        "preview-viewer",
        "Viewer",
        "بازبین",
        "viewer",
        frozenset({"viewer"}),
    ),
    DemoUser(
        "preview-admin",
        "Project administrator",
        "مدیر پروژه",
        "admin",
        frozenset({"project_admin"}),
    ),
    # A real account with no project membership. It exercises the first-run
    # creation path against the same authorization policy and project store;
    # it is never added to the seeded fixtures or to other users' projects.
    DemoUser(
        "preview-newcomer",
        "New account (no projects)",
        "حساب تازه (بدون پروژه)",
        "newcomer",
        frozenset({"project_admin"}),
    ),
)
DEMO_USERS_BY_ROLE: Mapping[str, DemoUser] = {
    user.role: user for user in DEMO_USERS
}
DEMO_USER_IDS: tuple[str, ...] = tuple(user.user_id for user in DEMO_USERS)
# Membership of the demo fixtures and of projects created by other demo roles.
# The newcomer stays outside so its first-run state is genuine.
DEMO_PROJECT_MEMBER_USER_IDS: tuple[str, ...] = tuple(
    user.user_id for user in DEMO_USERS if user.role != "newcomer"
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _connect(database: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        database,
        check_same_thread=False,
        timeout=10.0,
    )
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def _meta_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS preview_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )"""
    )


def _set_meta(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        "INSERT INTO preview_meta(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def _mark_seeded(connection: sqlite3.Connection) -> None:
    _meta_table(connection)
    _set_meta(connection, "application", PREVIEW_APPLICATION_MARKER)
    _set_meta(connection, "seed_version", PREVIEW_SEED_VERSION)
    _set_meta(connection, "schema_version", str(PREVIEW_SCHEMA_VERSION))
    _set_meta(connection, "seeded_at", utc_now().isoformat())
    connection.commit()


def _verify_owned_database(database: Path) -> None:
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(database)
        application_id = int(
            connection.execute("PRAGMA application_id").fetchone()[0]
        )
        if application_id != PREVIEW_APPLICATION_ID:
            raise PreviewDatabaseError(
                "PREVIEW_DATABASE_NOT_OWNED",
                "The selected database is not a CUBI preview database.",
            )
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='preview_meta'"
        ).fetchone()
        if row is None:
            raise PreviewDatabaseError(
                "PREVIEW_DATABASE_NOT_OWNED",
                "The selected database has no CUBI preview marker.",
            )
        meta = {
            str(key): str(value)
            for key, value in connection.execute(
                "SELECT key, value FROM preview_meta"
            ).fetchall()
        }
        if meta.get("application") != PREVIEW_APPLICATION_MARKER:
            raise PreviewDatabaseError(
                "PREVIEW_DATABASE_NOT_OWNED",
                "The selected database belongs to another application.",
            )
        if meta.get("seed_version") != PREVIEW_SEED_VERSION:
            raise PreviewDatabaseError(
                "PREVIEW_DATABASE_STALE_SEED",
                "The preview seed version is stale; rerun with --reset to create "
                "a backed-up, freshly seeded demo database.",
            )
    except PreviewDatabaseError:
        raise
    except sqlite3.DatabaseError as exc:
        raise PreviewDatabaseError(
            "PREVIEW_DATABASE_UNREADABLE",
            "The selected database cannot be read as SQLite.",
        ) from exc
    finally:
        if connection is not None:
            connection.close()


def _backup_database(database: Path) -> Path:
    backups = database.parent / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    backup = backups / f"{database.stem}-{stamp}.sqlite3"
    suffix = 1
    while backup.exists():
        backup = backups / f"{database.stem}-{stamp}-{suffix}.sqlite3"
        suffix += 1
    source = sqlite3.connect(database)
    try:
        target = sqlite3.connect(backup)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()
    return backup


def _build_fresh_database(
    database: Path,
    *,
    seed: Callable[[sqlite3.Connection], None],
) -> None:
    database.parent.mkdir(parents=True, exist_ok=True)
    temporary = database.with_name(
        f".{database.name}.tmp-{secrets.token_hex(8)}"
    )
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(temporary)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute(f"PRAGMA application_id = {PREVIEW_APPLICATION_ID}")
        connection.execute(f"PRAGMA user_version = {PREVIEW_SCHEMA_VERSION}")
        seed(connection)
        _mark_seeded(connection)
        connection.commit()
        connection.close()
        connection = None
        os.replace(temporary, database)
    except BaseException:
        if connection is not None:
            connection.close()
        for candidate in (temporary, Path(str(temporary) + "-journal")):
            try:
                candidate.unlink()
            except FileNotFoundError:
                pass
        raise


def open_preview_database(
    database: Path,
    *,
    seed: Callable[[sqlite3.Connection], None],
    reset: bool = False,
) -> sqlite3.Connection:
    """Open a guarded preview database, creating or resetting it safely."""

    database = Path(database).expanduser().resolve()
    if database.exists() and database.stat().st_size > 0:
        _verify_owned_database(database)
        if reset:
            _backup_database(database)
            _build_fresh_database(database, seed=seed)
    else:
        _build_fresh_database(database, seed=seed)
    connection = _connect(database)
    return connection


class PreviewSessionRepository:
    """In-memory opaque demo sessions; no password or production identity."""

    def __init__(self) -> None:
        self._sessions: dict[str, AuthenticatedSession] = {}
        self._lock = threading.RLock()

    def create(
        self,
        user: DemoUser,
        *,
        ttl: timedelta = PREVIEW_SESSION_TTL,
        now: datetime | None = None,
    ) -> AuthenticatedSession:
        created_at = now or utc_now()
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise ValueError("SESSION_CLOCK_MUST_BE_TIMEZONE_AWARE")
        session = AuthenticatedSession(
            session_id=secrets.token_urlsafe(32),
            user_id=user.user_id,
            tenant_id=PREVIEW_TENANT_ID,
            roles=user.roles,
            expires_at=created_at + ttl,
        )
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> AuthenticatedSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if session.expires_at <= utc_now():
                self._sessions.pop(session_id, None)
                return None
            return session

    def active_for_user(self, user_id: str) -> AuthenticatedSession | None:
        """Return a current server-held session for this exact demo user, if any."""
        if not isinstance(user_id, str) or not user_id.strip():
            return None
        now = utc_now()
        with self._lock:
            expired = [
                session_id for session_id, session in self._sessions.items()
                if session.expires_at <= now
            ]
            for session_id in expired:
                self._sessions.pop(session_id, None)
            candidates = [
                session for session in self._sessions.values()
                if session.user_id == user_id and session.expires_at > now
            ]
            return max(candidates, key=lambda session: session.expires_at, default=None)

    def revoke(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def count(self) -> int:
        with self._lock:
            return len(self._sessions)


class PreviewStore:
    """Demo project/membership persistence kept separate from domain records."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS preview_project (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                wbs_json TEXT NOT NULL,
                demo INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id)
            );
            CREATE TABLE IF NOT EXISTS preview_project_member (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, user_id),
                FOREIGN KEY (tenant_id, project_id)
                    REFERENCES preview_project(tenant_id, project_id)
                    ON DELETE CASCADE
            );
            """
        )
        self.connection.commit()

    def project_exists(self, tenant_id: str, project_id: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM preview_project WHERE tenant_id=? AND project_id=?",
            (tenant_id, project_id),
        ).fetchone()
        return row is not None

    def insert_project(
        self,
        *,
        tenant_id: str,
        project_id: str,
        name: str,
        revision: int,
        wbs_by_activity: Mapping[str, str],
        demo: bool,
        created_at: datetime,
    ) -> None:
        if not tenant_id.strip() or not project_id.strip() or not name.strip():
            raise ValueError("PREVIEW_PROJECT_IDENTITY_REQUIRED")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
            raise ValueError("PREVIEW_PROJECT_REVISION_INVALID")
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise ValueError("PREVIEW_PROJECT_CLOCK_MUST_BE_TIMEZONE_AWARE")
        wbs = {
            str(key): str(value)
            for key, value in wbs_by_activity.items()
            if isinstance(key, str) and key.strip() and isinstance(value, str)
        }
        owns_transaction = not self.connection.in_transaction
        self.connection.execute(
            "INSERT INTO preview_project "
            "(tenant_id, project_id, name, project_revision, wbs_json, demo, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                tenant_id,
                project_id,
                name,
                revision,
                json.dumps(wbs, ensure_ascii=False, sort_keys=True),
                1 if demo else 0,
                created_at.isoformat(),
            ),
        )
        if owns_transaction:
            self.connection.commit()

    def add_members(
        self,
        tenant_id: str,
        project_id: str,
        user_ids: Iterable[str],
    ) -> None:
        owns_transaction = not self.connection.in_transaction
        for user_id in sorted(set(user_ids)):
            if not isinstance(user_id, str) or not user_id.strip():
                continue
            self.connection.execute(
                "INSERT OR IGNORE INTO preview_project_member "
                "(tenant_id, project_id, user_id) VALUES (?,?,?)",
                (tenant_id, project_id, user_id),
            )
        if owns_transaction:
            self.connection.commit()

    def list_for_user(
        self, tenant_id: str, user_id: str
    ) -> tuple[ProjectSummary, ...]:
        rows = self.connection.execute(
            "SELECT p.project_id, p.tenant_id, p.name, p.project_revision "
            "FROM preview_project p "
            "JOIN preview_project_member m "
            "ON m.tenant_id=p.tenant_id AND m.project_id=p.project_id "
            "WHERE p.tenant_id=? AND m.user_id=? "
            "ORDER BY p.name COLLATE NOCASE, p.project_id",
            (tenant_id, user_id),
        ).fetchall()
        return tuple(
            ProjectSummary(
                project_id=str(row[0]),
                tenant_id=str(row[1]),
                name=str(row[2]),
                revision=int(row[3]),
            )
            for row in rows
        )

    def get_for_user(
        self, tenant_id: str, project_id: str, user_id: str
    ) -> ProjectSummary | None:
        row = self.connection.execute(
            "SELECT p.project_id, p.tenant_id, p.name, p.project_revision "
            "FROM preview_project p "
            "JOIN preview_project_member m "
            "ON m.tenant_id=p.tenant_id AND m.project_id=p.project_id "
            "WHERE p.tenant_id=? AND p.project_id=? AND m.user_id=?",
            (tenant_id, project_id, user_id),
        ).fetchone()
        if row is None:
            return None
        return ProjectSummary(
            project_id=str(row[0]),
            tenant_id=str(row[1]),
            name=str(row[2]),
            revision=int(row[3]),
        )

    def project_rows(self) -> tuple[dict[str, object], ...]:
        rows = self.connection.execute(
            "SELECT tenant_id, project_id, name, project_revision, demo, created_at "
            "FROM preview_project ORDER BY name COLLATE NOCASE, project_id"
        ).fetchall()
        return tuple(
            {
                "tenant_id": str(row[0]),
                "project_id": str(row[1]),
                "name": str(row[2]),
                "revision": int(row[3]),
                "demo": bool(row[4]),
                "created_at": str(row[5]),
            }
            for row in rows
        )

    def wbs_for(self, tenant_id: str, project_id: str) -> dict[str, str]:
        row = self.connection.execute(
            "SELECT wbs_json FROM preview_project WHERE tenant_id=? AND project_id=?",
            (tenant_id, project_id),
        ).fetchone()
        if row is None:
            return {}
        try:
            parsed = json.loads(str(row[0]))
        except json.JSONDecodeError as exc:
            raise ValueError("PREVIEW_WBS_INVALID") from exc
        if not isinstance(parsed, dict):
            raise ValueError("PREVIEW_WBS_INVALID")
        result: dict[str, str] = {}
        for key, value in parsed.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("PREVIEW_WBS_INVALID")
            result[key] = value
        return result

    def set_wbs_for(
        self,
        tenant_id: str,
        project_id: str,
        wbs_by_activity: Mapping[str, str],
    ) -> None:
        if not tenant_id.strip() or not project_id.strip():
            raise ValueError("PREVIEW_WBS_SCOPE_REQUIRED")
        if not isinstance(wbs_by_activity, Mapping):
            raise ValueError("PREVIEW_WBS_INVALID")
        normalized: dict[str, str] = {}
        for activity_id, wbs in wbs_by_activity.items():
            if (
                not isinstance(activity_id, str) or not activity_id.strip()
                or not isinstance(wbs, str) or not wbs.strip()
            ):
                raise ValueError("PREVIEW_WBS_INVALID")
            normalized[activity_id.strip()] = wbs.strip()
        encoded = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
        owns_transaction = not self.connection.in_transaction
        cursor = self.connection.execute(
            "UPDATE preview_project SET wbs_json=? WHERE tenant_id=? AND project_id=?",
            (encoded, tenant_id, project_id),
        )
        if cursor.rowcount != 1:
            if owns_transaction:
                self.connection.rollback()
            raise ValueError("PREVIEW_PROJECT_NOT_FOUND")
        if owns_transaction:
            self.connection.commit()
        if self.wbs_for(tenant_id, project_id) != normalized:
            raise ValueError("PREVIEW_WBS_READBACK_MISMATCH")

    def counts(self, tenant_id: str, project_id: str) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) FROM activity_master "
            "WHERE tenant_id=? AND project_id=?",
            (tenant_id, project_id),
        ).fetchone()
        return 0 if row is None else int(row[0])


class PreviewProjectRepository:
    """Project lifecycle repository backed by preview demo metadata."""

    def __init__(
        self,
        store: PreviewStore,
        *,
        initializer: Callable[[BackendScope], None],
        member_user_ids: Iterable[str] = DEMO_USER_IDS,
    ) -> None:
        self.store = store
        self.initializer = initializer
        self.member_user_ids = tuple(member_user_ids)

    def list_for_user(
        self, tenant_id: str, user_id: str
    ) -> tuple[ProjectSummary, ...]:
        return self.store.list_for_user(tenant_id, user_id)

    def get_for_user(
        self, tenant_id: str, project_id: str, user_id: str
    ) -> ProjectSummary | None:
        return self.store.get_for_user(tenant_id, project_id, user_id)

    def create_for_user(
        self, tenant_id: str, user_id: str, project_id: str, name: str
    ) -> ProjectSummary:
        if self.store.project_exists(tenant_id, project_id):
            raise ValueError("PROJECT_ALREADY_EXISTS")
        scope = BackendScope(tenant_id, project_id, 0)
        # Initialise presentation and calendar metadata before publishing the
        # project to the lifecycle boundary. A failure therefore never exposes a
        # half-created project in the browser.
        self.initializer(scope)
        created_at = utc_now()
        self.store.insert_project(
            tenant_id=tenant_id,
            project_id=project_id,
            name=name,
            revision=0,
            wbs_by_activity={},
            demo=False,
            created_at=created_at,
        )
        self.store.add_members(
            tenant_id,
            project_id,
            (user_id, *self.member_user_ids),
        )
        return ProjectSummary(
            project_id=project_id,
            tenant_id=tenant_id,
            name=name,
            revision=0,
        )


__all__ = [
    "DEMO_PROJECT_MEMBER_USER_IDS",
    "DEMO_USERS",
    "DEMO_USERS_BY_ROLE",
    "DEMO_USER_IDS",
    "DemoUser",
    "PREVIEW_APPLICATION_ID",
    "PREVIEW_SEED_VERSION",
    "PREVIEW_SESSION_TTL",
    "PREVIEW_TENANT_ID",
    "PreviewDatabaseError",
    "PreviewProjectRepository",
    "PreviewSessionRepository",
    "PreviewStore",
    "open_preview_database",
    "utc_now",
]
