from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.control_intelligence.quality_policy_pack import (
    SCORING_METHOD,
    ScheduleQualityPolicyError,
    ScheduleQualityPolicyPack,
    SQLiteScheduleQualityPolicyRepository,
)
from construction_pm.control_intelligence.quality_policy_pack_api import ScheduleQualityPolicyAPI


NOW = datetime(2026, 11, 4, 15, 0, tzinfo=timezone.utc)
SCOPE = BackendScope("tenant-1", "project-1", 7)


def policy_pack(*, scope: BackendScope = SCOPE, weights=None) -> ScheduleQualityPolicyPack:
    return ScheduleQualityPolicyPack(
        scope=scope,
        policy_id="schedule-quality",
        version="1.0.0",
        name="Approved project schedule policy",
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
        weights=weights or {
            "positive_lag": "0.50",
            "activity_duration": "0.30",
            "constraints_per_activity": "0.20",
        },
        created_by="admin-1",
        created_at=NOW,
    )


def test_policy_versions_are_immutable_and_only_approval_events_activate_them() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        repository = SQLiteScheduleQualityPolicyRepository(connection)
        draft = repository.create(policy_pack())
        assert draft.approved_at is None
        assert repository.latest_approved(SCOPE) is None

        approved = repository.approve(
            SCOPE, "schedule-quality", "1.0.0",
            approved_by="admin-2", approved_at=NOW,
        )
        assert approved.approved_by == "admin-2"
        assert approved.approved_at == NOW
        assert repository.latest_approved(SCOPE) == approved
        assert repository.get(BackendScope("tenant-2", "project-1", 7), "schedule-quality", "1.0.0") is None
        assert repository.get(BackendScope("tenant-1", "project-2", 7), "schedule-quality", "1.0.0") is None
        assert repository.list(SCOPE) == (approved,)

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE schedule_quality_policy_pack SET name='changed' "
                "WHERE tenant_id=? AND project_id=? AND policy_id=? AND version=?",
                ("tenant-1", "project-1", "schedule-quality", "1.0.0"),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "DELETE FROM schedule_quality_policy_approval "
                "WHERE tenant_id=? AND project_id=? AND policy_id=? AND version=?",
                ("tenant-1", "project-1", "schedule-quality", "1.0.0"),
            )
    finally:
        connection.close()


def test_policy_rejects_unapproved_thresholds_weights_and_reused_versions() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        repository = SQLiteScheduleQualityPolicyRepository(connection)
        with pytest.raises(ScheduleQualityPolicyError, match="WEIGHTS_MUST_SUM_TO_ONE"):
            repository.create(policy_pack(weights={
                "positive_lag": "0.5",
                "activity_duration": "0.3",
                "constraints_per_activity": "0.3",
            }))
        with pytest.raises(ScheduleQualityPolicyError, match="CONSTRAINT_LIMIT_INVALID"):
            bad = policy_pack()
            thresholds = dict(bad.thresholds)
            thresholds["constraints_per_activity"] = {"maximum": -1, "severity": "warning"}
            repository.create(ScheduleQualityPolicyPack(
                scope=bad.scope, policy_id=bad.policy_id, version="1.0.1",
                name=bad.name, scoring_method=bad.scoring_method, thresholds=thresholds,
                weights=bad.weights, created_by=bad.created_by, created_at=NOW,
            ))
        first = repository.create(policy_pack())
        changed = ScheduleQualityPolicyPack(
            scope=first.scope, policy_id=first.policy_id, version=first.version,
            name="Different policy with same version", scoring_method=first.scoring_method,
            thresholds=first.thresholds, weights=first.weights, created_by=first.created_by,
            created_at=first.created_at,
        )
        with pytest.raises(ScheduleQualityPolicyError, match="VERSION_REUSED"):
            repository.create(changed)
    finally:
        connection.close()


def test_policy_api_requires_project_admin_and_binds_authenticated_author_and_approver() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        repository = SQLiteScheduleQualityPolicyRepository(connection)
        api = ScheduleQualityPolicyAPI(
            repository, default_project_policy(), SQLiteTransactionManager(connection)
        )
        admin = AuthorizationContext("tenant-1", "project-1", "admin-1", frozenset({"project_admin"}))
        viewer = AuthorizationContext("tenant-1", "project-1", "viewer-1", frozenset({"viewer"}))
        pack = policy_pack()

        created = api.create(pack, auth_context=admin)
        assert created["policy_pack"]["status"] == "draft"
        with pytest.raises(AuthorizationError, match="authorization denied"):
            api.approve(SCOPE, "schedule-quality", "1.0.0", auth_context=viewer)
        with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
            api.list(SCOPE, auth_context=AuthorizationContext(
                "tenant-other", "project-1", "viewer-2", frozenset({"viewer"})
            ))
        approved = api.approve(SCOPE, "schedule-quality", "1.0.0", auth_context=admin)
        assert approved["policy_pack"]["status"] == "approved"
        assert approved["policy_pack"]["approved_by"] == "admin-1"
        latest = api.latest_approved(SCOPE, auth_context=viewer)
        assert latest is not None
        assert latest["policy_pack"]["policy_id"] == "schedule-quality"
    finally:
        connection.close()


def test_policy_repository_rejects_preapproved_creation_and_naive_timestamps() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        repository = SQLiteScheduleQualityPolicyRepository(connection)
        draft = policy_pack()
        preapproved = ScheduleQualityPolicyPack(
            scope=draft.scope, policy_id=draft.policy_id, version="1.0.2",
            name=draft.name, scoring_method=draft.scoring_method,
            thresholds=draft.thresholds, weights=draft.weights,
            created_by=draft.created_by, created_at=NOW,
            approved_by="admin-1", approved_at=NOW,
        )
        with pytest.raises(ScheduleQualityPolicyError, match="CANNOT_CREATE_PREAPPROVED_PACK"):
            repository.create(preapproved)
        naive = ScheduleQualityPolicyPack(
            scope=draft.scope, policy_id=draft.policy_id, version="1.0.3",
            name=draft.name, scoring_method=draft.scoring_method,
            thresholds=draft.thresholds, weights=draft.weights,
            created_by=draft.created_by, created_at=datetime(2026, 11, 4, 15, 0),
        )
        with pytest.raises(ScheduleQualityPolicyError, match="TIMESTAMP_INVALID"):
            repository.create(naive)
    finally:
        connection.close()
