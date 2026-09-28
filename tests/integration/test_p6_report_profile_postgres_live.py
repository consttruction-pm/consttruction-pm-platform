import os

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_report_profile_repository import (
    P6ReportProfileFieldMapping,
    P6ReportProfilePersistenceError,
    PostgresP6ReportProfileRepository,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)


def connect():
    import psycopg

    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def item(scope, field_id="activity_id"):
    return P6ReportProfileFieldMapping(
        scope,
        "profile-pg",
        "Activity Report",
        "ACTIVITY",
        field_id,
        0,
        metadata={"provider": "P6"},
    )


def test_postgres_round_trip_isolation_and_revision():
    with connect() as conn:
        repo = PostgresP6ReportProfileRepository(conn)
        repo.initialize()
        scope = BackendScope("tenant-report-pg", "project-report-pg", 1)
        value = item(scope)
        assert repo.upsert(value) == value
        assert repo.get(scope, "profile-pg", "activity_id") == value
        assert repo.get(
            BackendScope("other", "project-report-pg", 1), "profile-pg", "activity_id"
        ) is None
        with pytest.raises(P6ReportProfilePersistenceError, match="REVISION_CONFLICT"):
            repo.get(
                BackendScope("tenant-report-pg", "project-report-pg", 2),
                "profile-pg",
                "activity_id",
            )


def test_postgres_rollback():
    with connect() as conn:
        repo = PostgresP6ReportProfileRepository(conn)
        repo.initialize()
        scope = BackendScope("tenant-report-rb", "project-report-rb", 1)
        try:
            repo.upsert(item(scope))
            raise RuntimeError("force rollback")
        except RuntimeError:
            conn.rollback()
        assert repo.get(scope, "profile-pg", "activity_id") is None
