"""External open-source validation oracle smoke tests.

These tests do not delegate product calculations to pmcontrols. They provide
an independently implemented reference for a canonical CPM case.
"""

from __future__ import annotations

import pytest

pm = pytest.importorskip("pmcontrols")


def test_pmcontrols_general_foundry_reference_case() -> None:
    activities = [
        {"id": "A", "predecessors": [], "duration": 2},
        {"id": "B", "predecessors": [], "duration": 3},
        {"id": "C", "predecessors": ["A"], "duration": 2},
        {"id": "D", "predecessors": ["B"], "duration": 4},
        {"id": "E", "predecessors": ["C"], "duration": 4},
        {"id": "F", "predecessors": ["C"], "duration": 3},
        {"id": "G", "predecessors": ["D", "E"], "duration": 5},
        {"id": "H", "predecessors": ["F", "G"], "duration": 2},
    ]

    result = pm.cpm(activities)

    assert result.stats["project_duration"] == 15.0
    assert result.meta["critical_activities"] == ["A", "C", "E", "G", "H"]
