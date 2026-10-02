import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_master_repository import (
    ActivityCalendarAssignmentMaster,
    CalendarMaster,
    CalendarPersistenceError,
    PostgresCalendarAssignmentRepository,
    PostgresCalendarMasterRepository,
    RelationshipLagCalendarAssignmentMaster,
)
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.scheduling.calendar_context import RelationshipLagCalendar


def scope(revision: int = 7) -> BackendScope:
    suffix = uuid.uuid4().hex
    return BackendScope(f"cal-{suffix}", f"project-{suffix}", revision)


def calendar(s: BackendScope, version: str = "1") -> CalendarMaster:
    return CalendarMaster(s, "CAL-1", version, "working-day", "Project Calendar")


def test_postgres_calendar_round_trip_scope_revision_and_rollback():
    s = scope()
    with psycopg.connect(DSN) as connection:
        masters = PostgresCalendarMasterRepository(connection)
        assignments = PostgresCalendarAssignmentRepository(connection)
        masters.initialize()
        connection.commit()

        with PostgresTransactionManager(connection).transaction():
            stored = masters.save(calendar(s))
            assignments.save_activity(
                ActivityCalendarAssignmentMaster(s, "A-1", "CAL-1", "1")
            )
            assignments.save_relationship_lag(
                RelationshipLagCalendarAssignmentMaster(
                    s, "R-1", RelationshipLagCalendar.SUCCESSOR, "CAL-1", "1"
                )
            )

        assert stored.record_revision == 1
        assert masters.get(s, "CAL-1", "1") == stored
        assert assignments.get_activity(s, "A-1").calendar_version == "1"
        assert assignments.get_relationship_lag(s, "R-1").option is RelationshipLagCalendar.SUCCESSOR

        other_scope = BackendScope(s.tenant_id + "-other", s.project_id, s.project_revision)
        assert masters.get(other_scope, "CAL-1", "1") is None
        with pytest.raises(CalendarPersistenceError, match="REVISION_CONFLICT"):
            masters.get(BackendScope(s.tenant_id, s.project_id, 8), "CAL-1", "1")

        with pytest.raises(RuntimeError, match="FORCED_ROLLBACK"):
            with PostgresTransactionManager(connection).transaction():
                masters.save(calendar(s, "2"))
                assignments.save_activity(
                    ActivityCalendarAssignmentMaster(s, "A-2", "CAL-1", "2")
                )
                raise RuntimeError("FORCED_ROLLBACK")

        assert masters.get(s, "CAL-1", "2") is None
        assert assignments.get_activity(s, "A-2") is None


def test_postgres_calendar_versions_and_optimistic_revision():
    s = scope()
    with psycopg.connect(DSN) as connection:
        repo = PostgresCalendarMasterRepository(connection)
        repo.initialize()
        connection.commit()

        with PostgresTransactionManager(connection).transaction():
            first = repo.save(calendar(s, "1"))
            second = repo.save(calendar(s, "2"))

        assert tuple(item.calendar_version for item in repo.list(s)) == ("1", "2")
        assert first.record_revision == second.record_revision == 1

        with pytest.raises(CalendarPersistenceError, match="REVISION_CONFLICT"):
            with PostgresTransactionManager(connection).transaction():
                repo.save(
                    CalendarMaster(s, "CAL-1", "1", name="Changed"),
                    expected_revision=0,
                )
