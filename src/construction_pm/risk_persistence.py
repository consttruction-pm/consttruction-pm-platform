"""Authoritative project risk register facts.

A risk is a project-scoped record with a category, a probability and impact on
a five-point scale, a response strategy, named owners and a lifecycle status.
Exposure is derived from probability times impact; it is never supplied by the
caller and never stored as a separate fact.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from .backend_p0.models import MAX_SAFE_REVISION

RISK_CATEGORIES = (
    "technical",
    "commercial",
    "schedule",
    "cost",
    "quality",
    "safety",
    "resource",
    "external",
    "other",
)
RISK_STATUSES = ("open", "monitoring", "mitigating", "closed")
RISK_STRATEGIES = ("avoid", "transfer", "mitigate", "accept", "escalate")
RISK_STATUS_TRANSITIONS = {
    "open": frozenset({"monitoring", "mitigating", "closed"}),
    "monitoring": frozenset({"open", "mitigating", "closed"}),
    "mitigating": frozenset({"open", "monitoring", "closed"}),
    "closed": frozenset({"open"}),
}


class RiskPersistenceError(ValueError):
    """Raised when risk persistence receives an invalid or conflicting write."""


class RiskRevisionConflict(RiskPersistenceError):
    pass


class RiskIdempotencyReuse(RiskPersistenceError):
    pass


def risk_exposure_level(probability: int, impact: int) -> str:
    """Return ``low``, ``medium``, ``high`` or ``critical`` for a 1..5 x 1..5 score."""
    score = probability * impact
    if score <= 4:
        return "low"
    if score <= 9:
        return "medium"
    if score <= 16:
        return "high"
    return "critical"


def validate_risk_transition(current: str, target: str) -> None:
    if current == target:
        return
    if current not in RISK_STATUSES or target not in RISK_STATUSES:
        raise RiskPersistenceError("INVALID_RISK_STATUS")
    if target not in RISK_STATUS_TRANSITIONS[current]:
        raise RiskPersistenceError("RISK_STATUS_TRANSITION_INVALID")


def _parse_date(value: str, code: str) -> date:
    if not isinstance(value, str) or not value.strip():
        raise RiskPersistenceError(code)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise RiskPersistenceError(code) from exc


def _rating(value: object, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        raise RiskPersistenceError(code)
    return value


@dataclass(frozen=True)
class Risk:
    tenant_id: str
    project_id: str
    risk_id: str
    title: str
    description: str
    category: str
    status: str
    probability: int
    impact: int
    response_strategy: str
    owner: str
    date_identified: str
    response_owner: str | None = None
    response_due_date: str | None = None
    responsible_manager: str | None = None
    closure_note: str | None = None

    @property
    def score(self) -> int:
        return self.probability * self.impact

    @property
    def exposure_level(self) -> str:
        return risk_exposure_level(self.probability, self.impact)

    def validate(self) -> None:
        for value, code in (
            (self.tenant_id, "INVALID_RISK_TENANT"),
            (self.project_id, "INVALID_RISK_PROJECT"),
            (self.risk_id, "INVALID_RISK_ID"),
            (self.title, "INVALID_RISK_TITLE"),
            (self.owner, "INVALID_RISK_OWNER"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise RiskPersistenceError(code)
        if not isinstance(self.description, str):
            raise RiskPersistenceError("INVALID_RISK_DESCRIPTION")
        if self.category not in RISK_CATEGORIES:
            raise RiskPersistenceError("INVALID_RISK_CATEGORY")
        if self.status not in RISK_STATUSES:
            raise RiskPersistenceError("INVALID_RISK_STATUS")
        if self.response_strategy not in RISK_STRATEGIES:
            raise RiskPersistenceError("INVALID_RISK_STRATEGY")
        _rating(self.probability, "INVALID_RISK_PROBABILITY")
        _rating(self.impact, "INVALID_RISK_IMPACT")
        identified = _parse_date(self.date_identified, "INVALID_RISK_DATE_IDENTIFIED")
        if self.response_due_date is not None:
            due = _parse_date(self.response_due_date, "INVALID_RISK_RESPONSE_DUE_DATE")
            if due < identified:
                raise RiskPersistenceError("RISK_DATE_ORDER_INVALID")
        for value, code in (
            (self.response_owner, "INVALID_RISK_RESPONSE_OWNER"),
            (self.responsible_manager, "INVALID_RISK_MANAGER"),
        ):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise RiskPersistenceError(code)
        if self.closure_note is not None and not isinstance(self.closure_note, str):
            raise RiskPersistenceError("INVALID_RISK_CLOSURE_NOTE")
        if self.status == "closed" and not (self.closure_note or "").strip():
            raise RiskPersistenceError("RISK_CLOSURE_NOTE_REQUIRED")

    def as_dict(self) -> dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "risk_id": self.risk_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "status": self.status,
            "probability": self.probability,
            "impact": self.impact,
            "response_strategy": self.response_strategy,
            "owner": self.owner,
            "date_identified": self.date_identified,
            "response_owner": self.response_owner,
            "response_due_date": self.response_due_date,
            "responsible_manager": self.responsible_manager,
            "closure_note": self.closure_note,
        }


@dataclass(frozen=True)
class StoredRisk:
    risk: Risk
    revision: int


@dataclass(frozen=True)
class RiskAuditEvent:
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


class RiskStore(Protocol):
    def create_risk(
        self,
        risk: Risk,
        *,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredRisk: ...

    def get_risk(self, tenant_id: str, project_id: str, risk_id: str) -> StoredRisk: ...

    def list_risks(
        self,
        tenant_id: str,
        project_id: str,
        *,
        category: str | None = None,
        status: str | None = None,
        response_strategy: str | None = None,
        exposure: str | None = None,
        search: str | None = None,
    ) -> tuple[StoredRisk, ...]: ...

    def update_risk(
        self,
        risk: Risk,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> StoredRisk: ...

    def delete_risk(
        self,
        *,
        tenant_id: str,
        project_id: str,
        risk_id: str,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> None: ...

    def risk_history(
        self, tenant_id: str, project_id: str, risk_id: str
    ) -> tuple[RiskAuditEvent, ...]: ...


def _fingerprint(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _validate_audit(actor_id: str, occurred_at: datetime) -> None:
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise ValueError("INVALID_RISK_ACTOR")
    if not isinstance(occurred_at, datetime) or occurred_at.tzinfo is None:
        raise ValueError("INVALID_RISK_OCCURRED_AT")


def _coerce_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


class SQLiteRiskStore:
    """Project-scoped risk register with an immutable audit trail."""

    def __init__(self, connection) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_risk (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                risk_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 1,
                risk_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, risk_id),
                UNIQUE (tenant_id, project_id, idempotency_key)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_risk_audit (
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
        self.connection.commit()

    # -- reads ------------------------------------------------------------
    def get_risk(self, tenant_id: str, project_id: str, risk_id: str) -> StoredRisk:
        row = self.connection.execute(
            "SELECT risk_json, revision FROM project_risk "
            "WHERE tenant_id=? AND project_id=? AND risk_id=?",
            (tenant_id, project_id, risk_id),
        ).fetchone()
        if row is None:
            raise KeyError("RISK_NOT_FOUND")
        return StoredRisk(self._risk_from_json(row[0]), int(row[1]))

    def list_risks(
        self,
        tenant_id: str,
        project_id: str,
        *,
        category: str | None = None,
        status: str | None = None,
        response_strategy: str | None = None,
        exposure: str | None = None,
        search: str | None = None,
    ) -> tuple[StoredRisk, ...]:
        if category is not None and category not in RISK_CATEGORIES:
            raise RiskPersistenceError("INVALID_RISK_CATEGORY")
        if status is not None and status not in RISK_STATUSES:
            raise RiskPersistenceError("INVALID_RISK_STATUS")
        if response_strategy is not None and response_strategy not in RISK_STRATEGIES:
            raise RiskPersistenceError("INVALID_RISK_STRATEGY")
        if exposure is not None and exposure not in {"low", "medium", "high", "critical"}:
            raise RiskPersistenceError("INVALID_RISK_EXPOSURE")
        if search is not None and (not isinstance(search, str) or not search.strip()):
            raise RiskPersistenceError("INVALID_RISK_SEARCH")
        query = "SELECT risk_json, revision FROM project_risk WHERE tenant_id=? AND project_id=?"
        params: list[object] = [tenant_id, project_id]
        if category is not None:
            query += " AND json_extract(risk_json, '$.category')=?"
            params.append(category)
        if status is not None:
            query += " AND json_extract(risk_json, '$.status')=?"
            params.append(status)
        if response_strategy is not None:
            query += " AND json_extract(risk_json, '$.response_strategy')=?"
            params.append(response_strategy)
        if search is not None:
            query += (
                " AND (LOWER(risk_id) LIKE ?"
                " OR LOWER(json_extract(risk_json, '$.title')) LIKE ?"
                " OR LOWER(json_extract(risk_json, '$.owner')) LIKE ?)"
            )
            needle = f"%{search.lower()}%"
            params.extend([needle, needle, needle])
        query += " ORDER BY json_extract(risk_json, '$.probability') * json_extract(risk_json, '$.impact') DESC, risk_id"
        rows = tuple(
            StoredRisk(self._risk_from_json(row[0]), int(row[1]))
            for row in self.connection.execute(query, tuple(params)).fetchall()
        )
        if exposure is not None:
            rows = tuple(item for item in rows if item.risk.exposure_level == exposure)
        return rows

    # -- writes -----------------------------------------------------------
    def create_risk(
        self,
        risk: Risk,
        *,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredRisk:
        risk.validate()
        self._validate_key(idempotency_key)
        _validate_audit(actor_id, occurred_at)
        payload = risk.as_dict()
        fingerprint = _fingerprint(payload)
        existing = self.connection.execute(
            "SELECT risk_id, fingerprint FROM project_risk "
            "WHERE tenant_id=? AND project_id=? AND idempotency_key=?",
            (risk.tenant_id, risk.project_id, idempotency_key),
        ).fetchone()
        if existing is not None:
            if existing[1] != fingerprint:
                raise RiskIdempotencyReuse("RISK_IDEMPOTENCY_KEY_REUSE")
            return self.get_risk(risk.tenant_id, risk.project_id, str(existing[0]))
        try:
            self.connection.execute(
                "INSERT INTO project_risk "
                "(tenant_id, project_id, risk_id, idempotency_key, fingerprint, revision, risk_json) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    risk.tenant_id,
                    risk.project_id,
                    risk.risk_id,
                    idempotency_key,
                    fingerprint,
                    1,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                ),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc) or "PRIMARY KEY" in str(exc):
                raise RiskPersistenceError("RISK_ALREADY_EXISTS") from exc
            raise
        self._audit(risk, "created", 1, actor_id, occurred_at, "")
        return StoredRisk(risk, 1)

    def update_risk(
        self,
        risk: Risk,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> StoredRisk:
        risk.validate()
        _validate_audit(actor_id, occurred_at)
        self._check_revision(expected_revision, "INVALID_EXPECTED_RISK_REVISION")
        stored = self.get_risk(risk.tenant_id, risk.project_id, risk.risk_id)
        if stored.revision != expected_revision:
            raise RiskRevisionConflict("RISK_REVISION_CONFLICT")
        if stored.revision >= MAX_SAFE_REVISION:
            raise RiskPersistenceError("RISK_REVISION_EXHAUSTED")
        validate_risk_transition(stored.risk.status, risk.status)
        next_revision = stored.revision + 1
        self.connection.execute(
            "UPDATE project_risk SET revision=?, risk_json=? "
            "WHERE tenant_id=? AND project_id=? AND risk_id=?",
            (
                next_revision,
                json.dumps(
                    risk.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ),
                risk.tenant_id,
                risk.project_id,
                risk.risk_id,
            ),
        )
        event_type = "status_changed" if stored.risk.status != risk.status else "updated"
        self._audit(risk, event_type, next_revision, actor_id, occurred_at, reason)
        return StoredRisk(risk, next_revision)

    def delete_risk(
        self,
        *,
        tenant_id: str,
        project_id: str,
        risk_id: str,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> None:
        _validate_audit(actor_id, occurred_at)
        self._check_revision(expected_revision, "INVALID_EXPECTED_RISK_REVISION")
        stored = self.get_risk(tenant_id, project_id, risk_id)
        if stored.revision != expected_revision:
            raise RiskRevisionConflict("RISK_REVISION_CONFLICT")
        if stored.revision >= MAX_SAFE_REVISION:
            raise RiskPersistenceError("RISK_REVISION_EXHAUSTED")
        self._audit(
            stored.risk, "deleted", stored.revision + 1, actor_id, occurred_at, reason
        )
        self.connection.execute(
            "DELETE FROM project_risk WHERE tenant_id=? AND project_id=? AND risk_id=?",
            (tenant_id, project_id, risk_id),
        )

    def risk_history(
        self, tenant_id: str, project_id: str, risk_id: str
    ) -> tuple[RiskAuditEvent, ...]:
        rows = self.connection.execute(
            "SELECT entity_type, entity_id, revision, event_type, actor_id, occurred_at, reason "
            "FROM project_risk_audit "
            "WHERE tenant_id=? AND project_id=? AND entity_type='risk' AND entity_id=? "
            "ORDER BY revision",
            (tenant_id, project_id, risk_id),
        ).fetchall()
        if not rows:
            raise KeyError("RISK_AUDIT_NOT_FOUND")
        return tuple(
            RiskAuditEvent(
                row[0], row[1], int(row[2]), row[3], row[4], _coerce_datetime(row[5]), row[6]
            )
            for row in rows
        )

    # -- helpers ----------------------------------------------------------
    def _audit(
        self,
        risk: Risk,
        event_type: str,
        revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str,
    ) -> None:
        self.connection.execute(
            "INSERT INTO project_risk_audit "
            "(tenant_id, project_id, entity_type, entity_id, revision, event_type, actor_id, occurred_at, reason) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                risk.tenant_id,
                risk.project_id,
                "risk",
                risk.risk_id,
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
            raise ValueError("INVALID_RISK_IDEMPOTENCY_KEY")

    @staticmethod
    def _check_revision(expected_revision: object, code: str) -> None:
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
            raise ValueError(code)
        if expected_revision < 1 or expected_revision > MAX_SAFE_REVISION:
            raise ValueError(code)

    @staticmethod
    def _risk_from_json(payload: str) -> Risk:
        data = json.loads(payload)
        return Risk(
            tenant_id=data["tenant_id"],
            project_id=data["project_id"],
            risk_id=data["risk_id"],
            title=data["title"],
            description=data.get("description", ""),
            category=data["category"],
            status=data["status"],
            probability=int(data["probability"]),
            impact=int(data["impact"]),
            response_strategy=data["response_strategy"],
            owner=data["owner"],
            date_identified=data["date_identified"],
            response_owner=data.get("response_owner"),
            response_due_date=data.get("response_due_date"),
            responsible_manager=data.get("responsible_manager"),
            closure_note=data.get("closure_note"),
        )


__all__ = [
    "RISK_CATEGORIES",
    "RISK_STATUSES",
    "RISK_STATUS_TRANSITIONS",
    "RISK_STRATEGIES",
    "Risk",
    "RiskAuditEvent",
    "RiskIdempotencyReuse",
    "RiskPersistenceError",
    "RiskRevisionConflict",
    "RiskStore",
    "SQLiteRiskStore",
    "StoredRisk",
    "risk_exposure_level",
    "validate_risk_transition",
]
