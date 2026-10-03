from __future__ import annotations

"""Materialize immutable schedule snapshots into Shared Scheduling Core models."""

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from .schedule_input_snapshot_repository import ScheduleInputSnapshot
from .scheduling.activity import Activity, ActivityStatus, ActivityType, ActivityStatusCode, PercentCompleteType
from .scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from .scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
    RelationshipLagCalendar,
    SchedulingCalendarContext,
)
from .scheduling.constraints import ActivityConstraint, ConstraintType
from .scheduling.calendar_system import CalendarSystem
from .scheduling.relationships import Relationship, RelationshipType
from .scheduling.schedule import (
    CriticalActivityPathType,
    ScheduleMode,
    ScheduleOptions,
    TotalFloatCalculationType,
)
from .scheduling.schedule_options import (
    OutOfSequenceScheduleType,
    PriorityListItem,
    PrioritySortOrder,
    StartToStartLagCalculationType,
)
from .scheduling.time_constraints import TimeActivityConstraint, TimeConstraintType
from .scheduling.time_duration import DurationUnit, LagQuantity, TimeQuantity
from .scheduling.time_forward_pass import TimeActivity, TimeRelationship


class SnapshotMaterializationError(ValueError):
    """Raised when an immutable snapshot cannot be safely materialized."""


@dataclass(frozen=True)
class MaterializedScheduleInput:
    """Calculation-ready schedule input plus the resolver registry it references."""


