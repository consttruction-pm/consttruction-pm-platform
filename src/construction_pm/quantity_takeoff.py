"""Deterministic, auditable quantity takeoff and BOQ estimate primitives.

The assistant may propose source-backed line items, but this module owns all
quantity/cost arithmetic. Unpriced lines remain explicitly unpriced; they are
never silently treated as zero-cost items.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Mapping, Protocol

from .ai_action_activity_tools import AIActionExecutionIdempotencyStore
from .ai_action_boundary import AIActionProposal
from .ai_action_runtime import (
    AIActionRuntimeContext,
    AIActionRuntimeError,
    AIActionToolDefinition,
)
from .backend_p0.models import BackendScope, MAX_SAFE_REVISION


class QuantityTakeoffError(ValueError):
    """Stable validation or persistence error for quantity takeoff/BOQ."""


_ESTIMATE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
_LINE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")
_MEASUREMENT_STATUSES = {"measured", "calculated", "provisional"}
_MAX_LINES = 200


def _text(value: object, *, field: str, maximum: int, minimum: int = 1) -> str:
    if not isinstance(value, str):
        raise QuantityTakeoffError(f"QUANTITY_TAKEOFF_{field.upper()}_INVALID")
    result = value.strip()
    if not minimum <= len(result) <= maximum:
        raise QuantityTakeoffError(f"QUANTITY_TAKEOFF_{field.upper()}_INVALID")
    return result


def _decimal(value: object, *, field: str, minimum: Decimal | None = None) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise QuantityTakeoffError(f"QUANTITY_TAKEOFF_{field.upper()}_INVALID")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise QuantityTakeoffError(f"QUANTITY_TAKEOFF_{field.upper()}_INVALID") from exc
    if not result.is_finite() or (minimum is not None and result < minimum):
        raise QuantityTakeoffError(f"QUANTITY_TAKEOFF_{field.upper()}_INVALID")
    return result


def _minor_units(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 6:
        raise QuantityTakeoffError("QUANTITY_TAKEOFF_CURRENCY_MINOR_UNITS_INVALID")
    return value


@dataclass(frozen=True)
class QuantityTakeoffLine:
    line_id: str
    description: str
    unit: str
    base_quantity: Decimal
    waste_percent: Decimal
    measurement_status: str
    measurement_basis: str
    source_ref: str | None = None
    classification_code: str | None = None
    unit_rate: Decimal | None = None
    currency: str | None = None
    currency_minor_units: int | None = None
    rate_basis: str | None = None

    def normalized(self) -> "QuantityTakeoffLine":
        line_id = _text(self.line_id, field="line_id", maximum=64)
        if not _LINE_ID.fullmatch(line_id):
            raise QuantityTakeoffError("QUANTITY_TAKEOFF_LINE_ID_INVALID")
        description = _text(self.description, field="description", maximum=240)
        unit = _text(self.unit, field="unit", maximum=32)
        quantity = _decimal(self.base_quantity, field="base_quantity", minimum=Decimal("0"))
        waste = _decimal(self.waste_percent, field="waste_percent", minimum=Decimal("0"))
        if waste > Decimal("100"):
            raise QuantityTakeoffError("QUANTITY_TAKEOFF_WASTE_PERCENT_INVALID")
        status = _text(self.measurement_status, field="measurement_status", maximum=24)
        if status not in _MEASUREMENT_STATUSES:
            raise QuantityTakeoffError("QUANTITY_TAKEOFF_MEASUREMENT_STATUS_INVALID")
        basis = _text(self.measurement_basis, field="measurement_basis", maximum=500)
        source_ref = None if self.source_ref is None else _text(
            self.source_ref, field="source_ref", maximum=500
        )
        if status == "measured" and source_ref is None:
            raise QuantityTakeoffError("QUANTITY_TAKEOFF_MEASURED_SOURCE_REQUIRED")
        if status == "calculated" and source_ref is None:
            raise QuantityTakeoffError("QUANTITY_TAKEOFF_CALCULATED_SOURCE_REQUIRED")
        classification = None if self.classification_code is None else _text(
            self.classification_code, field="classification_code", maximum=64
        )

        rate: Decimal | None
        currency: str | None
        minor_units: int | None
        rate_basis: str | None
        if self.unit_rate is None:
            if self.currency is not None or self.currency_minor_units is not None or self.rate_basis is not None:
                raise QuantityTakeoffError("QUANTITY_TAKEOFF_UNPRICED_LINE_HAS_RATE_METADATA")
            rate, currency, minor_units, rate_basis = None, None, None, None
        else:
            rate = _decimal(self.unit_rate, field="unit_rate", minimum=Decimal("0"))
            if not isinstance(self.currency, str) or not _CURRENCY.fullmatch(self.currency.strip().upper()):
                raise QuantityTakeoffError("QUANTITY_TAKEOFF_CURRENCY_INVALID")
            currency = self.currency.strip().upper()
            minor_units = _minor_units(self.currency_minor_units)
            rate_basis = _text(self.rate_basis, field="rate_basis", maximum=500)
        return QuantityTakeoffLine(
            line_id=line_id,
            description=description,
            unit=unit,
            base_quantity=quantity,
            waste_percent=waste,
            measurement_status=status,
            measurement_basis=basis,
            source_ref=source_ref,
            classification_code=classification,
            unit_rate=rate,
            currency=currency,
            currency_minor_units=minor_units,
            rate_basis=rate_basis,
        )

    @property
    def billable_quantity(self) -> Decimal:
        line = self.normalized()
        return line.base_quantity * (Decimal("1") + line.waste_percent / Decimal("100"))

    @property
    def extended_cost(self) -> Decimal | None:
        line = self.normalized()
        if line.unit_rate is None:
            return None
        assert line.currency_minor_units is not None
        quantum = Decimal("1").scaleb(-line.currency_minor_units)
        return (line.billable_quantity * line.unit_rate).quantize(
            quantum, rounding=ROUND_HALF_UP
        )

    def to_payload(self) -> dict[str, object]:
        line = self.normalized()
        return {
            "line_id": line.line_id,
            "classification_code": line.classification_code,
            "description": line.description,
            "unit": line.unit,
            "base_quantity": str(line.base_quantity),
            "waste_percent": str(line.waste_percent),
            "billable_quantity": str(line.billable_quantity),
            "measurement_status": line.measurement_status,
            "measurement_basis": line.measurement_basis,
            "source_ref": line.source_ref,
            # This slice captures references but has no connected source/rate registry yet.
            # Never represent model-supplied free text as verified engineering evidence.
            "source_verification_status": "unverified_reference",
            "unit_rate": None if line.unit_rate is None else str(line.unit_rate),
            "currency": line.currency,
            "currency_minor_units": line.currency_minor_units,
            "rate_basis": line.rate_basis,
            "rate_verification_status": (
                "unverified_rate_basis" if line.unit_rate is not None else "not_applicable"
            ),
            "extended_cost": None if line.extended_cost is None else str(line.extended_cost),
        }

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "QuantityTakeoffLine":
        expected = {
            "line_id", "description", "unit", "base_quantity", "waste_percent",
            "measurement_status", "measurement_basis", "source_ref",
            "classification_code", "unit_rate", "currency",
            "currency_minor_units", "rate_basis",
        }
        if not isinstance(raw, Mapping) or set(raw) != expected:
            raise QuantityTakeoffError("QUANTITY_TAKEOFF_LINE_PAYLOAD_INVALID")
        return cls(
            line_id=raw["line_id"],  # type: ignore[arg-type]
            description=raw["description"],  # type: ignore[arg-type]
            unit=raw["unit"],  # type: ignore[arg-type]
            base_quantity=raw["base_quantity"],  # type: ignore[arg-type]
            waste_percent=raw["waste_percent"],  # type: ignore[arg-type]
            measurement_status=raw["measurement_status"],  # type: ignore[arg-type]
            measurement_basis=raw["measurement_basis"],  # type: ignore[arg-type]
            source_ref=raw["source_ref"],  # type: ignore[arg-type]
            classification_code=raw["classification_code"],  # type: ignore[arg-type]
            unit_rate=raw["unit_rate"],  # type: ignore[arg-type]
            currency=raw["currency"],  # type: ignore[arg-type]
            currency_minor_units=raw["currency_minor_units"],  # type: ignore[arg-type]
            rate_basis=raw["rate_basis"],  # type: ignore[arg-type]
        ).normalized()


@dataclass(frozen=True)
class QuantityTakeoffEstimate:
    scope: BackendScope
    estimate_id: str
    name: str
    lines: tuple[QuantityTakeoffLine, ...]
    created_by: str
    proposal_id: str
    created_at: datetime
    version: int = 1

    def normalized(self) -> "QuantityTakeoffEstimate":
        self.scope.validate()
        if not 0 <= self.scope.project_revision <= MAX_SAFE_REVISION:
            raise QuantityTakeoffError("QUANTITY_TAKEOFF_PROJECT_REVISION_INVALID")
        estimate_id = _text(self.estimate_id, field="estimate_id", maximum=64)
        if not _ESTIMATE_ID.fullmatch(estimate_id):
            raise QuantityTakeoffError("QUANTITY_TAKEOFF_ESTIMATE_ID_INVALID")
        name = _text(self.name, field="name", maximum=180)
        created_by = _text(self.created_by, field="created_by", maximum=128)
        proposal_id = _text(self.proposal_id, field="proposal_id", maximum=128)
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise QuantityTakeoffError("QUANTITY_TAKEOFF_CREATED_AT_MUST_BE_TIMEZONE_AWARE")
        if isinstance(self.version, bool) or self.version != 1:
            raise QuantityTakeoffError("QUANTITY_TAKEOFF_VERSION_INVALID")
        if not isinstance(self.lines, tuple) or not 1 <= len(self.lines) <= _MAX_LINES:
            raise QuantityTakeoffError("QUANTITY_TAKEOFF_LINES_INVALID")
        lines = tuple(
            item.normalized() if isinstance(item, QuantityTakeoffLine)
            else QuantityTakeoffLine.from_mapping(item)  # type: ignore[arg-type]
            for item in self.lines
        )
        ids = [line.line_id for line in lines]
        if len(ids) != len(set(ids)):
            raise QuantityTakeoffError("QUANTITY_TAKEOFF_LINE_ID_DUPLICATE")
        precision_by_currency: dict[str, int] = {}
        for line in lines:
            if line.currency is not None:
                previous = precision_by_currency.setdefault(line.currency, int(line.currency_minor_units))
                if previous != line.currency_minor_units:
                    raise QuantityTakeoffError("QUANTITY_TAKEOFF_CURRENCY_PRECISION_CONFLICT")
        return QuantityTakeoffEstimate(
            scope=self.scope, estimate_id=estimate_id, name=name, lines=lines,
            created_by=created_by, proposal_id=proposal_id,
            created_at=self.created_at.astimezone(timezone.utc), version=1,
        )

    def to_payload(self) -> dict[str, object]:
        estimate = self.normalized()
        totals: dict[str, dict[str, object]] = {}
        missing_rates = 0
        for line in estimate.lines:
            if line.unit_rate is None:
                missing_rates += 1
                continue
            assert line.currency is not None and line.currency_minor_units is not None
            entry = totals.setdefault(
                line.currency,
                {"currency": line.currency, "minor_units": line.currency_minor_units, "subtotal": Decimal("0")},
            )
            entry["subtotal"] = Decimal(str(entry["subtotal"])) + (line.extended_cost or Decimal("0"))
        return {
            "contract_version": "quantity-takeoff.v1",
            "estimate_id": estimate.estimate_id,
            "name": estimate.name,
            "version": estimate.version,
            "scope": {
                "tenant_id": estimate.scope.tenant_id,
                "project_id": estimate.scope.project_id,
                "project_revision": estimate.scope.project_revision,
            },
            "created_by": estimate.created_by,
            "proposal_id": estimate.proposal_id,
            "created_at": estimate.created_at.isoformat(),
            "lines": [line.to_payload() for line in estimate.lines],
            "summary": {
                "line_count": len(estimate.lines),
                "priced_line_count": len(estimate.lines) - missing_rates,
                "unpriced_line_count": missing_rates,
                "cost_complete": missing_rates == 0,
                "source_verification_performed": False,
                "rate_verification_performed": False,
                "totals_by_currency": [
                    {
                        "currency": currency,
                        "minor_units": int(value["minor_units"]),
                        "subtotal": str(value["subtotal"]),
                    }
                    for currency, value in sorted(totals.items())
                ],
            },
        }


def _encode(estimate: QuantityTakeoffEstimate) -> str:
    return json.dumps(
        estimate.to_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _decode(scope: BackendScope, encoded: str) -> QuantityTakeoffEstimate:
    try:
        raw = json.loads(encoded)
        if not isinstance(raw, dict) or raw.get("contract_version") != "quantity-takeoff.v1":
            raise ValueError
        lines_raw = raw["lines"]
        lines = tuple(
            QuantityTakeoffLine(
                line_id=item["line_id"],
                description=item["description"],
                unit=item["unit"],
                base_quantity=Decimal(item["base_quantity"]),
                waste_percent=Decimal(item["waste_percent"]),
                measurement_status=item["measurement_status"],
                measurement_basis=item["measurement_basis"],
                source_ref=item["source_ref"],
                classification_code=item["classification_code"],
                unit_rate=None if item["unit_rate"] is None else Decimal(item["unit_rate"]),
                currency=item["currency"],
                currency_minor_units=item["currency_minor_units"],
                rate_basis=item["rate_basis"],
            ).normalized()
            for item in lines_raw
        )
        estimate = QuantityTakeoffEstimate(
            scope=scope,
            estimate_id=raw["estimate_id"],
            name=raw["name"],
            lines=lines,
            created_by=raw["created_by"],
            proposal_id=raw["proposal_id"],
            created_at=datetime.fromisoformat(raw["created_at"]),
            version=raw["version"],
        ).normalized()
        # Validate stored derived values against the deterministic calculation.
        if _encode(estimate) != json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")):
            raise ValueError("STORED_QUANTITY_TAKEOFF_DERIVATION_MISMATCH")
        return estimate
    except (KeyError, TypeError, ValueError, InvalidOperation, json.JSONDecodeError) as exc:
        raise QuantityTakeoffError("QUANTITY_TAKEOFF_STORED_RECORD_INVALID") from exc


class QuantityTakeoffRepository(Protocol):
    def create(self, estimate: QuantityTakeoffEstimate) -> QuantityTakeoffEstimate: ...
    def get(self, scope: BackendScope, estimate_id: str) -> QuantityTakeoffEstimate | None: ...
    def list(self, scope: BackendScope) -> tuple[QuantityTakeoffEstimate, ...]: ...


class SQLiteQuantityTakeoffRepository:
    """Tenant/project-scoped immutable estimate store; transaction ownership stays with caller."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        was_in_transaction = connection.in_transaction
        connection.execute(
            """CREATE TABLE IF NOT EXISTS quantity_takeoff_estimates (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                estimate_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, estimate_id)
            )"""
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_quantity_takeoff_scope "
            "ON quantity_takeoff_estimates(tenant_id, project_id, project_revision, estimate_id)"
        )
        if not was_in_transaction:
            connection.commit()

    def create(self, estimate: QuantityTakeoffEstimate) -> QuantityTakeoffEstimate:
        normalized = estimate.normalized()
        encoded = _encode(normalized)
        row = self.connection.execute(
            "SELECT project_revision, payload_json FROM quantity_takeoff_estimates "
            "WHERE tenant_id=? AND project_id=? AND estimate_id=?",
            (normalized.scope.tenant_id, normalized.scope.project_id, normalized.estimate_id),
        ).fetchone()
        if row is not None:
            if int(row[0]) != normalized.scope.project_revision:
                raise QuantityTakeoffError("QUANTITY_TAKEOFF_REVISION_CONFLICT")
            existing = _decode(normalized.scope, str(row[1]))
            if _encode(existing) != encoded:
                raise QuantityTakeoffError("QUANTITY_TAKEOFF_ESTIMATE_ID_CONFLICT")
            return existing
        self.connection.execute(
            "INSERT INTO quantity_takeoff_estimates "
            "(tenant_id,project_id,project_revision,estimate_id,payload_json) VALUES (?,?,?,?,?)",
            (
                normalized.scope.tenant_id, normalized.scope.project_id,
                normalized.scope.project_revision, normalized.estimate_id, encoded,
            ),
        )
        return normalized

    def get(self, scope: BackendScope, estimate_id: str) -> QuantityTakeoffEstimate | None:
        scope.validate()
        estimate_id = _text(estimate_id, field="estimate_id", maximum=64)
        row = self.connection.execute(
            "SELECT project_revision,payload_json FROM quantity_takeoff_estimates "
            "WHERE tenant_id=? AND project_id=? AND estimate_id=?",
            (scope.tenant_id, scope.project_id, estimate_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise QuantityTakeoffError("QUANTITY_TAKEOFF_REVISION_CONFLICT")
        return _decode(scope, str(row[1]))

    def list(self, scope: BackendScope) -> tuple[QuantityTakeoffEstimate, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT estimate_id,payload_json FROM quantity_takeoff_estimates "
            "WHERE tenant_id=? AND project_id=? AND project_revision=? ORDER BY estimate_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(_decode(scope, str(row[1])) for row in rows)


class PostgresQuantityTakeoffRepository:
    """PostgreSQL adapter for deployments; never commits the caller's transaction."""

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS quantity_takeoff_estimates ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "estimate_id TEXT NOT NULL, payload_json TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, estimate_id))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_quantity_takeoff_scope "
            "ON quantity_takeoff_estimates(tenant_id, project_id, project_revision, estimate_id)"
        )

    def create(self, estimate: QuantityTakeoffEstimate) -> QuantityTakeoffEstimate:
        normalized = estimate.normalized()
        encoded = _encode(normalized)
        self.connection.execute(
            "INSERT INTO quantity_takeoff_estimates "
            "(tenant_id,project_id,project_revision,estimate_id,payload_json) "
            "VALUES (%s,%s,%s,%s,%s) ON CONFLICT (tenant_id,project_id,estimate_id) DO NOTHING",
            (normalized.scope.tenant_id, normalized.scope.project_id,
             normalized.scope.project_revision, normalized.estimate_id, encoded),
        )
        row = self.connection.execute(
            "SELECT project_revision,payload_json FROM quantity_takeoff_estimates "
            "WHERE tenant_id=%s AND project_id=%s AND estimate_id=%s",
            (normalized.scope.tenant_id, normalized.scope.project_id, normalized.estimate_id),
        ).fetchone()
        if row is None:
            raise QuantityTakeoffError("QUANTITY_TAKEOFF_PERSISTENCE_FAILED")
        if int(row[0]) != normalized.scope.project_revision:
            raise QuantityTakeoffError("QUANTITY_TAKEOFF_REVISION_CONFLICT")
        existing = _decode(normalized.scope, str(row[1]))
        if _encode(existing) != encoded:
            raise QuantityTakeoffError("QUANTITY_TAKEOFF_ESTIMATE_ID_CONFLICT")
        return existing

    def get(self, scope: BackendScope, estimate_id: str) -> QuantityTakeoffEstimate | None:
        scope.validate()
        estimate_id = _text(estimate_id, field="estimate_id", maximum=64)
        row = self.connection.execute(
            "SELECT project_revision,payload_json FROM quantity_takeoff_estimates "
            "WHERE tenant_id=%s AND project_id=%s AND estimate_id=%s",
            (scope.tenant_id, scope.project_id, estimate_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise QuantityTakeoffError("QUANTITY_TAKEOFF_REVISION_CONFLICT")
        return _decode(scope, str(row[1]))

    def list(self, scope: BackendScope) -> tuple[QuantityTakeoffEstimate, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT estimate_id,payload_json FROM quantity_takeoff_estimates "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s ORDER BY estimate_id",
            (scope.tenant_id, scope.project_id, scope.project_revision),
        ).fetchall()
        return tuple(_decode(scope, str(row[1])) for row in rows)


def _validate_tool_payload(payload: Mapping[str, object]) -> Mapping[str, object]:
    if not isinstance(payload, Mapping) or set(payload) != {"estimate_id", "name", "lines"}:
        raise QuantityTakeoffError("QUANTITY_TAKEOFF_PAYLOAD_INVALID")
    estimate_id = _text(payload["estimate_id"], field="estimate_id", maximum=64)
    if not _ESTIMATE_ID.fullmatch(estimate_id):
        raise QuantityTakeoffError("QUANTITY_TAKEOFF_ESTIMATE_ID_INVALID")
    name = _text(payload["name"], field="name", maximum=180)
    raw_lines = payload["lines"]
    if not isinstance(raw_lines, list) or not 1 <= len(raw_lines) <= _MAX_LINES:
        raise QuantityTakeoffError("QUANTITY_TAKEOFF_LINES_INVALID")
    lines = tuple(QuantityTakeoffLine.from_mapping(raw) for raw in raw_lines if isinstance(raw, Mapping))
    if len(lines) != len(raw_lines):
        raise QuantityTakeoffError("QUANTITY_TAKEOFF_LINE_PAYLOAD_INVALID")
    ids = [line.line_id for line in lines]
    if len(ids) != len(set(ids)):
        raise QuantityTakeoffError("QUANTITY_TAKEOFF_LINE_ID_DUPLICATE")
    currencies: dict[str, int] = {}
    for line in lines:
        if line.currency is not None:
            precision = int(line.currency_minor_units)
            prior = currencies.setdefault(line.currency, precision)
            if prior != precision:
                raise QuantityTakeoffError("QUANTITY_TAKEOFF_CURRENCY_PRECISION_CONFLICT")
    return {
        "estimate_id": estimate_id,
        "name": name,
        "lines": [
            {
                "line_id": line.line_id,
                "description": line.description,
                "unit": line.unit,
                "base_quantity": str(line.base_quantity),
                "waste_percent": str(line.waste_percent),
                "measurement_status": line.measurement_status,
                "measurement_basis": line.measurement_basis,
                "source_ref": line.source_ref,
                "classification_code": line.classification_code,
                "unit_rate": None if line.unit_rate is None else str(line.unit_rate),
                "currency": line.currency,
                "currency_minor_units": line.currency_minor_units,
                "rate_basis": line.rate_basis,
            }
            for line in lines
        ],
    }


def build_quantity_takeoff_create_tool(
    *,
    repository: QuantityTakeoffRepository,
    idempotency_store: AIActionExecutionIdempotencyStore,
) -> AIActionToolDefinition:
    """Build an approval-gated, revision-bound quantity-takeoff creation tool."""

    def execute(
        payload: Mapping[str, object],
        proposal: AIActionProposal,
        idempotency_key: str,
        context: AIActionRuntimeContext,
    ) -> Mapping[str, object]:
        context.validate()
        if (
            proposal.tenant_id != context.tenant_id
            or proposal.project_id != context.project_id
            or proposal.project_revision_id != context.project_revision_id
            or proposal.requested_by != context.subject_id
        ):
            raise AIActionRuntimeError("QUANTITY_TAKEOFF_TOOL_SCOPE_MISMATCH")
        try:
            revision = int(context.project_revision_id, 10)
        except (TypeError, ValueError) as exc:
            raise AIActionRuntimeError("QUANTITY_TAKEOFF_PROJECT_REVISION_INVALID") from exc
        if revision < 0 or str(revision) != context.project_revision_id:
            raise AIActionRuntimeError("QUANTITY_TAKEOFF_PROJECT_REVISION_INVALID")
        normalized = _validate_tool_payload(payload)
        lines = tuple(
            QuantityTakeoffLine.from_mapping(line)
            for line in normalized["lines"]  # type: ignore[index]
        )
        estimate = QuantityTakeoffEstimate(
            scope=BackendScope(context.tenant_id, context.project_id, revision),
            estimate_id=str(normalized["estimate_id"]),
            name=str(normalized["name"]),
            lines=lines,
            created_by=context.subject_id,
            proposal_id=proposal.proposal_id,
            created_at=datetime.now(timezone.utc),
        ).normalized()
        fingerprint_payload = json.dumps(
            {
                "operation": "quantity.takeoff.create",
                "tenant_id": context.tenant_id,
                "project_id": context.project_id,
                "project_revision_id": context.project_revision_id,
                "payload": dict(normalized),
            },
            sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        )
        fingerprint_value = hashlib.sha256(fingerprint_payload.encode("utf-8")).hexdigest()

        def persist() -> Mapping[str, object]:
            saved = repository.create(estimate)
            fresh = repository.get(estimate.scope, estimate.estimate_id)
            if fresh is None or _encode(fresh) != _encode(saved):
                raise QuantityTakeoffError("QUANTITY_TAKEOFF_READBACK_FAILED")
            return fresh.to_payload()

        return idempotency_store.execute(
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            tool_name=proposal.tool_name,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint_value,
            mutation=persist,
        )

    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["estimate_id", "name", "lines"],
        "properties": {
            "estimate_id": {"type": "string", "minLength": 3, "maxLength": 64},
            "name": {"type": "string", "minLength": 1, "maxLength": 180},
            "lines": {
                "type": "array",
                "minItems": 1,
                "maxItems": _MAX_LINES,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "line_id", "description", "unit", "base_quantity", "waste_percent",
                        "measurement_status", "measurement_basis", "source_ref",
                        "classification_code", "unit_rate", "currency",
                        "currency_minor_units", "rate_basis",
                    ],
                    "properties": {
                        "line_id": {"type": "string", "minLength": 1, "maxLength": 64},
                        "description": {"type": "string", "minLength": 1, "maxLength": 240},
                        "unit": {"type": "string", "minLength": 1, "maxLength": 32},
                        "base_quantity": {"type": "number", "minimum": 0},
                        "waste_percent": {"type": "number", "minimum": 0, "maximum": 100},
                        "measurement_status": {"type": "string", "enum": ["measured", "calculated", "provisional"]},
                        "measurement_basis": {"type": "string", "minLength": 1, "maxLength": 500},
                        "source_ref": {"type": ["string", "null"], "maxLength": 500},
                        "classification_code": {"type": ["string", "null"], "maxLength": 64},
                        "unit_rate": {"type": ["number", "null"], "minimum": 0},
                        "currency": {"type": ["string", "null"], "pattern": "^[A-Z]{3}$"},
                        "currency_minor_units": {"type": ["integer", "null"], "minimum": 0, "maximum": 6},
                        "rate_basis": {"type": ["string", "null"], "maxLength": 500},
                    },
                },
            },
        },
    }
    return AIActionToolDefinition(
        tool_name="quantity.takeoff.create",
        action="create",
        resource_domain="quantity_takeoff",
        requires_human_approval=True,
        validate_payload=_validate_tool_payload,
        execute=execute,
        description=(
            "Propose an auditable quantity takeoff/BOQ estimate using explicit units, "
            "measurement basis, source references, waste, and source-backed rates. "
            "Unpriced lines remain unpriced. User approval and fresh read-back are required."
        ),
        input_schema=schema,
    )


__all__ = [
    "QuantityTakeoffError",
    "QuantityTakeoffLine",
    "QuantityTakeoffEstimate",
    "QuantityTakeoffRepository",
    "SQLiteQuantityTakeoffRepository",
    "PostgresQuantityTakeoffRepository",
    "build_quantity_takeoff_create_tool",
]
