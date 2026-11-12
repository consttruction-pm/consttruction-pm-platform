"""Authoritative CSV export and validated resource import.

The exchange service reads the same authoritative stores the registers use; it
never re-derives facts. Import is limited to the resource master in this slice:
the file is parsed and validated against stored state first, and rows are then
created through the resource API so authorization, calendar/parent checks and
the duplicate rule stay in one place.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping, Sequence

from .application.authorization import (
    AuthorizationContext,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .exchange_persistence import (
    ExchangeIdempotencyRecord,
    ExchangeIdempotencyReuse,
    ExchangeImportRun,
    ExchangeStore,
)
from .p6_resource_master_api import P6ResourceAPI
from .p6_resource_master_repository import RESOURCE_TYPES, P6Resource

RESOURCE_COLUMNS = (
    "resource_id",
    "name",
    "resource_type",
    "parent_resource_id",
    "calendar_id",
    "default_units_per_time",
    "unit_of_measure",
    "email",
    "is_active",
)
ACTIVITY_COLUMNS = (
    "activity_id",
    "name",
    "activity_type",
    "status",
    "actual_start",
    "expected_finish",
    "duration_value",
    "duration_unit",
    "percent_complete",
    "wbs_id",
)
RISK_COLUMNS = (
    "risk_id",
    "title",
    "category",
    "status",
    "probability",
    "impact",
    "score",
    "exposure",
    "owner",
    "response_strategy",
    "date_identified",
)
EXCHANGE_DATASETS: dict[str, dict[str, Any]] = {
    "activities": {"columns": ACTIVITY_COLUMNS, "importable": False},
    "resources": {"columns": RESOURCE_COLUMNS, "importable": True},
    "risks": {"columns": RISK_COLUMNS, "importable": False},
}
MAX_IMPORT_CHARS = 1_000_000
PREVIEW_ROWS = 20
_DECIMAL = re.compile(r"^-?\d+(\.\d+)?$")


class ExchangeError(ValueError):
    """Raised when a dataset, request or file violates the exchange contract."""


class ExchangeAuthorizationError(ValueError):
    """Raised when the caller cannot export or import in this scope."""


def _enum(value: object) -> str:
    return str(getattr(value, "value", value))


def _iso(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _csv(columns: Sequence[str], rows: Sequence[Mapping[str, object]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer, fieldnames=list(columns), extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({column: "" if row.get(column) is None else row[column] for column in columns})
    return buffer.getvalue()


def _row_error(row: int, field: str, code: str) -> dict[str, Any]:
    return {"row": row, "field": field, "code": code}


@dataclass(frozen=True)
class ExchangeService:
    store: ExchangeStore
    activity_repository: object
    resource_repository: object
    resource_api: P6ResourceAPI
    risk_store: object
    authorization_policy: AuthorizationPolicy

    # -- catalogue and export -------------------------------------------------

    def catalogue(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            {
                "dataset": code,
                "columns": list(spec["columns"]),
                "importable": bool(spec["importable"]),
            }
            for code, spec in EXCHANGE_DATASETS.items()
        )

    def export(
        self,
        *,
        scope: BackendScope,
        dataset: str,
        context: AuthorizationContext,
        generated_at: datetime,
    ) -> dict[str, Any]:
        self._check(scope, context, Permission.PROJECT_READ)
        columns, rows = self._export_rows(scope, dataset)
        content = _csv(columns, rows)
        return {
            "dataset": dataset,
            "columns": list(columns),
            "rows": [dict(row) for row in rows[:PREVIEW_ROWS]],
            "row_count": len(rows),
            "content": content,
            "generated_at": generated_at.isoformat(),
            "project_revision": scope.project_revision,
        }

    def _export_rows(
        self, scope: BackendScope, dataset: str
    ) -> tuple[tuple[str, ...], list[dict[str, object]]]:
        spec = EXCHANGE_DATASETS.get(dataset)
        if spec is None:
            raise ExchangeError("EXCHANGE_DATASET_UNKNOWN")
        if dataset == "activities":
            rows = [
                {
                    "activity_id": item.activity_id,
                    "name": item.name,
                    "activity_type": _enum(item.activity_type),
                    "status": _enum(item.status),
                    "actual_start": _iso(item.actual_start),
                    "expected_finish": _iso(item.expected_finish),
                    "duration_value": str(item.duration_value),
                    "duration_unit": _enum(item.duration_unit),
                    "percent_complete": (
                        "" if item.percent_complete is None else item.percent_complete
                    ),
                    "wbs_id": item.wbs_id,
                }
                for item in sorted(
                    self.activity_repository.list(scope),
                    key=lambda item: item.activity_id,
                )
            ]
            return ACTIVITY_COLUMNS, rows
        if dataset == "resources":
            rows = [
                {
                    "resource_id": item.resource_id,
                    "name": item.name,
                    "resource_type": item.resource_type,
                    "parent_resource_id": item.parent_resource_id,
                    "calendar_id": item.calendar_id,
                    "default_units_per_time": item.default_units_per_time,
                    "unit_of_measure": item.unit_of_measure,
                    "email": item.email,
                    "is_active": "true" if item.is_active else "false",
                }
                for item in sorted(
                    self.resource_repository.list(
                        scope.tenant_id, scope.project_id, scope.project_revision
                    ),
                    key=lambda item: item.resource_id,
                )
            ]
            return RESOURCE_COLUMNS, rows
        stored = sorted(
            self.risk_store.list_risks(scope.tenant_id, scope.project_id),
            key=lambda item: item.risk.risk_id,
        )
        rows = [
            {
                "risk_id": item.risk.risk_id,
                "title": item.risk.title,
                "category": item.risk.category,
                "status": item.risk.status,
                "probability": item.risk.probability,
                "impact": item.risk.impact,
                "score": item.risk.score,
                "exposure": item.risk.exposure_level,
                "owner": item.risk.owner,
                "response_strategy": item.risk.response_strategy,
                "date_identified": item.risk.date_identified,
            }
            for item in stored
        ]
        return RISK_COLUMNS, rows

    # -- import ---------------------------------------------------------------

    def preview_import(
        self,
        *,
        scope: BackendScope,
        dataset: str,
        content: str,
        context: AuthorizationContext,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        self._check(scope, context, Permission.PROJECT_READ)
        result = self._validate_import(scope, dataset, content)
        self._record_run(
            scope=scope,
            dataset=dataset,
            mode="preview",
            content=content,
            actor_id=context.user_id,
            occurred_at=occurred_at,
            result=result,
            idempotency_key=None,
        )
        return result

    def apply_import(
        self,
        *,
        scope: BackendScope,
        dataset: str,
        content: str,
        idempotency_key: str,
        context: AuthorizationContext,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        self._check(scope, context, Permission.PROJECT_WRITE)
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ExchangeError("EXCHANGE_IDEMPOTENCY_KEY_REQUIRED")
        key = idempotency_key.strip()
        request_sha = self._request_sha(dataset, content)
        existing = self.store.read_idempotency(
            scope.tenant_id, scope.project_id, key
        )
        if existing is not None:
            if existing.request_sha256 != request_sha:
                raise ExchangeIdempotencyReuse("EXCHANGE_IDEMPOTENCY_KEY_REUSE")
            run = self.store.read_run(scope.tenant_id, scope.project_id, existing.run_id)
            if run is None:
                raise ExchangeError("EXCHANGE_RUN_NOT_FOUND")
            return {**run.result, "run_id": run.run_id, "replayed": True}

        result = self._validate_import(scope, dataset, content)
        if not result["valid"]:
            self._record_run(
                scope=scope,
                dataset=dataset,
                mode="apply",
                content=content,
                actor_id=context.user_id,
                occurred_at=occurred_at,
                result=result,
                idempotency_key=key,
            )
            return result

        created: list[str] = []
        for row in self._apply_order(result["parsed_rows"]):
            resource = P6Resource(
                tenant_id=scope.tenant_id,
                project_id=scope.project_id,
                project_revision=scope.project_revision,
                resource_id=row["resource_id"],
                name=row["name"],
                resource_type=row["resource_type"],
                parent_resource_id=row["parent_resource_id"],
                calendar_id=row["calendar_id"],
                default_units_per_time=row["default_units_per_time"],
                unit_of_measure=row["unit_of_measure"],
                email=row["email"],
                is_active=row["is_active"],
            )
            self.resource_api.create(resource, auth_context=context)
            created.append(row["resource_id"])

        applied = {
            key: value
            for key, value in result.items()
            if key not in {"parsed_rows"}
        }
        applied["created"] = created
        applied["valid"] = True
        applied["replayed"] = False
        run = self._record_run(
            scope=scope,
            dataset=dataset,
            mode="apply",
            content=content,
            actor_id=context.user_id,
            occurred_at=occurred_at,
            result=applied,
            idempotency_key=key,
        )
        applied["run_id"] = run.run_id
        return applied

    def imports(
        self,
        *,
        scope: BackendScope,
        context: AuthorizationContext,
        limit: int = 50,
    ) -> tuple[dict[str, Any], ...]:
        self._check(scope, context, Permission.PROJECT_READ)
        return tuple(
            run.as_dict()
            for run in self.store.list_runs(
                scope.tenant_id, scope.project_id, limit=limit
            )
        )

    def _validate_import(
        self, scope: BackendScope, dataset: str, content: str
    ) -> dict[str, Any]:
        spec = EXCHANGE_DATASETS.get(dataset)
        if spec is None:
            raise ExchangeError("EXCHANGE_DATASET_UNKNOWN")
        if not spec["importable"]:
            raise ExchangeError("EXCHANGE_DATASET_READ_ONLY")
        if not isinstance(content, str) or not content.strip():
            return self._invalid(dataset, spec["columns"], 0, [], [
                {"row": 1, "field": "content", "code": "EXCHANGE_CONTENT_EMPTY"}
            ])
        if len(content) > MAX_IMPORT_CHARS:
            raise ExchangeError("EXCHANGE_CONTENT_TOO_LARGE")

        reader = csv.DictReader(io.StringIO(content))
        fieldnames = list(reader.fieldnames or [])
        errors: list[dict[str, Any]] = []
        columns = spec["columns"]
        for column in columns:
            if column not in fieldnames:
                errors.append(_row_error(1, column, "EXCHANGE_COLUMN_MISSING"))
        for column in fieldnames:
            if column not in columns:
                errors.append(_row_error(1, column, "EXCHANGE_COLUMN_UNKNOWN"))

        parsed: list[dict[str, Any]] = []
        row_count = 0
        for offset, raw in enumerate(reader, start=2):
            if None in raw:
                errors.append(_row_error(offset, "row", "EXCHANGE_ROW_ARITY"))
                continue
            if not any((value or "").strip() for value in raw.values()):
                continue
            row_count += 1
            row, row_errors = self._validate_resource_row(scope, offset, raw)
            errors.extend(row_errors)
            if not row_errors:
                parsed.append(row)

        existing = {
            item.resource_id: item
            for item in self.resource_repository.list(
                scope.tenant_id, scope.project_id, scope.project_revision
            )
        }
        incoming = {row["resource_id"]: row for row in parsed}
        for row in parsed:
            resource_id = row["resource_id"]
            if resource_id in existing:
                errors.append(
                    _row_error(row["_row"], "resource_id", "RESOURCE_ALREADY_EXISTS")
                )
            parent = row["parent_resource_id"]
            if parent is not None and parent not in existing and parent not in incoming:
                errors.append(
                    _row_error(row["_row"], "parent_resource_id", "RESOURCE_PARENT_NOT_FOUND")
                )
        duplicate_seen: set[str] = set()
        for row in parsed:
            if row["resource_id"] in duplicate_seen:
                errors.append(
                    _row_error(row["_row"], "resource_id", "RESOURCE_ID_DUPLICATE_IN_FILE")
                )
            duplicate_seen.add(row["resource_id"])
        cycles = self._cycles(existing, incoming)
        for resource_id in cycles:
            row = incoming.get(resource_id)
            if row is not None:
                errors.append(
                    _row_error(row["_row"], "parent_resource_id", "RESOURCE_HIERARCHY_CYCLE")
                )

        result = {
            "dataset": dataset,
            "columns": list(columns),
            "row_count": row_count,
            "accepted": max(0, row_count - len({e["row"] for e in errors if e["row"] > 1})),
            "rejected": len({e["row"] for e in errors if e["row"] > 1}),
            "valid": not errors,
            "errors": errors,
            "rows": [
                {key: value for key, value in row.items() if key != "_row"}
                for row in parsed[:PREVIEW_ROWS]
            ],
            "parsed_rows": parsed,
        }
        return result

    def _validate_resource_row(
        self, scope: BackendScope, line: int, raw: Mapping[str, Any]
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        errors: list[dict[str, Any]] = []

        def text(field: str) -> str | None:
            value = (raw.get(field) or "").strip()
            return value or None

        resource_id = text("resource_id")
        if resource_id is None or len(resource_id) > 64:
            errors.append(_row_error(line, "resource_id", "INVALID_RESOURCE_ID"))
        name = text("name")
        if name is None or len(name) > 120:
            errors.append(_row_error(line, "name", "INVALID_RESOURCE_NAME"))
        resource_type = text("resource_type") or "labor"
        if resource_type not in RESOURCE_TYPES:
            errors.append(_row_error(line, "resource_type", "INVALID_RESOURCE_TYPE"))
        parent = text("parent_resource_id")
        calendar_id = text("calendar_id")
        if calendar_id is not None:
            known = {
                item.calendar_id
                for item in self.resource_api.calendar_repository.list(scope)
            }
            if calendar_id not in known:
                errors.append(
                    _row_error(line, "calendar_id", "RESOURCE_CALENDAR_NOT_FOUND")
                )
        units = text("default_units_per_time")
        if units is not None and (not _DECIMAL.match(units) or float(units) < 0):
            errors.append(
                _row_error(line, "default_units_per_time", "INVALID_RESOURCE_DEFAULT_UNITS")
            )
        email = text("email")
        if email is not None and ("@" not in email or len(email) > 160):
            errors.append(_row_error(line, "email", "INVALID_RESOURCE_EMAIL"))
        active_text = text("is_active")
        if active_text is None or active_text.lower() in {"true", "1", "yes"}:
            is_active = True
        elif active_text.lower() in {"false", "0", "no"}:
            is_active = False
        else:
            is_active = True
            errors.append(_row_error(line, "is_active", "INVALID_RESOURCE_ACTIVE_FLAG"))
        row = {
            "_row": line,
            "resource_id": resource_id or "",
            "name": name or "",
            "resource_type": resource_type,
            "parent_resource_id": parent,
            "calendar_id": calendar_id,
            "default_units_per_time": units,
            "unit_of_measure": text("unit_of_measure"),
            "email": email,
            "is_active": is_active,
        }
        return row, errors

    @staticmethod
    def _apply_order(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
        """Order accepted rows parents-first so a parent exists before its child."""
        by_id = {row["resource_id"]: row for row in rows}

        def depth(row: Mapping[str, Any]) -> int:
            value = 0
            parent = row["parent_resource_id"]
            seen: set[str] = set()
            while parent in by_id and parent not in seen:
                seen.add(parent)
                value += 1
                parent = by_id[parent]["parent_resource_id"]
            return value

        return sorted(rows, key=lambda row: (depth(row), row["resource_id"]))

    @staticmethod
    def _cycles(
        existing: Mapping[str, P6Resource], incoming: Mapping[str, Mapping[str, Any]]
    ) -> set[str]:
        parents: dict[str, str | None] = {
            resource_id: item.parent_resource_id
            for resource_id, item in existing.items()
        }
        for resource_id, row in incoming.items():
            parents[resource_id] = row["parent_resource_id"]
        cyclic: set[str] = set()
        for resource_id in incoming:
            seen: set[str] = set()
            cursor: str | None = resource_id
            while cursor is not None:
                if cursor in seen:
                    cyclic.add(resource_id)
                    break
                seen.add(cursor)
                cursor = parents.get(cursor)
        return cyclic

    def _invalid(
        self,
        dataset: str,
        columns: Sequence[str],
        row_count: int,
        rows: list[dict[str, Any]],
        errors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "dataset": dataset,
            "columns": list(columns),
            "row_count": row_count,
            "accepted": 0,
            "rejected": 0,
            "valid": False,
            "errors": errors,
            "rows": rows,
            "parsed_rows": [],
        }

    def _record_run(
        self,
        *,
        scope: BackendScope,
        dataset: str,
        mode: str,
        content: str,
        actor_id: str,
        occurred_at: datetime,
        result: Mapping[str, Any],
        idempotency_key: str | None,
    ) -> ExchangeImportRun:
        content_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        stored_result = {
            key: value for key, value in result.items() if key != "parsed_rows"
        }
        run = ExchangeImportRun(
            tenant_id=scope.tenant_id,
            project_id=scope.project_id,
            run_id=self.store.next_run_id(scope.tenant_id, scope.project_id, dataset),
            dataset=dataset,
            mode=mode,
            row_count=int(result.get("row_count", 0)),
            accepted=int(result.get("accepted", 0)),
            rejected=int(result.get("rejected", 0)),
            content_sha256=content_sha,
            actor_id=actor_id,
            occurred_at=occurred_at.isoformat(),
            idempotency_key=idempotency_key,
            result=dict(stored_result),
        )
        self.store.save_run(run)
        if idempotency_key is not None and result.get("valid"):
            self.store.save_idempotency(
                ExchangeIdempotencyRecord(
                    tenant_id=scope.tenant_id,
                    project_id=scope.project_id,
                    idempotency_key=idempotency_key,
                    request_sha256=self._request_sha(dataset, content),
                    run_id=run.run_id,
                    occurred_at=occurred_at.isoformat(),
                )
            )
        return run

    @staticmethod
    def _request_sha(dataset: str, content: str) -> str:
        return hashlib.sha256(
            f"{dataset}\n{content}".encode("utf-8")
        ).hexdigest()

    def _check(
        self,
        scope: BackendScope,
        context: AuthorizationContext,
        permission: Permission,
    ) -> None:
        scope.validate()
        context.validate()
        if (
            context.tenant_id != scope.tenant_id
            or context.project_id != scope.project_id
        ):
            raise ExchangeAuthorizationError("CROSS_SCOPE_ACCESS")
        if not self.authorization_policy.is_allowed(context, permission):
            raise ExchangeAuthorizationError("EXCHANGE_PERMISSION_DENIED")


__all__ = [
    "ACTIVITY_COLUMNS",
    "EXCHANGE_DATASETS",
    "ExchangeAuthorizationError",
    "ExchangeError",
    "ExchangeService",
    "RESOURCE_COLUMNS",
    "RISK_COLUMNS",
]
