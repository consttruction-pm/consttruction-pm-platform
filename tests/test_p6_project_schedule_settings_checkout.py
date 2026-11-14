from __future__ import annotations

from dataclasses import replace
from datetime import date
from types import SimpleNamespace

from construction_pm.application.authorization import (
    AuthorizationContext,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_schedule_snapshot_publication_api import (
    P6ScheduleSnapshotPublicationAPI,
)
from construction_pm.project_schedule_settings_repository import (
    ProjectScheduleSettings,
    ProjectScheduleSettingsPersistenceError,
)
from construction_pm.scheduling.authoritative_schedule import AuthoritativeScheduleMode
from construction_pm.scheduling.calendar_context import CalendarReference
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.schedule_options import ScheduleOptions

import pytest


SCOPE = BackendScope("T-1", "P-1", 7)


def _settings() -> ProjectScheduleSettings:
    return ProjectScheduleSettings(
        scope=SCOPE,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference(
            "CAL-1", "1", "working-day", CalendarSystem.GREGORIAN
        ),
        project_start=date(2026, 1, 5),
        schedule_options=ScheduleOptions(),
        project_leveling_priority=10,
    )


class _SettingsRepository:
    def __init__(self) -> None:
        self.saved: list[ProjectScheduleSettings] = []

    def save(
        self,
        settings: ProjectScheduleSettings,
        expected_revision: int | None = None,
    ) -> ProjectScheduleSettings:
        self.saved.append(settings)
        return replace(settings, record_revision=3)

    def get(self, scope: BackendScope) -> ProjectScheduleSettings | None:
        return None


class _Calendars:
    def get(self, scope: BackendScope, calendar_id: str, version: str) -> object:
        return SimpleNamespace(kind="working-day")


class _Lease:
    def __init__(self, holder: str | None) -> None:
        self.holder = holder
        self.reads = 0

    def checked_out_by(self, scope: BackendScope) -> str | None:
        self.reads += 1
        return self.holder


def _api(lease: _Lease | None, repository: _SettingsRepository):
    policy = RoleBasedAuthorizationPolicy(
        {"admin": frozenset({Permission.PROJECT_SCHEDULE})}
    )
    return P6ScheduleSnapshotPublicationAPI(
        object(),
        policy,
        repository,
        _Calendars(),
        checkout_lease=lease,
    )


def _auth(user_id: str = "owner-1") -> AuthorizationContext:
    return AuthorizationContext("T-1", "P-1", user_id, frozenset({"admin"}))


def test_checked_out_by_another_user_rejects_the_settings_write():
    repository = _SettingsRepository()
    lease = _Lease("owner-2")
    with pytest.raises(ProjectScheduleSettingsPersistenceError) as raised:
        _api(lease, repository).save_settings(
            SCOPE,
            settings=_settings(),
            expected_revision=0,
            auth_context=_auth(),
        )
    assert str(raised.value) == "PROJECT_CHECKED_OUT_BY_OTHER"
    assert repository.saved == []
    assert lease.reads == 1


def test_the_checkout_owner_can_still_save_settings():
    repository = _SettingsRepository()
    result = _api(_Lease("owner-1"), repository).save_settings(
        SCOPE,
        settings=_settings(),
        expected_revision=0,
        auth_context=_auth("owner-1"),
    )
    assert result["record_revision"] == 3
    assert result["project_leveling_priority"] == 10
    assert len(repository.saved) == 1


def test_an_unleased_project_writes_are_unchanged():
    repository = _SettingsRepository()
    result = _api(_Lease(None), repository).save_settings(
        SCOPE,
        settings=_settings(),
        expected_revision=2,
        auth_context=_auth(),
    )
    assert result["record_revision"] == 3
    assert len(repository.saved) == 1


def test_a_runtime_without_a_lease_reader_keeps_the_previous_behaviour():
    repository = _SettingsRepository()
    result = _api(None, repository).save_settings(
        SCOPE,
        settings=_settings(),
        expected_revision=2,
        auth_context=_auth(),
    )
    assert result["record_revision"] == 3
    assert len(repository.saved) == 1
