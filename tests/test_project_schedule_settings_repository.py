from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.project_schedule_settings_repository import (
    ProjectScheduleSettings,
    ProjectScheduleSettingsPersistenceError,
    PostgresProjectScheduleSettingsRepository,
    SQLiteProjectScheduleSettingsRepository,
)
from construction_pm.scheduling.authoritative_schedule import AuthoritativeScheduleMode
from construction_pm.scheduling.calendar_context import CalendarReference, RelationshipLagCalendar
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.schedule_options import (
    CriticalActivityPathType,
    OutOfSequenceScheduleType,
    PriorityListItem,
    PrioritySortOrder,
    ScheduleMode,
    ScheduleOptions,
    StartToStartLagCalculationType,
    TotalFloatCalculationType,
)


def scope(revision: int = 7, tenant: str = "T-1", project: str = "P-1") -> BackendScope:
    return BackendScope(tenant, project, revision)


def date_settings(revision: int = 7) -> ProjectScheduleSettings:
    options = ScheduleOptions(
        mode=ScheduleMode.ALAP,
        compute_total_float_type=TotalFloatCalculationType.FINISH_FLOAT,
        critical_activity_float_threshold=0.5,
        critical_activity_path_type=CriticalActivityPathType.LONGEST_PATH,
        make_open_ended_activities_critical=True,
        multiple_float_paths_enabled=True,
        maximum_multiple_float_paths=12,
        multiple_float_paths_ending_activity_object_id="END-1",
        multiple_float_paths_ending_activity_short_name="END",
        multiple_float_paths_use_total_float=False,
        min_float_to_preserve=4,
        out_of_sequence_schedule_type=OutOfSequenceScheduleType.PROGRESS_OVERRIDE,
        start_to_start_lag_calculation_type=StartToStartLagCalculationType.ACTUAL_START,
        relationship_lag_calendar=RelationshipLagCalendar.SUCCESSOR,
        use_expected_finish_dates=True,
        recalculate_resource_costs=True,
        calculate_float_based_on_finish_date=True,
        ignore_other_project_relationships=True,
        include_external_res_ass=True,
        level_all_resources=True,
        level_within_float=True,
        over_allocation_percentage=12.5,
        resource_list=("R-1", "R-2"),
        priority_list=(
            PriorityListItem("Total Float", PrioritySortOrder.ASCENDING),
            PriorityListItem("Late Start", PrioritySortOrder.DESCENDING),
        ),
        external_project_priority_limit=9,
        preserve_scheduled_early_and_late_dates=True,
        data_date=date(2026, 10, 15),
    )
    return ProjectScheduleSettings(
        scope=scope(revision),
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference(
            "CAL-PROJECT", "v3", "working-day", CalendarSystem.GREGORIAN
        ),
        project_start=date(2026, 10, 1),
        project_finish=date(2027, 3, 31),
        schedule_options=options,
        project_leveling_priority=23,
    )


def test_project_schedule_settings_round_trip_preserves_all_options_and_calendar_identity():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteProjectScheduleSettingsRepository(connection)
    original = date_settings()

    stored = repo.save(original, expected_revision=0)
    loaded = repo.get(scope())

    assert stored.record_revision == 1
    assert loaded == stored
    assert loaded is not None
    assert loaded.project_calendar == original.project_calendar
    assert loaded.schedule_options == original.schedule_options
    assert loaded.schedule_options.data_date == date(2026, 10, 15)
    assert loaded.schedule_options.resource_list == ("R-1", "R-2")
    assert loaded.schedule_options.priority_list == original.schedule_options.priority_list
    assert loaded.project_leveling_priority == 23


def test_project_schedule_settings_update_requires_exact_record_revision():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteProjectScheduleSettingsRepository(connection)
    repo.save(date_settings(), expected_revision=0)

    changed = replace(
        date_settings(),
        project_finish=date(2027, 4, 30),
        project_leveling_priority=24,
    )
    saved = repo.save(changed, expected_revision=1)
    assert saved.record_revision == 2
    assert repo.get(scope()) == saved

    with pytest.raises(ProjectScheduleSettingsPersistenceError, match="REVISION_CONFLICT"):
        repo.save(changed, expected_revision=1)


def test_project_schedule_settings_history_is_append_only_and_newest_first():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteProjectScheduleSettingsRepository(connection)
    first = repo.save(date_settings(), expected_revision=0)
    second = repo.save(
        replace(date_settings(), project_leveling_priority=24),
        expected_revision=first.record_revision,
    )
    third = repo.save(
        replace(date_settings(), project_leveling_priority=25),
        expected_revision=second.record_revision,
    )

    revisions = repo.list_revisions(scope())
    assert [item.record_revision for item in revisions] == [3, 2, 1]
    assert [item.project_leveling_priority for item in revisions] == [25, 24, 23]
    assert revisions[0] == third
    assert revisions[1] == second
    assert revisions[2] == first
    assert repo.get(scope()) == third

    with pytest.raises(ProjectScheduleSettingsPersistenceError, match="REVISION_CONFLICT"):
        repo.save(replace(date_settings(), project_leveling_priority=26), expected_revision=1)
    assert [item.record_revision for item in repo.list_revisions(scope())] == [3, 2, 1]


def test_sqlite_settings_history_detects_tampering_and_scope_changes():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteProjectScheduleSettingsRepository(connection)
    repo.save(date_settings(), expected_revision=0)

    assert repo.list_revisions(scope(8)) == []
    assert repo.list_revisions(scope(tenant="T-2")) == []
    assert repo.list_revisions(scope(project="P-2")) == []
    connection.execute(
        "UPDATE project_schedule_settings_history SET canonical_payload=? "
        "WHERE tenant_id=? AND project_id=? AND record_revision=1",
        ('{"tampered":true}', "T-1", "P-1"),
    )
    connection.commit()
    with pytest.raises(ProjectScheduleSettingsPersistenceError, match="SETTINGS_HASH_MISMATCH"):
        repo.list_revisions(scope())


def test_sqlite_settings_history_limit_is_bounded():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteProjectScheduleSettingsRepository(connection)
    first = repo.save(date_settings(), expected_revision=0)
    second = repo.save(
        replace(date_settings(), project_leveling_priority=24),
        expected_revision=first.record_revision,
    )
    repo.save(
        replace(date_settings(), project_leveling_priority=25),
        expected_revision=second.record_revision,
    )

    assert [item.record_revision for item in repo.list_revisions(scope(), limit=2)] == [3, 2]
    for invalid in (0, 101, True):
        with pytest.raises(
            ProjectScheduleSettingsPersistenceError,
            match="INVALID_SETTINGS_HISTORY_LIMIT",
        ):
            repo.list_revisions(scope(), limit=invalid)


def _prepare_history_conflict(
    connection: sqlite3.Connection,
    repo: SQLiteProjectScheduleSettingsRepository,
) -> None:
    repo.save(date_settings(), expected_revision=0)
    # Keep the revision-1 history row but remove the current settings row so
    # the next save tries to append a duplicate revision and must roll back.
    connection.execute(
        "DELETE FROM project_schedule_settings WHERE tenant_id=? AND project_id=?",
        ("T-1", "P-1"),
    )
    connection.commit()


def test_sqlite_settings_history_conflict_rolls_back_the_settings_write():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteProjectScheduleSettingsRepository(connection)
    _prepare_history_conflict(connection, repo)

    with pytest.raises(ProjectScheduleSettingsPersistenceError, match="SETTINGS_HISTORY_CONFLICT"):
        repo.save(date_settings(), expected_revision=0)

    assert connection.in_transaction is False
    assert repo.get(scope()) is None
    assert [item.record_revision for item in repo.list_revisions(scope())] == [1]


def test_sqlite_settings_repository_does_not_commit_a_caller_owned_transaction(tmp_path):
    database = str(tmp_path / "settings-constructor-transaction.sqlite")
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE marker (value TEXT NOT NULL)")
    connection.commit()
    connection.execute("BEGIN")
    connection.execute("INSERT INTO marker (value) VALUES ('pending')")

    SQLiteProjectScheduleSettingsRepository(connection)

    assert connection.in_transaction is True
    connection.rollback()
    assert connection.execute("SELECT COUNT(*) FROM marker").fetchone()[0] == 0
    connection.close()


def test_sqlite_settings_history_conflict_preserves_caller_owned_transaction(tmp_path):
    database = str(tmp_path / "settings-history-conflict.sqlite")
    writer = sqlite3.connect(database)
    repo = SQLiteProjectScheduleSettingsRepository(writer)
    reader = sqlite3.connect(database)
    reader_repo = SQLiteProjectScheduleSettingsRepository(reader)
    _prepare_history_conflict(writer, repo)

    writer.execute("BEGIN")
    with pytest.raises(ProjectScheduleSettingsPersistenceError, match="SETTINGS_HISTORY_CONFLICT"):
        repo.save(
            replace(date_settings(), project_leveling_priority=99),
            expected_revision=0,
        )
    assert writer.in_transaction is True
    assert reader_repo.get(scope()) is None
    # Committing after handling the error must not persist a settings row
    # whose history append failed inside the caller-owned transaction.
    writer.commit()
    assert reader_repo.get(scope()) is None
    assert [item.record_revision for item in reader_repo.list_revisions(scope())] == [1]
    reader.close()
    writer.close()


def test_project_schedule_settings_history_preserves_caller_owned_transaction(tmp_path):
    database = str(tmp_path / "settings-history-transaction.sqlite")
    writer = sqlite3.connect(database)
    repo = SQLiteProjectScheduleSettingsRepository(writer)
    reader = sqlite3.connect(database)
    reader_repo = SQLiteProjectScheduleSettingsRepository(reader)

    writer.execute("BEGIN")
    repo.save(date_settings(), expected_revision=0)
    assert reader_repo.list_revisions(scope()) == []
    writer.rollback()
    assert reader_repo.list_revisions(scope()) == []
    reader.close()
    writer.close()


def test_project_schedule_settings_fails_closed_on_missing_or_stale_project_revision():
    repo = SQLiteProjectScheduleSettingsRepository(sqlite3.connect(":memory:"))
    assert repo.get(scope()) is None
    repo.save(date_settings())

    with pytest.raises(ProjectScheduleSettingsPersistenceError, match="REVISION_CONFLICT"):
        repo.get(scope(8))
    with pytest.raises(ProjectScheduleSettingsPersistenceError, match="REVISION_CONFLICT"):
        repo.save(date_settings(revision=8), expected_revision=1)


def test_project_schedule_settings_rejects_calendar_mode_mismatch_and_naive_datetime():
    with pytest.raises(
        ProjectScheduleSettingsPersistenceError,
        match="PROJECT_CALENDAR_KIND_MODE_MISMATCH",
    ):
        ProjectScheduleSettings(
            scope=scope(),
            mode=AuthoritativeScheduleMode.DATE_BASED,
            project_calendar=CalendarReference("CAL-1", "1", "working-time"),
            project_start=date(2026, 10, 1),
            schedule_options=ScheduleOptions(),
            project_leveling_priority=10,
        ).validate()

    with pytest.raises(
        ProjectScheduleSettingsPersistenceError,
        match="TIMEZONE_REQUIRED_FOR_PROJECT_START",
    ):
        ProjectScheduleSettings(
            scope=scope(),
            mode=AuthoritativeScheduleMode.TIME_AWARE,
            project_calendar=CalendarReference("CAL-1", "1", "working-time"),
            project_start=datetime(2026, 10, 1, 8, 0),
            schedule_options=ScheduleOptions(),
            project_leveling_priority=10,
        ).validate()


def test_time_aware_project_schedule_settings_preserve_timezone_precision():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteProjectScheduleSettingsRepository(connection)
    original = ProjectScheduleSettings(
        scope=scope(),
        mode=AuthoritativeScheduleMode.TIME_AWARE,
        project_calendar=CalendarReference(
            "CAL-TIME", "2026.10", "working-time", CalendarSystem.GREGORIAN
        ),
        project_start=datetime.fromisoformat("2026-10-01T08:15:30.123456+02:00"),
        project_finish=datetime.fromisoformat("2026-10-31T17:45:00.654321+02:00"),
        schedule_options=ScheduleOptions(data_date=date(2026, 10, 15)),
        project_leveling_priority=10,
    )

    repo.save(original, expected_revision=0)
    loaded = repo.get(scope())

    assert loaded == replace(original, record_revision=1)
    assert loaded is not None
    assert loaded.project_start.isoformat() == "2026-10-01T08:15:30.123456+02:00"
    assert loaded.project_finish.isoformat() == "2026-10-31T17:45:00.654321+02:00"


def test_sqlite_settings_repository_preserves_caller_owned_transaction(tmp_path):
    database = str(tmp_path / "settings-transaction.sqlite")
    writer = sqlite3.connect(database)
    repo = SQLiteProjectScheduleSettingsRepository(writer)
    original = date_settings()

    reader = sqlite3.connect(database)
    reader_repo = SQLiteProjectScheduleSettingsRepository(reader)

    writer.execute("BEGIN")
    repo.save(original, expected_revision=0)
    assert reader_repo.get(scope()) is None

    writer.rollback()
    assert reader_repo.get(scope()) is None
    reader.close()
    writer.close()


def test_sqlite_settings_repository_detects_payload_tampering():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteProjectScheduleSettingsRepository(connection)
    repo.save(date_settings())
    connection.execute(
        "UPDATE project_schedule_settings SET canonical_payload=? WHERE tenant_id=? AND project_id=?",
        ('{"tampered":true}', "T-1", "P-1"),
    )
    connection.commit()

    with pytest.raises(ProjectScheduleSettingsPersistenceError, match="SETTINGS_HASH_MISMATCH"):
        repo.get(scope())


@pytest.fixture(scope="module")
def postgres_dsn():
    import os

    dsn = os.getenv("P6_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    return dsn


def test_postgres_project_schedule_settings_round_trip(postgres_dsn):
    psycopg = pytest.importorskip("psycopg")
    connection = psycopg.connect(postgres_dsn)
    repo = PostgresProjectScheduleSettingsRepository(connection)
    repo.initialize()
    connection.commit()
    try:
        connection.execute("DELETE FROM project_schedule_settings WHERE tenant_id=%s AND project_id=%s", ("T-1", "P-1"))
        connection.execute(
            "DELETE FROM project_schedule_settings_history WHERE tenant_id=%s AND project_id=%s",
            ("T-1", "P-1"),
        )
        connection.commit()
        original = date_settings()
        with connection.transaction():
            stored = repo.save(original, expected_revision=0)
            updated = repo.save(
                replace(original, project_leveling_priority=24),
                expected_revision=stored.record_revision,
            )
        assert stored.record_revision == 1
        assert repo.get(scope()) == updated
        revisions = repo.list_revisions(scope())
        assert [item.record_revision for item in revisions] == [2, 1]
        assert [item.project_leveling_priority for item in revisions] == [24, 23]
    finally:
        connection.execute("DELETE FROM project_schedule_settings WHERE tenant_id=%s AND project_id=%s", ("T-1", "P-1"))
        connection.execute(
            "DELETE FROM project_schedule_settings_history WHERE tenant_id=%s AND project_id=%s",
            ("T-1", "P-1"),
        )
        connection.commit()
        connection.close()
