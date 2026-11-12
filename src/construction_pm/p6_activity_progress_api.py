from __future__ import annotations

"""Authenticated application boundary for progress updates and their history.

``P6ActivityProgressAPI`` owns the write path used by the Progress window: it
delegates the Activity Master save to ``P6ActivityMasterAPI`` (the single
authoritative write boundary) and appends an immutable progress event in the
same transaction. The read path exposes the stored events and the
out-of-sequence review captured with each event.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from .activity_master_repository import ActivityMaster, ActivityMasterRepository
from .activity_progress_history import (
    ActivityProgressEvent,
    ActivityProgressHistoryRepository,
    diff_progress_fields,
    evaluate_out_of_sequence,
)
from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .backend_p0.transactions import TransactionManager
from .p6_activity_master_api import P6ActivityMasterAPI
from .relationship_master_repository import RelationshipMasterRepository


P6_ACTIVITY_PROGRESS_HISTORY_API_VERSION = "p6-activity-progress-history-api.v1"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_permission(
    policy: AuthorizationPolicy,
    auth_context: AuthorizationContext,
    permission: Permission,
) -> None:
    if not policy.is_allowed(auth_context, permission):
        raise AuthorizationError(f"authorization denied for permission={permission.value}")


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


def _event_dto(event: ActivityProgressEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "activity_id": event.activity_id,
        "recorded_at": event.recorded_at.isoformat(),
        "actor_user_id": event.actor_user_id,
        "from_record_revision": event.from_record_revision,
        "to_record_revision": event.to_record_revision,
        "changes": [
            {"field": change.field, "before": change.before, "after": change.after}
            for change in event.changes
        ],
        "out_of_sequence": {
            "is_out_of_sequence": event.out_of_sequence,
            "findings": [finding.as_json() for finding in event.findings],
        },
    }


@dataclass(frozen=True)
class P6ActivityProgressAPI:
    """Progress writes with append-only history and an out-of-sequence review."""

    activity_api: P6ActivityMasterAPI
    history_repository: ActivityProgressHistoryRepository
    authorization_policy: AuthorizationPolicy
    relationship_repository: RelationshipMasterRepository | None = None
    activity_repository: ActivityMasterRepository | None = None
    transaction_manager: TransactionManager | None = None
    clock: Callable[[], datetime] = _utcnow

    def update(
        self,
        activity: ActivityMaster,
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        """Save progress and append the history event in one transaction."""
        _require_scope(activity.scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        repository = self._activity_repository()
        if self.transaction_manager is None:
            return self._update_and_record(activity, expected_revision, auth_context, repository)
        with self.transaction_manager.transaction():
            return self._update_and_record(
                activity, expected_revision, auth_context, repository
            )

    def _update_and_record(
        self,
        activity: ActivityMaster,
        expected_revision: int,
        auth_context: AuthorizationContext,
        repository: ActivityMasterRepository,
    ) -> dict[str, Any]:
        previous = repository.get(activity.scope, activity.activity_id)
        result = self.activity_api.update(
            activity, expected_revision=expected_revision, auth_context=auth_context
        )
        if previous is not None:
            current = repository.get(activity.scope, activity.activity_id)
            if current is not None:
                self.record_change(previous, current, actor_user_id=auth_context.user_id)
        return result

    def record_change(
        self,
        previous: ActivityMaster,
        current: ActivityMaster,
        *,
        actor_user_id: str,
    ) -> ActivityProgressEvent | None:
        """Append one immutable event for the progress fields that changed."""
        changes = diff_progress_fields(previous, current)
        if not changes:
            return None
        findings = ()
        if self.relationship_repository is not None and self.activity_repository is not None:
            scope = current.scope
            findings = evaluate_out_of_sequence(
                current,
                self.relationship_repository.list(scope),
                self.activity_repository.list(scope),
            )
        event = ActivityProgressEvent(
            scope=current.scope,
            event_id=f"{current.activity_id}@{current.record_revision}",
            activity_id=current.activity_id,
            recorded_at=self.clock(),
            actor_user_id=actor_user_id,
            from_record_revision=previous.record_revision,
            to_record_revision=current.record_revision,
            changes=changes,
            findings=findings,
        )
        return self.history_repository.append(event)

    def history(
        self,
        scope: BackendScope,
        activity_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        """Read the stored progress events for one activity."""
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        if self.activity_repository is not None:
            if self.activity_repository.get(scope, activity_id) is None:
                return None
        events = self.history_repository.list(scope, activity_id)
        latest = events[-1] if events else None
        return {
            "contract_version": P6_ACTIVITY_PROGRESS_HISTORY_API_VERSION,
            "kind": "p6_activity_progress_history",
            "scope": _scope_dto(scope),
            "activity_id": activity_id,
            "events": [_event_dto(event) for event in events],
            "percent_complete_trend": _percent_trend(events),
            "out_of_sequence_review": _review_dto(latest),
        }

    def _activity_repository(self) -> ActivityMasterRepository:
        if self.activity_repository is not None:
            return self.activity_repository
        return self.activity_api.repository


def _percent_trend(
    events: tuple[ActivityProgressEvent, ...],
) -> list[dict[str, Any]]:
    """Percent-complete points read from the persisted events, oldest first."""
    points: list[dict[str, Any]] = []
    for event in events:
        change = next(
            (item for item in event.changes if item.field == "percent_complete"), None
        )
        if change is None:
            continue
        points.append(
            {
                "to_record_revision": event.to_record_revision,
                "recorded_at": event.recorded_at.isoformat(),
                "percent_complete": change.after,
            }
        )
    return points


def _review_dto(event: ActivityProgressEvent | None) -> dict[str, Any] | None:
    if event is None:
        return None
    return {
        "evaluated_event_id": event.event_id,
        "evaluated_at": event.recorded_at.isoformat(),
        "is_out_of_sequence": event.out_of_sequence,
        "findings": [finding.as_json() for finding in event.findings],
    }


__all__ = [
    "P6_ACTIVITY_PROGRESS_HISTORY_API_VERSION",
    "P6ActivityProgressAPI",
]
