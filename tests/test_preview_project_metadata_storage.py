import sqlite3
from datetime import datetime, timezone

from construction_pm.preview.storage import PreviewStore


def _legacy_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE preview_project (
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            project_revision INTEGER NOT NULL,
            wbs_json TEXT NOT NULL,
            demo INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            PRIMARY KEY (tenant_id, project_id)
        );
        CREATE TABLE preview_project_member (
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            PRIMARY KEY (tenant_id, project_id, user_id)
        );
        """
    )
    connection.execute(
        "INSERT INTO preview_project VALUES ('t1','p1','Legacy',3,'{}',0,'2026-01-01T00:00:00+00:00')"
    )
    connection.execute("INSERT INTO preview_project_member VALUES ('t1','p1','u1')")
    connection.commit()
    return connection


def test_preview_store_migrates_legacy_project_table_without_data_loss():
    connection = _legacy_connection()
    try:
        store = PreviewStore(connection)
        project = store.get_for_user("t1", "p1", "u1")
        assert project is not None
        assert project.name == "Legacy"
        assert project.revision == 3
        assert project.description == ""
        assert project.start_date is None
        assert project.date_system == "gregorian"
        assert project.primary_calendar_id is None

        assert store.update_project(
            "t1",
            "p1",
            "u1",
            expected_revision=3,
            name="Legacy renamed",
            description="Migrated",
            start_date="2026-11-02",
            date_system="jalali",
            primary_calendar_id="CAL-1",
        )
        migrated = store.get_for_user("t1", "p1", "u1")
        assert migrated.revision == 4
        assert migrated.description == "Migrated"
        assert migrated.date_system == "jalali"
    finally:
        connection.close()


def test_preview_store_update_is_scoped_to_revision_membership_and_tenant():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        store = PreviewStore(connection)
        store.insert_project(
            tenant_id="t1",
            project_id="p1",
            name="Project",
            revision=2,
            wbs_by_activity={},
            demo=False,
            created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
        store.add_members("t1", "p1", ("u1",))

        assert not store.update_project(
            "t1", "p1", "u1", expected_revision=1,
            name="Stale", description="", start_date=None,
            date_system="gregorian", primary_calendar_id=None,
        )
        assert not store.update_project(
            "t1", "p1", "u2", expected_revision=2,
            name="Outsider", description="", start_date=None,
            date_system="gregorian", primary_calendar_id=None,
        )
        assert not store.update_project(
            "t2", "p1", "u1", expected_revision=2,
            name="Cross tenant", description="", start_date=None,
            date_system="gregorian", primary_calendar_id=None,
        )
        unchanged = store.get_for_user("t1", "p1", "u1")
        assert unchanged.revision == 2 and unchanged.name == "Project"

        assert store.update_project(
            "t1", "p1", "u1", expected_revision=2,
            name="Project renamed", description="Scope",
            start_date="2026-12-01", date_system="jalali",
            primary_calendar_id="CAL-9",
        )
        updated = store.get_for_user("t1", "p1", "u1")
        assert updated.revision == 3
        assert updated.name == "Project renamed"
        assert updated.start_date == "2026-12-01"
        assert updated.primary_calendar_id == "CAL-9"
    finally:
        connection.close()
