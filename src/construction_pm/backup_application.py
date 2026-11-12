"""Project and layout backup/recovery over the authoritative stores.

A snapshot is a canonical JSON document with one section per captured
repository, its project revision and a SHA-256 over the exact bytes. Restore
re-hashes the stored document, refuses a mismatch with
``BACKUP_INTEGRITY_FAILED``, decodes every record and validates it before the
first write, and then applies the selected sections in dependency order inside
one transaction.

Restore is additive: ``merge`` creates missing records and leaves existing ones
untouched, while ``overwrite`` updates existing records using their stored
record revision as the optimistic-concurrency token. Nothing is deleted, so a
restore can never silently drop data that is not in the snapshot.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping

from .application.authorization import (
    AuthorizationContext,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .backup_persistence import (
    BackupIdempotencyReuse,
    BackupRestoreRun,
    BackupSnapshot,
    BackupStore,
)
from .relationship_master_repository import RelationshipMaster
from .scheduling.activity import (
    ActivityLevelingPriority,
    ActivityStatus,
    ActivityStatusCode,
    ActivityType,
    PercentCompleteType,
)
from .scheduling.relationships import RelationshipType
from .scheduling.time_duration import DurationUnit
from .activity_master_repository import ActivityMaster
from .p6_layout_definition_repository import (
    LayoutColumn,
    PersistedP6Layout,
    layout_column_from_mapping,
)
from .p6_resource_master_api import P6ResourceAPI
from .p6_resource_master_repository import P6Resource
from .wbs_master_repository import WBSMaster, WBSParentKind

BACKUP_FORMAT = "cubi-backup.v1"
PROJECT_SECTIONS = ("wbs", "activities", "resources", "relationships")
LAYOUT_SECTIONS = ("layouts",)
LAYOUT_VIEWS = ("activity",)
LAYOUT_SCOPES = ("global", "project", "user")
MAX_SNAPSHOTS_PER_REQUEST = 200


class BackupError(ValueError):
    """A backup request is invalid, not found or cannot be applied."""


class BackupAuthorizationError(BackupError):
    """The caller lacks the permission required for the operation."""


@dataclass(frozen=True)
class BackupService:
    store: BackupStore
    activity_repository: Any
    wbs_repository: Any
    relationship_repository: Any
    resource_api: P6ResourceAPI
    layout_repository: Any
    authorization_policy: AuthorizationPolicy
    transaction_manager: Any

    # -- authorization -----------------------------------------------------

    def _check(
        self,
        scope: BackendScope,
        context: AuthorizationContext,
        permission: Permission,
    ) -> None:
        scope.validate()
        if (
            context.tenant_id != scope.tenant_id
            or context.project_id != scope.project_id
        ):
            raise BackupAuthorizationError("CROSS_SCOPE_ACCESS")
        if not self.authorization_policy.is_allowed(context, permission):
            raise BackupAuthorizationError("BACKUP_PERMISSION_DENIED")

    # -- capture -----------------------------------------------------------

    def capture(
        self,
        *,
        scope: BackendScope,
        kind: str,
        label: str,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        self._check(scope, context, Permission.PROJECT_WRITE)
        if kind not in {"project", "layouts"}:
            raise BackupError("INVALID_BACKUP_KIND")
        if not label.strip():
            raise BackupError("BACKUP_LABEL_REQUIRED")
        if not idempotency_key.strip():
            raise BackupError("BACKUP_IDEMPOTENCY_KEY_REQUIRED")
        request_hash = _hash_text(f"{kind}|{label}")
        replay = self.store.idempotent_result(
            scope.tenant_id, scope.project_id, "create", idempotency_key
        )
        if replay is not None:
            stored_hash, snapshot_id = replay
            if stored_hash != request_hash:
                raise BackupIdempotencyReuse("BACKUP_IDEMPOTENCY_KEY_REUSE")
            snapshot = self.store.get_snapshot(
                scope.tenant_id, scope.project_id, snapshot_id
            )
            if snapshot is None:
                raise BackupError("BACKUP_SNAPSHOT_NOT_FOUND")
            return {**self._snapshot_dto(snapshot), "replayed": True}

        sections: dict[str, list[dict[str, Any]]] = {}
        if kind == "project":
            sections["wbs"] = self._capture_wbs(scope)
            sections["activities"] = self._capture_activities(scope)
            sections["resources"] = self._capture_resources(scope)
            sections["relationships"] = self._capture_relationships(scope)
        else:
            sections["layouts"] = self._capture_layouts(scope)
        payload = {
            "format": BACKUP_FORMAT,
            "kind": kind,
            "project_revision": scope.project_revision,
            "sections": sections,
        }
        content_json = _canonical(payload)
        snapshot = BackupSnapshot(
            tenant_id=scope.tenant_id,
            project_id=scope.project_id,
            snapshot_id=self.store.next_snapshot_id(
                scope.tenant_id, scope.project_id
            ),
            kind=kind,
            label=label.strip(),
            project_revision=scope.project_revision,
            section_counts={
                name: len(records) for name, records in sections.items()
            },
            content_sha256=hashlib.sha256(content_json.encode("utf-8")).hexdigest(),
            content_json=content_json,
            actor_id=actor_id,
            occurred_at=occurred_at,
            idempotency_key=idempotency_key,
        )
        self.store.save_snapshot(snapshot)
        self.store.save_idempotent_result(
            tenant_id=scope.tenant_id,
            project_id=scope.project_id,
            operation="create",
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            result_id=snapshot.snapshot_id,
            occurred_at=occurred_at,
        )
        return {**self._snapshot_dto(snapshot), "replayed": False}

    def snapshots(
        self,
        *,
        scope: BackendScope,
        context: AuthorizationContext,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        self._check(scope, context, Permission.PROJECT_READ)
        return [
            self._snapshot_dto(snapshot)
            for snapshot in self.store.list_snapshots(
                scope.tenant_id, scope.project_id, limit
            )
        ]

    def snapshot(
        self,
        *,
        scope: BackendScope,
        snapshot_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        self._check(scope, context, Permission.PROJECT_READ)
        return self._snapshot_dto(self._require(scope, snapshot_id))

    def content(
        self,
        *,
        scope: BackendScope,
        snapshot_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        self._check(scope, context, Permission.PROJECT_READ)
        snapshot = self._require(scope, snapshot_id)
        payload = self._verified_payload(snapshot)
        return {
            "snapshot_id": snapshot.snapshot_id,
            "kind": snapshot.kind,
            "content_sha256": snapshot.content_sha256,
            "project_revision": snapshot.project_revision,
            "sections": payload["sections"],
        }

    # -- restore -----------------------------------------------------------

    def restore(
        self,
        *,
        scope: BackendScope,
        snapshot_id: str,
        mode: str,
        sections: Iterable[str] | None,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        self._check(scope, context, Permission.PROJECT_ADMIN)
        if mode not in {"merge", "overwrite"}:
            raise BackupError("INVALID_RESTORE_MODE")
        if not idempotency_key.strip():
            raise BackupError("BACKUP_IDEMPOTENCY_KEY_REQUIRED")
        requested = tuple(dict.fromkeys(sections or ()))
        request_hash = _hash_text(
            f"{snapshot_id}|{mode}|{','.join(sorted(requested))}"
        )
        replay = self.store.idempotent_result(
            scope.tenant_id, scope.project_id, "restore", idempotency_key
        )
        if replay is not None:
            stored_hash, run_id = replay
            if stored_hash != request_hash:
                raise BackupIdempotencyReuse("BACKUP_IDEMPOTENCY_KEY_REUSE")
            run = self.store.get_restore_run(scope.tenant_id, scope.project_id, run_id)
            if run is None:
                raise BackupError("BACKUP_RUN_NOT_FOUND")
            return {**self._run_dto(run), "replayed": True}

        snapshot = self._require(scope, snapshot_id)
        payload = self._verified_payload(snapshot)
        available = tuple(payload["sections"].keys())
        chosen = requested or available
        for name in chosen:
            if name not in available:
                raise BackupError("BACKUP_SECTION_UNKNOWN")

        counts: dict[str, dict[str, int]] = {}
        run = None
        try:
            with self.transaction_manager.transaction():
                if "layouts" in chosen:
                    counts["layouts"] = self._restore_layouts(
                        scope, payload["sections"]["layouts"], mode
                    )
                if "wbs" in chosen:
                    counts["wbs"] = self._restore_wbs(
                        scope, payload["sections"]["wbs"], mode
                    )
                if "activities" in chosen:
                    counts["activities"] = self._restore_activities(
                        scope, payload["sections"]["activities"], mode
                    )
                if "resources" in chosen:
                    counts["resources"] = self._restore_resources(
                        scope, payload["sections"]["resources"], mode, context
                    )
                if "relationships" in chosen:
                    counts["relationships"] = self._restore_relationships(
                        scope, payload["sections"]["relationships"], mode
                    )
        except BackupError:
            raise
        except (ValueError, KeyError, TypeError, InvalidOperation) as exc:
            raise BackupError(f"BACKUP_RESTORE_FAILED:{exc}") from exc
        run = BackupRestoreRun(
            tenant_id=scope.tenant_id,
            project_id=scope.project_id,
            run_id=self.store.next_run_id(scope.tenant_id, scope.project_id),
            snapshot_id=snapshot.snapshot_id,
            mode=mode,
            sections=counts,
            actor_id=actor_id,
            occurred_at=occurred_at,
            idempotency_key=idempotency_key,
        )
        self.store.save_restore_run(run)
        self.store.save_idempotent_result(
            tenant_id=scope.tenant_id,
            project_id=scope.project_id,
            operation="restore",
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            result_id=run.run_id,
            occurred_at=occurred_at,
        )
        return {**self._run_dto(run), "replayed": False}

    def restores(
        self,
        *,
        scope: BackendScope,
        context: AuthorizationContext,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        self._check(scope, context, Permission.PROJECT_READ)
        return [
            self._run_dto(run)
            for run in self.store.list_restore_runs(
                scope.tenant_id, scope.project_id, limit
            )
        ]

    # -- capture helpers ---------------------------------------------------

    def _capture_wbs(self, scope: BackendScope) -> list[dict[str, Any]]:
        return [
            {
                "wbs_id": item.wbs_id,
                "parent_kind": item.parent_kind.value,
                "parent_wbs_id": item.parent_wbs_id,
                "code": item.code,
                "name": item.name,
                "sequence_number": item.sequence_number,
            }
            for item in self.wbs_repository.list(scope)
        ]

    def _capture_activities(self, scope: BackendScope) -> list[dict[str, Any]]:
        return [
            {
                "activity_id": item.activity_id,
                "duration_value": str(item.duration_value),
                "duration_unit": item.duration_unit.value,
                "actual_start": _iso(item.actual_start),
                "expected_finish": _iso(item.expected_finish),
                "actual_finish": _iso(item.actual_finish),
                "remaining_duration": item.remaining_duration,
                "remaining_start": _iso(item.remaining_start),
                "percent_complete": item.percent_complete,
                "percent_complete_type": item.percent_complete_type.value,
                "planned_finish": _iso(item.planned_finish),
                "leveling_priority": item.leveling_priority.value,
                "original_duration": item.original_duration,
                "name": item.name,
                "short_name": item.short_name,
                "activity_type": item.activity_type.value,
                "status": item.status.value,
                "status_code": item.status_code.value,
                "wbs_id": item.wbs_id,
            }
            for item in self.activity_repository.list(scope)
        ]

    def _capture_resources(self, scope: BackendScope) -> list[dict[str, Any]]:
        return [
            {
                "resource_id": item.resource_id,
                "name": item.name,
                "resource_type": item.resource_type,
                "parent_resource_id": item.parent_resource_id,
                "calendar_id": item.calendar_id,
                "default_units_per_time": item.default_units_per_time,
                "unit_of_measure": item.unit_of_measure,
                "email": item.email,
                "is_active": item.is_active,
            }
            for item in self.resource_api.repository.list(
                scope.tenant_id, scope.project_id, scope.project_revision
            )
        ]

    def _capture_relationships(self, scope: BackendScope) -> list[dict[str, Any]]:
        return [
            {
                "relationship_id": item.relationship_id,
                "predecessor_id": item.predecessor_id,
                "successor_id": item.successor_id,
                "relationship_type": item.relationship_type.value,
                "lag_value": str(item.lag_value),
                "lag_unit": item.lag_unit.value,
            }
            for item in self.relationship_repository.list(scope)
        ]

    def _capture_layouts(self, scope: BackendScope) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for layout_scope in LAYOUT_SCOPES:
            for view_id in LAYOUT_VIEWS:
                layout = self.layout_repository.get(scope, layout_scope, view_id)
                if layout is None:
                    continue
                records.append(
                    {
                        "layout_scope": layout.layout_scope,
                        "view_id": layout.view_id,
                        "revision": layout.revision,
                        "columns": [
                            {
                                "field_id": column.field_id,
                                "visible": column.visible,
                                "order": column.order,
                                "label": column.label,
                                "width": column.width,
                                "alignment": column.alignment,
                                "pinned": column.pinned,
                                "frozen": column.frozen,
                            }
                            for column in layout.columns
                        ],
                        "metadata": dict(layout.metadata),
                    }
                )
        return records

    # -- restore helpers ---------------------------------------------------

    def _restore_wbs(
        self, scope: BackendScope, records: Any, mode: str
    ) -> dict[str, int]:
        incoming = [
            self._decode_wbs(scope, item) for item in _records(records)
        ]
        existing = {item.wbs_id: item for item in self.wbs_repository.list(scope)}
        counts = _counts()
        for record in _parents_first(incoming, "wbs_id", "parent_wbs_id"):
            current = existing.get(record.wbs_id)
            if current is None:
                self.wbs_repository.save(record, expected_revision=None)
                counts["created"] += 1
            elif mode == "overwrite" and not _same_wbs(current, record):
                self.wbs_repository.save(
                    record, expected_revision=current.record_revision
                )
                counts["updated"] += 1
            else:
                counts["skipped"] += 1
        return counts

    def _restore_activities(
        self, scope: BackendScope, records: Any, mode: str
    ) -> dict[str, int]:
        incoming = [self._decode_activity(scope, item) for item in _records(records)]
        existing = {
            item.activity_id: item for item in self.activity_repository.list(scope)
        }
        counts = _counts()
        for record in incoming:
            current = existing.get(record.activity_id)
            if current is None:
                self.activity_repository.save(record, expected_revision=None)
                counts["created"] += 1
            elif mode == "overwrite" and not _same_activity(current, record):
                self.activity_repository.save(
                    record, expected_revision=current.record_revision
                )
                counts["updated"] += 1
            else:
                counts["skipped"] += 1
        return counts

    def _restore_resources(
        self,
        scope: BackendScope,
        records: Any,
        mode: str,
        context: AuthorizationContext,
    ) -> dict[str, int]:
        incoming = [self._decode_resource(scope, item) for item in _records(records)]
        existing = {
            item["resource"]["resource_id"]: item["resource"]
            for item in self.resource_api.list(
                scope.tenant_id,
                scope.project_id,
                scope.project_revision,
                auth_context=context,
            )
        }
        counts = _counts()
        for record in _parents_first(
            incoming, "resource_id", "parent_resource_id"
        ):
            current = existing.get(record.resource_id)
            if current is None:
                self.resource_api.create(record, auth_context=context)
                counts["created"] += 1
            elif mode == "overwrite" and not _same_resource(current, record):
                self.resource_api.update(
                    record,
                    expected_revision=int(current["record_revision"]),
                    auth_context=context,
                )
                counts["updated"] += 1
            else:
                counts["skipped"] += 1
        return counts

    def _restore_relationships(
        self, scope: BackendScope, records: Any, mode: str
    ) -> dict[str, int]:
        incoming = [
            self._decode_relationship(scope, item) for item in _records(records)
        ]
        existing = {
            item.relationship_id: item
            for item in self.relationship_repository.list(scope)
        }
        counts = _counts()
        for record in incoming:
            current = existing.get(record.relationship_id)
            if current is None:
                self.relationship_repository.save(record, expected_revision=None)
                counts["created"] += 1
            elif mode == "overwrite" and not _same_relationship(current, record):
                self.relationship_repository.save(
                    record, expected_revision=current.record_revision
                )
                counts["updated"] += 1
            else:
                counts["skipped"] += 1
        return counts

    def _restore_layouts(
        self, scope: BackendScope, records: Any, mode: str
    ) -> dict[str, int]:
        counts = _counts()
        for raw in _records(records):
            layout_scope = _text(raw, "layout_scope")
            view_id = _text(raw, "view_id")
            if layout_scope not in LAYOUT_SCOPES:
                raise BackupError("INVALID_LAYOUT_SCOPE")
            if view_id not in LAYOUT_VIEWS:
                raise BackupError("INVALID_BACKUP_LAYOUT_VIEW")
            source_revision = _int(raw, "revision", minimum=0)
            columns = _layout_columns(raw.get("columns"))
            metadata = raw.get("metadata")
            if not isinstance(metadata, Mapping):
                raise BackupError("BACKUP_RECORD_INVALID")
            current = self.layout_repository.get(scope, layout_scope, view_id)
            if current is not None and (
                current.columns == columns
                and dict(current.metadata) == dict(metadata)
            ):
                counts["skipped"] += 1
                continue
            revision = (
                source_revision if current is None else current.revision + 1
            )
            layout = PersistedP6Layout(
                scope=scope,
                layout_scope=layout_scope,
                view_id=view_id,
                revision=revision,
                columns=columns,
                metadata=dict(metadata),
            )
            layout.validate()
            self.layout_repository.upsert(layout)
            if current is None:
                counts["created"] += 1
            else:
                counts["updated"] += 1
        return counts

    # -- decoding ----------------------------------------------------------

    def _decode_wbs(
        self, scope: BackendScope, raw: Mapping[str, Any]
    ) -> WBSMaster:
        kind = _text(raw, "parent_kind")
        try:
            parent_kind = WBSParentKind(kind)
        except ValueError as exc:
            raise BackupError("BACKUP_RECORD_INVALID") from exc
        record = WBSMaster(
            scope=scope,
            wbs_id=_text(raw, "wbs_id"),
            parent_kind=parent_kind,
            parent_wbs_id=_optional_text(raw, "parent_wbs_id"),
            code=_text(raw, "code"),
            name=_text(raw, "name"),
            sequence_number=_int(raw, "sequence_number", minimum=0),
        )
        return record

    def _decode_activity(
        self, scope: BackendScope, raw: Mapping[str, Any]
    ) -> ActivityMaster:
        try:
            record = ActivityMaster(
                scope=scope,
                activity_id=_text(raw, "activity_id"),
                duration_value=_decimal(raw.get("duration_value")),
                duration_unit=DurationUnit(_text(raw, "duration_unit")),
                actual_start=_date(raw.get("actual_start")),
                expected_finish=_date(raw.get("expected_finish")),
                actual_finish=_date(raw.get("actual_finish")),
                remaining_duration=_optional_int(raw.get("remaining_duration")),
                remaining_start=_date(raw.get("remaining_start")),
                percent_complete=_optional_number(raw.get("percent_complete")),
                percent_complete_type=PercentCompleteType(
                    _text(raw, "percent_complete_type")
                ),
                planned_finish=_date(raw.get("planned_finish")),
                leveling_priority=ActivityLevelingPriority(
                    _text(raw, "leveling_priority")
                ),
                original_duration=_optional_int(raw.get("original_duration")),
                name=str(raw.get("name") or ""),
                short_name=_optional_text(raw, "short_name"),
                activity_type=ActivityType(_text(raw, "activity_type")),
                status=ActivityStatus(_text(raw, "status")),
                status_code=ActivityStatusCode(_text(raw, "status_code")),
                wbs_id=_optional_text(raw, "wbs_id"),
            )
            record.validate()
        except (TypeError, ValueError) as exc:
            raise BackupError("BACKUP_RECORD_INVALID") from exc
        return record

    def _decode_resource(
        self, scope: BackendScope, raw: Mapping[str, Any]
    ) -> P6Resource:
        try:
            record = P6Resource(
                tenant_id=scope.tenant_id,
                project_id=scope.project_id,
                project_revision=scope.project_revision,
                resource_id=_text(raw, "resource_id"),
                name=_text(raw, "name"),
                resource_type=_text(raw, "resource_type"),
                parent_resource_id=_optional_text(raw, "parent_resource_id"),
                calendar_id=_optional_text(raw, "calendar_id"),
                default_units_per_time=_optional_text(raw, "default_units_per_time"),
                unit_of_measure=_optional_text(raw, "unit_of_measure"),
                email=_optional_text(raw, "email"),
                is_active=bool(raw.get("is_active", True)),
            )
            record.validate()
        except (TypeError, ValueError) as exc:
            raise BackupError("BACKUP_RECORD_INVALID") from exc
        return record

    def _decode_relationship(
        self, scope: BackendScope, raw: Mapping[str, Any]
    ) -> RelationshipMaster:
        try:
            record = RelationshipMaster(
                scope=scope,
                relationship_id=_text(raw, "relationship_id"),
                predecessor_id=_text(raw, "predecessor_id"),
                successor_id=_text(raw, "successor_id"),
                relationship_type=RelationshipType(_text(raw, "relationship_type")),
                lag_value=_decimal(raw.get("lag_value")),
                lag_unit=DurationUnit(_text(raw, "lag_unit")),
            )
            record.validate()
        except (TypeError, ValueError) as exc:
            raise BackupError("BACKUP_RECORD_INVALID") from exc
        return record

    # -- lookup / verification --------------------------------------------

    def _require(self, scope: BackendScope, snapshot_id: str) -> BackupSnapshot:
        snapshot = self.store.get_snapshot(
            scope.tenant_id, scope.project_id, snapshot_id
        )
        if snapshot is None:
            raise BackupError("BACKUP_SNAPSHOT_NOT_FOUND")
        return snapshot

    def _verified_payload(self, snapshot: BackupSnapshot) -> dict[str, Any]:
        digest = hashlib.sha256(snapshot.content_json.encode("utf-8")).hexdigest()
        if digest != snapshot.content_sha256:
            raise BackupError("BACKUP_INTEGRITY_FAILED")
        try:
            payload = json.loads(snapshot.content_json)
        except ValueError as exc:
            raise BackupError("BACKUP_INTEGRITY_FAILED") from exc
        if not isinstance(payload, dict) or payload.get("format") != BACKUP_FORMAT:
            raise BackupError("BACKUP_INTEGRITY_FAILED")
        sections = payload.get("sections")
        if not isinstance(sections, dict):
            raise BackupError("BACKUP_INTEGRITY_FAILED")
        for name, records in sections.items():
            if not isinstance(name, str) or not isinstance(records, list):
                raise BackupError("BACKUP_INTEGRITY_FAILED")
            if any(not isinstance(item, dict) for item in records):
                raise BackupError("BACKUP_INTEGRITY_FAILED")
        return payload

    def _snapshot_dto(self, snapshot: BackupSnapshot) -> dict[str, Any]:
        return {
            "snapshot_id": snapshot.snapshot_id,
            "kind": snapshot.kind,
            "label": snapshot.label,
            "project_revision": snapshot.project_revision,
            "section_counts": dict(snapshot.section_counts),
            "content_sha256": snapshot.content_sha256,
            "actor_id": snapshot.actor_id,
            "occurred_at": snapshot.occurred_at.isoformat(),
        }

    def _run_dto(self, run: BackupRestoreRun) -> dict[str, Any]:
        return {
            "run_id": run.run_id,
            "snapshot_id": run.snapshot_id,
            "mode": run.mode,
            "sections": {name: dict(value) for name, value in run.sections.items()},
            "actor_id": run.actor_id,
            "occurred_at": run.occurred_at.isoformat(),
        }


# -- primitives ------------------------------------------------------------


def _canonical(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _iso(value: object) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _text(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BackupError("BACKUP_RECORD_INVALID")
    return value


def _optional_text(raw: Mapping[str, Any], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise BackupError("BACKUP_RECORD_INVALID")
    return value


def _int(raw: Mapping[str, Any], key: str, *, minimum: int) -> int:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise BackupError("BACKUP_RECORD_INVALID")
    return value


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BackupError("BACKUP_RECORD_INVALID")
    return value


def _optional_number(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BackupError("BACKUP_RECORD_INVALID")
    return float(value)


def _decimal(value: object) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise BackupError("BACKUP_RECORD_INVALID") from exc
    if not parsed.is_finite():
        raise BackupError("BACKUP_RECORD_INVALID")
    return parsed


def _date(value: object) -> date | datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise BackupError("BACKUP_RECORD_INVALID")
    try:
        return datetime.fromisoformat(value) if "T" in value else date.fromisoformat(value)
    except ValueError as exc:
        raise BackupError("BACKUP_RECORD_INVALID") from exc


def _records(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise BackupError("BACKUP_INTEGRITY_FAILED")
    if any(not isinstance(item, Mapping) for item in value):
        raise BackupError("BACKUP_INTEGRITY_FAILED")
    return list(value)


def _layout_columns(value: object) -> tuple[LayoutColumn, ...]:
    if not isinstance(value, list):
        raise BackupError("BACKUP_RECORD_INVALID")
    try:
        columns = tuple(layout_column_from_mapping(item) for item in value)
    except ValueError as exc:
        raise BackupError("BACKUP_RECORD_INVALID") from exc
    if tuple(column.order for column in columns) != tuple(range(len(columns))):
        raise BackupError("BACKUP_RECORD_INVALID")
    return columns


def _parents_first(
    records: Iterable[Any],
    id_attr: str,
    parent_attr: str,
    *,
    key: str | None = None,
) -> list[Any]:
    """Order records parents-first without trusting the stored order."""
    by_id: dict[str, Any] = {}
    for record in records:
        identifier = record[key] if key else getattr(record, id_attr)
        parent = record[parent_attr] if key else getattr(record, parent_attr)
        if identifier in by_id:
            raise BackupError("BACKUP_RECORD_DUPLICATE")
        by_id[identifier] = (record, parent)

    ordered: list[Any] = []
    visiting: set[str] = set()

    def visit(identifier: str) -> None:
        if identifier in visiting:
            raise BackupError("BACKUP_RECORD_CYCLE")
        record, parent = by_id[identifier]
        if parent in by_id:
            visiting.add(identifier)
            visit(parent)
            visiting.discard(identifier)
        ordered.append(record)

    for identifier in by_id:
        visit(identifier)
    return ordered


def _counts() -> dict[str, int]:
    return {"created": 0, "updated": 0, "skipped": 0}


def _same_wbs(current: WBSMaster, incoming: WBSMaster) -> bool:
    return (
        current.parent_kind == incoming.parent_kind
        and current.parent_wbs_id == incoming.parent_wbs_id
        and current.code == incoming.code
        and current.name == incoming.name
        and current.sequence_number == incoming.sequence_number
    )


def _same_activity(current: ActivityMaster, incoming: ActivityMaster) -> bool:
    return current.payload() == incoming.payload()


def _same_resource(current: Mapping[str, Any], incoming: P6Resource) -> bool:
    return (
        current.get("name") == incoming.name
        and current.get("resource_type") == incoming.resource_type
        and current.get("parent_resource_id") == incoming.parent_resource_id
        and current.get("calendar_id") == incoming.calendar_id
        and str(current.get("default_units_per_time"))
        == str(incoming.default_units_per_time)
        and current.get("unit_of_measure") == incoming.unit_of_measure
        and current.get("email") == incoming.email
        and current.get("is_active") == incoming.is_active
    )


def _same_relationship(
    current: RelationshipMaster, incoming: RelationshipMaster
) -> bool:
    return (
        current.predecessor_id == incoming.predecessor_id
        and current.successor_id == incoming.successor_id
        and current.relationship_type == incoming.relationship_type
        and current.lag_value == incoming.lag_value
        and current.lag_unit == incoming.lag_unit
    )


__all__ = [
    "BACKUP_FORMAT",
    "LAYOUT_SCOPES",
    "LAYOUT_SECTIONS",
    "LAYOUT_VIEWS",
    "PROJECT_SECTIONS",
    "BackupAuthorizationError",
    "BackupError",
    "BackupService",
]
