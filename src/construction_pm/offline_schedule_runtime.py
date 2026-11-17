from __future__ import annotations

"""Explicit offline scheduling runtime boundary.

An offline bundle is a self-contained, hash-bound artifact:

* the canonical immutable schedule snapshot payload and its SHA-256;
* the version-pinned calendar definitions (with exception layers and base
  references) that the snapshot references;
* the deterministic calculation context;
* the snapshot creation metadata needed to rebuild its validated value object.

The runtime executes the same authoritative Shared Scheduling Core used by the
online path. It accepts no repository, transport, URL or credential, so an
offline calculation has no remote engine, calendar or snapshot dependency. The
network guard is a process-local fail-closed assertion: any attempt to open a
socket during execution raises instead of reaching the network.

Resource leveling and resource-dependent placement need application-bound
capacity inputs that are not part of a scheduling bundle yet. Those snapshots
are rejected explicitly at execution instead of being silently simplified; the
existing engine semantics remain unchanged.
"""

import hashlib
import json
import socket
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any, Iterator, Mapping

from .backend_p0.models import BackendScope
from .schedule_evaluator import (
    ScheduleEvaluationError,
    ScheduleEvaluationResult,
    evaluate_schedule_snapshot,
)
from .schedule_input_snapshot_repository import (
    ScheduleInputSnapshot,
    ScheduleSnapshotPersistenceError,
)
from .scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from .scheduling.calendar_context import CalendarReference, CalendarResolverRegistry
from .scheduling.calendar_exception_overlay import CalendarExceptionLayers
from .scheduling.calendar_exceptions import CalendarException, CalendarExceptionType
from .scheduling.calendar_system import CalendarSystem
from .scheduling.calculation_context import CalculationContext
from .scheduling.time_calendar import TimeAwareWorkingTimeResolver, WorkingTimeCalendar
from .scheduling.time_schedule import FloatExecutionPolicy
from .scheduling_execution_budget import detect_effective_capacity


OFFLINE_BUNDLE_SCHEMA = "construction-pm/offline-schedule-bundle/v1"


class OfflineRuntimeError(ValueError):
    """Raised when an offline bundle cannot be executed exactly as online."""

    def __init__(self, code: str, detail: str | None = None) -> None:
        self.code = code
        self.detail = detail
        super().__init__(code if detail is None else f"{code}:{detail}")


class OfflineNetworkAccessError(RuntimeError):
    """Raised when an offline calculation attempts any network access."""

    code = "OFFLINE_NETWORK_ACCESS_DENIED"

    def __init__(self, operation: str) -> None:
        self.operation = operation
        super().__init__(f"{self.code}:{operation}")


@contextmanager
def deny_network_access() -> Iterator[None]:
    """Fail closed on any socket connection or address resolution.

    The guard is process-local and synchronous. It is intended for the
    dedicated offline calculation process, where patch scope cannot affect a
    concurrent server thread.
    """
    originals = (
        socket.socket.connect,
        socket.socket.connect_ex,
        socket.create_connection,
        socket.getaddrinfo,
    )

    def _denied(operation: str):
        def _raise(*args: object, **kwargs: object):
            raise OfflineNetworkAccessError(operation)

        return _raise

    socket.socket.connect = _denied("connect")  # type: ignore[method-assign]
    socket.socket.connect_ex = _denied("connect_ex")  # type: ignore[method-assign]
    socket.create_connection = _denied("create_connection")  # type: ignore[assignment]
    socket.getaddrinfo = _denied("getaddrinfo")  # type: ignore[assignment]
    try:
        yield
    finally:
        (
            socket.socket.connect,
            socket.socket.connect_ex,
            socket.create_connection,
            socket.getaddrinfo,
        ) = originals


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require_mapping(value: object, code: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise OfflineRuntimeError(code)
    return value


def _require_text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OfflineRuntimeError(code)
    return value


def _calendar_reference(value: object, code: str) -> CalendarReference:
    payload = _require_mapping(value, code)
    raw_system = payload.get("system", CalendarSystem.GREGORIAN.value)
    raw_kind = payload.get("kind", "working-day")
    if not isinstance(raw_system, str) or not isinstance(raw_kind, str):
        raise OfflineRuntimeError(code)
    try:
        system = CalendarSystem(raw_system)
    except ValueError as exc:
        raise OfflineRuntimeError(code) from exc
    return CalendarReference(
        _require_text(payload.get("calendar_id"), code),
        _require_text(payload.get("calendar_version"), code),
        raw_kind,
        system,
    )


def _exception_from_snapshot(value: object) -> CalendarException:
    payload = _require_mapping(value, "OFFLINE_CALENDAR_EXCEPTION_INVALID")
    try:
        exception_date = date.fromisoformat(_require_text(payload.get("date"), "OFFLINE_CALENDAR_EXCEPTION_INVALID"))
        kind = CalendarExceptionType(_require_text(payload.get("kind"), "OFFLINE_CALENDAR_EXCEPTION_INVALID"))
        total = payload.get("total_work_hours")
        intervals = tuple(
            (time.fromisoformat(str(start)), time.fromisoformat(str(end)))
            for start, end in payload.get("intervals", ())
        )
        return CalendarException(
            exception_date,
            kind,
            CalendarSystem.GREGORIAN,
            None if total is None else Decimal(str(total)),
            intervals,
        )
    except (TypeError, ValueError, InvalidOperation) as exc:
        raise OfflineRuntimeError("OFFLINE_CALENDAR_EXCEPTION_INVALID") from exc


@dataclass(frozen=True)
class OfflineCalendar:
    """One version-pinned calendar definition carried by an offline bundle."""

    reference: CalendarReference
    snapshot: dict[str, object]
    base: CalendarReference | None = None
    local_exceptions: tuple[dict[str, object], ...] = ()
    inherited_exceptions: tuple[dict[str, object], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.reference, CalendarReference):
            raise OfflineRuntimeError("OFFLINE_CALENDAR_REFERENCE_INVALID")
        if not isinstance(self.snapshot, dict):
            raise OfflineRuntimeError("OFFLINE_CALENDAR_SNAPSHOT_INVALID")
        definition = self.definition()
        if definition.system is not self.reference.system:
            raise OfflineRuntimeError(
                "OFFLINE_CALENDAR_SYSTEM_MISMATCH",
                self.reference.calendar_id,
            )
        for layer in (self.local_exceptions, self.inherited_exceptions):
            if not isinstance(layer, tuple):
                raise OfflineRuntimeError("OFFLINE_CALENDAR_EXCEPTION_INVALID")
            for item in layer:
                _exception_from_snapshot(item)

    def definition(self) -> WorkingCalendar | WorkingTimeCalendar:
        try:
            if self.reference.kind == "working-day":
                return WorkingCalendar.from_canonical_snapshot(self.snapshot)
            return WorkingTimeCalendar.from_canonical_snapshot(self.snapshot)
        except (TypeError, ValueError) as exc:
            raise OfflineRuntimeError(
                "OFFLINE_CALENDAR_SNAPSHOT_INVALID", self.reference.calendar_id
            ) from exc

    def as_payload(self) -> dict[str, object]:
        return {
            "reference": {
                "calendar_id": self.reference.calendar_id,
                "calendar_version": self.reference.calendar_version,
                "kind": self.reference.kind,
                "system": self.reference.system.value,
            },
            "snapshot": self.snapshot,
            "base": (
                None
                if self.base is None
                else {
                    "calendar_id": self.base.calendar_id,
                    "calendar_version": self.base.calendar_version,
                    "kind": self.base.kind,
                    "system": self.base.system.value,
                }
            ),
            "local_exceptions": list(self.local_exceptions),
            "inherited_exceptions": list(self.inherited_exceptions),
        }

    @classmethod
    def from_payload(cls, value: object) -> "OfflineCalendar":
        payload = _require_mapping(value, "OFFLINE_CALENDAR_INVALID")
        reference = _calendar_reference(payload.get("reference"), "OFFLINE_CALENDAR_REFERENCE_INVALID")
        snapshot = _require_mapping(payload.get("snapshot"), "OFFLINE_CALENDAR_SNAPSHOT_INVALID")
        base_raw = payload.get("base")
        base = (
            None
            if base_raw is None
            else _calendar_reference(base_raw, "OFFLINE_CALENDAR_BASE_INVALID")
        )

        def _layers(name: str) -> tuple[dict[str, object], ...]:
            raw = payload.get(name, ())
            if not isinstance(raw, (list, tuple)):
                raise OfflineRuntimeError("OFFLINE_CALENDAR_EXCEPTION_INVALID")
            return tuple(_require_mapping(item, "OFFLINE_CALENDAR_EXCEPTION_INVALID") for item in raw)

        return cls(
            reference=reference,
            snapshot=snapshot,
            base=base,
            local_exceptions=_layers("local_exceptions"),
            inherited_exceptions=_layers("inherited_exceptions"),
        )


@dataclass(frozen=True)
class OfflineScheduleBundle:
    """Self-contained artifact that can be executed without remote dependencies."""

    snapshot_payload: str
    snapshot_hash: str
    calculation_identity: str
    calculation_context: dict[str, Any]
    created_at: str
    calendars: tuple[OfflineCalendar, ...]
    record_revision: int = 1
    calculation_identity_version: int = 2
    schema: str = OFFLINE_BUNDLE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != OFFLINE_BUNDLE_SCHEMA:
            raise OfflineRuntimeError("OFFLINE_BUNDLE_SCHEMA_UNSUPPORTED", self.schema)
        if not isinstance(self.snapshot_payload, str) or not self.snapshot_payload:
            raise OfflineRuntimeError("OFFLINE_SNAPSHOT_INVALID")
        if not isinstance(self.snapshot_hash, str) or len(self.snapshot_hash) != 64:
            raise OfflineRuntimeError("OFFLINE_SNAPSHOT_HASH_INVALID")
        if not isinstance(self.calculation_identity, str) or len(self.calculation_identity) != 64:
            raise OfflineRuntimeError("OFFLINE_CALCULATION_IDENTITY_INVALID")
        if not isinstance(self.calculation_context, dict) or not self.calculation_context:
            raise OfflineRuntimeError("OFFLINE_CALCULATION_CONTEXT_INVALID")
        if not isinstance(self.calendars, tuple) or not self.calendars:
            raise OfflineRuntimeError("OFFLINE_CALENDARS_MISSING")
        if not all(isinstance(item, OfflineCalendar) for item in self.calendars):
            raise OfflineRuntimeError("OFFLINE_CALENDAR_INVALID")
        keys = [item.reference for item in self.calendars]
        if len(keys) != len(set(keys)):
            raise OfflineRuntimeError("OFFLINE_CALENDAR_DUPLICATE")
        if self.calculation_identity_version not in (1, 2):
            raise OfflineRuntimeError("OFFLINE_CALCULATION_IDENTITY_INVALID")
        try:
            parsed = datetime.fromisoformat(self.created_at)
        except (TypeError, ValueError) as exc:
            raise OfflineRuntimeError("OFFLINE_SNAPSHOT_TIMESTAMP_INVALID") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise OfflineRuntimeError("OFFLINE_SNAPSHOT_TIMESTAMP_INVALID")

    def payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "snapshot_payload": self.snapshot_payload,
            "snapshot_hash": self.snapshot_hash,
            "calculation_identity": self.calculation_identity,
            "calculation_context": self.calculation_context,
            "created_at": self.created_at,
            "calendars": [
                item.as_payload()
                for item in sorted(
                    self.calendars,
                    key=lambda item: (
                        item.reference.calendar_id,
                        item.reference.calendar_version,
                        item.reference.kind,
                    ),
                )
            ],
            "record_revision": self.record_revision,
            "calculation_identity_version": self.calculation_identity_version,
        }

    @property
    def bundle_hash(self) -> str:
        return _sha256(_canonical_json(self.payload()))

    def to_payload(self) -> dict[str, object]:
        return {**self.payload(), "bundle_hash": self.bundle_hash}

    def to_json(self) -> str:
        return _canonical_json(self.to_payload())

    @classmethod
    def from_json(cls, text: str) -> "OfflineScheduleBundle":
        try:
            value = json.loads(text)
        except (TypeError, ValueError) as exc:
            raise OfflineRuntimeError("OFFLINE_BUNDLE_INVALID") from exc
        return cls.from_payload(value)

    @classmethod
    def from_payload(cls, value: object) -> "OfflineScheduleBundle":
        payload = _require_mapping(value, "OFFLINE_BUNDLE_INVALID")
        # Copy so the caller's mapping and nested calendars cannot alias state.
        decoded = json.loads(_canonical_json(payload))
        claimed_hash = decoded.pop("bundle_hash", None)
        if not isinstance(claimed_hash, str) or len(claimed_hash) != 64:
            raise OfflineRuntimeError("OFFLINE_BUNDLE_HASH_MISSING")
        calendars_raw = decoded.get("calendars")
        if not isinstance(calendars_raw, (list, tuple)) or not calendars_raw:
            raise OfflineRuntimeError("OFFLINE_CALENDARS_MISSING")
        try:
            bundle = cls(
                snapshot_payload=_require_text(decoded.get("snapshot_payload"), "OFFLINE_SNAPSHOT_INVALID"),
                snapshot_hash=_require_text(decoded.get("snapshot_hash"), "OFFLINE_SNAPSHOT_HASH_INVALID"),
                calculation_identity=_require_text(
                    decoded.get("calculation_identity"),
                    "OFFLINE_CALCULATION_IDENTITY_INVALID",
                ),
                calculation_context=_require_mapping(
                    decoded.get("calculation_context"),
                    "OFFLINE_CALCULATION_CONTEXT_INVALID",
                ),
                created_at=_require_text(decoded.get("created_at"), "OFFLINE_SNAPSHOT_TIMESTAMP_INVALID"),
                calendars=tuple(OfflineCalendar.from_payload(item) for item in calendars_raw),
                record_revision=decoded.get("record_revision", 1),
                calculation_identity_version=decoded.get("calculation_identity_version", 2),
                schema=decoded.get("schema", OFFLINE_BUNDLE_SCHEMA),
            )
        except TypeError as exc:
            raise OfflineRuntimeError("OFFLINE_BUNDLE_INVALID") from exc
        if bundle.bundle_hash != claimed_hash:
            raise OfflineRuntimeError("OFFLINE_BUNDLE_HASH_MISMATCH")
        return bundle


def _default_float_workers() -> int:
    """Slots an offline process may use for the independent float pass.

    The pass only leaves the current process when it is provably safe; a
    single-threaded offline run may fork up to the capacity the kernel reports,
    and a threaded embedder falls back to the exact sequential loop.
    """
    try:
        return max(1, int(detect_effective_capacity().effective_cores))
    except (OSError, ValueError):
        return 1


def _snapshot_payload_text(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise OfflineRuntimeError("OFFLINE_SNAPSHOT_INVALID") from exc
    if not isinstance(payload, dict):
        raise OfflineRuntimeError("OFFLINE_SNAPSHOT_INVALID")
    return payload


def _snapshot_payload(snapshot: ScheduleInputSnapshot) -> dict[str, Any]:
    return _snapshot_payload_text(snapshot.canonical_payload)


def _required_calendar_references(payload: Mapping[str, Any]) -> tuple[CalendarReference, ...]:
    """Collect every calendar reference the evaluator would resolve."""
    references: list[CalendarReference] = []

    def _add(value: object) -> None:
        if value is None:
            return
        references.append(_calendar_reference(value, "OFFLINE_SNAPSHOT_CALENDAR_INVALID"))

    _add(payload.get("project_calendar"))
    for item in payload.get("activity_calendar_assignments", ()):
        _add(_require_mapping(item, "OFFLINE_SNAPSHOT_CALENDAR_INVALID").get("calendar"))
    for item in payload.get("relationship_lag_calendar_assignments", ()):
        _add(_require_mapping(item, "OFFLINE_SNAPSHOT_CALENDAR_INVALID").get("calendar"))
    if payload.get("mode") == "TIME_AWARE":
        for item in payload.get("activities", ()):
            context = _require_mapping(item, "OFFLINE_SNAPSHOT_CALENDAR_INVALID").get("calendar_context")
            if context is None:
                continue
            context_map = _require_mapping(context, "OFFLINE_SNAPSHOT_CALENDAR_INVALID")
            _add(context_map.get("activity"))
            _add(context_map.get("relationship_lag"))
    ordered: dict[tuple[str, str, str], CalendarReference] = {}
    for reference in references:
        ordered.setdefault(
            (reference.calendar_id, reference.calendar_version, reference.kind),
            reference,
        )
    return tuple(ordered.values())


def _calendar_closure(
    required: tuple[CalendarReference, ...],
    entries: Mapping[tuple[str, str, str], OfflineCalendar],
) -> tuple[OfflineCalendar, ...]:
    selected: dict[tuple[str, str, str], OfflineCalendar] = {}
    pending = list(required)
    while pending:
        reference = pending.pop()
        key = (reference.calendar_id, reference.calendar_version, reference.kind)
        if key in selected:
            continue
        entry = entries.get(key)
        if entry is None:
            raise OfflineRuntimeError(
                "OFFLINE_CALENDAR_MISSING",
                f"{reference.calendar_id}@{reference.calendar_version}",
            )
        selected[key] = entry
        if entry.base is not None:
            base_key = (entry.base.calendar_id, entry.base.calendar_version, entry.base.kind)
            base = entries.get(base_key)
            if base is None:
                raise OfflineRuntimeError(
                    "OFFLINE_CALENDAR_BASE_MISSING",
                    f"{entry.base.calendar_id}@{entry.base.calendar_version}",
                )
            pending.append(entry.base)
    return tuple(
        selected[key]
        for key in sorted(selected, key=lambda item: (item[0], item[1], item[2]))
    )


def build_offline_bundle(
    snapshot: ScheduleInputSnapshot,
    calculation_context: CalculationContext,
    calendar_registry: CalendarResolverRegistry,
) -> OfflineScheduleBundle:
    """Bind one snapshot and its exact calendar definitions into an offline bundle."""
    if not isinstance(snapshot, ScheduleInputSnapshot):
        raise TypeError("snapshot must be a ScheduleInputSnapshot")
    if not isinstance(calculation_context, CalculationContext):
        raise TypeError("calculation_context must be a CalculationContext")
    if not isinstance(calendar_registry, CalendarResolverRegistry):
        raise TypeError("calendar_registry must be a CalendarResolverRegistry")

    try:
        snapshot.validate()
    except ScheduleSnapshotPersistenceError as exc:
        raise OfflineRuntimeError("OFFLINE_SNAPSHOT_INVALID", str(exc)) from exc
    if calculation_context.input_snapshot_id != snapshot.snapshot_id:
        raise OfflineRuntimeError("OFFLINE_CONTEXT_SNAPSHOT_MISMATCH")
    if calculation_context.project_id != snapshot.scope.project_id:
        raise OfflineRuntimeError("OFFLINE_CONTEXT_PROJECT_MISMATCH")
    if calculation_context.project_version != snapshot.scope.project_revision:
        raise OfflineRuntimeError("OFFLINE_CONTEXT_REVISION_MISMATCH")
    if (
        calculation_context.tenant_id is not None
        and calculation_context.tenant_id != snapshot.scope.tenant_id
    ):
        raise OfflineRuntimeError("OFFLINE_CONTEXT_TENANT_MISMATCH")
    if snapshot.calculation_identity_version == 2:
        identity = calculation_context.calculation_identity
    else:
        identity = calculation_context.legacy_calculation_identity
    if snapshot.calculation_identity != identity:
        raise OfflineRuntimeError("OFFLINE_CALCULATION_IDENTITY_MISMATCH")

    payload = _snapshot_payload(snapshot)
    entries = {
        (entry.reference.calendar_id, entry.reference.calendar_version, entry.reference.kind): OfflineCalendar(
            reference=entry.reference,
            snapshot=dict(entry.snapshot),
            base=entry.base,
            local_exceptions=tuple(dict(item) for item in entry.local_exceptions),
            inherited_exceptions=tuple(dict(item) for item in entry.inherited_exceptions),
        )
        for entry in calendar_registry.entries()
    }
    calendars = _calendar_closure(_required_calendar_references(payload), entries)
    return OfflineScheduleBundle(
        snapshot_payload=snapshot.canonical_payload,
        snapshot_hash=snapshot.snapshot_hash,
        calculation_identity=snapshot.calculation_identity,
        calculation_context=calculation_context.to_dict(),
        created_at=snapshot.created_at.isoformat(),
        calendars=calendars,
        record_revision=snapshot.record_revision,
        calculation_identity_version=snapshot.calculation_identity_version,
    )


@dataclass(frozen=True)
class OfflineScheduleExecution:
    """Result of executing one offline bundle."""

    bundle_hash: str
    snapshot_hash: str
    calculation_run_identity: str
    evaluation: ScheduleEvaluationResult


class OfflineSchedulingRuntime:
    """Execute a self-contained bundle through the authoritative engine.

    Construction validates every hash and reconstructs the exact snapshot,
    calculation context and calendar registry that the online path would use.
    Execution holds the network guard; no repository or transport is accepted.
    """

    def __init__(
        self,
        bundle: OfflineScheduleBundle,
        *,
        float_execution: FloatExecutionPolicy | None = None,
    ) -> None:
        if not isinstance(bundle, OfflineScheduleBundle):
            raise TypeError("bundle must be an OfflineScheduleBundle")
        if float_execution is not None and not isinstance(
            float_execution, FloatExecutionPolicy
        ):
            raise TypeError("float_execution must be a FloatExecutionPolicy")
        self._bundle = bundle
        self._snapshot, self._context, self._registry = self._reconstruct(bundle)
        self._float_execution = (
            float_execution
            if float_execution is not None
            else FloatExecutionPolicy(workers=_default_float_workers())
        )

    @property
    def bundle(self) -> OfflineScheduleBundle:
        return self._bundle

    @property
    def registry(self) -> CalendarResolverRegistry:
        return self._registry

    @property
    def snapshot(self) -> ScheduleInputSnapshot:
        return self._snapshot

    @property
    def calculation_context(self) -> CalculationContext:
        return self._context

    @classmethod
    def from_json(cls, text: str) -> "OfflineSchedulingRuntime":
        return cls(OfflineScheduleBundle.from_json(text))

    def _reconstruct(
        self, bundle: OfflineScheduleBundle
    ) -> tuple[ScheduleInputSnapshot, CalculationContext, CalendarResolverRegistry]:
        payload = _snapshot_payload_text(bundle.snapshot_payload)
        actual_hash = _sha256(bundle.snapshot_payload)
        if actual_hash != bundle.snapshot_hash:
            raise OfflineRuntimeError("OFFLINE_SNAPSHOT_HASH_MISMATCH")
        for field_name, code in (
            ("snapshot_id", "OFFLINE_SNAPSHOT_INVALID"),
            ("tenant_id", "OFFLINE_SNAPSHOT_INVALID"),
            ("project_id", "OFFLINE_SNAPSHOT_INVALID"),
        ):
            _require_text(payload.get(field_name), code)
        revision = payload.get("project_revision")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
            raise OfflineRuntimeError("OFFLINE_SNAPSHOT_INVALID")

        try:
            context = CalculationContext(**bundle.calculation_context)
        except (TypeError, ValueError) as exc:
            raise OfflineRuntimeError("OFFLINE_CALCULATION_CONTEXT_INVALID") from exc
        expected_identity = (
            context.calculation_identity
            if bundle.calculation_identity_version == 2
            else context.legacy_calculation_identity
        )
        if expected_identity != bundle.calculation_identity:
            raise OfflineRuntimeError("OFFLINE_CALCULATION_IDENTITY_MISMATCH")
        if context.input_snapshot_id != payload["snapshot_id"]:
            raise OfflineRuntimeError("OFFLINE_CONTEXT_SNAPSHOT_MISMATCH")

        try:
            snapshot = ScheduleInputSnapshot(
                scope=BackendScope(
                    payload["tenant_id"],
                    payload["project_id"],
                    revision,
                ),
                snapshot_id=payload["snapshot_id"],
                snapshot_hash=bundle.snapshot_hash,
                canonical_payload=bundle.snapshot_payload,
                calculation_identity=bundle.calculation_identity,
                created_at=datetime.fromisoformat(bundle.created_at),
                record_revision=bundle.record_revision,
                calculation_identity_version=bundle.calculation_identity_version,
            )
            snapshot.validate()
        except ScheduleSnapshotPersistenceError as exc:
            code = "OFFLINE_SNAPSHOT_HASH_MISMATCH" if "HASH" in str(exc) else "OFFLINE_SNAPSHOT_INVALID"
            raise OfflineRuntimeError(code) from exc
        except (TypeError, ValueError) as exc:
            raise OfflineRuntimeError("OFFLINE_SNAPSHOT_INVALID") from exc

        registry = _build_registry(bundle.calendars)
        available = {
            (entry.reference.calendar_id, entry.reference.calendar_version, entry.reference.kind)
            for entry in bundle.calendars
        }
        for reference in _required_calendar_references(payload):
            if (reference.calendar_id, reference.calendar_version, reference.kind) not in available:
                raise OfflineRuntimeError(
                    "OFFLINE_CALENDAR_MISSING",
                    f"{reference.calendar_id}@{reference.calendar_version}",
                )
        return snapshot, context, registry

    def execute(self) -> OfflineScheduleExecution:
        """Evaluate the bundle exactly as the online engine would."""
        try:
            with deny_network_access():
                evaluation = evaluate_schedule_snapshot(
                    self._snapshot,
                    self._context,
                    self._registry,
                    float_execution=self._float_execution,
                )
        except OfflineNetworkAccessError:
            raise
        except ScheduleEvaluationError as exc:
            code = str(exc)
            if code in {
                "SCHEDULE_LEVELING_INPUT_REQUIRED",
                "SCHEDULE_RESOURCE_INPUT_REQUIRED",
            }:
                raise OfflineRuntimeError(
                    "OFFLINE_LEVELING_INPUT_REQUIRED",
                    "resource leveling and resource-dependent inputs are not yet part of an offline bundle",
                ) from exc
            raise
        return OfflineScheduleExecution(
            bundle_hash=self._bundle.bundle_hash,
            snapshot_hash=self._snapshot.snapshot_hash,
            calculation_run_identity=evaluation.calculation_run_identity,
            evaluation=evaluation,
        )


def _snapshot_payload_text(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise OfflineRuntimeError("OFFLINE_SNAPSHOT_INVALID") from exc
    if not isinstance(payload, dict):
        raise OfflineRuntimeError("OFFLINE_SNAPSHOT_INVALID")
    return payload


def _build_registry(calendars: tuple[OfflineCalendar, ...]) -> CalendarResolverRegistry:
    day_resolvers = {}
    time_resolvers = {}
    exception_layers = {}
    base_references = {}
    for item in calendars:
        definition = item.definition()
        key = item.reference.calendar_id + "@" + item.reference.calendar_version
        if item.reference.kind == "working-day":
            day_resolvers[key] = WorkingTimeResolver(definition)  # type: ignore[arg-type]
        else:
            time_resolvers[key] = TimeAwareWorkingTimeResolver(definition)  # type: ignore[arg-type]
        if item.local_exceptions or item.inherited_exceptions:
            exception_layers[key] = CalendarExceptionLayers(
                local=tuple(_exception_from_snapshot(value) for value in item.local_exceptions),
                inherited=tuple(
                    _exception_from_snapshot(value) for value in item.inherited_exceptions
                ),
            )
        if item.base is not None:
            base_references[key] = item.base
    try:
        return CalendarResolverRegistry(
            day_resolvers=day_resolvers,
            time_resolvers=time_resolvers,
            exception_layers=exception_layers,
            base_calendar_references=base_references,
        )
    except (TypeError, ValueError) as exc:
        raise OfflineRuntimeError("OFFLINE_CALENDAR_INVALID") from exc
