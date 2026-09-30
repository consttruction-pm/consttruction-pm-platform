from __future__ import annotations

"""Immutable batch contract for multi-project P6 scheduling boundaries."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from .authoritative_schedule import AuthoritativeScheduleInput
from .multi_project_float import (
    MultiProjectFloatBoundary,
    ProjectFinishBoundary,
    resolve_multi_project_float_boundary,
)


@dataclass(frozen=True)
class AuthoritativeScheduleBatch:
    snapshots: tuple[AuthoritativeScheduleInput, ...]
    float_boundary: MultiProjectFloatBoundary

    @classmethod
    def from_snapshots(
        cls,
        snapshots: Iterable[AuthoritativeScheduleInput],
        *,
        calculate_based_on_project_finish: bool,
    ) -> "AuthoritativeScheduleBatch":
        snapshot_list = tuple(snapshots)
        if not snapshot_list:
            raise ValueError("at least one schedule snapshot is required")

        project_ids = [snapshot.project_id for snapshot in snapshot_list]
        if len(project_ids) != len(set(project_ids)):
            raise ValueError("schedule batch project ids must be unique")

        finishes: list[ProjectFinishBoundary] = []
        for snapshot in snapshot_list:
            if snapshot.project_finish is None:
                raise ValueError(
                    f"project_finish is required for batch project {snapshot.project_id}"
                )
            if not isinstance(snapshot.project_finish, date) or isinstance(snapshot.project_finish, datetime):
                raise ValueError(
                    f"date-based project_finish is required for batch project {snapshot.project_id}"
                )
            finishes.append(
                ProjectFinishBoundary(snapshot.project_id, snapshot.project_finish)
            )

        boundary = resolve_multi_project_float_boundary(
            finishes,
            calculate_based_on_project_finish=calculate_based_on_project_finish,
        )
        return cls(snapshot_list, boundary)

    def finish_boundary_for(self, project_id: str):
        return self.float_boundary.finish_for(project_id)
