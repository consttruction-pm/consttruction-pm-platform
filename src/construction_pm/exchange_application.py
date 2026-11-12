"""Authoritative CSV/XLSX export and validated register import.

The exchange service reads the same authoritative stores the registers use; it
never re-derives facts. Supported imports are the resource master, the WBS
hierarchy, activity master rows, resource assignments and cost/expense records:
every file is parsed and fully validated against stored state before apply, and
apply runs through the canonical APIs inside one transaction so a failing row
rolls the whole batch back.
"""

from __future__ import annotations

import base64
import zipfile
import binascii
import csv
import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from .application.authorization import (
    AuthorizationContext,
    AuthorizationPolicy,
    Permission,
)
from .activity_master_repository import ActivityMaster
from .backend_p0.models import BackendScope
from .exchange_persistence import (
    ExchangeIdempotencyRecord,
    ExchangeIdempotencyReuse,
    ExchangeImportRun,
    ExchangeStore,
)
from .p6_activity_master_api import P6ActivityMasterAPI
from .p6_expense_repository import P6Expense, P6ExpenseApplicationService
from .p6_resource_assignment_repository import (
    P6ResourceAssignment,
    P6ResourceAssignmentApplicationService,
)
from .p6_resource_master_api import P6ResourceAPI
from .p6_resource_master_repository import RESOURCE_TYPES, P6Resource
from .p6_wbs_master_api import P6WBSMasterAPI
from .scheduling.activity import ActivityStatus, ActivityType
from .scheduling.time_duration import DurationUnit
from .wbs_master_repository import WBSMaster, WBSParentKind

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
WBS_COLUMNS = (
    "wbs_id",
    "code",
    "name",
    "parent_wbs_id",
    "sequence_number",
)
ASSIGNMENT_COLUMNS = (
    "assignment_id",
    "activity_id",
    "resource_id",
    "role_id",
    "units",
    "actual_units",
    "remaining_units",
    "planned_cost",
    "actual_cost",
    "remaining_cost",
    "unit",
    "currency",
    "calendar_id",
)
COST_COLUMNS = (
    "expense_id",
    "name",
    "category",
    "activity_id",
    "wbs_id",
    "expense_date",
    "planned_cost",
    "actual_cost",
    "remaining_cost",
    "currency",
    "note",
)
EXCHANGE_DATASETS: dict[str, dict[str, Any]] = {
    "activities": {"columns": ACTIVITY_COLUMNS, "importable": True},
    "resources": {"columns": RESOURCE_COLUMNS, "importable": True},
    "risks": {"columns": RISK_COLUMNS, "importable": False},
    "wbs": {"columns": WBS_COLUMNS, "importable": True},
    "assignments": {"columns": ASSIGNMENT_COLUMNS, "importable": True},
    "costs": {"columns": COST_COLUMNS, "importable": True},
}
MAX_IMPORT_CHARS = 1_000_000
MAX_XLSX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_XLSX_ROWS = 50_000
PREVIEW_ROWS = 20
EXCHANGE_EXPORT_FORMATS = ("csv", "xlsx")
_XLSX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
_DECIMAL = re.compile(r"^-?\d+(\.\d+)?$")
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
_TYPED_XLSX_COLUMNS: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "activities": (
        frozenset({"duration_value", "percent_complete"}),
        frozenset({"actual_start", "expected_finish"}),
    ),
    "resources": (frozenset({"default_units_per_time"}), frozenset()),
    "risks": (
        frozenset({"probability", "impact", "score"}),
        frozenset({"date_identified"}),
    ),
    "wbs": (frozenset({"sequence_number"}), frozenset()),
    "assignments": (
        frozenset(
            {
                "units",
                "actual_units",
                "remaining_units",
                "planned_cost",
                "actual_cost",
                "remaining_cost",
            }
        ),
        frozenset(),
    ),
    "costs": (
        frozenset({"planned_cost", "actual_cost", "remaining_cost"}),
        frozenset({"expense_date"}),
    ),
}


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


def _literal(text: str) -> str:
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def _csv_cell(value: object) -> str:
    return _literal(_cell_text(value))


def _csv(columns: Sequence[str], rows: Sequence[Mapping[str, object]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer, fieldnames=list(columns), extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({column: _csv_cell(row.get(column)) for column in columns})
    return buffer.getvalue()


def _decimal_text(value: object) -> str | None:
    if value is None:
        return None
    return format(value, "f") if isinstance(value, Decimal) else str(value)


def _raw_text(raw: Mapping[str, Any], field: str) -> str:
    value = raw.get(field)
    if value is None:
        return ""
    return str(value).strip()


def _decimal_field_value(
    raw: Mapping[str, Any], field: str, line: int, errors: list[dict[str, Any]]
) -> str | None:
    text = _raw_text(raw, field)
    if not text:
        return None
    try:
        value = Decimal(text)
    except (InvalidOperation, ValueError):
        value = None
    if value is None or not value.is_finite():
        errors.append(_row_error(line, field, f"INVALID_{field.upper()}"))
        return None
    return format(value, "f")


def _parse_date(value: str | None) -> date | None:
    return None if value in (None, "") else date.fromisoformat(value)


def _parse_decimal(value: str | None) -> Decimal | None:
    return None if value in (None, "") else Decimal(value)


def _date_text(
    raw: Mapping[str, Any], field: str, line: int, errors: list[dict[str, Any]]
) -> str | None:
    text = _raw_text(raw, field)
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        errors.append(_row_error(line, field, f"INVALID_{field.upper()}"))
        return None


def _cell_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _xlsx_cell(
    value: object, *, numeric: bool, date_value: bool
) -> object:
    if value is None or value == "":
        return None
    if isinstance(value, (bool, int, float, datetime, date)):
        return value
    text = str(value)
    if numeric:
        try:
            number = Decimal(text)
        except (InvalidOperation, ValueError):
            return _literal(text)
        return int(number) if number == number.to_integral_value() else float(number)
    if date_value:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return _literal(text)
    return _literal(text)


def _xlsx(
    columns: Sequence[str],
    rows: Sequence[Mapping[str, object]],
    *,
    numeric: frozenset[str] = frozenset(),
    dates: frozenset[str] = frozenset(),
) -> bytes:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
        from openpyxl.utils import get_column_letter
    except ImportError as exc:  # pragma: no cover - declared dependency
        raise ExchangeError("EXCHANGE_XLSX_UNAVAILABLE") from exc
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "exchange"
    sheet.append(list(columns))
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in rows:
        sheet.append(
            [
                _xlsx_cell(
                    row.get(column),
                    numeric=column in numeric,
                    date_value=column in dates,
                )
                for column in columns
            ]
        )
    for index, column in enumerate(columns, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = min(
            48, max(12, len(column) + 2)
        )
    sheet.freeze_panes = "A2"
    if rows:
        sheet.auto_filter.ref = sheet.dimensions
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _decode_xlsx(content: str) -> tuple[list[str], list[dict[str, Any]]]:
    """Decode a base64 XLSX payload into headers and DictReader-shaped rows.

    The archive is inspected before openpyxl loads it: a workbook whose
    uncompressed payload exceeds the bound is refused, macro projects are
    refused, and row iteration stops at a fixed limit. This keeps a small
    compressed payload from expanding without bound in memory.
    """
    try:
        payload = base64.b64decode(content, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ExchangeError("EXCHANGE_XLSX_INVALID") from exc
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            infos = archive.infolist()
            if any(
                info.filename.lower().endswith("vbaproject.bin")
                for info in infos
            ):
                raise ExchangeError("EXCHANGE_XLSX_MACROS_REJECTED")
            if sum(info.file_size for info in infos) > MAX_XLSX_UNCOMPRESSED_BYTES:
                raise ExchangeError("EXCHANGE_XLSX_TOO_LARGE")
    except ExchangeError:
        raise
    except (zipfile.BadZipFile, OSError) as exc:
        raise ExchangeError("EXCHANGE_XLSX_INVALID") from exc
    try:
        from openpyxl import load_workbook

        workbook = load_workbook(
            io.BytesIO(payload),
            data_only=True,
            read_only=True,
            keep_links=False,
        )
    except Exception as exc:  # noqa: BLE001 - bounded file boundary
        raise ExchangeError("EXCHANGE_XLSX_INVALID") from exc
    sheet = workbook.active
    values: list[tuple[Any, ...]] = []
    for row in sheet.iter_rows(values_only=True):
        if len(values) >= MAX_XLSX_ROWS:
            raise ExchangeError("EXCHANGE_XLSX_TOO_MANY_ROWS")
        values.append(row)
    if not values:
        return [], []
    headers = [_cell_text(value).strip() for value in values[0]]
    if any(not header for header in headers):
        raise ExchangeError("EXCHANGE_XLSX_INVALID_HEADERS")
    if len(set(headers)) != len(headers):
        raise ExchangeError("EXCHANGE_XLSX_DUPLICATE_HEADERS")
    rows: list[dict[str, Any]] = []
    for values_row in values[1:]:
        if all(value is None or _cell_text(value) == "" for value in values_row):
            continue
        raw = {
            header: _cell_text(value)
            for header, value in zip(headers, values_row)
        }
        if any(
            value is not None and _cell_text(value) != ""
            for value in values_row[len(headers):]
        ):
            raw[None] = "extra"
        rows.append(raw)
    return headers, rows


def _format(value: object) -> str:
    if value in (None, ""):
        return "csv"
    if not isinstance(value, str) or value not in EXCHANGE_EXPORT_FORMATS:
        raise ExchangeError("EXCHANGE_FORMAT_UNSUPPORTED")
    return value


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
    # Import/export dependencies for the canonical registers. They are optional
    # so a deployment that only exposes activities/resources/risks keeps the
    # original contract; importing a dataset without its dependency fails closed.
    wbs_repository: object | None = None
    activity_api: P6ActivityMasterAPI | None = None
    wbs_api: P6WBSMasterAPI | None = None
    assignment_service: P6ResourceAssignmentApplicationService | None = None
    expense_service: P6ExpenseApplicationService | None = None
    transaction_manager: object | None = None

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
        export_format: str = "csv",
    ) -> dict[str, Any]:
        self._check(scope, context, Permission.PROJECT_READ)
        resolved = _format(export_format)
        columns, rows = self._export_rows(scope, dataset)
        result: dict[str, Any] = {
            "dataset": dataset,
            "format": resolved,
            "columns": list(columns),
            "rows": [dict(row) for row in rows[:PREVIEW_ROWS]],
            "row_count": len(rows),
            "generated_at": generated_at.isoformat(),
            "project_revision": scope.project_revision,
        }
        if resolved == "csv":
            content = _csv(columns, rows)
            result["content"] = content
            result["content_type"] = "text/csv; charset=utf-8"
            result["content_sha256"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
        else:
            numeric, dates = _TYPED_XLSX_COLUMNS.get(
                dataset, (frozenset(), frozenset())
            )
            document = _xlsx(
                columns, rows, numeric=numeric, dates=dates
            )
            result["content_base64"] = base64.b64encode(document).decode("ascii")
            result["content_type"] = _XLSX_CONTENT_TYPE
            result["content_sha256"] = hashlib.sha256(document).hexdigest()
        return result

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
        if dataset == "wbs":
            if self.wbs_repository is None:
                raise ExchangeError("EXCHANGE_DATASET_UNAVAILABLE")
            rows = [
                {
                    "wbs_id": item.wbs_id,
                    "code": item.code,
                    "name": item.name,
                    "parent_wbs_id": item.parent_wbs_id,
                    "sequence_number": item.sequence_number,
                }
                for item in sorted(
                    self.wbs_repository.list(scope),
                    key=lambda item: item.wbs_id,
                )
            ]
            return WBS_COLUMNS, rows
        if dataset == "assignments":
            if self.assignment_service is None:
                raise ExchangeError("EXCHANGE_DATASET_UNAVAILABLE")
            rows = [
                {
                    "assignment_id": item.assignment_id,
                    "activity_id": item.activity_id,
                    "resource_id": item.resource_id,
                    "role_id": item.role_id,
                    "units": _decimal_text(item.units),
                    "actual_units": _decimal_text(item.actual_units),
                    "remaining_units": _decimal_text(item.remaining_units),
                    "planned_cost": _decimal_text(item.planned_cost),
                    "actual_cost": _decimal_text(item.actual_cost),
                    "remaining_cost": _decimal_text(item.remaining_cost),
                    "unit": item.unit,
                    "currency": item.currency,
                    "calendar_id": item.calendar_id,
                }
                for item in sorted(
                    self.assignment_service.list(scope),
                    key=lambda item: item.assignment_id,
                )
            ]
            return ASSIGNMENT_COLUMNS, rows
        if dataset == "costs":
            if self.expense_service is None:
                raise ExchangeError("EXCHANGE_DATASET_UNAVAILABLE")
            rows = [
                {
                    "expense_id": item.expense_id,
                    "name": item.name,
                    "category": item.category,
                    "activity_id": item.activity_id,
                    "wbs_id": item.wbs_id,
                    "expense_date": item.expense_date,
                    "planned_cost": _decimal_text(item.planned_cost),
                    "actual_cost": _decimal_text(item.actual_cost),
                    "remaining_cost": _decimal_text(item.remaining_cost),
                    "currency": item.currency,
                    "note": item.note,
                }
                for item in sorted(
                    self.expense_service.list(scope),
                    key=lambda item: item.expense_id,
                )
            ]
            return COST_COLUMNS, rows
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
        import_format: str = "csv",
    ) -> dict[str, Any]:
        self._check(scope, context, Permission.PROJECT_READ)
        result = self._validate_import(scope, dataset, content, import_format)
        self._record_run(
            scope=scope,
            dataset=dataset,
            mode="preview",
            content=content,
            import_format=import_format,
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
        import_format: str = "csv",
    ) -> dict[str, Any]:
        self._check(scope, context, Permission.PROJECT_WRITE)
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ExchangeError("EXCHANGE_IDEMPOTENCY_KEY_REQUIRED")
        key = idempotency_key.strip()
        request_sha = self._request_sha(dataset, content, import_format)
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

        result = self._validate_import(scope, dataset, content, import_format)
        if not result["valid"]:
            result["atomic"] = True
            self._record_run(
                scope=scope,
                dataset=dataset,
                mode="apply",
                content=content,
                import_format=import_format,
                actor_id=context.user_id,
                occurred_at=occurred_at,
                result=result,
                idempotency_key=key,
            )
            return result
        if self.transaction_manager is None:
            raise ExchangeError("EXCHANGE_TRANSACTION_UNAVAILABLE")

        try:
            with self.transaction_manager.transaction():
                created = self._apply_rows(
                    scope, dataset, result["parsed_rows"], context
                )
                applied = {
                    field: value
                    for field, value in result.items()
                    if field not in {"parsed_rows"}
                }
                applied["created"] = created
                applied["valid"] = True
                applied["atomic"] = True
                applied["replayed"] = False
                run = self._record_run(
                    scope=scope,
                    dataset=dataset,
                    mode="apply",
                    content=content,
                    import_format=import_format,
                    actor_id=context.user_id,
                    occurred_at=occurred_at,
                    result=applied,
                    idempotency_key=key,
                    commit=False,
                )
        except Exception:  # noqa: BLE001 - the batch is rolled back as a unit
            failed = self._invalid(
                dataset,
                EXCHANGE_DATASETS[dataset]["columns"],
                int(result.get("row_count", 0)),
                list(result.get("rows", [])),
                [
                    {
                        "row": 0,
                        "field": "apply",
                        "code": "EXCHANGE_APPLY_FAILED",
                    }
                ],
            )
            failed["format"] = result.get("format", "csv")
            failed["atomic"] = True
            # A rolled-back batch does not reserve the idempotency key: the
            # caller can correct the file and retry with the same key.
            self._record_run(
                scope=scope,
                dataset=dataset,
                mode="apply",
                content=content,
                import_format=import_format,
                actor_id=context.user_id,
                occurred_at=occurred_at,
                result=failed,
                idempotency_key=None,
            )
            return failed
        applied["run_id"] = run.run_id
        return applied

    def _apply_rows(
        self,
        scope: BackendScope,
        dataset: str,
        rows: Sequence[Mapping[str, Any]],
        context: AuthorizationContext,
    ) -> list[str]:
        if dataset == "resources":
            created: list[str] = []
            for row in self._apply_order(rows):
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
            return created

        if dataset == "wbs":
            if self.wbs_api is None:
                raise ExchangeError("EXCHANGE_DATASET_UNAVAILABLE")
            created = []
            for row in self._wbs_apply_order(rows):
                parent = row["parent_wbs_id"]
                item = WBSMaster(
                    scope,
                    row["wbs_id"],
                    WBSParentKind.WBS if parent is not None else WBSParentKind.PROJECT,
                    parent,
                    row["code"],
                    row["name"],
                    int(row["sequence_number"]),
                )
                self.wbs_api.create(item, auth_context=context)
                created.append(row["wbs_id"])
            return created

        if dataset == "activities":
            if self.activity_api is None:
                raise ExchangeError("EXCHANGE_DATASET_UNAVAILABLE")
            created = []
            for row in sorted(rows, key=lambda item: item["activity_id"]):
                activity = ActivityMaster(
                    scope=scope,
                    activity_id=row["activity_id"],
                    duration_value=Decimal(row["duration_value"] or "0"),
                    duration_unit=DurationUnit(row["duration_unit"]),
                    actual_start=_parse_date(row["actual_start"]),
                    expected_finish=_parse_date(row["expected_finish"]),
                    percent_complete=(
                        None
                        if row["percent_complete"] is None
                        else float(Decimal(row["percent_complete"]))
                    ),
                    name=row["name"],
                    activity_type=ActivityType(row["activity_type"]),
                    status=ActivityStatus(row["status"]),
                    wbs_id=row["wbs_id"],
                )
                self.activity_api.create(activity, auth_context=context)
                created.append(row["activity_id"])
            return created

        if dataset == "assignments":
            if self.assignment_service is None:
                raise ExchangeError("EXCHANGE_DATASET_UNAVAILABLE")
            created = []
            for row in sorted(rows, key=lambda item: item["assignment_id"]):
                assignment = P6ResourceAssignment(
                    scope=scope,
                    assignment_id=row["assignment_id"],
                    activity_id=row["activity_id"],
                    resource_id=row["resource_id"],
                    role_id=row["role_id"],
                    units=_parse_decimal(row["units"]),
                    actual_units=_parse_decimal(row["actual_units"]),
                    remaining_units=_parse_decimal(row["remaining_units"]),
                    planned_cost=_parse_decimal(row["planned_cost"]),
                    actual_cost=_parse_decimal(row["actual_cost"]),
                    remaining_cost=_parse_decimal(row["remaining_cost"]),
                    unit=row["unit"],
                    currency=row["currency"],
                    calendar_id=row["calendar_id"],
                )
                self.assignment_service.save(assignment)
                created.append(row["assignment_id"])
            return created

        if self.expense_service is None:
            raise ExchangeError("EXCHANGE_DATASET_UNAVAILABLE")
        created = []
        for row in sorted(rows, key=lambda item: item["expense_id"]):
            expense = P6Expense(
                scope=scope,
                expense_id=row["expense_id"],
                name=row["name"],
                category=row["category"],
                activity_id=row["activity_id"],
                wbs_id=row["wbs_id"],
                expense_date=row["expense_date"],
                planned_cost=_parse_decimal(row["planned_cost"]),
                actual_cost=_parse_decimal(row["actual_cost"]),
                remaining_cost=_parse_decimal(row["remaining_cost"]),
                currency=row["currency"],
                note=row["note"],
            )
            self.expense_service.save(expense)
            created.append(row["expense_id"])
        return created

    @staticmethod
    def _wbs_apply_order(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
        by_id = {row["wbs_id"]: row for row in rows}

        def depth(row: Mapping[str, Any]) -> int:
            value = 0
            parent = row["parent_wbs_id"]
            seen: set[str] = set()
            while parent in by_id and parent not in seen:
                seen.add(parent)
                value += 1
                parent = by_id[parent]["parent_wbs_id"]
            return value

        return sorted(rows, key=lambda row: (depth(row), row["wbs_id"]))

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
        self,
        scope: BackendScope,
        dataset: str,
        content: str,
        import_format: str = "csv",
    ) -> dict[str, Any]:
        spec = EXCHANGE_DATASETS.get(dataset)
        if spec is None:
            raise ExchangeError("EXCHANGE_DATASET_UNKNOWN")
        if not spec["importable"]:
            raise ExchangeError("EXCHANGE_DATASET_READ_ONLY")
        resolved = _format(import_format)
        if not isinstance(content, str) or not content.strip():
            empty = self._invalid(dataset, spec["columns"], 0, [], [
                {"row": 1, "field": "content", "code": "EXCHANGE_CONTENT_EMPTY"}
            ])
            empty["format"] = resolved
            return empty
        if len(content) > MAX_IMPORT_CHARS:
            raise ExchangeError("EXCHANGE_CONTENT_TOO_LARGE")

        columns = spec["columns"]
        if resolved == "csv":
            reader = csv.DictReader(io.StringIO(content))
            fieldnames = list(reader.fieldnames or [])
            source_rows: list[tuple[int, Mapping[str, Any]]] = list(
                enumerate(reader, start=2)
            )
        else:
            fieldnames, decoded = _decode_xlsx(content)
            source_rows = list(enumerate(decoded, start=2))

        errors: list[dict[str, Any]] = []
        for column in columns:
            if column not in fieldnames:
                errors.append(_row_error(1, column, "EXCHANGE_COLUMN_MISSING"))
        for column in fieldnames:
            if column not in columns:
                errors.append(_row_error(1, column, "EXCHANGE_COLUMN_UNKNOWN"))

        clean_rows: list[tuple[int, Mapping[str, Any]]] = []
        for offset, raw in source_rows:
            if None in raw:
                errors.append(_row_error(offset, "row", "EXCHANGE_ROW_ARITY"))
                continue
            if not any((value or "").strip() for value in raw.values()):
                continue
            clean_rows.append((offset, raw))

        if dataset == "resources":
            parsed, row_errors = self._validate_resource_dataset(scope, clean_rows)
        else:
            parsed, row_errors = self._validate_register_dataset(
                scope, dataset, clean_rows
            )
        errors.extend(row_errors)

        row_count = len(clean_rows)
        result = {
            "dataset": dataset,
            "format": resolved,
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

    def _validate_resource_dataset(
        self, scope: BackendScope, rows: Sequence[tuple[int, Mapping[str, Any]]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        errors: list[dict[str, Any]] = []
        parsed: list[dict[str, Any]] = []
        for offset, raw in rows:
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
        return parsed, errors

    def _validate_register_dataset(
        self, scope: BackendScope, dataset: str, rows: Sequence[tuple[int, Mapping[str, Any]]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        errors: list[dict[str, Any]] = []
        parsed: list[dict[str, Any]] = []
        validator = {
            "activities": self._validate_activity_row,
            "wbs": self._validate_wbs_row,
            "assignments": self._validate_assignment_row,
            "costs": self._validate_cost_row,
        }[dataset]
        for offset, raw in rows:
            row, row_errors = validator(offset, raw)
            errors.extend(row_errors)
            if not row_errors:
                parsed.append(row)

        if dataset == "activities":
            self._check_activities(scope, parsed, errors)
        elif dataset == "wbs":
            self._check_wbs(scope, parsed, errors)
        elif dataset == "assignments":
            self._check_assignments(scope, parsed, errors)
        else:
            self._check_costs(scope, parsed, errors)
        return parsed, errors

    def _check_activities(
        self, scope: BackendScope, rows: Sequence[Mapping[str, Any]],
        errors: list[dict[str, Any]],
    ) -> None:
        existing = {item.activity_id for item in self.activity_repository.list(scope)}
        wbs_ids = {
            item.wbs_id
            for item in (
                self.wbs_repository.list(scope)
                if self.wbs_repository is not None
                else ()
            )
        }
        seen: set[str] = set()
        for row in rows:
            activity_id = row["activity_id"]
            if activity_id in existing:
                errors.append(
                    _row_error(row["_row"], "activity_id", "ACTIVITY_ALREADY_EXISTS")
                )
            if activity_id in seen:
                errors.append(
                    _row_error(row["_row"], "activity_id", "ACTIVITY_ID_DUPLICATE_IN_FILE")
                )
            seen.add(activity_id)
            wbs_id = row["wbs_id"]
            if wbs_id is not None and wbs_id not in wbs_ids:
                errors.append(
                    _row_error(row["_row"], "wbs_id", "ACTIVITY_WBS_NOT_FOUND")
                )

    def _check_wbs(
        self, scope: BackendScope, rows: Sequence[Mapping[str, Any]],
        errors: list[dict[str, Any]],
    ) -> None:
        existing = {
            item.wbs_id
            for item in (
                self.wbs_repository.list(scope)
                if self.wbs_repository is not None
                else ()
            )
        }
        incoming = {row["wbs_id"]: row for row in rows}
        seen: set[str] = set()
        for row in rows:
            wbs_id = row["wbs_id"]
            if wbs_id in existing:
                errors.append(_row_error(row["_row"], "wbs_id", "WBS_ALREADY_EXISTS"))
            if wbs_id in seen:
                errors.append(
                    _row_error(row["_row"], "wbs_id", "WBS_ID_DUPLICATE_IN_FILE")
                )
            seen.add(wbs_id)
            parent = row["parent_wbs_id"]
            if parent is not None and parent not in existing and parent not in incoming:
                errors.append(
                    _row_error(row["_row"], "parent_wbs_id", "WBS_PARENT_NOT_FOUND")
                )
        parents: dict[str, str | None] = {wbs_id: None for wbs_id in existing}
        for row in rows:
            parents[row["wbs_id"]] = row["parent_wbs_id"]
        for wbs_id in incoming:
            seen_path: set[str] = set()
            cursor: str | None = wbs_id
            while cursor is not None:
                if cursor in seen_path:
                    errors.append(
                        _row_error(
                            incoming[wbs_id]["_row"], "parent_wbs_id",
                            "WBS_HIERARCHY_CYCLE",
                        )
                    )
                    break
                seen_path.add(cursor)
                cursor = parents.get(cursor)

    def _check_assignments(
        self, scope: BackendScope, rows: Sequence[Mapping[str, Any]],
        errors: list[dict[str, Any]],
    ) -> None:
        if self.assignment_service is None:
            raise ExchangeError("EXCHANGE_DATASET_UNAVAILABLE")
        existing = {
            item.assignment_id for item in self.assignment_service.list(scope)
        }
        activity_ids = {item.activity_id for item in self.activity_repository.list(scope)}
        resource_ids = {
            item.resource_id
            for item in self.resource_repository.list(
                scope.tenant_id, scope.project_id, scope.project_revision
            )
        }
        seen: set[str] = set()
        for row in rows:
            assignment_id = row["assignment_id"]
            if assignment_id in existing:
                errors.append(
                    _row_error(row["_row"], "assignment_id", "ASSIGNMENT_ALREADY_EXISTS")
                )
            if assignment_id in seen:
                errors.append(
                    _row_error(
                        row["_row"], "assignment_id", "ASSIGNMENT_ID_DUPLICATE_IN_FILE"
                    )
                )
            seen.add(assignment_id)
            if row["activity_id"] not in activity_ids:
                errors.append(
                    _row_error(row["_row"], "activity_id", "ASSIGNMENT_ACTIVITY_NOT_FOUND")
                )
            if row["resource_id"] not in resource_ids:
                errors.append(
                    _row_error(row["_row"], "resource_id", "ASSIGNMENT_RESOURCE_NOT_FOUND")
                )

    def _check_costs(
        self, scope: BackendScope, rows: Sequence[Mapping[str, Any]],
        errors: list[dict[str, Any]],
    ) -> None:
        if self.expense_service is None:
            raise ExchangeError("EXCHANGE_DATASET_UNAVAILABLE")
        existing = {item.expense_id for item in self.expense_service.list(scope)}
        activity_ids = {item.activity_id for item in self.activity_repository.list(scope)}
        wbs_ids = {
            item.wbs_id
            for item in (
                self.wbs_repository.list(scope)
                if self.wbs_repository is not None
                else ()
            )
        }
        seen: set[str] = set()
        for row in rows:
            expense_id = row["expense_id"]
            if expense_id in existing:
                errors.append(
                    _row_error(row["_row"], "expense_id", "EXPENSE_ALREADY_EXISTS")
                )
            if expense_id in seen:
                errors.append(
                    _row_error(row["_row"], "expense_id", "EXPENSE_ID_DUPLICATE_IN_FILE")
                )
            seen.add(expense_id)
            activity_id = row["activity_id"]
            if activity_id is not None and activity_id not in activity_ids:
                errors.append(
                    _row_error(row["_row"], "activity_id", "EXPENSE_ACTIVITY_NOT_FOUND")
                )
            wbs_id = row["wbs_id"]
            if wbs_id is not None and wbs_id not in wbs_ids:
                errors.append(
                    _row_error(row["_row"], "wbs_id", "EXPENSE_WBS_NOT_FOUND")
                )
    def _validate_activity_row(
        self, line: int, raw: Mapping[str, Any]
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        errors: list[dict[str, Any]] = []
        activity_id = _raw_text(raw, "activity_id")
        if not activity_id or len(activity_id) > 64:
            errors.append(_row_error(line, "activity_id", "INVALID_ACTIVITY_ID"))
        activity_type = _raw_text(raw, "activity_type") or ActivityType.TASK_DEPENDENT.value
        try:
            ActivityType(activity_type)
        except ValueError:
            errors.append(_row_error(line, "activity_type", "INVALID_ACTIVITY_TYPE"))
        status = _raw_text(raw, "status") or ActivityStatus.NOT_STARTED.value
        try:
            ActivityStatus(status)
        except ValueError:
            errors.append(_row_error(line, "status", "INVALID_ACTIVITY_STATUS"))
        duration_unit = _raw_text(raw, "duration_unit") or DurationUnit.WORKING_DAY.value
        try:
            DurationUnit(duration_unit)
        except ValueError:
            errors.append(_row_error(line, "duration_unit", "INVALID_DURATION_UNIT"))
        duration = _decimal_field_value(raw, "duration_value", line, errors)
        if duration is not None and Decimal(duration) < 0:
            errors.append(_row_error(line, "duration_value", "INVALID_DURATION_VALUE"))
        percent = _decimal_field_value(raw, "percent_complete", line, errors)
        if percent is not None and not (Decimal("0") <= Decimal(percent) <= Decimal("100")):
            errors.append(_row_error(line, "percent_complete", "INVALID_PERCENT_COMPLETE"))
        wbs_id = _raw_text(raw, "wbs_id") or None
        if wbs_id is None:
            errors.append(_row_error(line, "wbs_id", "ACTIVITY_WBS_REQUIRED"))
        actual_start = _date_text(raw, "actual_start", line, errors)
        expected_finish = _date_text(raw, "expected_finish", line, errors)
        row = {
            "_row": line,
            "activity_id": activity_id,
            "name": _raw_text(raw, "name"),
            "activity_type": activity_type,
            "status": status,
            "actual_start": actual_start,
            "expected_finish": expected_finish,
            "duration_value": duration if duration is not None else "",
            "duration_unit": duration_unit,
            "percent_complete": percent,
            "wbs_id": wbs_id,
        }
        if duration is None:
            row["duration_value"] = ""
        return row, errors

    def _validate_wbs_row(
        self, line: int, raw: Mapping[str, Any]
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        errors: list[dict[str, Any]] = []
        wbs_id = _raw_text(raw, "wbs_id")
        if not wbs_id or len(wbs_id) > 64:
            errors.append(_row_error(line, "wbs_id", "INVALID_WBS_ID"))
        code = _raw_text(raw, "code")
        if not code or len(code) > 40:
            errors.append(_row_error(line, "code", "INVALID_WBS_CODE"))
        name = _raw_text(raw, "name")
        if not name:
            errors.append(_row_error(line, "name", "INVALID_WBS_NAME"))
        sequence_text = _raw_text(raw, "sequence_number") or "0"
        try:
            sequence = int(sequence_text)
            if sequence < 0 or str(sequence) != sequence_text.lstrip("+"):
                raise ValueError
            sequence_text = str(sequence)
        except ValueError:
            errors.append(
                _row_error(line, "sequence_number", "INVALID_WBS_SEQUENCE_NUMBER")
            )
            sequence_text = "0"
        return (
            {
                "_row": line,
                "wbs_id": wbs_id,
                "code": code,
                "name": name,
                "parent_wbs_id": _raw_text(raw, "parent_wbs_id") or None,
                "sequence_number": sequence_text,
            },
            errors,
        )

    def _validate_assignment_row(
        self, line: int, raw: Mapping[str, Any]
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        errors: list[dict[str, Any]] = []
        assignment_id = _raw_text(raw, "assignment_id")
        activity_id = _raw_text(raw, "activity_id")
        resource_id = _raw_text(raw, "resource_id")
        if not assignment_id or len(assignment_id) > 64:
            errors.append(_row_error(line, "assignment_id", "INVALID_ASSIGNMENT_ID"))
        if not activity_id:
            errors.append(_row_error(line, "activity_id", "INVALID_ACTIVITY_ID"))
        if not resource_id:
            errors.append(_row_error(line, "resource_id", "INVALID_RESOURCE_ID"))
        values = {
            field: _decimal_field_value(raw, field, line, errors)
            for field in (
                "units",
                "actual_units",
                "remaining_units",
                "planned_cost",
                "actual_cost",
                "remaining_cost",
            )
        }
        return (
            {
                "_row": line,
                "assignment_id": assignment_id,
                "activity_id": activity_id,
                "resource_id": resource_id,
                "role_id": _raw_text(raw, "role_id") or None,
                **values,
                "unit": _raw_text(raw, "unit") or None,
                "currency": _raw_text(raw, "currency") or None,
                "calendar_id": _raw_text(raw, "calendar_id") or None,
            },
            errors,
        )

    def _validate_cost_row(
        self, line: int, raw: Mapping[str, Any]
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        errors: list[dict[str, Any]] = []
        expense_id = _raw_text(raw, "expense_id")
        name = _raw_text(raw, "name")
        category = _raw_text(raw, "category")
        if not expense_id or len(expense_id) > 64:
            errors.append(_row_error(line, "expense_id", "INVALID_EXPENSE_ID"))
        if not name:
            errors.append(_row_error(line, "name", "INVALID_EXPENSE_NAME"))
        if not category:
            errors.append(_row_error(line, "category", "INVALID_EXPENSE_CATEGORY"))
        expense_date = _date_text(raw, "expense_date", line, errors)
        values = {
            field: _decimal_field_value(raw, field, line, errors)
            for field in ("planned_cost", "actual_cost", "remaining_cost")
        }
        return (
            {
                "_row": line,
                "expense_id": expense_id,
                "name": name,
                "category": category,
                "activity_id": _raw_text(raw, "activity_id") or None,
                "wbs_id": _raw_text(raw, "wbs_id") or None,
                "expense_date": expense_date,
                **values,
                "currency": _raw_text(raw, "currency") or None,
                "note": _raw_text(raw, "note") or None,
            },
            errors,
        )

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
        import_format: str,
        actor_id: str,
        occurred_at: datetime,
        result: Mapping[str, Any],
        idempotency_key: str | None,
        commit: bool = True,
    ) -> ExchangeImportRun:
        content_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        stored_result = {
            key: value for key, value in result.items() if key != "parsed_rows"
        }
        stored_result["format"] = import_format
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
                    request_sha256=self._request_sha(dataset, content, import_format),
                    run_id=run.run_id,
                    occurred_at=occurred_at.isoformat(),
                )
            )
        if commit:
            commit_store = getattr(self.store, "commit", None)
            if callable(commit_store):
                commit_store()
        return run

    @staticmethod
    def _request_sha(dataset: str, content: str, import_format: str = "csv") -> str:
        return hashlib.sha256(
            f"{dataset}\n{import_format}\n{content}".encode("utf-8")
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
    "ASSIGNMENT_COLUMNS",
    "COST_COLUMNS",
    "EXCHANGE_DATASETS",
    "ExchangeAuthorizationError",
    "ExchangeError",
    "ExchangeService",
    "RESOURCE_COLUMNS",
    "RISK_COLUMNS",
    "WBS_COLUMNS",
]
