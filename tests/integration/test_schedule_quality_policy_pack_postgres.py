from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.backend_p0.models import BackendScope
from construction_pm.control_intelligence.quality_policy_pack import (
    SCORING_METHOD,
    PostgresScheduleQualityPolicyRepository,
    ScheduleQualityPolicyError,
    ScheduleQualityPolicyPack,
)


@pytest.fixture()
def postgres_connection():
    dsn = os.getenv("P6_TEST_POSTGRES_DSN") or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
    if not dsn:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    connection = psycopg.connect(dsn)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def test_postgres_quality_policy_is_versioned_approved_scoped_and_append_only(postgres_connection):
    suffix = uuid4().hex
    scope = BackendScope(f"tenant-{suffix}", f"project-{suffix}", 14)
    policy_id = f"schedule-quality-{suffix}"
    pack = ScheduleQualityPolicyPack(
        scope=scope,
        policy_id=policy_id,
        version="1.0.0",
        name="Project schedule policy",
        scoring_method=SCORING_METHOD,
        thresholds={
            "positive_lag": {
                "date_based_max_working_days": 5,
                "time_aware_max": {"working-day": "5", "working-hour": "40"},
                "severity": "warning",
            },
            "activity_duration": {
                "date_based_max_working_days": "60",
                "time_aware_max": {"working-day": "60", "working-hour": "480"},
                "severity": "critical",
            },
            "constraints_per_activity": {"maximum": 2, "severity": "warning"},
        },
        weights={
            "positive_lag": "0.50",
            "activity_duration": "0.30",
            "constraints_per_activity": "0.20",
        },
        created_by="admin-1",
        created_at=datetime(2026, 11, 4, 17, 0, tzinfo=timezone.utc),
    )

    with postgres_connection.transaction():
        repository = PostgresScheduleQualityPolicyRepository(postgres_connection)
        draft = repository.create(pack)
        assert draft.approved_by is None
        assert repository.latest_approved(scope) is None

        approved = repository.approve(
            scope,
            policy_id,
            "1.0.0",
            approved_by="admin-2",
            approved_at=datetime(2026, 11, 4, 18, 0, tzinfo=timezone.utc),
        )
        assert approved.approved_by == "admin-2"
        assert approved.approved_at is not None
        assert repository.latest_approved(scope) == approved
        assert repository.get(
            BackendScope(f"other-{suffix}", scope.project_id, 14), policy_id, "1.0.0"
        ) is None
        assert repository.get(
            BackendScope(scope.tenant_id, f"other-{suffix}", 14), policy_id, "1.0.0"
        ) is None
        assert len(repository.list(scope)) == 1

        changed = ScheduleQualityPolicyPack(
            scope=scope,
            policy_id=policy_id,
            version="1.0.0",
            name="Changed",
            scoring_method=SCORING_METHOD,
            thresholds=pack.thresholds,
            weights=pack.weights,
            created_by="admin-1",
            created_at=pack.created_at,
        )
        with pytest.raises(ScheduleQualityPolicyError, match="VERSION_REUSED"):
            repository.create(changed)

        with pytest.raises(
            psycopg.errors.RaiseException,
            match="SCHEDULE_QUALITY_POLICY_IMMUTABLE",
        ):
            with postgres_connection.transaction():
                postgres_connection.execute(
                    "UPDATE schedule_quality_policy_pack SET name=%s "
                    "WHERE tenant_id=%s AND project_id=%s AND policy_id=%s AND version=%s",
                    ("tampered", scope.tenant_id, scope.project_id, policy_id, "1.0.0"),
                )
        with pytest.raises(
            psycopg.errors.RaiseException,
            match="SCHEDULE_QUALITY_POLICY_IMMUTABLE",
        ):
            with postgres_connection.transaction():
                postgres_connection.execute(
                    "DELETE FROM schedule_quality_policy_approval "
                    "WHERE tenant_id=%s AND project_id=%s AND policy_id=%s AND version=%s",
                    (scope.tenant_id, scope.project_id, policy_id, "1.0.0"),
                )
