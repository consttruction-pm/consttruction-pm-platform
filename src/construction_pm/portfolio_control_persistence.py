from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from .control_intelligence.contracts import MAX_SAFE_REVISION, SourceReference
from .control_intelligence.portfolio import PortfolioControlSnapshot, PortfolioProjectControlInput


class PortfolioControlPersistenceError(ValueError):
    """Raised when a canonical Enterprise portfolio record is invalid or stale."""


class PortfolioControlRevisionConflict(PortfolioControlPersistenceError):
    pass


@dataclass(frozen=True)
class PortfolioProjectFacts:
    """Read-only facts returned by the authoritative Engineering project source."""

    project_id: str
    project_revision: int
    status: str
    name_key: str | None = None

    def validate(self) -> None:
        if not isinstance(self.project_id, str) or not self.project_id.strip():
            raise PortfolioControlPersistenceError("INVALID_PORTFOLIO_PROJECT_ID")
        if (
            isinstance(self.project_revision, bool)
            or not isinstance(self.project_revision, int)
            or not 0 <= self.project_revision <= MAX_SAFE_REVISION
        ):
            raise PortfolioControlPersistenceError("INVALID_PORTFOLIO_PROJECT_REVISION")
        if not isinstance(self.status, str) or not self.status.strip():
            raise PortfolioControlPersistenceError("INVALID_PORTFOLIO_PROJECT_STATUS")
        if self.name_key is not None and (
            not isinstance(self.name_key, str) or not self.name_key.strip()
        ):
            raise PortfolioControlPersistenceError("INVALID_PORTFOLIO_PROJECT_NAME_KEY")


class PortfolioProjectFactsReader(Protocol):
    def get_project_facts(self, tenant_id: str, project_id: str) -> PortfolioProjectFacts:
        """Return current authoritative facts; unknown/cross-tenant projects must fail closed."""
        ...


@dataclass(frozen=True)
class PortfolioMembershipRecord:
    tenant_id: str
    portfolio_id: str
    project_id: str
    membership_status: str
    project_revision: int
    source_refs: tuple[SourceReference, ...]
    membership_revision: int
    updated_at: datetime


@dataclass(frozen=True)
class PortfolioRecord:
    tenant_id: str
    portfolio_id: str
    revision: int
    created_at: datetime
    updated_at: datetime


class PostgresPortfolioControlRepository:
    """Canonical tenant-scoped Enterprise portfolio lifecycle and membership store.

    The repository stores membership and opaque revision-pinned source references only.
    Project status/name and all engineering metrics are read from the injected Engineering
    facts reader; this repository never derives or recalculates them.
    """

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def initialize(self) -> None:
        statements = (
            """
            CREATE TABLE IF NOT EXISTS enterprise_portfolios (
                tenant_id TEXT NOT NULL,
                portfolio_id TEXT NOT NULL,
                revision BIGINT NOT NULL CHECK (revision >= 1),
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL,
                PRIMARY KEY (tenant_id, portfolio_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS enterprise_portfolio_memberships (
                tenant_id TEXT NOT NULL,
                portfolio_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                membership_status TEXT NOT NULL
                    CHECK (membership_status IN ('included','on_hold','excluded')),
                project_revision BIGINT NOT NULL CHECK (project_revision >= 0),
                source_refs_json JSONB NOT NULL,
                membership_revision BIGINT NOT NULL CHECK (membership_revision >= 1),
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL,
                PRIMARY KEY (tenant_id, portfolio_id, project_id),
                FOREIGN KEY (tenant_id, portfolio_id)
                    REFERENCES enterprise_portfolios(tenant_id, portfolio_id) ON DELETE RESTRICT,
                CHECK (jsonb_typeof(source_refs_json) = 'array'),
                CHECK (jsonb_array_length(source_refs_json) > 0)
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS enterprise_portfolio_memberships_project
            ON enterprise_portfolio_memberships (tenant_id, project_id, portfolio_id)
            """,
            """
            CREATE TABLE IF NOT EXISTS enterprise_portfolio_audit (
                audit_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                portfolio_id TEXT NOT NULL,
                project_id TEXT,
                portfolio_revision BIGINT NOT NULL CHECK (portfolio_revision >= 1),
                action TEXT NOT NULL CHECK (action IN ('portfolio_created','membership_added','membership_updated')),
                actor_id TEXT NOT NULL,
                before_state JSONB,
                after_state JSONB NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL,
                FOREIGN KEY (tenant_id, portfolio_id)
                    REFERENCES enterprise_portfolios(tenant_id, portfolio_id) ON DELETE RESTRICT
            )
            """,
            """
            CREATE OR REPLACE FUNCTION cubi_enterprise_portfolio_audit_immutable()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'ENTERPRISE_PORTFOLIO_AUDIT_APPEND_ONLY';
            END;
            $$
            """,
            """
            DROP TRIGGER IF EXISTS enterprise_portfolio_audit_immutable
            ON enterprise_portfolio_audit
            """,
            """
            CREATE TRIGGER enterprise_portfolio_audit_immutable
            BEFORE UPDATE OR DELETE ON enterprise_portfolio_audit
            FOR EACH ROW EXECUTE FUNCTION cubi_enterprise_portfolio_audit_immutable()
            """,
        )
        for statement in statements:
            self._connection.execute(statement)

    def create_portfolio(
        self,
        tenant_id: str,
        portfolio_id: str,
        *,
        actor_id: str,
        occurred_at: datetime,
    ) -> PortfolioRecord:
        self._validate_scope(tenant_id, portfolio_id, actor_id, occurred_at)
        self._connection.execute(
            "INSERT INTO enterprise_portfolios "
            "(tenant_id,portfolio_id,revision,created_at,updated_at) VALUES (%s,%s,1,%s,%s)",
            (tenant_id, portfolio_id, occurred_at, occurred_at),
        )
        self._audit(
            tenant_id, portfolio_id, None, 1, "portfolio_created", actor_id,
            None, {"portfolio_id": portfolio_id, "revision": 1}, occurred_at,
        )
        return PortfolioRecord(tenant_id, portfolio_id, 1, occurred_at, occurred_at)

    def add_membership(
        self,
        tenant_id: str,
        portfolio_id: str,
        project_id: str,
        *,
        membership_status: str,
        project_revision: int,
        source_refs: tuple[SourceReference, ...],
        expected_portfolio_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> PortfolioMembershipRecord:
        self._validate_scope(tenant_id, portfolio_id, actor_id, occurred_at)
        self._validate_membership(project_id, membership_status, project_revision, source_refs)
        portfolio = self._lock_portfolio(tenant_id, portfolio_id, expected_portfolio_revision)
        payload = self._encode_sources(source_refs)
        self._connection.execute(
            "INSERT INTO enterprise_portfolio_memberships "
            "(tenant_id,portfolio_id,project_id,membership_status,project_revision,source_refs_json,"
            "membership_revision,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s::jsonb,1,%s,%s)",
            (tenant_id, portfolio_id, project_id, membership_status, project_revision,
             payload, occurred_at, occurred_at),
        )
        next_revision = portfolio.revision + 1
        self._advance_portfolio(tenant_id, portfolio_id, portfolio.revision, next_revision, occurred_at)
        after = {
            "project_id": project_id, "membership_status": membership_status,
            "project_revision": project_revision, "source_refs": json.loads(payload),
            "membership_revision": 1,
        }
        self._audit(
            tenant_id, portfolio_id, project_id, next_revision, "membership_added",
            actor_id, None, after, occurred_at,
        )
        return PortfolioMembershipRecord(
            tenant_id, portfolio_id, project_id, membership_status, project_revision,
            source_refs, 1, occurred_at,
        )

    def update_membership(
        self,
        tenant_id: str,
        portfolio_id: str,
        project_id: str,
        *,
        membership_status: str,
        project_revision: int,
        source_refs: tuple[SourceReference, ...],
        expected_portfolio_revision: int,
        expected_membership_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> PortfolioMembershipRecord:
        self._validate_scope(tenant_id, portfolio_id, actor_id, occurred_at)
        self._validate_membership(project_id, membership_status, project_revision, source_refs)
        portfolio = self._lock_portfolio(tenant_id, portfolio_id, expected_portfolio_revision)
        row = self._connection.execute(
            "SELECT membership_status,project_revision,source_refs_json,membership_revision "
            "FROM enterprise_portfolio_memberships "
            "WHERE tenant_id=%s AND portfolio_id=%s AND project_id=%s FOR UPDATE",
            (tenant_id, portfolio_id, project_id),
        ).fetchone()
        if row is None:
            raise KeyError("PORTFOLIO_MEMBERSHIP_NOT_FOUND")
        current_membership_revision = int(row[3])
        if current_membership_revision != expected_membership_revision:
            raise PortfolioControlRevisionConflict("PORTFOLIO_MEMBERSHIP_REVISION_CONFLICT")
        before = {
            "project_id": project_id, "membership_status": row[0],
            "project_revision": int(row[1]), "source_refs": self._decode_sources(row[2]),
            "membership_revision": current_membership_revision,
        }
        next_membership_revision = current_membership_revision + 1
        payload = self._encode_sources(source_refs)
        self._connection.execute(
            "UPDATE enterprise_portfolio_memberships SET membership_status=%s,project_revision=%s,"
            "source_refs_json=%s::jsonb,membership_revision=%s,updated_at=%s "
            "WHERE tenant_id=%s AND portfolio_id=%s AND project_id=%s",
            (membership_status, project_revision, payload, next_membership_revision, occurred_at,
             tenant_id, portfolio_id, project_id),
        )
        next_portfolio_revision = portfolio.revision + 1
        self._advance_portfolio(
            tenant_id, portfolio_id, portfolio.revision, next_portfolio_revision, occurred_at
        )
        after = {
            "project_id": project_id, "membership_status": membership_status,
            "project_revision": project_revision, "source_refs": json.loads(payload),
            "membership_revision": next_membership_revision,
        }
        self._audit(
            tenant_id, portfolio_id, project_id, next_portfolio_revision,
            "membership_updated", actor_id, before, after, occurred_at,
        )
        return PortfolioMembershipRecord(
            tenant_id, portfolio_id, project_id, membership_status, project_revision,
            source_refs, next_membership_revision, occurred_at,
        )

    def get_portfolio(self, tenant_id: str, portfolio_id: str) -> PortfolioRecord:
        row = self._connection.execute(
            "SELECT tenant_id,portfolio_id,revision,created_at,updated_at "
            "FROM enterprise_portfolios WHERE tenant_id=%s AND portfolio_id=%s",
            (tenant_id, portfolio_id),
        ).fetchone()
        if row is None:
            raise KeyError("PORTFOLIO_NOT_FOUND")
        return PortfolioRecord(str(row[0]), str(row[1]), int(row[2]), row[3], row[4])

    def list_memberships(self, tenant_id: str, portfolio_id: str) -> tuple[PortfolioMembershipRecord, ...]:
        self.get_portfolio(tenant_id, portfolio_id)
        rows = self._connection.execute(
            "SELECT tenant_id,portfolio_id,project_id,membership_status,project_revision,"
            "source_refs_json,membership_revision,updated_at "
            "FROM enterprise_portfolio_memberships "
            "WHERE tenant_id=%s AND portfolio_id=%s ORDER BY project_id",
            (tenant_id, portfolio_id),
        ).fetchall()
        return tuple(
            PortfolioMembershipRecord(
                str(row[0]), str(row[1]), str(row[2]), str(row[3]), int(row[4]),
                self._decode_sources(row[5]), int(row[6]), row[7],
            )
            for row in rows
        )

    def get_snapshot_records(
        self, tenant_id: str, portfolio_id: str
    ) -> tuple[PortfolioRecord, tuple[PortfolioMembershipRecord, ...]]:
        """Read portfolio revision and its ordered memberships in one MVCC statement."""
        rows = self._connection.execute(
            "SELECT p.tenant_id,p.portfolio_id,p.revision,p.created_at,p.updated_at,"
            "m.project_id,m.membership_status,m.project_revision,m.source_refs_json,"
            "m.membership_revision,m.updated_at "
            "FROM enterprise_portfolios p LEFT JOIN enterprise_portfolio_memberships m "
            "ON m.tenant_id=p.tenant_id AND m.portfolio_id=p.portfolio_id "
            "WHERE p.tenant_id=%s AND p.portfolio_id=%s ORDER BY m.project_id",
            (tenant_id, portfolio_id),
        ).fetchall()
        if not rows:
            raise KeyError("PORTFOLIO_NOT_FOUND")
        first = rows[0]
        portfolio = PortfolioRecord(
            str(first[0]), str(first[1]), int(first[2]), first[3], first[4]
        )
        memberships = tuple(
            PortfolioMembershipRecord(
                str(row[0]), str(row[1]), str(row[5]), str(row[6]), int(row[7]),
                self._decode_sources(row[8]), int(row[9]), row[10],
            )
            for row in rows if row[5] is not None
        )
        return portfolio, memberships

    def _lock_portfolio(
        self, tenant_id: str, portfolio_id: str, expected_revision: int
    ) -> PortfolioRecord:
        row = self._connection.execute(
            "SELECT tenant_id,portfolio_id,revision,created_at,updated_at "
            "FROM enterprise_portfolios WHERE tenant_id=%s AND portfolio_id=%s FOR UPDATE",
            (tenant_id, portfolio_id),
        ).fetchone()
        if row is None:
            raise KeyError("PORTFOLIO_NOT_FOUND")
        record = PortfolioRecord(str(row[0]), str(row[1]), int(row[2]), row[3], row[4])
        if record.revision != expected_revision:
            raise PortfolioControlRevisionConflict("PORTFOLIO_REVISION_CONFLICT")
        return record

    def _advance_portfolio(
        self, tenant_id: str, portfolio_id: str, current: int, next_revision: int,
        occurred_at: datetime,
    ) -> None:
        result = self._connection.execute(
            "UPDATE enterprise_portfolios SET revision=%s,updated_at=%s "
            "WHERE tenant_id=%s AND portfolio_id=%s AND revision=%s",
            (next_revision, occurred_at, tenant_id, portfolio_id, current),
        )
        if getattr(result, "rowcount", 1) != 1:
            raise PortfolioControlRevisionConflict("PORTFOLIO_REVISION_CONFLICT")

    def _audit(
        self, tenant_id: str, portfolio_id: str, project_id: str | None,
        revision: int, action: str, actor_id: str, before: dict | None,
        after: dict, occurred_at: datetime,
    ) -> None:
        self._connection.execute(
            "INSERT INTO enterprise_portfolio_audit "
            "(audit_id,tenant_id,portfolio_id,project_id,portfolio_revision,action,actor_id,"
            "before_state,after_state,occurred_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s)",
            (str(uuid.uuid4()), tenant_id, portfolio_id, project_id, revision, action,
             actor_id, None if before is None else json.dumps(before, sort_keys=True),
             json.dumps(after, sort_keys=True), occurred_at),
        )

    @staticmethod
    def _validate_scope(
        tenant_id: str, portfolio_id: str, actor_id: str, occurred_at: datetime
    ) -> None:
        for name, value in (
            ("tenant_id", tenant_id), ("portfolio_id", portfolio_id), ("actor_id", actor_id)
        ):
            if not isinstance(value, str) or not value.strip():
                raise PortfolioControlPersistenceError(f"INVALID_PORTFOLIO_{name.upper()}")
        if not isinstance(occurred_at, datetime) or occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise PortfolioControlPersistenceError("PORTFOLIO_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")

    @staticmethod
    def _validate_membership(
        project_id: str, membership_status: str, project_revision: int,
        source_refs: tuple[SourceReference, ...],
    ) -> None:
        if not isinstance(project_id, str) or not project_id.strip():
            raise PortfolioControlPersistenceError("INVALID_PORTFOLIO_PROJECT_ID")
        if membership_status not in {"included", "on_hold", "excluded"}:
            raise PortfolioControlPersistenceError("INVALID_PORTFOLIO_MEMBERSHIP_STATUS")
        if (
            isinstance(project_revision, bool) or not isinstance(project_revision, int)
            or not 0 <= project_revision <= MAX_SAFE_REVISION
        ):
            raise PortfolioControlPersistenceError("INVALID_PORTFOLIO_PROJECT_REVISION")
        if not isinstance(source_refs, tuple) or not source_refs:
            raise PortfolioControlPersistenceError("PORTFOLIO_MEMBERSHIP_SOURCE_REQUIRED")
        for source in source_refs:
            if not isinstance(source, SourceReference) or source.revision != project_revision:
                raise PortfolioControlPersistenceError("PORTFOLIO_SOURCE_REVISION_MISMATCH")

    @staticmethod
    def _encode_sources(source_refs: tuple[SourceReference, ...]) -> str:
        return json.dumps(
            [
                {
                    "source_id": item.source_id, "source_type": item.source_type,
                    "locator": item.locator, "revision": item.revision,
                    "excerpt_key": item.excerpt_key, "content_hash": item.content_hash,
                }
                for item in source_refs
            ],
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )

    @staticmethod
    def _decode_sources(value: Any) -> tuple[SourceReference, ...]:
        if isinstance(value, str):
            value = json.loads(value)
        if not isinstance(value, list) or not value:
            raise PortfolioControlPersistenceError("PORTFOLIO_MEMBERSHIP_SOURCE_REQUIRED")
        return tuple(SourceReference(**item) for item in value)


class PostgresProjectLifecycleFactsReader:
    """Reads project identity/status/revision from the existing Engineering lifecycle store.

    It is deliberately read-only and tenant-qualified. Project-level user authorization is
    still enforced by the Enterprise consumer before any snapshot is exposed.
    """

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def get_project_facts(self, tenant_id: str, project_id: str) -> PortfolioProjectFacts:
        row = self._connection.execute(
            "SELECT project_id,revision,status FROM project_lifecycle_projects "
            "WHERE tenant_id=%s AND project_id=%s",
            (tenant_id, project_id),
        ).fetchone()
        if row is None:
            raise KeyError("ENGINEERING_PROJECT_NOT_FOUND")
        facts = PortfolioProjectFacts(str(row[0]), int(row[1]), str(row[2]))
        facts.validate()
        return facts


class PostgresPortfolioControlSnapshotProvider:
    """Production read provider over canonical membership + authoritative Engineering facts."""

    def __init__(
        self,
        repository: PostgresPortfolioControlRepository,
        project_facts_reader: PortfolioProjectFactsReader,
        *,
        clock=lambda: datetime.now(timezone.utc),
    ) -> None:
        self._repository = repository
        self._project_facts_reader = project_facts_reader
        self._clock = clock

    def get_snapshot(self, portfolio_id: str, *, tenant_id: str) -> PortfolioControlSnapshot:
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise PortfolioControlPersistenceError("INVALID_PORTFOLIO_TENANT_ID")
        portfolio, memberships = self._repository.get_snapshot_records(
            tenant_id, portfolio_id
        )
        if not memberships:
            raise PortfolioControlPersistenceError("PORTFOLIO_SNAPSHOT_PROJECTS_REQUIRED")
        projects: list[PortfolioProjectControlInput] = []
        source_refs: list[SourceReference] = []
        for membership in memberships:
            facts = self._project_facts_reader.get_project_facts(tenant_id, membership.project_id)
            facts.validate()
            if facts.project_id != membership.project_id:
                raise PortfolioControlPersistenceError("PORTFOLIO_PROJECT_SOURCE_ID_MISMATCH")
            if facts.project_revision != membership.project_revision:
                raise PortfolioControlPersistenceError("PORTFOLIO_PROJECT_SOURCE_STALE")
            if not membership.source_refs:
                raise PortfolioControlPersistenceError("PORTFOLIO_MEMBERSHIP_SOURCE_REQUIRED")
            for source in membership.source_refs:
                if source.revision != membership.project_revision:
                    raise PortfolioControlPersistenceError("PORTFOLIO_SOURCE_REVISION_STALE")
                source_refs.append(source)
            projects.append(
                PortfolioProjectControlInput(
                    project_id=membership.project_id,
                    project_revision=membership.project_revision,
                    membership_status=membership.membership_status,
                    status=facts.status,
                    name_key=facts.name_key,
                    **self._result_refs(membership.source_refs),
                )
            )
        # Stable identity/time for the same persisted revision set and ordered inputs.
        generated_at = max(
            [portfolio.updated_at, *(membership.updated_at for membership in memberships)]
        )
        identity = {
            "tenant_id": tenant_id, "portfolio_id": portfolio_id,
            "portfolio_revision": portfolio.revision,
            "projects": [project.as_dict() for project in projects],
            "source_refs": [self._source_dict(source) for source in source_refs],
        }
        snapshot_id = "pcs-" + hashlib.sha256(
            json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        snapshot = PortfolioControlSnapshot(
            snapshot_id=snapshot_id, portfolio_id=portfolio_id, tenant_id=tenant_id,
            generated_at=generated_at, projects=tuple(projects), source_refs=tuple(source_refs),
        )
        snapshot.validate()
        return snapshot

    @staticmethod
    def _result_refs(source_refs: tuple[SourceReference, ...]) -> dict[str, str | None]:
        mapping = {
            "schedule": "schedule_result_ref", "progress": "progress_result_ref",
            "cost": "cost_result_ref", "resource": "resource_result_ref",
            "risk": "risk_result_ref", "claim": "claim_result_ref",
            "procurement": "procurement_result_ref",
        }
        result: dict[str, str | None] = {value: None for value in mapping.values()}
        for source in source_refs:
            field = mapping.get(source.source_type.lower())
            if field is None:
                continue
            if result[field] is not None:
                raise PortfolioControlPersistenceError("DUPLICATE_PORTFOLIO_RESULT_REFERENCE")
            result[field] = source.locator
        return result

    @staticmethod
    def _source_dict(source: SourceReference) -> dict[str, object]:
        return {
            "source_id": source.source_id, "source_type": source.source_type,
            "locator": source.locator, "revision": source.revision,
            "excerpt_key": source.excerpt_key, "content_hash": source.content_hash,
        }


__all__ = [
    "PortfolioControlPersistenceError", "PortfolioControlRevisionConflict",
    "PortfolioMembershipRecord", "PortfolioProjectFacts", "PortfolioProjectFactsReader",
    "PortfolioRecord", "PostgresProjectLifecycleFactsReader", "PostgresPortfolioControlRepository",
    "PostgresPortfolioControlSnapshotProvider",
]
