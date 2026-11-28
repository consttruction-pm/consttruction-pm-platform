"""Live PostgreSQL acceptance for Activity Cut/Copy/Paste/Delete.

Runs the production migration registry (including step 23) into a throw-away
schema, then drives the same service and repositories the production runtime
composes. Proves: real committed copies, internal relationship copying,
idempotent replay, permission enforcement, cascade delete with audit, and the
Revoke + restrictive-RLS hardening on the two new tables.

Run with::

    CONSTRUCTION_PM_POSTGRES_DSN=postgresql://... \
        PYTHONPATH=src python -m pytest -q \
        tests/integration/test_p6_activity_operations_postgres_live.py
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
import json
import os
import uuid

import pytest

if not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN") and os.getenv("P6_TEST_POSTGRES_DSN"):
    os.environ["CONSTRUCTION_PM_POSTGRES_DSN"] = os.environ["P6_TEST_POSTGRES_DSN"]

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)

from construction_pm.activity_master_repository import (  # noqa: E402
    ActivityMaster,
    PostgresActivityMasterRepository,
)
from construction_pm.application.authorization import (  # noqa: E402
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope  # noqa: E402
from construction_pm.calendar_master_repository import (  # noqa: E402
    PostgresCalendarAssignmentRepository,
    PostgresCalendarMasterRepository,
    RelationshipLagCalendarAssignmentMaster,
)
from construction_pm.constraint_master_repository import (  # noqa: E402
    PostgresConstraintMasterRepository,
)
from construction_pm.deployment.migrations import apply_migrations  # noqa: E402
from construction_pm.p6_activity_operations import (  # noqa: E402
    ActivityOperationError,
    ActivityOperationStore,
    P6ActivityOperationAPI,
)
from construction_pm.p6_activity_step_repository import (  # noqa: E402
    PostgresP6ActivityStepRepository,
)
from construction_pm.p6_resource_assignment_repository import (  # noqa: E402
    P6ResourceAssignment,
    P6ResourceAssignmentPeriodValue,
    PostgresP6ResourceAssignmentPeriodRepository,
    PostgresP6ResourceAssignmentRepository,
)
from construction_pm.relationship_master_repository import (  # noqa: E402
    PostgresRelationshipMasterRepository,
    RelationshipMaster,
)
from construction_pm.scheduling.activity import (  # noqa: E402
    ActivityStatus,
    ActivityStatusCode,
    ActivityType,
)
from construction_pm.scheduling.calendar_context import RelationshipLagCalendar  # noqa: E402
from construction_pm.scheduling.relationships import RelationshipType  # noqa: E402
from construction_pm.scheduling.time_duration import DurationUnit  # noqa: E402
from construction_pm.wbs_master_repository import (  # noqa: E402
    PostgresWBSMasterRepository,
    WBSParentKind,
    WBSMaster,
)

SCOPE = BackendScope("tenant-live", "project-live", 1)


class _Tx:
    """Commit-per-service manager bound to the test connection."""

    def __init__(self, connection) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self):
        try:
            yield
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise


def _connect():
    import psycopg

    schema = f"cubi_ops_{uuid.uuid4().hex[:12]}"
    connection = psycopg.connect(
        os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        autocommit=True,
        options=f"-c search_path={schema}",
    )
    connection.execute(f'CREATE SCHEMA "{schema}"')
    report = apply_migrations(connection)
    connection.autocommit = False
    return connection, report, schema


@pytest.fixture()
def live():
    connection, report, schema = _connect()
    try:
        yield connection, report
    finally:
        connection.rollback()
        connection.autocommit = True
        connection.execute("SET search_path TO public")
        connection.execute(f'DROP SCHEMA "{schema}" CASCADE')
        connection.close()


def _seed(connection):
    activities = PostgresActivityMasterRepository(connection)
    wbs = PostgresWBSMasterRepository(connection)
    relationships = PostgresRelationshipMasterRepository(connection)
    assignments = PostgresP6ResourceAssignmentRepository(connection)
    wbs.save(
        WBSMaster(
            scope=SCOPE,
            wbs_id="W-ROOT",
            parent_kind=WBSParentKind.PROJECT,
            parent_wbs_id=None,
            code="1",
            name="Root",
            sequence_number=0,
        )
    )
    for activity_id in ("A-1", "A-2"):
        activities.save(
            ActivityMaster(
                scope=SCOPE,
                activity_id=activity_id,
                duration_value=Decimal("4"),
                duration_unit=DurationUnit.WORKING_DAY,
                name=activity_id,
                wbs_id="W-ROOT",
                status=ActivityStatus.IN_PROGRESS,
                status_code=ActivityStatusCode.ACTIVE,
                percent_complete=25.0,
                actual_start=date(2026, 1, 2),
            )
        )
    relationships.save(
        RelationshipMaster(
            scope=SCOPE,
            relationship_id="R-1",
            predecessor_id="A-1",
            successor_id="A-2",
            relationship_type=RelationshipType.FS,
            lag_value=Decimal("1"),
            lag_unit=DurationUnit.WORKING_DAY,
        )
    )
    assignments.upsert(
        P6ResourceAssignment(
            scope=SCOPE,
            assignment_id="AS-1",
            activity_id="A-1",
            resource_id="RES-1",
            units=Decimal("16"),
            actual_units=Decimal("4"),
            remaining_units=Decimal("12"),
        )
    )
    # Repositories write inside the caller's transaction, so commit the fixture
    # before the service starts its own atomic operation.
    connection.commit()
    store = ActivityOperationStore(connection, placeholder="%s")
    api = P6ActivityOperationAPI(
        activity_repository=activities,
        wbs_repository=wbs,
        store=store,
        authorization_policy=default_project_policy(),
        transaction_manager=_Tx(connection),
    )
    return api, activities, relationships


def _context(*roles: str) -> AuthorizationContext:
    return AuthorizationContext(
        tenant_id=SCOPE.tenant_id,
        project_id=SCOPE.project_id,
        user_id="user-live",
        roles=frozenset(roles or ("planner",)),
    )


def test_migration_step_23_creates_and_hardens_the_journal(live):
    connection, report = live
    assert report.ledger_version == 23
    rows = connection.execute(
        "SELECT c.relname, c.relrowsecurity FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = current_schema() "
        "AND c.relname IN ('p6_activity_operation', 'p6_activity_operation_audit') "
        "ORDER BY c.relname"
    ).fetchall()
    assert [row[0] for row in rows] == [
        "p6_activity_operation",
        "p6_activity_operation_audit",
    ]
    assert all(row[1] is True for row in rows)


def test_copy_commits_relationships_and_assignments(live):
    connection, _ = live
    api, activities, relationships = _seed(connection)

    result = api.execute(
        SCOPE,
        "copy",
        ["A-1", "A-2"],
        auth_context=_context("planner"),
        idempotency_key="live-copy-1",
        now=datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc),
    )
    assert [item["activity_id"] for item in result["created"]] == [
        "A-1-COPY",
        "A-2-COPY",
    ]
    assert result["relationships_created"] == ["R-1-COPY"]
    assert result["assignments_created"] == 1

    # A fresh repository instance reads the committed rows, not a cache.
    reader = PostgresActivityMasterRepository(connection)
    copied = reader.get(SCOPE, "A-1-COPY")
    assert copied is not None
    assert copied.percent_complete == 0.0
    assert copied.actual_start is None
    copied_link = relationships.get(SCOPE, "R-1-COPY")
    assert copied_link is not None
    assert (copied_link.predecessor_id, copied_link.successor_id) == (
        "A-1-COPY",
        "A-2-COPY",
    )
    assignment_reader = PostgresP6ResourceAssignmentRepository(connection)
    copied_assignment = assignment_reader.get(SCOPE, "AS-1-COPY")
    assert copied_assignment is not None
    assert copied_assignment.actual_units is None

    # Idempotent replay must not create a second copy.
    replay = api.execute(
        SCOPE,
        "copy",
        ["A-1", "A-2"],
        auth_context=_context("planner"),
        idempotency_key="live-copy-1",
        now=datetime(2026, 11, 26, 12, 30, tzinfo=timezone.utc),
    )
    assert replay["replayed"] is True
    assert reader.get(SCOPE, "A-1-COPY2") is None

    audit = connection.execute(
        "SELECT operation, actor_id FROM p6_activity_operation_audit"
    ).fetchall()
    assert audit == [("copy", "user-live")]


def test_viewer_is_denied_without_writing(live):
    connection, _ = live
    api, activities, _ = _seed(connection)

    with pytest.raises(AuthorizationError):
        api.execute(
            SCOPE,
            "copy",
            ["A-1"],
            auth_context=_context("viewer"),
            idempotency_key="live-viewer",
        )
    assert activities.get(SCOPE, "A-1-COPY") is None


def test_delete_requires_confirmation_and_cascades_with_audit(live):
    connection, _ = live
    api, activities, relationships = _seed(connection)

    with pytest.raises(ActivityOperationError) as unconfirmed:
        api.execute(
            SCOPE,
            "delete",
            ["A-1"],
            auth_context=_context("planner"),
            idempotency_key="live-del-0",
        )
    assert str(unconfirmed.value).startswith(
        "P6_ACTIVITY_DELETE_CONFIRMATION_REQUIRED:"
    )

    result = api.execute(
        SCOPE,
        "delete",
        ["A-1"],
        auth_context=_context("planner"),
        idempotency_key="live-del-1",
        confirm_dependencies=True,
        now=datetime(2026, 11, 26, 13, 0, tzinfo=timezone.utc),
    )
    assert result["deleted_count"] == 1
    assert activities.get(SCOPE, "A-1") is None
    assert relationships.get(SCOPE, "R-1") is None
    assignment_reader = PostgresP6ResourceAssignmentRepository(connection)
    assert assignment_reader.get(SCOPE, "AS-1") is None
    # A-2 survives; only the selected activity was removed.
    assert activities.get(SCOPE, "A-2") is not None


def test_delete_both_relationship_endpoints_counts_the_row_once(live):
    connection, _ = live
    api, activities, relationships = _seed(connection)

    with pytest.raises(ActivityOperationError) as unconfirmed:
        api.execute(
            SCOPE,
            "delete",
            ["A-1", "A-2"],
            auth_context=_context("planner"),
            idempotency_key="live-del-both-0",
        )
    code, _, detail = str(unconfirmed.value).partition(":")
    assert code == "P6_ACTIVITY_DELETE_CONFIRMATION_REQUIRED"
    # R-1 connects the two selected activities, so it matches both endpoint
    # tests but is still one row to cascade.
    assert json.loads(detail)["relationships"] == 1

    result = api.execute(
        SCOPE,
        "delete",
        ["A-1", "A-2"],
        auth_context=_context("planner"),
        idempotency_key="live-del-both-1",
        confirm_dependencies=True,
        now=datetime(2026, 11, 26, 14, 0, tzinfo=timezone.utc),
    )
    assert result["deleted"] == ["A-1", "A-2"]
    assert result["removed_rows"]["relationship_master"] == 1
    assert relationships.get(SCOPE, "R-1") is None
    audit = api.audit_trail(SCOPE)
    assert audit[0]["detail"]["removed_rows"]["relationship_master"] == 1


def test_progressed_resource_dependent_copy_is_refused_without_writing(live):
    connection, _ = live
    api, activities, _ = _seed(connection)
    # A progressed Resource Dependent activity whose time-phased demand only
    # describes the remaining contract. Copying it resets progress but the
    # demand rows cannot be re-spread from a calendar, so the operation must
    # fail closed instead of writing a copy the composer would reject.
    activities.save(
        ActivityMaster(
            scope=SCOPE,
            activity_id="A-RD",
            duration_value=Decimal("5"),
            duration_unit=DurationUnit.WORKING_DAY,
            name="A-RD",
            wbs_id="W-ROOT",
            activity_type=ActivityType.RESOURCE_DEPENDENT,
            status=ActivityStatus.IN_PROGRESS,
            status_code=ActivityStatusCode.ACTIVE,
            percent_complete=40.0,
            actual_start=date(2026, 1, 2),
        )
    )
    assignments = PostgresP6ResourceAssignmentRepository(connection)
    assignments.upsert(
        P6ResourceAssignment(
            scope=SCOPE,
            assignment_id="AS-RD",
            activity_id="A-RD",
            resource_id="RES-RD",
            units=Decimal("20"),
            actual_units=Decimal("8"),
            remaining_units=Decimal("12"),
            units_per_time=Decimal("4"),
            units_per_time_period="day",
            hours_per_units_time_period=Decimal("8"),
        )
    )
    periods = PostgresP6ResourceAssignmentPeriodRepository(connection)
    for period_start in ("2026-01-05", "2026-01-06", "2026-01-07"):
        periods.upsert(
            P6ResourceAssignmentPeriodValue(
                scope=SCOPE,
                assignment_id="AS-RD",
                activity_id="A-RD",
                resource_id="RES-RD",
                period_start=period_start,
                units=Decimal("4"),
                cost=Decimal("0"),
            )
        )
    connection.commit()

    with pytest.raises(ActivityOperationError) as refused:
        api.execute(
            SCOPE,
            "copy",
            ["A-RD"],
            auth_context=_context("planner"),
            idempotency_key="live-rd-copy",
            now=datetime(2026, 11, 26, 15, 0, tzinfo=timezone.utc),
        )
    assert str(refused.value).startswith(
        "P6_ACTIVITY_COPY_PROGRESS_DEMAND_UNSUPPORTED:"
    )

    # The atomic transaction left no partial copy behind.
    assert activities.get(SCOPE, "A-RD-COPY") is None
    assignment_reader = PostgresP6ResourceAssignmentRepository(connection)
    assert assignment_reader.get(SCOPE, "AS-RD-COPY") is None
    assert periods.list(SCOPE, assignment_id="AS-RD-COPY") == ()
    # The source demand is untouched.
    assert len(periods.list(SCOPE, assignment_id="AS-RD")) == 3


def _lag_repository(connection):
    PostgresCalendarMasterRepository(connection).initialize()
    return PostgresCalendarAssignmentRepository(connection)


def test_delete_removes_the_relationship_lag_override(live):
    connection, _ = live
    api, activities, relationships = _seed(connection)
    calendar_assignments = _lag_repository(connection)
    calendar_assignments.save_relationship_lag(
        RelationshipLagCalendarAssignmentMaster(
            scope=SCOPE,
            relationship_id="R-1",
            option=RelationshipLagCalendar.PREDECESSOR,
        )
    )
    connection.commit()

    result = api.execute(
        SCOPE,
        "delete",
        ["A-1"],
        auth_context=_context("planner"),
        idempotency_key="live-del-lag",
        confirm_dependencies=True,
        now=datetime(2026, 11, 28, 8, 0, tzinfo=timezone.utc),
    )

    assert result["removed_rows"]["relationship_lag_calendar_assignment"] == 1
    assert relationships.get(SCOPE, "R-1") is None
    assert calendar_assignments.get_relationship_lag(SCOPE, "R-1") is None
    remaining = connection.execute(
        "SELECT relationship_id FROM relationship_lag_calendar_assignment"
    ).fetchall()
    assert remaining == []


def test_copy_preserves_the_relationship_lag_override(live):
    connection, _ = live
    api, _, relationships = _seed(connection)
    calendar_assignments = _lag_repository(connection)
    calendar_assignments.save_relationship_lag(
        RelationshipLagCalendarAssignmentMaster(
            scope=SCOPE,
            relationship_id="R-1",
            option=RelationshipLagCalendar.SUCCESSOR,
            calendar_id="CAL-LAG",
            calendar_version="V1",
        )
    )
    connection.commit()

    result = api.execute(
        SCOPE,
        "copy",
        ["A-1", "A-2"],
        auth_context=_context("planner"),
        idempotency_key="live-copy-lag",
        now=datetime(2026, 11, 28, 8, 30, tzinfo=timezone.utc),
    )

    assert result["lag_calendar_assignments_created"] == 1
    copied = calendar_assignments.get_relationship_lag(SCOPE, "R-1-COPY")
    assert copied is not None
    assert copied.option is RelationshipLagCalendar.SUCCESSOR
    assert (copied.calendar_id, copied.calendar_version) == ("CAL-LAG", "V1")
    # The source relationship and its override are unchanged.
    assert relationships.get(SCOPE, "R-1") is not None
    source = calendar_assignments.get_relationship_lag(SCOPE, "R-1")
    assert source is not None and source.option is RelationshipLagCalendar.SUCCESSOR
