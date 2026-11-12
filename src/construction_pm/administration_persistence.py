"""Project administration preferences, dictionaries and their audit trail.

Administration facts are project-scoped: one revision-guarded preference record
per project and a code-namespaced dictionary whose entries carry their own
revision. Every accepted write appends an immutable audit event and creates are
idempotent. Role grants are not stored here; they are read from the single
authorization policy so the administration screen cannot drift from enforcement.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

PREFERENCE_DEFAULTS = {
    "currency": "USD",
    "unit_of_measure": "day",
    "date_display": "gregorian",
    "decimal_places": 2,
    "fiscal_year_start_month": 1,
}

DATE_DISPLAY_VALUES = ("gregorian", "jalali")

DICTIONARY_CODES = (
    "cost_category",
    "risk_category",
    "issue_type",
    "document_type",
    "expense_category",
)


class AdministrationPersistenceError(ValueError):
    """Raised when an administration fact violates its contract."""


class AdministrationRevisionConflict(AdministrationPersistenceError):
    """Raised when a write carries a stale record revision."""


class AdministrationIdempotencyReuse(AdministrationPersistenceError):
    """Raised when an idempotency key is reused for different content."""


def _required_text(value: object, code: str, maximum: int = 120) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AdministrationPersistenceError(code)
    if len(value) > maximum:
        raise AdministrationPersistenceError(code)
    return value.strip()


def _iso(occurred_at: datetime) -> str:
    if not isinstance(occurred_at, datetime) or occurred_at.tzinfo is None:
        raise AdministrationPersistenceError("INVALID_ADMIN_OCCURRED_AT")
    return occurred_at.isoformat()


def _actor(actor_id: str) -> str:
    return _required_text(actor_id, "INVALID_ADMIN_ACTOR")


@dataclass(frozen=True)
class AdministrationPreferences:
    tenant_id: str
    project_id: str
    currency: str = PREFERENCE_DEFAULTS["currency"]
    unit_of_measure: str = PREFERENCE_DEFAULTS["unit_of_measure"]
    date_display: str = PREFERENCE_DEFAULTS["date_display"]
    decimal_places: int = PREFERENCE_DEFAULTS["decimal_places"]
    fiscal_year_start_month: int = PREFERENCE_DEFAULTS["fiscal_year_start_month"]
    revision: int = 0
    updated_at: str | None = None
    updated_by: str | None = None

    def validate(self) -> None:
        _required_text(self.tenant_id, "INVALID_ADMIN_TENANT")
        _required_text(self.project_id, "INVALID_ADMIN_PROJECT")
        currency = _required_text(self.currency, "INVALID_ADMIN_CURRENCY", 3)
        if len(currency) != 3 or not currency.isalpha() or not currency.isupper():
            raise AdministrationPersistenceError("INVALID_ADMIN_CURRENCY")
        _required_text(self.unit_of_measure, "INVALID_ADMIN_UNIT", 20)
        if self.date_display not in DATE_DISPLAY_VALUES:
            raise AdministrationPersistenceError("INVALID_ADMIN_DATE_DISPLAY")
        if isinstance(self.decimal_places, bool) or not isinstance(
            self.decimal_places, int
        ):
            raise AdministrationPersistenceError("INVALID_ADMIN_DECIMAL_PLACES")
        if not 0 <= self.decimal_places <= 4:
            raise AdministrationPersistenceError("INVALID_ADMIN_DECIMAL_PLACES")
        if isinstance(self.fiscal_year_start_month, bool) or not isinstance(
            self.fiscal_year_start_month, int
        ):
            raise AdministrationPersistenceError("INVALID_ADMIN_FISCAL_MONTH")
        if not 1 <= self.fiscal_year_start_month <= 12:
            raise AdministrationPersistenceError("INVALID_ADMIN_FISCAL_MONTH")
        if not isinstance(self.revision, int) or self.revision < 0:
            raise AdministrationPersistenceError("INVALID_ADMIN_REVISION")

    def as_dict(self) -> dict[str, Any]:
        return {
            "currency": self.currency,
            "unit_of_measure": self.unit_of_measure,
            "date_display": self.date_display,
            "decimal_places": self.decimal_places,
            "fiscal_year_start_month": self.fiscal_year_start_month,
            "revision": self.revision,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }


@dataclass(frozen=True)
class DictionaryEntry:
    tenant_id: str
    project_id: str
    dictionary_code: str
    entry_id: str
    label: str
    sequence: int = 0
    is_active: bool = True
    revision: int = 1
    updated_at: str | None = None
    updated_by: str | None = None

    def validate(self) -> None:
        _required_text(self.tenant_id, "INVALID_ADMIN_TENANT")
        _required_text(self.project_id, "INVALID_ADMIN_PROJECT")
        if self.dictionary_code not in DICTIONARY_CODES:
            raise AdministrationPersistenceError("INVALID_ADMIN_DICTIONARY_CODE")
        entry_id = _required_text(
            self.entry_id, "INVALID_ADMIN_DICTIONARY_ENTRY", 32
        )
        if not all(
            character.isalnum() or character in "_-" for character in entry_id
        ):
            raise AdministrationPersistenceError("INVALID_ADMIN_DICTIONARY_ENTRY")
        _required_text(self.label, "INVALID_ADMIN_DICTIONARY_LABEL", 80)
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int):
            raise AdministrationPersistenceError("INVALID_ADMIN_SEQUENCE")
        if not 0 <= self.sequence <= 9999:
            raise AdministrationPersistenceError("INVALID_ADMIN_SEQUENCE")
        if not isinstance(self.is_active, bool):
            raise AdministrationPersistenceError("INVALID_ADMIN_ACTIVE")
        if not isinstance(self.revision, int) or self.revision < 1:
            raise AdministrationPersistenceError("INVALID_ADMIN_REVISION")

    def as_dict(self) -> dict[str, Any]:
        return {
            "dictionary_code": self.dictionary_code,
            "entry_id": self.entry_id,
            "label": self.label,
            "sequence": self.sequence,
            "is_active": self.is_active,
            "revision": self.revision,
            "updated_at": self.updated_at,
            "updated_by": self.updated_by,
        }


@dataclass(frozen=True)
class AdministrationAuditEvent:
    tenant_id: str
    project_id: str
    entity_kind: str
    entity_id: str
    action: str
    actor_id: str
    occurred_at: str
    revision: int
    details: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "entity_kind": self.entity_kind,
            "entity_id": self.entity_id,
            "action": self.action,
            "actor_id": self.actor_id,
            "occurred_at": self.occurred_at,
            "revision": self.revision,
            "details": self.details,
        }


class AdministrationStore(Protocol):
    def read_preferences(
        self, tenant_id: str, project_id: str
    ) -> AdministrationPreferences: ...

    def write_preferences(
        self,
        preferences: AdministrationPreferences,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> AdministrationPreferences: ...

    def list_dictionary(
        self,
        tenant_id: str,
        project_id: str,
        *,
        dictionary_code: str | None = None,
        search: str | None = None,
        include_inactive: bool = True,
    ) -> tuple[DictionaryEntry, ...]: ...

    def read_dictionary_entry(
        self, tenant_id: str, project_id: str, dictionary_code: str, entry_id: str
    ) -> DictionaryEntry: ...

    def create_dictionary_entry(
        self,
        entry: DictionaryEntry,
        *,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> DictionaryEntry: ...

    def update_dictionary_entry(
        self,
        entry: DictionaryEntry,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> DictionaryEntry: ...

    def delete_dictionary_entry(
        self,
        *,
        tenant_id: str,
        project_id: str,
        dictionary_code: str,
        entry_id: str,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> None: ...

    def audit_history(
        self, tenant_id: str, project_id: str
    ) -> tuple[AdministrationAuditEvent, ...]: ...


class SQLiteAdministrationStore:
    """SQLite implementation shared by the preview runtime and API tests."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")

    def initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS project_administration_preferences (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                currency TEXT NOT NULL,
                unit_of_measure TEXT NOT NULL,
                date_display TEXT NOT NULL,
                decimal_places INTEGER NOT NULL,
                fiscal_year_start_month INTEGER NOT NULL,
                revision INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id)
            );
            CREATE TABLE IF NOT EXISTS project_administration_dictionary (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                dictionary_code TEXT NOT NULL,
                entry_id TEXT NOT NULL,
                label TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                is_active INTEGER NOT NULL,
                revision INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, dictionary_code, entry_id)
            );
            CREATE TABLE IF NOT EXISTS project_administration_audit (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                entity_kind TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                action TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                revision INTEGER NOT NULL,
                details TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS project_administration_idempotency (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                response_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, idempotency_key)
            );
            """
        )
        self.connection.commit()

    def read_preferences(
        self, tenant_id: str, project_id: str
    ) -> AdministrationPreferences:
        row = self.connection.execute(
            """SELECT currency, unit_of_measure, date_display, decimal_places,
                      fiscal_year_start_month, revision, updated_at, updated_by
               FROM project_administration_preferences
               WHERE tenant_id = ? AND project_id = ?""",
            (tenant_id, project_id),
        ).fetchone()
        if row is None:
            return AdministrationPreferences(
                tenant_id=tenant_id, project_id=project_id
            )
        return AdministrationPreferences(
            tenant_id=tenant_id,
            project_id=project_id,
            currency=row[0],
            unit_of_measure=row[1],
            date_display=row[2],
            decimal_places=row[3],
            fiscal_year_start_month=row[4],
            revision=row[5],
            updated_at=row[6],
            updated_by=row[7],
        )

    def write_preferences(
        self,
        preferences: AdministrationPreferences,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> AdministrationPreferences:
        preferences.validate()
        actor = _actor(actor_id)
        stamp = _iso(occurred_at)
        if isinstance(expected_revision, bool) or not isinstance(
            expected_revision, int
        ):
            raise AdministrationPersistenceError("INVALID_ADMIN_REVISION")
        with self.connection:
            current = self.read_preferences(
                preferences.tenant_id, preferences.project_id
            )
            if current.revision != expected_revision:
                raise AdministrationRevisionConflict(
                    "ADMIN_PREFERENCES_REVISION_CONFLICT"
                )
            revision = current.revision + 1
            self.connection.execute(
                """INSERT INTO project_administration_preferences
                       (tenant_id, project_id, currency, unit_of_measure,
                        date_display, decimal_places, fiscal_year_start_month,
                        revision, updated_at, updated_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT (tenant_id, project_id) DO UPDATE SET
                       currency = excluded.currency,
                       unit_of_measure = excluded.unit_of_measure,
                       date_display = excluded.date_display,
                       decimal_places = excluded.decimal_places,
                       fiscal_year_start_month = excluded.fiscal_year_start_month,
                       revision = excluded.revision,
                       updated_at = excluded.updated_at,
                       updated_by = excluded.updated_by""",
                (
                    preferences.tenant_id,
                    preferences.project_id,
                    preferences.currency,
                    preferences.unit_of_measure,
                    preferences.date_display,
                    preferences.decimal_places,
                    preferences.fiscal_year_start_month,
                    revision,
                    stamp,
                    actor,
                ),
            )
            self._append_audit(
                preferences.tenant_id,
                preferences.project_id,
                "preferences",
                "project-preferences",
                "updated",
                actor,
                stamp,
                revision,
                "",
            )
        return AdministrationPreferences(
            tenant_id=preferences.tenant_id,
            project_id=preferences.project_id,
            currency=preferences.currency,
            unit_of_measure=preferences.unit_of_measure,
            date_display=preferences.date_display,
            decimal_places=preferences.decimal_places,
            fiscal_year_start_month=preferences.fiscal_year_start_month,
            revision=revision,
            updated_at=stamp,
            updated_by=actor,
        )

    def list_dictionary(
        self,
        tenant_id: str,
        project_id: str,
        *,
        dictionary_code: str | None = None,
        search: str | None = None,
        include_inactive: bool = True,
    ) -> tuple[DictionaryEntry, ...]:
        if dictionary_code is not None and dictionary_code not in DICTIONARY_CODES:
            raise AdministrationPersistenceError("INVALID_ADMIN_DICTIONARY_CODE")
        query = (
            """SELECT dictionary_code, entry_id, label, sequence, is_active,
                      revision, updated_at, updated_by
               FROM project_administration_dictionary
               WHERE tenant_id = ? AND project_id = ?"""
        )
        params: list[object] = [tenant_id, project_id]
        if dictionary_code:
            query += " AND dictionary_code = ?"
            params.append(dictionary_code)
        if not include_inactive:
            query += " AND is_active = 1"
        if search:
            pattern = f"%{search}%"
            query += " AND (entry_id LIKE ? OR label LIKE ?)"
            params.extend([pattern, pattern])
        query += " ORDER BY dictionary_code, sequence, entry_id"
        return tuple(
            DictionaryEntry(
                tenant_id=tenant_id,
                project_id=project_id,
                dictionary_code=row[0],
                entry_id=row[1],
                label=row[2],
                sequence=row[3],
                is_active=bool(row[4]),
                revision=row[5],
                updated_at=row[6],
                updated_by=row[7],
            )
            for row in self.connection.execute(query, tuple(params)).fetchall()
        )

    def read_dictionary_entry(
        self, tenant_id: str, project_id: str, dictionary_code: str, entry_id: str
    ) -> DictionaryEntry:
        row = self.connection.execute(
            """SELECT label, sequence, is_active, revision, updated_at, updated_by
               FROM project_administration_dictionary
               WHERE tenant_id = ? AND project_id = ?
                 AND dictionary_code = ? AND entry_id = ?""",
            (tenant_id, project_id, dictionary_code, entry_id),
        ).fetchone()
        if row is None:
            raise AdministrationPersistenceError("ADMIN_DICTIONARY_NOT_FOUND")
        return DictionaryEntry(
            tenant_id=tenant_id,
            project_id=project_id,
            dictionary_code=dictionary_code,
            entry_id=entry_id,
            label=row[0],
            sequence=row[1],
            is_active=bool(row[2]),
            revision=row[3],
            updated_at=row[4],
            updated_by=row[5],
        )

    def create_dictionary_entry(
        self,
        entry: DictionaryEntry,
        *,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> DictionaryEntry:
        entry.validate()
        actor = _actor(actor_id)
        stamp = _iso(occurred_at)
        key = _required_text(
            idempotency_key, "ADMIN_IDEMPOTENCY_KEY_REQUIRED", 120
        )
        request_hash = hashlib.sha256(
            json.dumps(
                {
                    "dictionary_code": entry.dictionary_code,
                    "entry_id": entry.entry_id,
                    "label": entry.label,
                    "sequence": entry.sequence,
                    "is_active": entry.is_active,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        with self.connection:
            cached = self.connection.execute(
                """SELECT request_hash, response_json
                   FROM project_administration_idempotency
                   WHERE tenant_id = ? AND project_id = ?
                     AND idempotency_key = ?""",
                (entry.tenant_id, entry.project_id, key),
            ).fetchone()
            if cached is not None:
                if cached[0] != request_hash:
                    raise AdministrationIdempotencyReuse(
                        "ADMIN_IDEMPOTENCY_KEY_REUSE"
                    )
                payload = json.loads(cached[1])
                return DictionaryEntry(
                    tenant_id=entry.tenant_id,
                    project_id=entry.project_id,
                    dictionary_code=payload["dictionary_code"],
                    entry_id=payload["entry_id"],
                    label=payload["label"],
                    sequence=payload["sequence"],
                    is_active=payload["is_active"],
                    revision=payload["revision"],
                    updated_at=payload["updated_at"],
                    updated_by=payload["updated_by"],
                )
            existing = self.connection.execute(
                """SELECT 1 FROM project_administration_dictionary
                   WHERE tenant_id = ? AND project_id = ?
                     AND dictionary_code = ? AND entry_id = ?""",
                (
                    entry.tenant_id,
                    entry.project_id,
                    entry.dictionary_code,
                    entry.entry_id,
                ),
            ).fetchone()
            if existing is not None:
                raise AdministrationPersistenceError(
                    "ADMIN_DICTIONARY_ID_ALREADY_EXISTS"
                )
            revision = 1
            self.connection.execute(
                """INSERT INTO project_administration_dictionary
                       (tenant_id, project_id, dictionary_code, entry_id, label,
                        sequence, is_active, revision, updated_at, updated_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.tenant_id,
                    entry.project_id,
                    entry.dictionary_code,
                    entry.entry_id,
                    entry.label,
                    entry.sequence,
                    1 if entry.is_active else 0,
                    revision,
                    stamp,
                    actor,
                ),
            )
            stored = DictionaryEntry(
                tenant_id=entry.tenant_id,
                project_id=entry.project_id,
                dictionary_code=entry.dictionary_code,
                entry_id=entry.entry_id,
                label=entry.label,
                sequence=entry.sequence,
                is_active=entry.is_active,
                revision=revision,
                updated_at=stamp,
                updated_by=actor,
            )
            self.connection.execute(
                """INSERT INTO project_administration_idempotency
                       (tenant_id, project_id, idempotency_key, request_hash,
                        response_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    entry.tenant_id,
                    entry.project_id,
                    key,
                    request_hash,
                    json.dumps(stored.as_dict(), sort_keys=True),
                ),
            )
            self._append_audit(
                entry.tenant_id,
                entry.project_id,
                "dictionary",
                f"{entry.dictionary_code}/{entry.entry_id}",
                "created",
                actor,
                stamp,
                revision,
                stored.label,
            )
        return stored

    def update_dictionary_entry(
        self,
        entry: DictionaryEntry,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> DictionaryEntry:
        entry.validate()
        actor = _actor(actor_id)
        stamp = _iso(occurred_at)
        if isinstance(expected_revision, bool) or not isinstance(
            expected_revision, int
        ):
            raise AdministrationPersistenceError("INVALID_ADMIN_REVISION")
        with self.connection:
            current = self.read_dictionary_entry(
                entry.tenant_id,
                entry.project_id,
                entry.dictionary_code,
                entry.entry_id,
            )
            if current.revision != expected_revision:
                raise AdministrationRevisionConflict(
                    "ADMIN_DICTIONARY_REVISION_CONFLICT"
                )
            revision = current.revision + 1
            self.connection.execute(
                """UPDATE project_administration_dictionary
                   SET label = ?, sequence = ?, is_active = ?, revision = ?,
                       updated_at = ?, updated_by = ?
                   WHERE tenant_id = ? AND project_id = ?
                     AND dictionary_code = ? AND entry_id = ?""",
                (
                    entry.label,
                    entry.sequence,
                    1 if entry.is_active else 0,
                    revision,
                    stamp,
                    actor,
                    entry.tenant_id,
                    entry.project_id,
                    entry.dictionary_code,
                    entry.entry_id,
                ),
            )
            stored = DictionaryEntry(
                tenant_id=entry.tenant_id,
                project_id=entry.project_id,
                dictionary_code=entry.dictionary_code,
                entry_id=entry.entry_id,
                label=entry.label,
                sequence=entry.sequence,
                is_active=entry.is_active,
                revision=revision,
                updated_at=stamp,
                updated_by=actor,
            )
            self._append_audit(
                entry.tenant_id,
                entry.project_id,
                "dictionary",
                f"{entry.dictionary_code}/{entry.entry_id}",
                "updated",
                actor,
                stamp,
                revision,
                stored.label,
            )
        return stored

    def delete_dictionary_entry(
        self,
        *,
        tenant_id: str,
        project_id: str,
        dictionary_code: str,
        entry_id: str,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> None:
        actor = _actor(actor_id)
        stamp = _iso(occurred_at)
        if isinstance(expected_revision, bool) or not isinstance(
            expected_revision, int
        ):
            raise AdministrationPersistenceError("INVALID_ADMIN_REVISION")
        with self.connection:
            current = self.read_dictionary_entry(
                tenant_id, project_id, dictionary_code, entry_id
            )
            if current.revision != expected_revision:
                raise AdministrationRevisionConflict(
                    "ADMIN_DICTIONARY_REVISION_CONFLICT"
                )
            self.connection.execute(
                """DELETE FROM project_administration_dictionary
                   WHERE tenant_id = ? AND project_id = ?
                     AND dictionary_code = ? AND entry_id = ?""",
                (tenant_id, project_id, dictionary_code, entry_id),
            )
            self._append_audit(
                tenant_id,
                project_id,
                "dictionary",
                f"{dictionary_code}/{entry_id}",
                "deleted",
                actor,
                stamp,
                current.revision + 1,
                current.label,
            )

    def audit_history(
        self, tenant_id: str, project_id: str
    ) -> tuple[AdministrationAuditEvent, ...]:
        rows = self.connection.execute(
            """SELECT entity_kind, entity_id, action, actor_id, occurred_at,
                      revision, details
               FROM project_administration_audit
               WHERE tenant_id = ? AND project_id = ?
               ORDER BY occurred_at DESC, revision DESC""",
            (tenant_id, project_id),
        ).fetchall()
        return tuple(
            AdministrationAuditEvent(
                tenant_id=tenant_id,
                project_id=project_id,
                entity_kind=row[0],
                entity_id=row[1],
                action=row[2],
                actor_id=row[3],
                occurred_at=row[4],
                revision=row[5],
                details=row[6],
            )
            for row in rows
        )

    def _append_audit(
        self,
        tenant_id: str,
        project_id: str,
        entity_kind: str,
        entity_id: str,
        action: str,
        actor_id: str,
        occurred_at: str,
        revision: int,
        details: str,
    ) -> None:
        self.connection.execute(
            """INSERT INTO project_administration_audit
                   (tenant_id, project_id, entity_kind, entity_id, action,
                    actor_id, occurred_at, revision, details)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tenant_id,
                project_id,
                entity_kind,
                entity_id,
                action,
                actor_id,
                occurred_at,
                revision,
                details,
            ),
        )
