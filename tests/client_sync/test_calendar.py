import pytest

from construction_pm.client_sync.calendar import ClientCalendarContext, ClientCalendarReference


def test_calendar_reference_serializes_version_and_kind():
    reference = ClientCalendarReference('cal-1', 'v7', 'working-time')
    assert reference.to_payload() == {'contract_version':'client-calendar-reference.v1','calendar_id':'cal-1','calendar_version':'v7','kind':'working-time'}


def test_context_uses_explicit_activity_and_lag_references():
    project = ClientCalendarReference('project-cal','v1')
    activity = ClientCalendarReference('activity-cal','v3')
    lag = ClientCalendarReference('lag-cal','v2')
    context = ClientCalendarContext(project, activity, lag)
    assert context.effective_activity() is activity
    assert context.effective_relationship_lag() is lag


def test_context_follows_authoritative_fallback_chain():
    project = ClientCalendarReference('project-cal','v1')
    activity = ClientCalendarReference('activity-cal','v3')
    context = ClientCalendarContext(project, activity)
    assert context.effective_activity() is activity
    assert context.effective_relationship_lag() is activity
    project_only = ClientCalendarContext(project)
    assert project_only.effective_activity() is project
    assert project_only.effective_relationship_lag() is project


@pytest.mark.parametrize('reference',[ClientCalendarReference('','v1'),ClientCalendarReference('cal-1',''),ClientCalendarReference('cal-1','v1','unsupported')])
def test_invalid_calendar_reference_is_rejected(reference):
    with pytest.raises(ValueError): reference.validate()


def test_calendar_context_payload_is_presentation_only():
    payload = ClientCalendarContext(ClientCalendarReference('cal-1','v1')).to_payload()
    assert payload['contract_version'] == 'client-calendar-context.v1'
    assert payload['project']['calendar_id'] == 'cal-1'
    assert payload['activity'] is None
    assert payload['relationship_lag'] is None
