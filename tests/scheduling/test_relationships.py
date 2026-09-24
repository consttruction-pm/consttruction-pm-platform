from datetime import date

from construction_pm.scheduling import (
    Relationship,
    RelationshipType,
    WorkingCalendar,
    WorkingTimeResolver,
    successor_earliest_start,
)


def test_relationship_types_have_stable_codes() -> None:
    assert [x.value for x in RelationshipType] == ["FS", "SS", "FF", "SF"]


def test_fs_with_zero_lag_starts_after_predecessor_finish() -> None:
    r = WorkingTimeResolver(WorkingCalendar())
    rel = Relationship("A", "B", RelationshipType.FS)
    assert successor_earliest_start(rel, date(2026, 9, 21), date(2026, 9, 22), 2, r) == date(2026, 9, 23)


def test_ss_with_zero_lag_uses_predecessor_start() -> None:
    r = WorkingTimeResolver(WorkingCalendar())
    rel = Relationship("A", "B", RelationshipType.SS)
    assert successor_earliest_start(rel, date(2026, 9, 21), date(2026, 9, 23), 2, r) == date(2026, 9, 21)


def test_ff_and_sf_convert_required_finish_to_successor_start() -> None:
    r = WorkingTimeResolver(WorkingCalendar())
    ff = Relationship("A", "B", RelationshipType.FF)
    sf = Relationship("A", "B", RelationshipType.SF)
    assert successor_earliest_start(ff, date(2026, 9, 21), date(2026, 9, 23), 2, r) == date(2026, 9, 22)
    assert successor_earliest_start(sf, date(2026, 9, 21), date(2026, 9, 23), 2, r) == date(2026, 9, 20)


def test_positive_working_lag_is_applied() -> None:
    r = WorkingTimeResolver(WorkingCalendar())
    rel = Relationship("A", "B", RelationshipType.FS, lag=2)
    assert successor_earliest_start(rel, date(2026, 9, 21), date(2026, 9, 22), 1, r) == date(2026, 9, 25)
