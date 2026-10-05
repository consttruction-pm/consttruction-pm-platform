import os
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_master_repository import CalendarMaster, PostgresCalendarMasterRepository
from construction_pm.calendar_work_hours_repository import CalendarWorkHourRule, PostgresCalendarWorkHourRepository

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)

def connect():
    import psycopg
    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])

def test_postgres_work_hours_contract_roundtrip():
    scope = BackendScope("tenant-calendar-hours", "project-hours", 7)
    with connect() as connection:
        master = PostgresCalendarMasterRepository(connection)
        master.initialize()
        work_hours = PostgresCalendarWorkHourRepository(connection)
        work_hours.initialize()
        connection.execute("DELETE FROM calendar_work_hour_rule WHERE tenant_id=%s AND project_id=%s", (scope.tenant_id, scope.project_id))
        connection.execute("DELETE FROM calendar_master WHERE tenant_id=%s AND project_id=%s", (scope.tenant_id, scope.project_id))
        connection.commit()

        calendar = master.save(CalendarMaster(scope, "CAL-H", "1", "working-day", "Hours", calendar_type="project"))
        connection.commit()
        rule = CalendarWorkHourRule(
            scope, calendar.calendar_id, calendar.calendar_version,
            "detailed_work_hours", 0, True, Decimal("8"),
            (("08:00", "12:00"), ("13:00", "17:00")),
        )
        stored = work_hours.save(rule)
        connection.commit()
        restored = work_hours.list(scope, "CAL-H", "1", "detailed_work_hours")[0]
        assert restored == stored
        assert restored.canonical_snapshot()["total_work_hours"] == "8"

        connection.execute("DELETE FROM calendar_work_hour_rule WHERE tenant_id=%s AND project_id=%s", (scope.tenant_id, scope.project_id))
        connection.execute("DELETE FROM calendar_master WHERE tenant_id=%s AND project_id=%s", (scope.tenant_id, scope.project_id))
        connection.commit()
