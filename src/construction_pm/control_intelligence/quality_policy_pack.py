from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Mapping, Protocol

from construction_pm.backend_p0.models import BackendScope


SCORING_METHOD = "weighted_pass_rate.v1"
_ALLOWED_UNITS = frozenset({"working-hour", "working-day"})
_ALLOWED_RULES = frozenset({"positive_lag", "activity_duration", "constraints_per_activity"})
_ALLOWED_SEVERITIES = frozenset({"warning", "critical"})


class ScheduleQualityPolicyError(ValueError):
    """Raised when a versioned schedule-quality policy is invalid or conflicts."""


def _decimal(value: object, code: str, *, minimum: Decimal = Decimal("0")) -> Decimal:
    if isinstance(value, bool):
        raise ScheduleQualityPolicyError(code)
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ScheduleQualityPolicyError(code) from exc
    if not result.is_finite() or result < minimum:
        raise ScheduleQualityPolicyError(code)
    return result


def _severity(rule: Mapping[str, object], code: str) -> None:
    if rule.get("severity") not in _ALLOWED_SEVERITIES:
        raise ScheduleQualityPolicyError(code)


def _validate_thresholds(value: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(value, Mapping) or not value:
        raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_THRESHOLDS_REQUIRED")
    if set(value) != _ALLOWED_RULES:
        raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_ALL_RULES_REQUIRED")
    normalized: dict[str, object] = {}
    for rule_id, raw in value.items():
        if not isinstance(raw, Mapping):
            raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_RULE_INVALID")
        _severity(raw, "SCHEDULE_QUALITY_POLICY_RULE_SEVERITY_INVALID")
        rule: dict[str, object] = {"severity": raw["severity"]}
        if rule_id == "positive_lag":
            date_limit = raw.get("date_based_max_working_days")
            time_limits = raw.get("time_aware_max")
            if date_limit is not None:
                parsed = _decimal(date_limit, "SCHEDULE_QUALITY_POLICY_LAG_LIMIT_INVALID")
                if parsed != parsed.to_integral_value():
                    raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_LAG_LIMIT_MUST_BE_INTEGER")
                rule["date_based_max_working_days"] = int(parsed)
            if time_limits is not None:
                if not isinstance(time_limits, Mapping) or not time_limits:
                    raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_LAG_UNIT_LIMITS_INVALID")
                parsed_limits = {}
                for unit, limit in time_limits.items():
                    if unit not in _ALLOWED_UNITS:
                        raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_LAG_UNIT_INVALID")
                    parsed_limits[str(unit)] = str(_decimal(limit, "SCHEDULE_QUALITY_POLICY_LAG_LIMIT_INVALID"))
                rule["time_aware_max"] = parsed_limits
            if date_limit is None or time_limits is None:
                raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_LAG_LIMIT_REQUIRED")
            if set(rule["time_aware_max"]) != _ALLOWED_UNITS:
                raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_LAG_LIMITS_MUST_COVER_SUPPORTED_UNITS")
        elif rule_id == "activity_duration":
            date_limit = raw.get("date_based_max_working_days")
            time_limits = raw.get("time_aware_max")
            if date_limit is not None:
                rule["date_based_max_working_days"] = str(
                    _decimal(date_limit, "SCHEDULE_QUALITY_POLICY_DURATION_LIMIT_INVALID")
                )
            if time_limits is not None:
                if not isinstance(time_limits, Mapping) or not time_limits:
                    raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_DURATION_UNIT_LIMITS_INVALID")
                parsed_limits = {}
                for unit, limit in time_limits.items():
                    if unit not in _ALLOWED_UNITS:
                        raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_DURATION_UNIT_INVALID")
                    parsed_limits[str(unit)] = str(_decimal(limit, "SCHEDULE_QUALITY_POLICY_DURATION_LIMIT_INVALID"))
                rule["time_aware_max"] = parsed_limits
            if date_limit is None or time_limits is None:
                raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_DURATION_LIMIT_REQUIRED")
            if set(rule["time_aware_max"]) != _ALLOWED_UNITS:
                raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_DURATION_LIMITS_MUST_COVER_SUPPORTED_UNITS")
        else:
            maximum = raw.get("maximum")
            if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 0:
                raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_CONSTRAINT_LIMIT_INVALID")
            rule["maximum"] = maximum
        normalized[str(rule_id)] = rule
    return normalized


def _validate_weights(
    value: Mapping[str, object], enabled_rules: set[str]
) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != enabled_rules:
        raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_WEIGHTS_MUST_MATCH_ENABLED_RULES")
    weights: dict[str, Decimal] = {
        rule: _decimal(raw, "SCHEDULE_QUALITY_POLICY_WEIGHT_INVALID", minimum=Decimal("0.0000000001"))
        for rule, raw in value.items()
    }
    if sum(weights.values(), Decimal("0")) != Decimal("1"):
        raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_WEIGHTS_MUST_SUM_TO_ONE")
    return {key: str(weights[key]) for key in sorted(weights)}


@dataclass(frozen=True)
class ScheduleQualityPolicyPack:
    scope: BackendScope
    policy_id: str
    version: str
    name: str
    scoring_method: str
    thresholds: Mapping[str, object]
    weights: Mapping[str, str]
    created_by: str
    created_at: datetime
    approved_by: str | None = None
    approved_at: datetime | None = None

    def validate(self) -> None:
        self.scope.validate()
        for value, code in (
            (self.policy_id, "SCHEDULE_QUALITY_POLICY_ID_REQUIRED"),
            (self.version, "SCHEDULE_QUALITY_POLICY_VERSION_REQUIRED"),
            (self.name, "SCHEDULE_QUALITY_POLICY_NAME_REQUIRED"),
            (self.created_by, "SCHEDULE_QUALITY_POLICY_CREATOR_REQUIRED"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ScheduleQualityPolicyError(code)
        if self.scoring_method != SCORING_METHOD:
            raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_SCORING_METHOD_UNSUPPORTED")
        normalized = _validate_thresholds(self.thresholds)
        _validate_weights(self.weights, set(normalized))
        for stamp in (self.created_at, self.approved_at):
            if stamp is not None and (
                not isinstance(stamp, datetime)
                or stamp.tzinfo is None
                or stamp.utcoffset() is None
            ):
                raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_TIMESTAMP_INVALID")
        if (self.approved_by is None) != (self.approved_at is None):
            raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_APPROVAL_INCOMPLETE")


class ScheduleQualityPolicyRepository(Protocol):
    def create(self, pack: ScheduleQualityPolicyPack) -> ScheduleQualityPolicyPack: ...
    def approve(
        self, scope: BackendScope, policy_id: str, version: str,
        *, approved_by: str, approved_at: datetime | None = None,
    ) -> ScheduleQualityPolicyPack: ...
    def get(
        self, scope: BackendScope, policy_id: str, version: str
    ) -> ScheduleQualityPolicyPack | None: ...
    def list(self, scope: BackendScope) -> tuple[ScheduleQualityPolicyPack, ...]: ...
    def latest_approved(self, scope: BackendScope) -> ScheduleQualityPolicyPack | None: ...


def _pack_json(pack: ScheduleQualityPolicyPack) -> tuple[str, str]:
    return (
        json.dumps(dict(pack.thresholds), sort_keys=True, separators=(",", ":"), allow_nan=False),
        json.dumps(dict(pack.weights), sort_keys=True, separators=(",", ":"), allow_nan=False),
    )


def _decode(row: tuple[object, ...]) -> ScheduleQualityPolicyPack:
    try:
        (
            tenant_id, project_id, project_revision, policy_id, version, name,
            scoring_method, thresholds_json, weights_json, created_by, created_at,
            approved_by, approved_at,
        ) = row
        pack = ScheduleQualityPolicyPack(
            scope=BackendScope(str(tenant_id), str(project_id), int(project_revision)),
            policy_id=str(policy_id),
            version=str(version),
            name=str(name),
            scoring_method=str(scoring_method),
            thresholds=json.loads(str(thresholds_json)),
            weights=json.loads(str(weights_json)),
            created_by=str(created_by),
            created_at=datetime.fromisoformat(str(created_at)),
            approved_by=None if approved_by is None else str(approved_by),
            approved_at=None if approved_at is None else datetime.fromisoformat(str(approved_at)),
        )
        pack.validate()
        return pack
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        if isinstance(exc, ScheduleQualityPolicyError):
            raise
        raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_STORED_RECORD_INVALID") from exc


class _SqlScheduleQualityPolicyRepository:
    placeholder = "?"

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def _initialize(self, *, postgres: bool) -> None:
        if postgres:
            self.connection.execute(
                "CREATE TABLE IF NOT EXISTS schedule_quality_policy_pack ("
                "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
                "policy_id TEXT NOT NULL, version TEXT NOT NULL, name TEXT NOT NULL, scoring_method TEXT NOT NULL, "
                "thresholds_json TEXT NOT NULL, weights_json TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL, "
                "PRIMARY KEY (tenant_id, project_id, policy_id, version))"
            )
            self.connection.execute(
                "CREATE TABLE IF NOT EXISTS schedule_quality_policy_approval ("
                "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, policy_id TEXT NOT NULL, version TEXT NOT NULL, "
                "approved_by TEXT NOT NULL, approved_at TEXT NOT NULL, "
                "PRIMARY KEY (tenant_id, project_id, policy_id, version), "
                "FOREIGN KEY (tenant_id, project_id, policy_id, version) REFERENCES "
                "schedule_quality_policy_pack (tenant_id, project_id, policy_id, version))"
            )
            self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_schedule_quality_policy_approved "
                "ON schedule_quality_policy_approval (tenant_id, project_id, approved_at)"
            )
            self.connection.execute(
                "CREATE OR REPLACE FUNCTION cubi_schedule_quality_policy_no_mutation() "
                "RETURNS TRIGGER LANGUAGE plpgsql AS "
                "'BEGIN RAISE EXCEPTION ''SCHEDULE_QUALITY_POLICY_IMMUTABLE''; END;'"
            )
            for table in ("schedule_quality_policy_pack", "schedule_quality_policy_approval"):
                trigger = "trg_" + table + "_no_mutation"
                self.connection.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
                self.connection.execute(
                    f"CREATE TRIGGER {trigger} BEFORE UPDATE OR DELETE ON {table} "
                    "FOR EACH ROW EXECUTE FUNCTION cubi_schedule_quality_policy_no_mutation()"
                )
            return
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS schedule_quality_policy_pack ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL, "
            "policy_id TEXT NOT NULL, version TEXT NOT NULL, name TEXT NOT NULL, scoring_method TEXT NOT NULL, "
            "thresholds_json TEXT NOT NULL, weights_json TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, policy_id, version))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS schedule_quality_policy_approval ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, policy_id TEXT NOT NULL, version TEXT NOT NULL, "
            "approved_by TEXT NOT NULL, approved_at TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, policy_id, version), "
            "FOREIGN KEY (tenant_id, project_id, policy_id, version) REFERENCES "
            "schedule_quality_policy_pack (tenant_id, project_id, policy_id, version))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_schedule_quality_policy_approved "
            "ON schedule_quality_policy_approval (tenant_id, project_id, approved_at)"
        )
        for table in ("schedule_quality_policy_pack", "schedule_quality_policy_approval"):
            self.connection.execute(
                f"CREATE TRIGGER IF NOT EXISTS trg_{table}_no_update BEFORE UPDATE ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'SCHEDULE_QUALITY_POLICY_IMMUTABLE'); END"
            )
            self.connection.execute(
                f"CREATE TRIGGER IF NOT EXISTS trg_{table}_no_delete BEFORE DELETE ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'SCHEDULE_QUALITY_POLICY_IMMUTABLE'); END"
            )

    def create(self, pack: ScheduleQualityPolicyPack) -> ScheduleQualityPolicyPack:
        pack.validate()
        thresholds_json, weights_json = _pack_json(pack)
        p = self.placeholder
        self._insert_pack(pack, thresholds_json, weights_json)
        stored = self.get(pack.scope, pack.policy_id, pack.version)
        if stored is None:
            raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_PERSISTENCE_FAILED")
        if (
            stored.scope != pack.scope or stored.name != pack.name
            or stored.scoring_method != pack.scoring_method
            or dict(stored.thresholds) != dict(pack.thresholds)
            or dict(stored.weights) != dict(pack.weights)
            or stored.created_by != pack.created_by
        ):
            raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_VERSION_REUSED")
        return stored

    def _insert_pack(
        self, pack: ScheduleQualityPolicyPack, thresholds_json: str, weights_json: str
    ) -> None:
        raise NotImplementedError

    def approve(
        self, scope: BackendScope, policy_id: str, version: str,
        *, approved_by: str, approved_at: datetime | None = None,
    ) -> ScheduleQualityPolicyPack:
        scope.validate()
        if not all(isinstance(x, str) and x.strip() for x in (policy_id, version, approved_by)):
            raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_APPROVAL_INVALID")
        existing = self.get(scope, policy_id, version)
        if existing is None:
            raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_NOT_FOUND")
        stamp = approved_at or datetime.now(timezone.utc)
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_TIMESTAMP_INVALID")
        self._insert_approval(scope, policy_id, version, approved_by, stamp.astimezone(timezone.utc))
        approved = self.get(scope, policy_id, version)
        if approved is None or approved.approved_by != approved_by:
            raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_ALREADY_APPROVED_OR_INVALID")
        return approved

    def _insert_approval(
        self, scope: BackendScope, policy_id: str, version: str,
        approved_by: str, approved_at: datetime,
    ) -> None:
        raise NotImplementedError

    def get(
        self, scope: BackendScope, policy_id: str, version: str
    ) -> ScheduleQualityPolicyPack | None:
        scope.validate()
        if not all(isinstance(x, str) and x.strip() for x in (policy_id, version)):
            raise ScheduleQualityPolicyError("SCHEDULE_QUALITY_POLICY_LOOKUP_INVALID")
        p = self.placeholder
        row = self.connection.execute(
            "SELECT p.tenant_id,p.project_id,p.project_revision,p.policy_id,p.version,p.name,p.scoring_method,"
            "p.thresholds_json,p.weights_json,p.created_by,p.created_at,a.approved_by,a.approved_at "
            "FROM schedule_quality_policy_pack p LEFT JOIN schedule_quality_policy_approval a "
            "ON a.tenant_id=p.tenant_id AND a.project_id=p.project_id AND a.policy_id=p.policy_id AND a.version=p.version "
            "WHERE p.tenant_id=" + p + " AND p.project_id=" + p + " AND p.policy_id=" + p + " AND p.version=" + p,
            (scope.tenant_id, scope.project_id, policy_id, version),
        ).fetchone()
        return None if row is None else _decode(row)

    def list(self, scope: BackendScope) -> tuple[ScheduleQualityPolicyPack, ...]:
        scope.validate()
        p = self.placeholder
        rows = self.connection.execute(
            "SELECT p.tenant_id,p.project_id,p.project_revision,p.policy_id,p.version,p.name,p.scoring_method,"
            "p.thresholds_json,p.weights_json,p.created_by,p.created_at,a.approved_by,a.approved_at "
            "FROM schedule_quality_policy_pack p LEFT JOIN schedule_quality_policy_approval a "
            "ON a.tenant_id=p.tenant_id AND a.project_id=p.project_id AND a.policy_id=p.policy_id AND a.version=p.version "
            "WHERE p.tenant_id=" + p + " AND p.project_id=" + p + " ORDER BY p.created_at DESC,p.policy_id,p.version",
            (scope.tenant_id, scope.project_id),
        ).fetchall()
        return tuple(_decode(row) for row in rows)

    def latest_approved(self, scope: BackendScope) -> ScheduleQualityPolicyPack | None:
        scope.validate()
        p = self.placeholder
        row = self.connection.execute(
            "SELECT p.tenant_id,p.project_id,p.project_revision,p.policy_id,p.version,p.name,p.scoring_method,"
            "p.thresholds_json,p.weights_json,p.created_by,p.created_at,a.approved_by,a.approved_at "
            "FROM schedule_quality_policy_pack p JOIN schedule_quality_policy_approval a "
            "ON a.tenant_id=p.tenant_id AND a.project_id=p.project_id AND a.policy_id=p.policy_id AND a.version=p.version "
            "WHERE p.tenant_id=" + p + " AND p.project_id=" + p + " ORDER BY a.approved_at DESC,p.policy_id,p.version LIMIT 1",
            (scope.tenant_id, scope.project_id),
        ).fetchone()
        return None if row is None else _decode(row)


class SQLiteScheduleQualityPolicyRepository(_SqlScheduleQualityPolicyRepository):
    """Append-only project-scoped policy packs and approval events."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection)
        self._initialize(postgres=False)

    def _insert_pack(self, pack, thresholds_json: str, weights_json: str) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO schedule_quality_policy_pack "
            "(tenant_id,project_id,project_revision,policy_id,version,name,scoring_method,thresholds_json,weights_json,created_by,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                pack.scope.tenant_id, pack.scope.project_id, pack.scope.project_revision,
                pack.policy_id, pack.version, pack.name, pack.scoring_method,
                thresholds_json, weights_json, pack.created_by, pack.created_at.astimezone(timezone.utc).isoformat(),
            ),
        )

    def _insert_approval(self, scope, policy_id, version, approved_by, approved_at) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO schedule_quality_policy_approval "
            "(tenant_id,project_id,policy_id,version,approved_by,approved_at) VALUES (?,?,?,?,?,?)",
            (scope.tenant_id, scope.project_id, policy_id, version, approved_by, approved_at.isoformat()),
        )


class PostgresScheduleQualityPolicyRepository(_SqlScheduleQualityPolicyRepository):
    """PostgreSQL append-only policy packs and approval events."""

    placeholder = "%s"

    def __init__(self, connection: object) -> None:
        super().__init__(connection)
        self._initialize(postgres=True)

    def _insert_pack(self, pack, thresholds_json: str, weights_json: str) -> None:
        self.connection.execute(
            "INSERT INTO schedule_quality_policy_pack "
            "(tenant_id,project_id,project_revision,policy_id,version,name,scoring_method,thresholds_json,weights_json,created_by,created_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id,project_id,policy_id,version) DO NOTHING",
            (
                pack.scope.tenant_id, pack.scope.project_id, pack.scope.project_revision,
                pack.policy_id, pack.version, pack.name, pack.scoring_method,
                thresholds_json, weights_json, pack.created_by, pack.created_at.astimezone(timezone.utc).isoformat(),
            ),
        )

    def _insert_approval(self, scope, policy_id, version, approved_by, approved_at) -> None:
        self.connection.execute(
            "INSERT INTO schedule_quality_policy_approval "
            "(tenant_id,project_id,policy_id,version,approved_by,approved_at) VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id,project_id,policy_id,version) DO NOTHING",
            (scope.tenant_id, scope.project_id, policy_id, version, approved_by, approved_at.isoformat()),
        )


__all__ = [
    "SCORING_METHOD",
    "PostgresScheduleQualityPolicyRepository",
    "ScheduleQualityPolicyError",
    "ScheduleQualityPolicyPack",
    "ScheduleQualityPolicyRepository",
    "SQLiteScheduleQualityPolicyRepository",
]
