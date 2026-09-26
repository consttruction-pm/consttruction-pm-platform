from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator

from .contracts import SourceReference
from .portfolio_control_actions import (
    PortfolioActionStatus,
    PortfolioActionType,
    PortfolioControlAction,
)


@dataclass(frozen=True)
class StoredPortfolioControlAction:
    action: PortfolioControlAction
    action_revision: int


@dataclass(frozen=True)
class PortfolioActionAuditEvent:
    event_id: str
    tenant_id: str
    portfolio_id: str
    action_id: str
    action_revision: int
    event_type: str
    actor_id: str
    occurred_at: datetime
    metadata: dict[str, object]


class PortfolioControlActionStore:
    def create(self, action: PortfolioControlAction) -> StoredPortfolioControlAction:
        raise NotImplementedError

    def get(
        self,
        tenant_id: str,
        portfolio_id: str,
        action_id: str,
    ) -> StoredPortfolioControlAction | None:
        raise NotImplementedError

    def transition(
        self,
        *,
        action: PortfolioControlAction,
        expected_action_revision: int,
        actor_id: str,
        occurred_at: datetime,
        event_type: str,
    ) -> StoredPortfolioControlAction:
        raise NotImplementedError

    def history(
        self,
        tenant_id: str,
        portfolio_id: str,
        action_id: str,
    ) -> tuple[PortfolioActionAuditEvent, ...]:
        raise NotImplementedError


class SQLitePortfolioControlActionStore(PortfolioControlActionStore):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self._savepoint_counter = 0
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS portfolio_control_actions (
                tenant_id TEXT NOT NULL,
                portfolio_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                initial_result_json TEXT,
                action_revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, portfolio_id, action_id),
                UNIQUE (tenant_id, portfolio_id, idempotency_key)
            );

            CREATE TABLE IF NOT EXISTS portfolio_control_action_audit (
                event_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                portfolio_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                action_revision INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                UNIQUE (tenant_id, portfolio_id, action_id, action_revision)
            );

            CREATE INDEX IF NOT EXISTS idx_portfolio_action_audit_action
                ON portfolio_control_action_audit (
                    tenant_id,
                    portfolio_id,
                    action_id,
                    action_revision
                );
            """
        )
        columns = {
            row[1]
            for row in self.connection.execute(
                "PRAGMA table_info(portfolio_control_actions)"
            ).fetchall()
        }
        if "initial_result_json" not in columns:
            self.connection.execute(
                "ALTER TABLE portfolio_control_actions ADD COLUMN initial_result_json TEXT"
            )
        self.connection.execute(
            """
            UPDATE portfolio_control_actions
            SET initial_result_json=payload_json
            WHERE initial_result_json IS NULL
            """
        )
        self.connection.commit()

    def create(self, action: PortfolioControlAction) -> StoredPortfolioControlAction:
        action.validate()
        fingerprint = _fingerprint(action.as_dict())

        with self._transaction():
            existing = self.connection.execute(
                """
                SELECT payload_json, initial_result_json, action_revision, fingerprint
                FROM portfolio_control_actions
                WHERE tenant_id=? AND portfolio_id=? AND idempotency_key=?
                """,
                (action.tenant_id, action.portfolio_id, action.idempotency_key),
            ).fetchone()
            if existing is not None:
                if existing[3] != fingerprint:
                    raise ValueError("PORTFOLIO_ACTION_IDEMPOTENCY_KEY_REUSE")
                return StoredPortfolioControlAction(
                    _action_from_payload(json.loads(existing[1])),
                    1,
                )

            conflict = self.connection.execute(
                """
                SELECT 1 FROM portfolio_control_actions
                WHERE tenant_id=? AND portfolio_id=? AND action_id=?
                """,
                (action.tenant_id, action.portfolio_id, action.action_id),
            ).fetchone()
            if conflict is not None:
                raise ValueError("PORTFOLIO_ACTION_ID_ALREADY_EXISTS")

            stored = StoredPortfolioControlAction(action, 1)
            self.connection.execute(
                """
                INSERT INTO portfolio_control_actions (
                    tenant_id, portfolio_id, action_id, idempotency_key,
                    fingerprint, payload_json, initial_result_json, action_revision,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action.tenant_id,
                    action.portfolio_id,
                    action.action_id,
                    action.idempotency_key,
                    fingerprint,
                    json.dumps(action.as_dict(), sort_keys=True, separators=(",", ":")),
                    json.dumps(action.as_dict(), sort_keys=True, separators=(",", ":")),
                    1,
                    action.requested_at.isoformat(),
                    action.requested_at.isoformat(),
                ),
            )
            self._append_audit(
                action=action,
                action_revision=1,
                event_type="proposed",
                actor_id=action.requested_by,
                occurred_at=action.requested_at,
            )
            return stored

    def get(
        self,
        tenant_id: str,
        portfolio_id: str,
        action_id: str,
    ) -> StoredPortfolioControlAction | None:
        row = self.connection.execute(
            """
            SELECT payload_json, action_revision
            FROM portfolio_control_actions
            WHERE tenant_id=? AND portfolio_id=? AND action_id=?
            """,
            (tenant_id, portfolio_id, action_id),
        ).fetchone()
        if row is None:
            return None
        return StoredPortfolioControlAction(
            _action_from_payload(json.loads(row[0])),
            int(row[1]),
        )

    def transition(
        self,
        *,
        action: PortfolioControlAction,
        expected_action_revision: int,
        actor_id: str,
        occurred_at: datetime,
        event_type: str,
    ) -> StoredPortfolioControlAction:
        action.validate()
        if not actor_id.strip():
            raise ValueError("PORTFOLIO_ACTION_AUDIT_ACTOR_REQUIRED")
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise ValueError("PORTFOLIO_ACTION_AUDIT_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
        if expected_action_revision < 1:
            raise ValueError("INVALID_EXPECTED_ACTION_REVISION")

        with self._transaction():
            row = self.connection.execute(
                """
                SELECT payload_json, action_revision
                FROM portfolio_control_actions
                WHERE tenant_id=? AND portfolio_id=? AND action_id=?
                """,
                (action.tenant_id, action.portfolio_id, action.action_id),
            ).fetchone()
            if row is None:
                raise ValueError("PORTFOLIO_ACTION_NOT_FOUND")

            current_revision = int(row[1])
            if current_revision != expected_action_revision:
                raise ValueError("PORTFOLIO_ACTION_STALE_REVISION")

            next_revision = current_revision + 1
            payload = json.dumps(
                action.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
            )
            fp = _fingerprint(action.as_dict())
            self.connection.execute(
                """
                UPDATE portfolio_control_actions
                SET payload_json=?, fingerprint=?, action_revision=?, updated_at=?
                WHERE tenant_id=? AND portfolio_id=? AND action_id=?
                  AND action_revision=?
                """,
                (
                    payload,
                    fp,
                    next_revision,
                    occurred_at.isoformat(),
                    action.tenant_id,
                    action.portfolio_id,
                    action.action_id,
                    expected_action_revision,
                ),
            )
            self._append_audit(
                action=action,
                action_revision=next_revision,
                event_type=event_type,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )
            return StoredPortfolioControlAction(action, next_revision)

    def history(
        self,
        tenant_id: str,
        portfolio_id: str,
        action_id: str,
    ) -> tuple[PortfolioActionAuditEvent, ...]:
        rows = self.connection.execute(
            """
            SELECT event_id, action_revision, event_type, actor_id,
                   occurred_at, metadata_json
            FROM portfolio_control_action_audit
            WHERE tenant_id=? AND portfolio_id=? AND action_id=?
            ORDER BY action_revision ASC
            """,
            (tenant_id, portfolio_id, action_id),
        ).fetchall()
        return tuple(
            PortfolioActionAuditEvent(
                event_id=row[0],
                tenant_id=tenant_id,
                portfolio_id=portfolio_id,
                action_id=action_id,
                action_revision=int(row[1]),
                event_type=row[2],
                actor_id=row[3],
                occurred_at=datetime.fromisoformat(row[4]),
                metadata=json.loads(row[5]),
            )
            for row in rows
        )

    def _append_audit(
        self,
        *,
        action: PortfolioControlAction,
        action_revision: int,
        event_type: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> None:
        event_id = _event_id(
            action.tenant_id,
            action.portfolio_id,
            action.action_id,
            action_revision,
            event_type,
        )
        self.connection.execute(
            """
            INSERT INTO portfolio_control_action_audit (
                event_id, tenant_id, portfolio_id, action_id,
                action_revision, event_type, actor_id,
                occurred_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                action.tenant_id,
                action.portfolio_id,
                action.action_id,
                action_revision,
                event_type,
                actor_id,
                occurred_at.isoformat(),
                json.dumps(
                    {
                        "action_type": action.action_type.value,
                        "status": action.status.value,
                        "expected_portfolio_revision": action.expected_portfolio_revision,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            ),
        )

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        outer = self.connection.in_transaction
        savepoint = None
        if outer:
            self._savepoint_counter += 1
            savepoint = f"portfolio_action_sp_{self._savepoint_counter}"
            self.connection.execute(f"SAVEPOINT {savepoint}")
        else:
            self.connection.execute("BEGIN IMMEDIATE")

        try:
            yield None
        except Exception:
            if savepoint is not None:
                self.connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                self.connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            else:
                self.connection.rollback()
            raise
        else:
            if savepoint is not None:
                self.connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            else:
                self.connection.commit()


def _fingerprint(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _event_id(
    tenant_id: str,
    portfolio_id: str,
    action_id: str,
    action_revision: int,
    event_type: str,
) -> str:
    parts = (tenant_id, portfolio_id, action_id, str(action_revision), event_type)
    canonical = b"".join(
        len(part.encode("utf-8")).to_bytes(4, "big") + part.encode("utf-8")
        for part in parts
    )
    return hashlib.sha256(canonical).hexdigest()


def _action_from_payload(payload: dict[str, object]) -> PortfolioControlAction:
    refs = tuple(
        SourceReference(
            source_id=item["source_id"],
            source_type=item["source_type"],
            locator=item["locator"],
            revision=int(item["revision"]),
            excerpt_key=item.get("excerpt_key"),
            content_hash=item.get("content_hash"),
        )
        for item in payload.get("evidence_refs", [])
    )
    return PortfolioControlAction(
        action_id=str(payload["action_id"]),
        tenant_id=str(payload["tenant_id"]),
        portfolio_id=str(payload["portfolio_id"]),
        portfolio_revision=int(payload["portfolio_revision"]),
        target_type=str(payload["target_type"]),
        target_id=str(payload["target_id"]),
        action_type=next(
            member
            for member in PortfolioActionType
            if member.value == payload["action_type"]
        ),
        source_snapshot_id=str(payload["source_snapshot_id"]),
        expected_portfolio_revision=int(payload["expected_portfolio_revision"]),
        requested_by=str(payload["requested_by"]),
        requested_at=datetime.fromisoformat(str(payload["requested_at"])),
        status=next(
            member
            for member in PortfolioActionStatus
            if member.value == payload["status"]
        ),
        requires_approval=bool(payload["requires_approval"]),
        idempotency_key=str(payload["idempotency_key"]),
        rationale_key=payload.get("rationale_key"),
        evidence_refs=refs,
        decided_by=payload.get("decided_by"),
        decided_at=datetime.fromisoformat(str(payload["decided_at"]))
        if payload.get("decided_at")
        else None,
    )
