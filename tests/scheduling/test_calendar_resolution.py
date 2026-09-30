        )
        assert result.early_activities is not None
        assert result.late_activities is not None
        assert result.early_activities["A"].start <= result.early_activities["B"].finish
        repeat = schedule(
            snapshot.activities,
            snapshot.relationships,
            snapshot.project_start,
            project_resolver,
            options=snapshot.schedule_options,
            relationship_lag_resolvers=resolve_relationship_lag_resolvers(snapshot, registry),
        )
        assert result.early_activities == repeat.early_activities
        assert result.late_activities == repeat.late_activities


def test_backward_sf_uses_selected_relationship_lag_calendar():
    from construction_pm.scheduling.forward_pass import ScheduledActivity
    from construction_pm.scheduling.schedule import _latest_predecessor_start

    project_resolver = WorkingTimeResolver(WorkingCalendar())
    lag_resolver = WorkingTimeResolver(
        WorkingCalendar(holidays=frozenset({date(2026, 9, 22)}))
    )
    successor = ScheduledActivity("B", date(2026, 9, 24), date(2026, 9, 24), 1)
    relationship = Relationship("A", "B", RelationshipType.SF, lag=1)
    actual = _latest_predecessor_start(
        relationship, successor, 1, project_resolver, lag_resolver
    )
    assert actual == date(2026, 9, 21)


def test_backward_relationship_validation_uses_selected_lag_calendar():
    project = CalendarReference("project", "1")
    predecessor = CalendarReference("pred", "1")
    successor = CalendarReference("succ", "1")
    snapshot = AuthoritativeScheduleInput(
        snapshot_id="snap-sf-validation",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision=1,