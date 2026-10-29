from datetime import datetime, timezone
import json

from construction_pm.postgres_project_lifecycle import PostgresProjectRepository, PostgresSessionRepository


class Result:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self):
        self.calls = []
        self.next_rows = []

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        return Result(self.next_rows)


def test_session_repository_maps_persisted_session():
    c = FakeConnection()
    c.next_rows = [
        ("s1", "u1", "t1", json.dumps(["viewer"]), datetime(2030, 1, 1, tzinfo=timezone.utc))
    ]
    s = PostgresSessionRepository(c).get("s1")
    assert s is not None and s.session_id == "s1" and s.roles == frozenset({"viewer"})
    assert c.calls[0][1] == ("s1",)


def test_project_repository_is_membership_scoped():
    c = FakeConnection()
    c.next_rows = [("p1", "t1", "Project 1", 4, "Scope", None, "jalali", "CAL-1")]
    p = PostgresProjectRepository(c).get_for_user("t1", "p1", "u1")
    assert p is not None and p.revision == 4
    assert p.description == "Scope"
    assert p.start_date is None
    assert p.date_system == "jalali"
    assert p.primary_calendar_id == "CAL-1"
    assert c.calls[0][1] == ("t1", "p1", "u1")


def test_project_creation_writes_project_then_membership():
    c = FakeConnection()
    p = PostgresProjectRepository(c).create_for_user("t1", "u1", "p2", "Project 2")
    assert p.revision == 0
    assert len(c.calls) == 2
    assert "INSERT INTO project_lifecycle_projects" in c.calls[0][0]
    assert "INSERT INTO project_lifecycle_memberships" in c.calls[1][0]


def test_project_creation_persists_metadata_columns():
    c = FakeConnection()
    p = PostgresProjectRepository(c).create_for_user(
        "t1", "u1", "p2", "Project 2",
        description="Scope", start_date="2026-11-02",
        date_system="jalali", primary_calendar_id="CAL-1",
    )
    assert p.description == "Scope" and p.start_date == "2026-11-02"
    assert p.date_system == "jalali"
    insert_params = c.calls[0][1]
    assert insert_params == ("t1", "p2", "Project 2", "Scope", "2026-11-02", "jalali", "CAL-1")


def test_project_update_is_guarded_by_expected_revision_and_returns_fresh_row():
    c = FakeConnection()
    c.next_rows = [("p2", "t1", "Renamed", 5, "Updated", "2026-12-01", "gregorian", "CAL-2")]
    p = PostgresProjectRepository(c).update_for_user(
        "t1", "u1", "p2",
        expected_revision=4, name="Renamed", description="Updated",
        start_date="2026-12-01", date_system="gregorian",
        primary_calendar_id="CAL-2",
    )
    assert p is not None and p.revision == 5 and p.name == "Renamed"
    sql, params = c.calls[0]
    assert "revision=revision+1" in sql and "revision=%s" in sql and "RETURNING" in sql
    assert "EXISTS (SELECT 1 FROM project_lifecycle_memberships" in sql
    assert params == (
        "Renamed", "Updated", "2026-12-01", "gregorian", "CAL-2",
        "t1", "p2", 4, "u1",
    )


def test_project_update_returns_none_when_revision_is_stale():
    c = FakeConnection()
    assert PostgresProjectRepository(c).update_for_user(
        "t1", "u1", "p2", expected_revision=1, name="Stale"
    ) is None
