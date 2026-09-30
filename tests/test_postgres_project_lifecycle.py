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
    c.next_rows = [("p1", "t1", "Project 1", 4)]
    p = PostgresProjectRepository(c).get_for_user("t1", "p1", "u1")
    assert p is not None and p.revision == 4
    assert c.calls[0][1] == ("t1", "p1", "u1")


def test_project_creation_writes_project_then_membership():
    c = FakeConnection()
    p = PostgresProjectRepository(c).create_for_user("t1", "u1", "p2", "Project 2")
    assert p.revision == 0
    assert len(c.calls) == 2
    assert "INSERT INTO project_lifecycle_projects" in c.calls[0][0]
    assert "INSERT INTO project_lifecycle_memberships" in c.calls[1][0]
