from __future__ import annotations

"""Authenticated API boundary for publishing authoritative schedule snapshots."""

from dataclasses import dataclass
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .authoritative_schedule_input_composer import (
    ScheduleInputCompositionError,
)
from .project_schedule_settings_repository import (
    ProjectScheduleSettings,
    ProjectScheduleSettingsPersistenceError,
    ProjectScheduleSettingsRepository,
    _schedule_options_payload,
)
from .schedule_snapshot_publisher import (
    AuthoritativeScheduleSnapshotPublisher,
    ScheduleSnapshotPublicationError,
)


P6_SCHEDULE_SNAPSHOT_API_VERSION = "p6-schedule-snapshot-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


@dataclass(frozen=True)
class P6ScheduleSnapshotPublicationAPI:
    """Requires scheduling permission and publishes only from fresh persisted reads."""

    publisher: AuthoritativeScheduleSnapshotPublisher
    authorization_policy: AuthorizationPolicy
    project_schedule_settings_repository: ProjectScheduleSettingsRepository

    def _require_schedule_permission(
        self,
        scope: BackendScope,
        auth_context: AuthorizationContext,
    ) -> None:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_SCHEDULE):
            raise AuthorizationError("authorization denied for permission=project.schedule")

    @staticmethod
    def _settings_dto(settings: ProjectScheduleSettings) -> dict[str, Any]:
        return {
            "contract_version": "p6-project-schedule-settings-api.v1",
            "kind": "project_schedule_settings",
            "scope": {
                "tenant_id": settings.scope.tenant_id,
                "project_id": settings.scope.project_id,
                "project_revision": settings.scope.project_revision,
            },
            "record_revision": settings.record_revision,
            "mode": settings.mode.value,
            "project_calendar": {
                "calendar_id": settings.project_calendar.calendar_id,
                "calendar_version": settings.project_calendar.calendar_version,
                "kind": settings.project_calendar.kind,
                "system": settings.project_calendar.system.value,
            },
            "project_start": settings.project_start.isoformat(),
            "project_finish": (
                None if settings.project_finish is None else settings.project_finish.isoformat()
            ),
            "schedule_options": _schedule_options_payload(settings.schedule_options),
            "project_leveling_priority": settings.project_leveling_priority,
        }

    def save_settings(
        self,
        scope: BackendScope,
        *,
        settings: ProjectScheduleSettings,
        expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        self._require_schedule_permission(scope, auth_context)
        if settings.scope != scope:
            raise ProjectScheduleSettingsPersistenceError("SETTINGS_SCOPE_MISMATCH")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 0:
            raise ProjectScheduleSettingsPersistenceError("INVALID_EXPECTED_REVISION")
        try:
            settings.validate()
            stored = self.project_schedule_settings_repository.save(
                settings,
                expected_revision=expected_revision,
            )
        except ProjectScheduleSettingsPersistenceError:
            raise
        except (TypeError, ValueError, ArithmeticError) as exc:
            raise ProjectScheduleSettingsPersistenceError(
                f"INVALID_PROJECT_SCHEDULE_SETTINGS:{exc}"
            ) from exc
        return self._settings_dto(stored)

    def get_settings(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        self._require_schedule_permission(scope, auth_context)
        try:
            settings = self.project_schedule_settings_repository.get(scope)
        except ProjectScheduleSettingsPersistenceError:
            raise
        if settings is None:
            return None
        return self._settings_dto(settings)

    def publish(
        self,
        scope: BackendScope,
        *,
        timezone_name: str,
        auth_context: AuthorizationContext,
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        self._require_schedule_permission(scope, auth_context)
        try:
            result = self.publisher.publish(
                scope,
                timezone_name=timezone_name,
                actor_id=auth_context.user_id,
                request_id=request_id,
                idempotency_key=idempotency_key,
            )
        except (ScheduleSnapshotPublicationError, ScheduleInputCompositionError):
            raise
        return {
            "contract_version": P6_SCHEDULE_SNAPSHOT_API_VERSION,
            "kind": "schedule_input_snapshot",
            "scope": {
                "tenant_id": result.scope.tenant_id,
                "project_id": result.scope.project_id,
                "project_revision": result.scope.project_revision,
            },
            "snapshot_id": result.snapshot_id,
            "snapshot_hash": result.snapshot_hash,
            "calculation_identity": result.calculation_identity,
            "created_at": result.created_at.isoformat(),
        }


__all__ = [
    "P6_SCHEDULE_SNAPSHOT_API_VERSION",
    "P6ScheduleSnapshotPublicationAPI",
]
