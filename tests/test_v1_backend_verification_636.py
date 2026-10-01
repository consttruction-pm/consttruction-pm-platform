from datetime import datetime, timezone

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleService,
    ProjectSummary,
)
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment,
    SQLiteP6ResourceAssignmentRepository,
)
from construction_pm.p6_resource_spread_repository import (
    P6ResourceSpreadBucket,
    SQLiteP6ResourceSpreadRepository,
)
from construction_pm.backend_p0.models import BackendScope
from decimal import Decimal
import sqlite3


class Sessions:
    def __init__(self, session):
        self.session = session

    def get(self, session_id):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def get_for_user(self, tenant_id, project_id, user_id):
        if (tenant_id, project_id, user_id) == ("tenant-a", "project-a", "user-a"):
            return ProjectSummary("project-a", "tenant-a", "Project A", 7)
        return None

    def list_for_user(self, tenant_id, user_id):
        project = self.get_for_user(tenant_id, "project-a", user_id)
        return (project,) if project else ()

    def create_for_user(self, tenant_id, user_id, project_id, name):
        return ProjectSummary(project_id, tenant_id, name, 0)


def test_project_context_is_derived_from_authorized_session():
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "session-a", "user-a", "tenant-a",
        frozenset({"planner"}), now.replace(hour=23),
    )
    service = ProjectLifecycleService(
        Sessions(session), Projects(), default_project_policy()
    )

    context = service.open_project("session-a", "project-a", now=now)

    assert (context.tenant_id, context.project_id, context.user_id) == (
        "tenant-a", "project-a", "user-a"
    )
    assert context.revision == 7


def test_assignment_read_is_scope_and_revision_bound():
    repo = SQLiteP6ResourceAssignmentRepository(sqlite3.connect(":memory:"))
    scope = BackendScope("tenant-a", "project-a", 1)
    assignment = P6ResourceAssignment(
        scope, "ra-1", "act-1", "res-1", "role-1",
        Decimal("8.5"), Decimal("2.5"), Decimal("6.0"),
        Decimal("850.25"), Decimal("250.00"), Decimal("600.25"),
        "h", "USD", "cal-1", "verification",
    )

    repo.upsert(assignment)

    assert repo.get(scope, "ra-1") == assignment
    assert repo.get(BackendScope("tenant-b", "project-a", 1), "ra-1") is None


def test_spread_read_is_scope_and_revision_bound():
    repo = SQLiteP6ResourceSpreadRepository(sqlite3.connect(":memory:"))
    scope = BackendScope("tenant-a", "project-a", 1)
    spread = P6ResourceSpreadBucket(
        scope=scope,
        spread_id="spread-1",
        resource_id="resource-1",
        period_id="2026-10",
        period_start="2026-10-01",
        period_end="2026-10-31",
        spread_type="PLANNED",
        metric="UNITS",
        value=Decimal("12.50"),
        unit="hours",
    )

    repo.upsert(spread)

    assert repo.get(scope, "spread-1", "2026-10") == spread
    assert repo.get(BackendScope("tenant-b", "project-a", 1), "spread-1", "2026-10") is None
