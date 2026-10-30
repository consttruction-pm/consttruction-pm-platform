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
    assert successor_earliest_start(sf, date(2026, 9, 21), date(2026, 9, 23), 2, r) == date(2026, 9, 18)


def test_positive_working_lag_is_applied() -> None:
    r = WorkingTimeResolver(WorkingCalendar())
    rel = Relationship("A", "B", RelationshipType.FS, lag=2)
    assert successor_earliest_start(rel, date(2026, 9, 21), date(2026, 9, 22), 1, r) == date(2026, 9, 25)


def test_fs_zero_lag_skips_nonworking_days_after_finish() -> None:
    resolver = WorkingTimeResolver(WorkingCalendar())
    relationship = Relationship("A", "B", RelationshipType.FS)
    # Friday finish: the next activity starts on Monday, not Saturday.
    assert successor_earliest_start(
        relationship, date(2026, 9, 24), date(2026, 9, 25), 1, resolver
    ) == date(2026, 9, 28)


def test_negative_fs_lag_moves_back_by_working_day() -> None:
    resolver = WorkingTimeResolver(WorkingCalendar())
    relationship = Relationship("A", "B", RelationshipType.FS, lag=-1)
    assert successor_earliest_start(
        relationship, date(2026, 9, 21), date(2026, 9, 23), 1, resolver
    ) == date(2026, 9, 22)


def test_negative_ss_lag_moves_before_predecessor_start() -> None:
    resolver = WorkingTimeResolver(WorkingCalendar())
    relationship = Relationship("A", "B", RelationshipType.SS, lag=-1)
    assert successor_earliest_start(
        relationship, date(2026, 9, 21), date(2026, 9, 23), 1, resolver
    ) == date(2026, 9, 18)


def test_relationship_rejects_boolean_lag() -> None:
    import pytest

    with pytest.raises(TypeError, match="lag must be an integer"):
        Relationship("A", "B", RelationshipType.FS, lag=True)
