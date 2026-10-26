from __future__ import annotations

"""Curated, reproducible demo data for the local full-stack preview.

Everything in this module is preview fixture data. It is written only to the
guarded local preview SQLite database and is never a production seed. Dates are
deliberately explicit so a browser walkthrough can compare the rendered table
and Gantt with the immutable snapshot inputs.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Mapping

from construction_pm.resources.max_units_time import ResourceCapacityBasis
from construction_pm.scheduling.activity import (
    ActivityLevelingPriority,
    ActivityStatus,
    ActivityStatusCode,
    ActivityType,
)
from construction_pm.scheduling.calendar_system import CalendarSystem, JalaliDate
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_duration import DurationUnit


REGISTRY_VERSION = "p6-field-registry.v1"
LAYOUT_SCOPE = "project"
LAYOUT_VIEW = "activity"

# This is the curated presentation catalogue seeded per project. It is a
# subset of the complete in-repo field registry and keeps the demo table
# readable while retaining the persisted field/layout architecture.
CURATED_FIELD_IDS: tuple[str, ...] = (
    "activity.id",
    "activity.name",
    "activity.status",
    "activity.type",
    "activity.wbs",
    "activity.leveling_priority",
    "activity.status_code",
    "activity.planned_duration",
    "activity.planned_finish",
    "activity.actual_start",
    "activity.actual_finish",
    "activity.remaining_duration",
    "activity.duration_percent_complete",
    "activity.early_start",
    "activity.early_finish",
    "activity.late_start",
    "activity.late_finish",
    "activity.total_float",
    "activity.free_float",
    "activity.is_critical",
)


@dataclass(frozen=True)
class LayoutColumnFixture:
    field_id: str
    visible: bool
    width: float
    alignment: str = "start"


# Column order is persisted with the project layout. The visible subset is
# what the Web grid renders first; hidden columns remain addable from the
# persisted field registry without inventing fields in the browser.
LAYOUT_COLUMNS: tuple[LayoutColumnFixture, ...] = (
    LayoutColumnFixture("activity.id", True, 130, "start"),
    LayoutColumnFixture("activity.name", True, 290, "start"),
    LayoutColumnFixture("activity.status", True, 110, "start"),
    LayoutColumnFixture("activity.wbs", True, 190, "start"),
    LayoutColumnFixture("activity.planned_duration", True, 120, "end"),
    LayoutColumnFixture("activity.early_start", True, 115, "center"),
    LayoutColumnFixture("activity.early_finish", True, 115, "center"),
    LayoutColumnFixture("activity.duration_percent_complete", True, 120, "end"),
    LayoutColumnFixture("activity.total_float", True, 95, "end"),
    LayoutColumnFixture("activity.is_critical", True, 90, "center"),
    LayoutColumnFixture("activity.type", False, 130, "start"),
    LayoutColumnFixture("activity.leveling_priority", False, 120, "start"),
    LayoutColumnFixture("activity.status_code", False, 110, "start"),
    LayoutColumnFixture("activity.planned_finish", False, 115, "center"),
    LayoutColumnFixture("activity.actual_start", False, 115, "center"),
    LayoutColumnFixture("activity.actual_finish", False, 115, "center"),
    LayoutColumnFixture("activity.remaining_duration", False, 120, "end"),
    LayoutColumnFixture("activity.late_start", False, 115, "center"),
    LayoutColumnFixture("activity.late_finish", False, 115, "center"),
    LayoutColumnFixture("activity.free_float", False, 95, "end"),
)


@dataclass(frozen=True)
class DemoActivity:
    activity_id: str
    name: str
    duration: int
    wbs: str
    activity_type: ActivityType = ActivityType.TASK_DEPENDENT
    status: ActivityStatus = ActivityStatus.NOT_STARTED
    status_code: ActivityStatusCode = ActivityStatusCode.PLANNED
    leveling_priority: ActivityLevelingPriority = ActivityLevelingPriority.NORMAL
    actual_start: date | None = None
    actual_finish: date | None = None
    remaining_duration: int | None = None
    percent_complete: float | None = None


@dataclass(frozen=True)
class DemoRelationship:
    relationship_id: str
    predecessor_id: str
    successor_id: str
    relationship_type: RelationshipType = RelationshipType.FS
    lag: int = 0


@dataclass(frozen=True)
class DemoCapacitySegment:
    """A reproducible, explicit Resource Max Units/Time fixture segment.

    The preview seeds these through the real typed-capacity repository. They
    are never derived from assignment demand or from a calendar default.
    """

    resource_id: str
    max_units: Decimal
    effective_from: date
    effective_to: date | None
    source: str
    unit_basis: ResourceCapacityBasis = ResourceCapacityBasis.DAY
    hours_per_time_period: Decimal = Decimal("8")


@dataclass(frozen=True)
class DemoProjectFixture:
    project_id: str
    name: str
    revision: int
    project_start: date
    calendar_id: str
    calendar_name: str
    working_weekdays: frozenset[int]
    calendar_system: CalendarSystem
    holiday_dates: tuple[date, ...]
    snapshot_id: str
    snapshot_clock: datetime
    timezone_name: str
    activities: tuple[DemoActivity, ...]
    relationships: tuple[DemoRelationship, ...]
    wbs: Mapping[str, str] = field(default_factory=dict)
    data_date: date | None = None
    capacities: tuple[DemoCapacitySegment, ...] = ()


RPS_CALENDAR_ID = "CUBI-RPS-CAL"
NSE_CALENDAR_ID = "CUBI-NSE-CAL"


RPS_ACTIVITIES: tuple[DemoActivity, ...] = (
    DemoActivity(
        "A100",
        "Project kickoff",
        1,
        "1 Project management",
        status=ActivityStatus.COMPLETED,
        status_code=ActivityStatusCode.ACTIVE,
        actual_start=date(2026, 9, 21),
        actual_finish=date(2026, 9, 21),
        remaining_duration=0,
        percent_complete=100.0,
    ),
    DemoActivity(
        "A110",
        "Mobilization",
        3,
        "1 Project management",
        status=ActivityStatus.COMPLETED,
        status_code=ActivityStatusCode.ACTIVE,
        actual_start=date(2026, 9, 22),
        actual_finish=date(2026, 9, 24),
        remaining_duration=0,
        percent_complete=100.0,
    ),
    DemoActivity(
        "A120",
        "Site survey and geotechnical investigation",
        4,
        "2 Civil works",
        status=ActivityStatus.COMPLETED,
        status_code=ActivityStatusCode.ACTIVE,
        actual_start=date(2026, 9, 25),
        actual_finish=date(2026, 9, 30),
        remaining_duration=0,
        percent_complete=100.0,
    ),
    DemoActivity(
        "A130",
        "Earthworks",
        8,
        "2 Civil works",
        status=ActivityStatus.IN_PROGRESS,
        status_code=ActivityStatusCode.ACTIVE,
        actual_start=date(2026, 10, 7),
        remaining_duration=5,
        percent_complete=37.5,
    ),
    DemoActivity("A140", "Piling and foundations", 10, "2 Civil works"),
    DemoActivity("A150", "Structural steel procurement", 12, "3 Procurement"),
    DemoActivity("A145", "Site utilities diversion", 4, "2 Civil works"),
    DemoActivity("A155", "Envelope mock-up approval", 3, "4 Envelope works"),
    DemoActivity("A160", "Steel erection", 7, "2 Civil works"),
    DemoActivity("A170", "MEP first fix", 6, "5 MEP works"),
    DemoActivity("A180", "Facade and envelope", 5, "4 Envelope works"),
    DemoActivity("A190", "Commissioning", 4, "5 MEP works"),
    DemoActivity("A200", "QA/QC and handover", 3, "6 Commissioning and handover"),
    DemoActivity("A210", "Project closeout", 2, "1 Project management"),
)


RPS_RELATIONSHIPS: tuple[DemoRelationship, ...] = (
    DemoRelationship("REL-RPS-100", "A100", "A110"),
    DemoRelationship("REL-RPS-110", "A110", "A120"),
    DemoRelationship("REL-RPS-120", "A120", "A130"),
    DemoRelationship("REL-RPS-130", "A130", "A140"),
    DemoRelationship("REL-RPS-140", "A130", "A150"),
    DemoRelationship("REL-RPS-145", "A130", "A145"),
    DemoRelationship("REL-RPS-150", "A145", "A155"),
    DemoRelationship("REL-RPS-160", "A140", "A160"),
    DemoRelationship("REL-RPS-165", "A150", "A160"),
    DemoRelationship(
        "REL-RPS-170",
        "A140",
        "A170",
        relationship_type=RelationshipType.SS,
        lag=5,
    ),
    DemoRelationship("REL-RPS-180", "A160", "A180"),
    DemoRelationship("REL-RPS-185", "A155", "A180"),
    DemoRelationship("REL-RPS-190", "A180", "A190"),
    DemoRelationship("REL-RPS-200", "A190", "A200"),
    DemoRelationship("REL-RPS-210", "A200", "A210"),
)


RPS_WBS: Mapping[str, str] = {
    activity.activity_id: activity.wbs for activity in RPS_ACTIVITIES
}


NSE_ACTIVITIES: tuple[DemoActivity, ...] = (
    DemoActivity("N100", "آغاز طراحی", 2, "۱ طراحی و مهندسی"),
    DemoActivity("N110", "طراحی مفهومی", 5, "۱ طراحی و مهندسی"),
    DemoActivity("N120", "تأیید مرجع کارفرما", 4, "۱ طراحی و مهندسی"),
    DemoActivity("N130", "تهیه اسناد مناقصه", 3, "۱ طراحی و مهندسی"),
    DemoActivity("N140", "ارزیابی پیشنهادها", 4, "۲ تدارکات و قرارداد"),
    DemoActivity("N150", "واگذاری قرارداد", 2, "۲ تدارکات و قرارداد"),
)


NSE_RELATIONSHIPS: tuple[DemoRelationship, ...] = (
    DemoRelationship("REL-NSE-100", "N100", "N110"),
    DemoRelationship("REL-NSE-110", "N110", "N120"),
    DemoRelationship(
        "REL-NSE-120",
        "N110",
        "N130",
        relationship_type=RelationshipType.SS,
        lag=2,
    ),
    DemoRelationship("REL-NSE-130", "N130", "N140"),
    DemoRelationship("REL-NSE-140", "N140", "N150"),
    DemoRelationship("REL-NSE-150", "N120", "N150"),
)


NSE_WBS: Mapping[str, str] = {
    activity.activity_id: activity.wbs for activity in NSE_ACTIVITIES
}


# 2027-02-08 is recorded through the Shared Core Jalali conversion so the
# holiday is demonstrably a Jalali calendar exception, not an ad hoc date.
NSE_HOLIDAY = JalaliDate.from_gregorian(date(2027, 2, 8)).to_gregorian()


DEMO_PROJECTS: tuple[DemoProjectFixture, ...] = (
    DemoProjectFixture(
        project_id="preview-rps-01",
        name="Riverside Pump Station Upgrade",
        revision=7,
        project_start=date(2026, 9, 21),
        calendar_id=RPS_CALENDAR_ID,
        calendar_name="Riverside Mon-Fri (Gregorian)",
        working_weekdays=frozenset({0, 1, 2, 3, 4}),
        calendar_system=CalendarSystem.GREGORIAN,
        holiday_dates=(date(2026, 10, 28),),
        snapshot_id="SNAP-PREVIEW-RPS01-001",
        snapshot_clock=datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc),
        timezone_name="UTC",
        data_date=date(2026, 10, 12),
        activities=RPS_ACTIVITIES,
        relationships=RPS_RELATIONSHIPS,
        wbs=RPS_WBS,
        capacities=(
            DemoCapacitySegment(
                resource_id="RPS-CIVIL-CREW",
                max_units=Decimal("8"),
                effective_from=date(2026, 9, 21),
                effective_to=date(2026, 10, 14),
                source="preview-fixture:RPS-rev7-capacity-1",
            ),
            DemoCapacitySegment(
                resource_id="RPS-CIVIL-CREW",
                max_units=Decimal("12"),
                effective_from=date(2026, 10, 15),
                effective_to=None,
                source="preview-fixture:RPS-rev7-capacity-2",
            ),
        ),
    ),
    DemoProjectFixture(
        project_id="preview-nse-02",
        name="نوسازی سامانه شرقی",
        revision=2,
        project_start=date(2027, 2, 2),
        calendar_id=NSE_CALENDAR_ID,
        calendar_name="NSE Sat-Wed (Jalali)",
        working_weekdays=frozenset({5, 6, 0, 1, 2}),
        calendar_system=CalendarSystem.JALALI,
        holiday_dates=(NSE_HOLIDAY,),
        snapshot_id="SNAP-PREVIEW-NSE02-001",
        snapshot_clock=datetime(2026, 10, 26, 8, 5, tzinfo=timezone.utc),
        timezone_name="Asia/Tehran",
        data_date=None,
        activities=NSE_ACTIVITIES,
        relationships=NSE_RELATIONSHIPS,
        wbs=NSE_WBS,
        capacities=(
            DemoCapacitySegment(
                resource_id="NSE-DESIGN-TEAM",
                max_units=Decimal("4"),
                effective_from=date(2027, 2, 2),
                effective_to=None,
                source="preview-fixture:NSE-rev2-capacity-1",
            ),
        ),
    ),
)


DEFAULT_CALENDAR_VERSION = "1"
DEFAULT_ACTIVITY_DURATION_UNIT = DurationUnit.WORKING_DAY
DEFAULT_PROJECT_LEVELING_PRIORITY = 10


def fixture_by_project_id(project_id: str) -> DemoProjectFixture | None:
    for fixture in DEMO_PROJECTS:
        if fixture.project_id == project_id:
            return fixture
    return None


def working_day_lag_value(relationship: DemoRelationship) -> Decimal:
    return Decimal(relationship.lag)


__all__ = [
    "CURATED_FIELD_IDS",
    "DEFAULT_CALENDAR_VERSION",
    "DEFAULT_PROJECT_LEVELING_PRIORITY",
    "DEMO_PROJECTS",
    "DemoActivity",
    "DemoCapacitySegment",
    "DemoProjectFixture",
    "DemoRelationship",
    "LAYOUT_COLUMNS",
    "LAYOUT_SCOPE",
    "LAYOUT_VIEW",
    "NSE_CALENDAR_ID",
    "REGISTRY_VERSION",
    "RPS_CALENDAR_ID",
    "fixture_by_project_id",
]
