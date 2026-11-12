from __future__ import annotations

"""Scale and completeness invariants for the authoritative schedule input.

A presentation choice in the Activities window (a filter, a collapsed WBS
branch, a hidden column) is never an input to schedule calculation. The
composer therefore reads every persisted activity in the project scope, and
the same persisted facts must produce the same immutable input regardless of
what the browser currently draws.
"""

import inspect

from construction_pm.authoritative_schedule_input_composer import (
    AuthoritativeScheduleInputComposer,
)

from test_authoritative_schedule_snapshot_composer import _fixture, _request, _save_settings

ACTIVITY_COUNT = 260


def _activity_payload(activity_id: str) -> dict[str, object]:
    return {
        "contract_version": "p6-activity-master-api.v1",
        "activity_id": activity_id,
        "name": f"Stress activity {activity_id}",
        "duration_unit": "working-day",
        "duration_value": "2",
        "percent_complete_type": "DURATION",
        "activity_type": "Task Dependent",
        "status": "Not Started",
        "status_code": "Planned",
        "leveling_priority": "Normal",
        "original_duration": 2,
        "wbs_id": "W-ROOT",
    }


def test_composer_reads_every_persisted_activity_without_a_row_cap(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    composer = fixture["composer"]
    scope = fixture["scope"]

    for index in range(1, ACTIVITY_COUNT + 1):
        status, _ = _request(
            app,
            "POST",
            "/api/projects/p1/p6/activities",
            _activity_payload(f"S{index:03d}"),
        )
        assert status == "201 Created", status

    settings_status, _ = _save_settings(app)
    assert settings_status == "201 Created"

    schedule_input = composer.compose(scope, snapshot_id="SNAP-SCALE-1")

    assert len(schedule_input.activities) == ACTIVITY_COUNT
    assert {activity.id for activity in schedule_input.activities} == {
        f"S{index:03d}" for index in range(1, ACTIVITY_COUNT + 1)
    }
    assert schedule_input.snapshot_id == "SNAP-SCALE-1"


def test_composition_is_deterministic_across_repeated_fresh_reads(tmp_path):
    fixture = _fixture(tmp_path)
    app = fixture["app"]
    composer = fixture["composer"]
    scope = fixture["scope"]

    for index in range(1, ACTIVITY_COUNT + 1):
        status, _ = _request(
            app,
            "POST",
            "/api/projects/p1/p6/activities",
            _activity_payload(f"S{index:03d}"),
        )
        assert status == "201 Created", status

    settings_status, _ = _save_settings(app)
    assert settings_status == "201 Created"

    first = composer.compose(scope, snapshot_id="SNAP-SCALE-A")
    second = composer.compose(scope, snapshot_id="SNAP-SCALE-B")

    # The snapshot identity differs; every factual input is identical.
    assert first.activities == second.activities
    assert first.relationships == second.relationships
    assert first.constraints == second.constraints
    assert first.project_calendar == second.project_calendar


def test_compose_accepts_no_presentation_or_selection_inputs():
    parameters = set(
        inspect.signature(AuthoritativeScheduleInputComposer.compose).parameters
    )
    assert parameters == {"self", "scope", "snapshot_id"}
    for forbidden in ("filter", "filters", "collapsed", "columns", "selection", "highlight"):
        assert forbidden not in parameters
