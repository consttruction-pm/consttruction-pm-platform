from __future__ import annotations

"""Shared-Core contract for P6 multi-project float boundaries.

This module intentionally does not run a project scheduler. It only resolves
the late-finish boundary that a multi-project batch must pass to each project's
backward/float calculation. This keeps P6 batch semantics separate from the
single-project CPM engine.
"""

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Mapping


@dataclass(frozen=True)
class ProjectFinishBoundary:
    project_id: str
    scheduled_finish: date

    def __post_init__(self) -> None:
        if not self.project_id.strip():
            raise ValueError("project_id is required")


@dataclass(frozen=True)
class MultiProjectFloatBoundary:
    calculate_based_on_project_finish: bool
    project_finishes: Mapping[str, date]
    batch_finish: date

    def finish_for(self, project_id: str) -> date:
        if project_id not in self.project_finishes:
            raise ValueError(f"unknown project_id: {project_id}")
        if self.calculate_based_on_project_finish:
            return self.project_finishes[project_id]
        return self.batch_finish


def resolve_multi_project_float_boundary(
    projects: Iterable[ProjectFinishBoundary],
    *,
    calculate_based_on_project_finish: bool,
) -> MultiProjectFloatBoundary:
    project_list = list(projects)
    if not project_list:
        raise ValueError("at least one project is required")

    project_finishes: dict[str, date] = {}
    for project in project_list:
        if project.project_id in project_finishes:
            raise ValueError(f"duplicate project_id: {project.project_id}")
        project_finishes[project.project_id] = project.scheduled_finish

    batch_finish = max(project_finishes.values())
    return MultiProjectFloatBoundary(
        calculate_based_on_project_finish=calculate_based_on_project_finish,
        project_finishes=project_finishes,
        batch_finish=batch_finish,
    )
