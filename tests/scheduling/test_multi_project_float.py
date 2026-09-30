from datetime import date

import pytest

from construction_pm.scheduling.multi_project_float import (
    ProjectFinishBoundary,
    resolve_multi_project_float_boundary,
)


def test_multi_project_float_uses_each_project_finish_when_enabled():
    boundary = resolve_multi_project_float_boundary(
        [
            ProjectFinishBoundary("P1", date(2026, 10, 10)),
            ProjectFinishBoundary("P2", date(2026, 10, 20)),
        ],
        calculate_based_on_project_finish=True,
    )

    assert boundary.finish_for("P1") == date(2026, 10, 10)
    assert boundary.finish_for("P2") == date(2026, 10, 20)
    assert boundary.batch_finish == date(2026, 10, 20)


def test_multi_project_float_uses_batch_finish_when_disabled():
    boundary = resolve_multi_project_float_boundary(
        [
            ProjectFinishBoundary("P1", date(2026, 10, 10)),
            ProjectFinishBoundary("P2", date(2026, 10, 20)),
        ],
        calculate_based_on_project_finish=False,
    )

    assert boundary.finish_for("P1") == date(2026, 10, 20)
    assert boundary.finish_for("P2") == date(2026, 10, 20)


def test_single_project_batch_is_identity_for_both_modes():
    project = [ProjectFinishBoundary("P1", date(2026, 10, 10))]

    each = resolve_multi_project_float_boundary(
        project, calculate_based_on_project_finish=True
    )
    batch = resolve_multi_project_float_boundary(
        project, calculate_based_on_project_finish=False
    )

    assert each.finish_for("P1") == batch.finish_for("P1") == date(2026, 10, 10)


def test_multi_project_float_rejects_empty_batch_and_duplicate_projects():
    with pytest.raises(ValueError, match="at least one project"):
        resolve_multi_project_float_boundary(
            [], calculate_based_on_project_finish=False
        )

    with pytest.raises(ValueError, match="duplicate project_id"):
        resolve_multi_project_float_boundary(
            [
                ProjectFinishBoundary("P1", date(2026, 10, 10)),
                ProjectFinishBoundary("P1", date(2026, 10, 11)),
            ],
            calculate_based_on_project_finish=False,
        )


def test_multi_project_float_rejects_unknown_project():
    boundary = resolve_multi_project_float_boundary(
        [ProjectFinishBoundary("P1", date(2026, 10, 10))],
        calculate_based_on_project_finish=True,
    )

    with pytest.raises(ValueError, match="unknown project_id"):
        boundary.finish_for("P2")
