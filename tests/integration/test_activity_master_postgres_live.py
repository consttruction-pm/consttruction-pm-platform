import os
from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from construction_pm.activity_master_repository import (
    ActivityMaster,
    PostgresActivityMasterRepository,
)
from construction_pm.wbs_master_repository import (
    PostgresWBSMasterRepository,
    WBSMaster,
    WBSParentKind,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.scheduling.activity import (
    ActivityLevelingPriority,
    ActivityStatus,
    ActivityStatusCode,
    ActivityType,
    PercentCompleteType,
)
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
        planned_finish=date(2026, 9, 28),
        leveling_priority=ActivityLevelingPriority.TOP,
        original_duration=14,
        name="Concrete Pour",
        activity_type=ActivityType.RESOURCE_DEPENDENT,
        status=ActivityStatus.IN_PROGRESS,
        status_code=ActivityStatusCode.ACTIVE,
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
        assert restored.planned_finish == date(2026, 9, 28)
        assert restored.leveling_priority is ActivityLevelingPriority.TOP
        assert restored.original_duration == 14
        assert restored.name == "Concrete Pour"
        assert restored.activity_type is ActivityType.RESOURCE_DEPENDENT
        assert restored.status is ActivityStatus.IN_PROGRESS
        assert restored.status_code is ActivityStatusCode.ACTIVE

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
            planned_finish=date(2026, 10, 4),
            leveling_priority=ActivityLevelingPriority.LOWEST,
            original_duration=18,
            name="Concrete Pour Complete",
            activity_type=ActivityType.TASK_DEPENDENT,
            status=ActivityStatus.COMPLETED,
            status_code=ActivityStatusCode.INACTIVE,
        )
        saved = repo.save(updated, expected_revision=1)
        connection.commit()

        assert saved.record_revision == 2
        assert saved.original_duration == 18
        assert repo.get(scope, "A-PROGRESS") == saved
        assert saved.planned_finish == date(2026, 10, 4)
        assert saved.leveling_priority is ActivityLevelingPriority.LOWEST
        assert saved.name == "Concrete Pour Complete"
        assert saved.activity_type is ActivityType.TASK_DEPENDENT
        assert saved.status is ActivityStatus.COMPLETED
        assert saved.status_code is ActivityStatusCode.INACTIVE

        connection.execute(
            "DELETE FROM activity_master WHERE tenant_id=%s AND project_id=%s",
            (scope.tenant_id, scope.project_id),
        )
        connection.commit()



def test_postgres_activity_master_persists_canonical_wbs_assignment():
    suffix = uuid4().hex
    scope = BackendScope(f"tenant-activity-wbs-{suffix}", f"project-activity-wbs-{suffix}", 7)

    with connect() as connection:
        wbs_repo = PostgresWBSMasterRepository(connection)
        wbs_repo.initialize()
        activity_repo = PostgresActivityMasterRepository(connection)
        activity_repo.initialize()
        try:
            root = wbs_repo.save(
                WBSMaster(scope, "W-ROOT", WBSParentKind.PROJECT, None, "1", "Project Root", 0)
            )
            connection.commit()
            child = wbs_repo.save(
                WBSMaster(scope, "W-CHILD", WBSParentKind.WBS, "W-ROOT", "2", "Package", 1)
            )
            connection.commit()

            stored = activity_repo.save(replace(_source_activity(scope), wbs_id=root.wbs_id))
            connection.commit()
            assert stored.wbs_id == "W-ROOT"
            assert activity_repo.get(scope, stored.activity_id) == stored
            assert activity_repo.list(scope) == (stored,)

            updated = activity_repo.save(
                replace(stored, wbs_id=child.wbs_id, name="Concrete Pour Updated"),
                expected_revision=1,
            )
            connection.commit()
            assert updated.record_revision == 2
            assert updated.wbs_id == "W-CHILD"
            assert activity_repo.get(scope, stored.activity_id) == updated

            with pytest.raises(ValueError, match="WBS_NOT_FOUND_OR_SCOPE_MISMATCH"):
                activity_repo.save(
                    replace(updated, wbs_id="W-MISSING"),
                    expected_revision=2,
                )
            connection.rollback()
            assert activity_repo.get(scope, stored.activity_id) == updated
        finally:
            connection.execute(
                "DELETE FROM activity_master WHERE tenant_id=%s AND project_id=%s",
                (scope.tenant_id, scope.project_id),
            )
            connection.execute(
                "DELETE FROM wbs_master WHERE tenant_id=%s AND project_id=%s AND parent_kind='wbs'",
                (scope.tenant_id, scope.project_id),
            )
            connection.execute(
                "DELETE FROM wbs_master WHERE tenant_id=%s AND project_id=%s",
                (scope.tenant_id, scope.project_id),
            )
            connection.commit()
