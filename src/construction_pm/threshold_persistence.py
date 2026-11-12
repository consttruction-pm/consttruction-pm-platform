"""Authoritative project threshold definitions and monitoring runs.

A threshold definition is a project-scoped monitoring rule: one measurable
parameter, optional lower/upper bounds, optional warning and issue deviation
levels, and a responsible manager. Monitoring is a write operation because it
appends an immutable run row and can raise a real issue in the issue register.

The store never derives or fabricates an observed value: the caller supplies a
value read from authoritative project data by ``threshold_metrics``.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol

from .backend_p0.models import MAX_SAFE_REVISION

THRESHOLD_SUBJECTS = ("schedule", "cost", "quality", "safety", "resource", "scope", "other")
THRESHOLD_PARAMETERS = ("open_issue_count", "expense_actual_total", "budget_balance")
MONETARY_PARAMETERS = frozenset({"expense_actual_total", "budget_balance"})
THRESHOLD_STATUSES = ("active", "inactive")
THRESHOLD_LEVELS = ("normal", "warning", "issue")

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


class ThresholdPersistenceError(ValueError):
    """Raised when threshold persistence receives an invalid or conflicting write."""


class ThresholdRevisionConflict(ThresholdPersistenceError):
    pass


class ThresholdIdempotencyReuse(ThresholdPersistenceError):
    pass


def parse_threshold_number(
    value: object, *, code: str, allow_negative: bool = False
) -> Decimal:
    """Parse a threshold number with at most four decimals, never a float."""
    if isinstance(value, bool) or value is None:
        raise ThresholdPersistenceError(code)
    if isinstance(value, Decimal):
        number = value
    elif isinstance(value, (str, int)):
        text = str(value).strip()
        if not text or "e" in text.lower():
            raise ThresholdPersistenceError(code)
        try:
            number = Decimal(text)
        except InvalidOperation as exc:
            raise ThresholdPersistenceError(code) from exc
    else:
        raise ThresholdPersistenceError(code)
    if not number.is_finite():
        raise ThresholdPersistenceError(code)
    if abs(number.as_tuple().exponent) > 4:  # type: ignore[operator]
        raise ThresholdPersistenceError(code)
    if number != number.quantize(Decimal("0.0001")):
        raise ThresholdPersistenceError(code)
    if not allow_negative and number < 0:
        raise ThresholdPersistenceError(code)
    return number


def threshold_number_text(value: Decimal) -> str:
    """Canonical text: integral values have no decimal tail, others up to four places."""
    if value == value.to_integral_value():
        return str(int(value))
    return format(value.normalize(), "f")


@dataclass(frozen=True)
class Threshold:
    tenant_id: str
    project_id: str
    threshold_id: str
    name: str
    monitoring_subject: str
    parameter: str
    currency: str | None = None
    lower_threshold: Decimal | None = None
    upper_threshold: Decimal | None = None
    warning_level: Decimal | None = None
    issue_level: Decimal | None = None
    responsible_manager: str | None = None
    status: str = "active"

    def validate(self) -> None:
        for value, code in (
            (self.tenant_id, "INVALID_THRESHOLD_TENANT"),
            (self.project_id, "INVALID_THRESHOLD_PROJECT"),
            (self.threshold_id, "INVALID_THRESHOLD_ID"),
            (self.name, "INVALID_THRESHOLD_NAME"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ThresholdPersistenceError(code)
        if self.monitoring_subject not in THRESHOLD_SUBJECTS:
            raise ThresholdPersistenceError("INVALID_THRESHOLD_SUBJECT")
        if self.parameter not in THRESHOLD_PARAMETERS:
            raise ThresholdPersistenceError("INVALID_THRESHOLD_PARAMETER")
        if self.status not in THRESHOLD_STATUSES:
            raise ThresholdPersistenceError("INVALID_THRESHOLD_STATUS")
        if self.responsible_manager is not None and (
            not isinstance(self.responsible_manager, str) or not self.responsible_manager.strip()
        ):
            raise ThresholdPersistenceError("INVALID_THRESHOLD_MANAGER")
        if self.parameter in MONETARY_PARAMETERS:
            if not isinstance(self.currency, str) or not _CURRENCY_RE.match(self.currency):
                raise ThresholdPersistenceError("THRESHOLD_CURRENCY_REQUIRED")
        elif self.currency is not None:
            raise ThresholdPersistenceError("THRESHOLD_CURRENCY_NOT_ALLOWED")
        if self.lower_threshold is None and self.upper_threshold is None:
            raise ThresholdPersistenceError("THRESHOLD_BOUND_REQUIRED")
        if (
            self.lower_threshold is not None
            and self.upper_threshold is not None
            and self.lower_threshold >= self.upper_threshold
        ):
            raise ThresholdPersistenceError("INVALID_THRESHOLD_BOUNDS")
        for value, code in (
            (self.warning_level, "INVALID_THRESHOLD_WARNING_LEVEL"),
            (self.issue_level, "INVALID_THRESHOLD_ISSUE_LEVEL"),
        ):
            if value is not None and (not isinstance(value, Decimal) or value < 0):
                raise ThresholdPersistenceError(code)
        if (
            self.warning_level is not None
            and self.issue_level is not None
            and self.issue_level <= self.warning_level
        ):
            raise ThresholdPersistenceError("INVALID_THRESHOLD_LEVELS")

    def as_dict(self) -> dict[str, object]:
        def number(value: Decimal | None) -> str | None:
            return None if value is None else threshold_number_text(value)

        return {
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "threshold_id": self.threshold_id,
            "name": self.name,
            "monitoring_subject": self.monitoring_subject,
            "parameter": self.parameter,
            "currency": self.currency,
            "lower_threshold": number(self.lower_threshold),
            "upper_threshold": number(self.upper_threshold),
            "warning_level": number(self.warning_level),
            "issue_level": number(self.issue_level),
            "responsible_manager": self.responsible_manager,
            "status": self.status,
        }


@dataclass(frozen=True)
class StoredThreshold:
    threshold: Threshold
    revision: int


@dataclass(frozen=True)
class ThresholdRun:
    tenant_id: str
    project_id: str
    threshold_id: str
    run_sequence: int
    observed_value: Decimal
    level: str
    currency: str | None
    actor_id: str
    occurred_at: datetime
    generated_issue_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "threshold_id": self.threshold_id,
            "run_sequence": self.run_sequence,
            "observed_value": threshold_number_text(self.observed_value),
            "level": self.level,
            "currency": self.currency,
            "actor_id": self.actor_id,
            "occurred_at": self.occurred_at.isoformat(),
            "generated_issue_id": self.generated_issue_id,
        }


@dataclass(frozen=True)
class ThresholdAuditEvent:
    entity_type: str
    entity_id: str
    revision: int
    event_type: str
    actor_id: str
    occurred_at: datetime
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "revision": self.revision,
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "occurred_at": self.occurred_at.isoformat(),
            "reason": self.reason,
        }


class ThresholdStore(Protocol):
    def create_threshold(
        self,
        threshold: Threshold,
        *,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredThreshold: ...

    def get_threshold(
        self, tenant_id: str, project_id: str, threshold_id: str
    ) -> StoredThreshold: ...

    def list_thresholds(
        self,
        tenant_id: str,
        project_id: str,
        *,
        monitoring_subject: str | None = None,
        parameter: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[StoredThreshold, ...]: ...

    def update_threshold(
        self,
        threshold: Threshold,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredThreshold: ...

    def delete_threshold(
        self,
        *,
        tenant_id: str,
        project_id: str,
        threshold_id: str,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> None: ...

    def threshold_history(
        self, tenant_id: str, project_id: str, threshold_id: str
    ) -> tuple[ThresholdAuditEvent, ...]: ...

    def record_run(self, run: ThresholdRun) -> ThresholdRun: ...

    def runs(
        self, tenant_id: str, project_id: str, threshold_id: str
    ) -> tuple[ThresholdRun, ...]: ...

    def next_run_sequence(
        self, tenant_id: str, project_id: str, threshold_id: str
    ) -> int: ...


def evaluate_threshold_level(threshold: Threshold, observed: Decimal) -> str:
    """Return ``normal``, ``warning`` or ``issue`` for one observed value."""
    deviation: Decimal | None = None
    if threshold.lower_threshold is not None and observed < threshold.lower_threshold:
        deviation = threshold.lower_threshold - observed
    elif threshold.upper_threshold is not None and observed > threshold.upper_threshold:
        deviation = observed - threshold.upper_threshold
    if deviation is None:
        return "normal"
    if threshold.issue_level is not None and deviation >= threshold.issue_level:
        return "issue"
    return "warning"


def _fingerprint(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _validate_audit(actor_id: str, occurred_at: datetime) -> None:
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise ValueError("INVALID_THRESHOLD_ACTOR")
    if not isinstance(occurred_at, datetime) or occurred_at.tzinfo is None:
        raise ValueError("INVALID_THRESHOLD_OCCURRED_AT")


def _coerce_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


class SQLiteThresholdStore:
    """Project-scoped threshold definitions, audit trail and monitoring runs."""

    def __init__(self, connection) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_threshold (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                threshold_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 1,
                threshold_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, threshold_id),
                UNIQUE (tenant_id, project_id, idempotency_key)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_threshold_audit (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (tenant_id, project_id, entity_type, entity_id, revision)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_threshold_run (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                threshold_id TEXT NOT NULL,
                run_sequence INTEGER NOT NULL,
                run_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, threshold_id, run_sequence)
            )"""
        )
        self.connection.commit()

    # -- definitions ------------------------------------------------------
    def create_threshold(
        self,
        threshold: Threshold,
        *,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredThreshold:
        threshold.validate()
        self._validate_key(idempotency_key)
        _validate_audit(actor_id, occurred_at)
        payload = threshold.as_dict()
        fingerprint = _fingerprint(payload)
        existing = self.connection.execute(
            "SELECT threshold_id, fingerprint FROM project_threshold "
            "WHERE tenant_id=? AND project_id=? AND idempotency_key=?",
            (threshold.tenant_id, threshold.project_id, idempotency_key),
        ).fetchone()
        if existing is not None:
            if existing[1] != fingerprint:
                raise ThresholdIdempotencyReuse("THRESHOLD_IDEMPOTENCY_KEY_REUSE")
            return self.get_threshold(
                threshold.tenant_id, threshold.project_id, str(existing[0])
            )
        try:
            self.connection.execute(
                "INSERT INTO project_threshold "
                "(tenant_id, project_id, threshold_id, idempotency_key, fingerprint, revision, threshold_json) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    threshold.tenant_id,
                    threshold.project_id,
                    threshold.threshold_id,
                    idempotency_key,
                    fingerprint,
                    1,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc) or "PRIMARY KEY" in str(exc):
                raise ValueError("THRESHOLD_ALREADY_EXISTS") from exc
            raise
        self._audit(threshold, "created", 1, actor_id, occurred_at, "")
        return StoredThreshold(threshold, 1)

    def get_threshold(
        self, tenant_id: str, project_id: str, threshold_id: str
    ) -> StoredThreshold:
        row = self.connection.execute(
            "SELECT threshold_json, revision FROM project_threshold "
            "WHERE tenant_id=? AND project_id=? AND threshold_id=?",
            (tenant_id, project_id, threshold_id),
        ).fetchone()
        if row is None:
            raise KeyError("THRESHOLD_NOT_FOUND")
        return StoredThreshold(self._threshold_from_json(row[0]), int(row[1]))

    def list_thresholds(
        self,
        tenant_id: str,
        project_id: str,
        *,
        monitoring_subject: str | None = None,
        parameter: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[StoredThreshold, ...]:
        if monitoring_subject is not None and monitoring_subject not in THRESHOLD_SUBJECTS:
            raise ValueError("INVALID_THRESHOLD_SUBJECT")
        if parameter is not None and parameter not in THRESHOLD_PARAMETERS:
            raise ValueError("INVALID_THRESHOLD_PARAMETER")
        if status is not None and status not in THRESHOLD_STATUSES:
            raise ValueError("INVALID_THRESHOLD_STATUS")
        if search is not None and (not isinstance(search, str) or not search.strip()):
            raise ValueError("INVALID_THRESHOLD_SEARCH")
        query = (
            "SELECT threshold_json, revision FROM project_threshold "
            "WHERE tenant_id=? AND project_id=?"
        )
        params: list[object] = [tenant_id, project_id]
        if monitoring_subject is not None:
            query += " AND json_extract(threshold_json, '$.monitoring_subject')=?"
            params.append(monitoring_subject)
        if parameter is not None:
            query += " AND json_extract(threshold_json, '$.parameter')=?"
            params.append(parameter)
        if status is not None:
            query += " AND json_extract(threshold_json, '$.status')=?"
            params.append(status)
        if search is not None:
            query += (
                " AND (LOWER(threshold_id) LIKE ? OR LOWER(json_extract(threshold_json, '$.name')) LIKE ?)"
            )
            needle = f"%{search.lower()}%"
            params.extend([needle, needle])
        query += " ORDER BY threshold_id"
        return tuple(
            StoredThreshold(self._threshold_from_json(row[0]), int(row[1]))
            for row in self.connection.execute(query, tuple(params)).fetchall()
        )

    def update_threshold(
        self,
        threshold: Threshold,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredThreshold:
        threshold.validate()
        _validate_audit(actor_id, occurred_at)
        self._check_revision(expected_revision, "INVALID_EXPECTED_THRESHOLD_REVISION")
        stored = self.get_threshold(
            threshold.tenant_id, threshold.project_id, threshold.threshold_id
        )
        if stored.revision != expected_revision:
            raise ThresholdRevisionConflict("THRESHOLD_REVISION_CONFLICT")
        if stored.revision >= MAX_SAFE_REVISION:
            raise ValueError("THRESHOLD_REVISION_EXHAUSTED")
        next_revision = stored.revision + 1
        self.connection.execute(
            "UPDATE project_threshold SET revision=?, threshold_json=? "
            "WHERE tenant_id=? AND project_id=? AND threshold_id=?",
            (
                next_revision,
                json.dumps(
                    threshold.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ),
                threshold.tenant_id,
                threshold.project_id,
                threshold.threshold_id,
            ),
        )
        self._audit(threshold, "updated", next_revision, actor_id, occurred_at, "")
        return StoredThreshold(threshold, next_revision)

    def delete_threshold(
        self,
        *,
        tenant_id: str,
        project_id: str,
        threshold_id: str,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> None:
        _validate_audit(actor_id, occurred_at)
        self._check_revision(expected_revision, "INVALID_EXPECTED_THRESHOLD_REVISION")
        stored = self.get_threshold(tenant_id, project_id, threshold_id)
        if stored.revision != expected_revision:
            raise ThresholdRevisionConflict("THRESHOLD_REVISION_CONFLICT")
        if stored.revision >= MAX_SAFE_REVISION:
            raise ValueError("THRESHOLD_REVISION_EXHAUSTED")
        self._audit(
            stored.threshold,
            "deleted",
            stored.revision + 1,
            actor_id,
            occurred_at,
            reason,
        )
        self.connection.execute(
            "DELETE FROM project_threshold "
            "WHERE tenant_id=? AND project_id=? AND threshold_id=?",
            (tenant_id, project_id, threshold_id),
        )

    def threshold_history(
        self, tenant_id: str, project_id: str, threshold_id: str
    ) -> tuple[ThresholdAuditEvent, ...]:
        rows = self.connection.execute(
            "SELECT entity_type, entity_id, revision, event_type, actor_id, occurred_at, reason "
            "FROM project_threshold_audit "
            "WHERE tenant_id=? AND project_id=? AND entity_type='threshold' AND entity_id=? "
            "ORDER BY revision",
            (tenant_id, project_id, threshold_id),
        ).fetchall()
        if not rows:
            raise KeyError("THRESHOLD_AUDIT_NOT_FOUND")
        return tuple(
            ThresholdAuditEvent(
                row[0], row[1], int(row[2]), row[3], row[4], _coerce_datetime(row[5]), row[6]
            )
            for row in rows
        )

    # -- monitoring -------------------------------------------------------
    def record_run(self, run: ThresholdRun) -> ThresholdRun:
        if run.level not in THRESHOLD_LEVELS:
            raise ValueError("INVALID_THRESHOLD_LEVEL")
        if not isinstance(run.run_sequence, int) or run.run_sequence < 1:
            raise ValueError("INVALID_THRESHOLD_RUN_SEQUENCE")
        self.get_threshold(run.tenant_id, run.project_id, run.threshold_id)
        existing = self.connection.execute(
            "SELECT run_json FROM project_threshold_run "
            "WHERE tenant_id=? AND project_id=? AND threshold_id=? AND run_sequence=?",
            (run.tenant_id, run.project_id, run.threshold_id, run.run_sequence),
        ).fetchone()
        if existing is not None:
            raise ValueError("THRESHOLD_RUN_ALREADY_RECORDED")
        self.connection.execute(
            "INSERT INTO project_threshold_run "
            "(tenant_id, project_id, threshold_id, run_sequence, run_json) VALUES (?,?,?,?,?)",
            (
                run.tenant_id,
                run.project_id,
                run.threshold_id,
                run.run_sequence,
                json.dumps(
                    run.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ),
            ),
        )
        return run

    def runs(
        self, tenant_id: str, project_id: str, threshold_id: str
    ) -> tuple[ThresholdRun, ...]:
        rows = self.connection.execute(
            "SELECT run_json FROM project_threshold_run "
            "WHERE tenant_id=? AND project_id=? AND threshold_id=? ORDER BY run_sequence",
            (tenant_id, project_id, threshold_id),
        ).fetchall()
        return tuple(self._run_from_json(row[0]) for row in rows)

    def next_run_sequence(
        self, tenant_id: str, project_id: str, threshold_id: str
    ) -> int:
        row = self.connection.execute(
            "SELECT COALESCE(MAX(run_sequence), 0) FROM project_threshold_run "
            "WHERE tenant_id=? AND project_id=? AND threshold_id=?",
            (tenant_id, project_id, threshold_id),
        ).fetchone()
        return int(row[0]) + 1

    # -- helpers ----------------------------------------------------------
    def _audit(
        self,
        threshold: Threshold,
        event_type: str,
        revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str,
    ) -> None:
        self.connection.execute(
            "INSERT INTO project_threshold_audit "
            "(tenant_id, project_id, entity_type, entity_id, revision, event_type, actor_id, occurred_at, reason) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                threshold.tenant_id,
                threshold.project_id,
                "threshold",
                threshold.threshold_id,
                revision,
                event_type,
                actor_id,
                occurred_at.isoformat(),
                reason,
            ),
        )

    @staticmethod
    def _validate_key(idempotency_key: str) -> None:
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("INVALID_THRESHOLD_IDEMPOTENCY_KEY")

    @staticmethod
    def _check_revision(expected_revision: object, code: str) -> None:
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
            raise ValueError(code)
        if expected_revision < 1 or expected_revision > MAX_SAFE_REVISION:
            raise ValueError(code)

    @staticmethod
    def _threshold_from_json(payload: str) -> Threshold:
        data = json.loads(payload)

        def number(key: str) -> Decimal | None:
            value = data.get(key)
            return None if value is None else Decimal(value)

        return Threshold(
            tenant_id=data["tenant_id"],
            project_id=data["project_id"],
            threshold_id=data["threshold_id"],
            name=data["name"],
            monitoring_subject=data["monitoring_subject"],
            parameter=data["parameter"],
            currency=data.get("currency"),
            lower_threshold=number("lower_threshold"),
            upper_threshold=number("upper_threshold"),
            warning_level=number("warning_level"),
            issue_level=number("issue_level"),
            responsible_manager=data.get("responsible_manager"),
            status=data.get("status", "active"),
        )

    @staticmethod
    def _run_from_json(payload: str) -> ThresholdRun:
        data = json.loads(payload)
        return ThresholdRun(
            tenant_id=data["tenant_id"],
            project_id=data["project_id"],
            threshold_id=data["threshold_id"],
            run_sequence=int(data["run_sequence"]),
            observed_value=Decimal(data["observed_value"]),
            level=data["level"],
            currency=data.get("currency"),
            actor_id=data["actor_id"],
            occurred_at=_coerce_datetime(data["occurred_at"]),
            generated_issue_id=data.get("generated_issue_id"),
        )


__all__ = [
    "MONETARY_PARAMETERS",
    "THRESHOLD_LEVELS",
    "THRESHOLD_PARAMETERS",
    "THRESHOLD_STATUSES",
    "THRESHOLD_SUBJECTS",
    "SQLiteThresholdStore",
    "StoredThreshold",
    "Threshold",
    "ThresholdAuditEvent",
    "ThresholdIdempotencyReuse",
    "ThresholdPersistenceError",
    "ThresholdRevisionConflict",
    "ThresholdRun",
    "ThresholdStore",
    "evaluate_threshold_level",
    "parse_threshold_number",
    "threshold_number_text",
]
