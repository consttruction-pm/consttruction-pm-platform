from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timezone

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.backend_p0.models import BackendScope
from construction_pm.project_schedule_settings_repository import (
    PostgresProjectScheduleSettingsRepository,
    ProjectScheduleSettings,
)
from construction_pm.scheduling.authoritative_schedule import AuthoritativeScheduleMode
from construction_pm.scheduling.calendar_context import CalendarReference, RelationshipLagCalendar
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.schedule_options import (
    OutOfSequenceScheduleType,
    PriorityListItem,
    PrioritySortOrder,
    ScheduleMode,
    ScheduleOptions,
)


def make_settings(suffix: str) -> ProjectScheduleSettings:
    return ProjectScheduleSettings(
        scope=BackendScope(f"settings-tenant-{suffix}", f"settings-project-{suffix}", 7),
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference(
            f"CAL-{suffix}", "v26.10", "working-day", CalendarSystem.GREGORIAN
        ),
        project_start=date(2026, 10, 1),
        project_finish=date(2027, 3, 31),
        schedule_options=ScheduleOptions(
            mode=ScheduleMode.ALAP,
            out_of_sequence_schedule_type=OutOfSequenceScheduleType.PROGRESS_OVERRIDE,
            relationship_lag_calendar=RelationshipLagCalendar.SUCCESSOR,
            resource_list=(f"R-{suffix}",),
            priority_list=(
                PriorityListItem("Total Float", PrioritySortOrder.ASCENDING),
                PriorityListItem("Late Start", PrioritySortOrder.DESCENDING),
            ),
            level_all_resources=True,
            level_within_float=True,
            data_date=date(2026, 10, 15),
        ),
        project_leveling_priority=23,
    )


def test_project_schedule_settings_postgres_round_trip_update_and_scope_isolation() -> None:
    suffix = uuid.uuid4().hex
    original = make_settings(suffix)

    with psycopg.connect(DSN) as connection:
        repository = PostgresProjectScheduleSettingsRepository(connection)
        repository.initialize()
        connection.commit()

        with connection.transaction():
            created = repository.save(original, expected_revision=0)
        assert created.record_revision == 1
        assert repository.get(original.scope) == created

        changed = ProjectScheduleSettings(
            **{
                **created.__dict__,
                "project_finish": date(2027, 4, 30),
            }
        )
        with connection.transaction():
            updated = repository.save(changed, expected_revision=1)
        assert updated.record_revision == 2
        assert repository.get(original.scope) == updated

        isolated_scope = BackendScope(
            f"other-tenant-{suffix}", f"settings-project-{suffix}", 7
        )
        assert repository.get(isolated_scope) is None

        with connection.transaction():
            connection.execute(
                "DELETE FROM project_schedule_settings WHERE tenant_id=%s AND project_id=%s",
                (original.scope.tenant_id, original.scope.project_id),
            )


def test_project_schedule_settings_postgres_preserves_caller_owned_rollback() -> None:
    suffix = uuid.uuid4().hex
    settings = make_settings(suffix)
    writer = psycopg.connect(DSN)
    reader = psycopg.connect(DSN)
    try:
        repository = PostgresProjectScheduleSettingsRepository(writer)
        repository.initialize()
        writer.commit()
        reader_repository = PostgresProjectScheduleSettingsRepository(reader)

        with pytest.raises(RuntimeError, match="intentional rollback probe"):
            with writer.transaction():
                repository.save(settings, expected_revision=0)
                assert reader_repository.get(settings.scope) is None
                raise RuntimeError("intentional rollback probe")

        assert reader_repository.get(settings.scope) is None
    finally:
        with writer.transaction():
            writer.execute(
                "DELETE FROM project_schedule_settings WHERE tenant_id=%s AND project_id=%s",
                (settings.scope.tenant_id, settings.scope.project_id),
            )
        writer.close()
        reader.close()
