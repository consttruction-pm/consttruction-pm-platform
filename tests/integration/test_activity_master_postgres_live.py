import os
from datetime import date
from decimal import Decimal

import pytest

from construction_pm.activity_master_repository import (
    ActivityMaster,
    PostgresActivityMasterRepository,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.scheduling.activity import PercentCompleteType
from construction_pm.scheduling.time_duration import DurationUnit


pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)


def connect():
    import psycopg

    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def _source_activity(scope: BackendScope) -> ActivityMaster:
    return ActivityMaster(
        scope,
        "A-PROGRESS",
        Decimal("4"),
        DurationUnit.WORKING_DAY,
        date(2026, 9, 21),
        0,
        date(2026, 9, 30),
        date(2026, 9, 24),
        2,
        date(2026, 9, 25),
        37.5,
        PercentCompleteType.PHYSICAL,
    )


def test_postgres_activity_master_preserves_all_progress_state():
    scope = BackendScope("tenant-activity-progress", "project-master", 7)

    with connect() as connection:
        repo = PostgresActivityMasterRepository(connection)
        repo.initialize()
        connection.execute(
            "DELETE FROM activity_master WHERE tenant_id=%s AND project_id=%s",
            (scope.tenant_id, scope.project_id),
        )
        connection.commit()

        stored = repo.save(_source_activity(scope))
        connection.commit()
        restored = repo.get(scope, "A-PROGRESS")

        assert stored.record_revision == 1
        assert restored == stored
        assert restored.actual_start == date(2026, 9, 21)
        assert restored.actual_finish == date(2026, 9, 24)
        assert restored.remaining_duration == 2
        assert restored.remaining_start == date(2026, 9, 25)
        assert restored.percent_complete == 37.5
        assert restored.percent_complete_type is PercentCompleteType.PHYSICAL

        connection.execute(
            "DELETE FROM activity_master WHERE tenant_id=%s AND project_id=%s",
            (scope.tenant_id, scope.project_id),
        )
        connection.commit()


def test_postgres_activity_master_updates_all_progress_state():
    scope = BackendScope("tenant-activity-progress-update", "project-master", 7)

    with connect() as connection:
        repo = PostgresActivityMasterRepository(connection)
        repo.initialize()
        connection.execute(
            "DELETE FROM activity_master WHERE tenant_id=%s AND project_id=%s",
            (scope.tenant_id, scope.project_id),
        )
        connection.commit()

        repo.save(_source_activity(scope))
        connection.commit()

        updated = ActivityMaster(
            scope,
            "A-PROGRESS",
            Decimal("5"),
            DurationUnit.WORKING_DAY,
            date(2026, 9, 21),
            0,
            date(2026, 10, 2),
            date(2026, 9, 26),
            3,
            date(2026, 9, 27),
            62.5,
            PercentCompleteType.UNITS,
        )
        saved = repo.save(updated, expected_revision=1)
        connection.commit()

        assert saved.record_revision == 2
        assert repo.get(scope, "A-PROGRESS") == saved

        connection.execute(
            "DELETE FROM activity_master WHERE tenant_id=%s AND project_id=%s",
            (scope.tenant_id, scope.project_id),
        )
        connection.commit()
