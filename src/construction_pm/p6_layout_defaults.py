"""Canonical default column set for the Activity Table layout.

The Activities window starts from this ordered, registry-backed set when a
scope has never saved a layout. The Columns dialog's Default action restores
the same set, so the client never invents its own default layout.

Widths are presentation defaults only; they never change schedule data.
"""

from __future__ import annotations

from .p6_layout_definition_repository import LayoutColumn

DEFAULT_ACTIVITY_LAYOUT_ID = "activity"
P6_LAYOUT_DEFAULTS_VERSION = "p6-layout-defaults.v1"

_DEFAULT_ACTIVITY_COLUMNS: tuple[LayoutColumn, ...] = (
    LayoutColumn("activity.id", True, 0, "Activity ID", 120.0, "start", False, False),
    LayoutColumn("activity.name", True, 1, "Activity Name", 260.0, "start", False, False),
    LayoutColumn("activity.planned_duration", True, 2, "Original Duration", 110.0, "end", False, False),
    LayoutColumn("activity.remaining_duration", True, 3, "Remaining Duration", 110.0, "end", False, False),
    LayoutColumn("activity.duration_percent_complete", True, 4, "Schedule % Complete", 120.0, "end", False, False),
    LayoutColumn("activity.early_start", True, 5, "Start", 120.0, "center", False, False),
    LayoutColumn("activity.early_finish", True, 6, "Finish", 120.0, "center", False, False),
    LayoutColumn("activity.status", True, 7, "Status", 100.0, "start", False, False),
)


def default_activity_columns() -> tuple[LayoutColumn, ...]:
    """Return a fresh, immutable copy of the documented default columns."""

    return tuple(
        LayoutColumn(
            column.field_id,
            column.visible,
            column.order,
            column.label,
            column.width,
            column.alignment,
            column.pinned,
            column.frozen,
        )
        for column in _DEFAULT_ACTIVITY_COLUMNS
    )


def default_layout_columns(view_id: str) -> tuple[LayoutColumn, ...] | None:
    """Return the default column set for a known view, or ``None``.

    Only the Activity Table view has a documented default layout. Returning
    ``None`` lets the HTTP layer answer honestly instead of inventing defaults
    for a view that has no canonical definition.
    """

    if view_id == DEFAULT_ACTIVITY_LAYOUT_ID:
        return default_activity_columns()
    return None


__all__ = [
    "DEFAULT_ACTIVITY_LAYOUT_ID",
    "P6_LAYOUT_DEFAULTS_VERSION",
    "default_activity_columns",
    "default_layout_columns",
]
