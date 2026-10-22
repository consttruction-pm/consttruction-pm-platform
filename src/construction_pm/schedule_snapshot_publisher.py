from __future__ import annotations

"""Atomic publication of fresh repository state as immutable schedule inputs."""

from dataclasses import dataclass
from datetime import datetime, timezone as datetime_timezone
from typing import Callable
from uuid import uuid4

from .backend_p0.models import BackendScope
from .backend_p0.transactions import TransactionManager
from .schedule_calculation_context_repository import (
    CalculationContextRepository,
    PersistedCalculationContext,
    build_persisted_context,
)
from .schedule_input_snapshot_repository import (
    ScheduleInputSnapshot,
    ScheduleInputSnapshotRepository,
    build_snapshot,
)
from .scheduling.calculation_context import CalculationContext

from .authoritative_schedule_input_composer import (
    AuthoritativeScheduleInputComposer,
    ScheduleInputCompositionError,
)


class ScheduleSnapshotPublicationError(ValueError):
    """Raised when a schedule snapshot cannot be atomically published."""


@dataclass(frozen=True)
class PublishedScheduleSnapshot:
    scope: BackendScope
    snapshot_id: str
    snapshot_hash: str
    calculation_identity: str
    created_at: datetime

    @classmethod
    def from_records(
        cls,
        snapshot: ScheduleInputSnapshot,
        context: PersistedCalculationContext,
    ) -> "PublishedScheduleSnapshot":
        if snapshot.scope != context.scope or snapshot.snapshot_id != context.snapshot_id:
            raise ScheduleSnapshotPublicationError("PUBLISHED_SNAPSHOT_CONTEXT_IDENTITY_MISMATCH")
        if snapshot.calculation_identity != context.calculation_identity:
            raise ScheduleSnapshotPublicationError("PUBLISHED_SNAPSHOT_CALCULATION_IDENTITY_MISMATCH")
        return cls(
            scope=snapshot.scope,
            snapshot_id=snapshot.snapshot_id,
            snapshot_hash=snapshot.snapshot_hash,
            calculation_identity=snapshot.calculation_identity,
            created_at=snapshot.created_at,
        )


class AuthoritativeScheduleSnapshotPublisher:
    """Fresh-read, compose, persist and verify a schedule snapshot as one operation."""

    def __init__(
        self,
        *,
        composer: AuthoritativeScheduleInputComposer,
        snapshot_repository: ScheduleInputSnapshotRepository,
        calculation_context_repository: CalculationContextRepository,
        transaction_manager: TransactionManager,
        rules_version: str,
        engine_version: str,
        clock: Callable[[], datetime] | None = None,
        snapshot_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.composer = composer
        self.snapshot_repository = snapshot_repository
        self.calculation_context_repository = calculation_context_repository
        self.transaction_manager = transaction_manager
        self.rules_version = rules_version
        self.engine_version = engine_version
        self.clock = clock or (lambda: datetime.now(datetime_timezone.utc))
        self.snapshot_id_factory = snapshot_id_factory or (lambda: str(uuid4()))
        if not isinstance(rules_version, str) or not rules_version.strip():
            raise ValueError("RULES_VERSION_REQUIRED")
        if not isinstance(engine_version, str) or not engine_version.strip():
            raise ValueError("ENGINE_VERSION_REQUIRED")

    def publish(
        self,
        scope: BackendScope,
        *,
        timezone_name: str,
        actor_id: str,
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> PublishedScheduleSnapshot:
        scope.validate()
        if not isinstance(timezone_name, str) or not timezone_name.strip():
            raise ScheduleSnapshotPublicationError("CALCULATION_TIMEZONE_REQUIRED")
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise ScheduleSnapshotPublicationError("ACTOR_ID_REQUIRED")
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise ScheduleSnapshotPublicationError("PUBLICATION_CLOCK_MUST_BE_TIMEZONE_AWARE")
        snapshot_id = self.snapshot_id_factory()
        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            raise ScheduleSnapshotPublicationError("SNAPSHOT_ID_FACTORY_RETURNED_INVALID_ID")

        try:
            # Repository reads and both immutable writes share the same outer
            # transaction. SQLite adapters must not commit inside this scope.
            with self.transaction_manager.transaction():
                schedule_input = self.composer.compose(
                    scope,
                    snapshot_id=snapshot_id,
                    calculation_timezone=timezone_name,
                )
                context = CalculationContext(
                    project_id=scope.project_id,
                    project_version=scope.project_revision,
                    calendar_id=schedule_input.project_calendar.calendar_id,
                    calendar_version=schedule_input.project_calendar.calendar_version,
                    rules_version=self.rules_version,
                    engine_version=self.engine_version,
                    timezone=timezone_name,
                    calculation_timestamp=now.isoformat(),
                    input_snapshot_id=snapshot_id,
                    tenant_id=scope.tenant_id,
                    actor_id=actor_id,
                    request_id=request_id,
                    idempotency_key=idempotency_key,
                )
                snapshot = build_snapshot(schedule_input, context, now)
                self.snapshot_repository.save(snapshot)
                self.calculation_context_repository.save(
                    build_persisted_context(scope, context)
                )
        except (ScheduleInputCompositionError, ScheduleSnapshotPublicationError):
            raise
        except (TypeError, ValueError, ArithmeticError) as exc:
            raise ScheduleSnapshotPublicationError(
                f"SCHEDULE_SNAPSHOT_PUBLICATION_FAILED:{exc}"
            ) from exc

        # Fresh, post-commit reads verify that publication did not merely return
        # constructed DTOs and that snapshot/context identities agree in storage.
        try:
            saved_snapshot = self.snapshot_repository.get(scope, snapshot_id)
            if saved_snapshot is None:
                raise ScheduleSnapshotPublicationError("PUBLISHED_SNAPSHOT_NOT_READABLE")
            saved_context = self.calculation_context_repository.get(
                scope,
                snapshot_id,
                expected_calculation_identity=saved_snapshot.calculation_identity,
            )
            if saved_context is None:
                raise ScheduleSnapshotPublicationError("PUBLISHED_CONTEXT_NOT_READABLE")
            return PublishedScheduleSnapshot.from_records(saved_snapshot, saved_context)
        except (ScheduleSnapshotPublicationError, TypeError, ValueError) as exc:
            if isinstance(exc, ScheduleSnapshotPublicationError):
                raise
            raise ScheduleSnapshotPublicationError(
                f"PUBLISHED_SNAPSHOT_FRESH_READ_FAILED:{exc}"
            ) from exc


__all__ = [
    "AuthoritativeScheduleSnapshotPublisher",
    "PublishedScheduleSnapshot",
    "ScheduleSnapshotPublicationError",
]
