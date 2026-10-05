import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from construction_pm.application.authorization import AuthorizationContext, default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_exception_repository import SQLiteCalendarExceptionRepository
from construction_pm.calendar_master_repository import CalendarMaster, SQLiteCalendarMasterRepository
from construction_pm.calendar_snapshot_repository import SQLiteCalendarSnapshotRepository
from construction_pm.p6_calendar_api import (
    P6_CALENDAR_API_VERSION,
    P6CalendarAPI,
    P6CalendarCreateRequest,
)
from construction_pm.scheduling.calendar import WorkingCalendar
from construction_pm.scheduling.calendar_periods import CalendarTimePeriodFactors
from construction_pm.scheduling.calendar_system import CalendarSystem


def _scope(revision: int = 7) -> BackendScope:
    return BackendScope("T-1", "P-1", revision)


def _auth(role: str = "planner") -> AuthorizationContext:
    return AuthorizationContext("T-1", "P-1", "U-1", frozenset({role}))


def _api():
    conn = sqlite3.connect(":memory:")
    master = SQLiteCalendarMasterRepository(conn)
    snapshot = SQLiteCalendarSnapshotRepository(conn)
    exceptions = SQLiteCalendarExceptionRepository(conn)
    return P6CalendarAPI(master, snapshot, exceptions, default_project_policy()), conn


def _definition() -> WorkingCalendar:
    return WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}),
        holidays=frozenset({date(2026, 3, 21)}),
        system=CalendarSystem.JALALI,
        time_period_factors=CalendarTimePeriodFactors(
            hours_per_day=Decimal("8"), hours_per_week=Decimal("40"),
            hours_per_month=Decimal("176"), hours_per_year=Decimal("2080"),
        ),
    )


def _request(calendar_id: str, version: str = "1", calendar_type: str = "project") -> P6CalendarCreateRequest:
    return P6CalendarCreateRequest(
        P6_CALENDAR_API_VERSION, calendar_id, version, calendar_type,
        "working-day", "Calendar", 0,
    )


def test_create_list_and_get_expose_explicit_p6_calendar_type():
    api, _ = _api()
    created = api.create(_scope(), _request("CAL-P"), auth_context=_auth())
    assert created["calendar_type"] == "project"
    assert api.get(_scope(), "CAL-P", "1", auth_context=_auth())["calendar_type"] == "project"
    assert api.list(_scope(), auth_context=_auth())["calendars"][0]["calendar_id"] == "CAL-P"


@pytest.mark.parametrize("calendar_type", ["global", "resource", "project"])
def test_all_p6_calendar_types_are_accepted(calendar_type):
    api, _ = _api()
    created = api.create(_scope(), _request(f"CAL-{calendar_type}", calendar_type=calendar_type), auth_context=_auth())
    assert created["calendar_type"] == calendar_type


def test_invalid_calendar_type_is_rejected():
    api, _ = _api()
    with pytest.raises(ValueError, match="INVALID_CALENDAR_TYPE"):
        api.create(_scope(), _request("CAL-X", calendar_type="other"), auth_context=_auth())


def test_copy_replays_snapshot_and_keeps_type():
    api, _ = _api()
    api.create(_scope(), _request("CAL-S", calendar_type="global"), auth_context=_auth())
    source = api.calendar_repository.get(_scope(), "CAL-S", "1")
    api.snapshot_repository.save(source, _definition())
    copied = api.copy(_scope(), "CAL-S", "1", "CAL-C", "1", auth_context=_auth())
    assert copied["calendar_type"] == "global"
    assert api.snapshot_repository.get(api.calendar_repository.get(_scope(), "CAL-C", "1")) is not None


def test_replace_uses_authoritative_snapshot_and_optimistic_revision():
    api, _ = _api()
    api.create(_scope(), _request("CAL-S"), auth_context=_auth())
    api.create(_scope(), _request("CAL-T"), auth_context=_auth())
    source = api.calendar_repository.get(_scope(), "CAL-S", "1")
    api.snapshot_repository.save(source, _definition())
    replaced = api.replace(_scope(), "CAL-T", "1", "CAL-S", "1", auth_context=_auth())
    assert replaced["calendar_id"] == "CAL-T"
    assert replaced["record_revision"] == 2
    target = api.calendar_repository.get(_scope(), "CAL-T", "1")
    assert api.snapshot_repository.get(target) is not None


def test_delete_requires_current_record_revision():
    api, _ = _api()
    api.create(_scope(), _request("CAL-D"), auth_context=_auth())
    with pytest.raises(ValueError, match="REVISION_CONFLICT"):
        api.delete(_scope(), "CAL-D", "1", expected_revision=2, auth_context=_auth())
    assert api.delete(_scope(), "CAL-D", "1", expected_revision=1, auth_context=_auth())
    assert api.get(_scope(), "CAL-D", "1", auth_context=_auth()) is None


def test_viewer_can_read_but_cannot_mutate():
    api, _ = _api()
    with pytest.raises(ValueError, match="authorization denied"):
        api.create(_scope(), _request("CAL-V"), auth_context=_auth("viewer"))
