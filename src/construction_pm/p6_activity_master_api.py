from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import uuid4

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .activity_master_repository import ActivityMaster, ActivityMasterRepository, ActivityPersistenceError
from .backend_p0.models import BackendScope
from .project_checkout import (
    ProjectCheckoutLease,
    require_project_write_ownership,
)
from .relationship_master_repository import RelationshipMaster
from .scheduling.activity import (
    ActivityDurationType,
    ActivityLevelingPriority,
    ActivityStatus,
    ActivityStatusCode,
    ActivityType,
    PercentCompleteType,
)
from .scheduling.relationships import RelationshipType
from .scheduling.time_duration import DurationUnit


P6_ACTIVITY_MASTER_API_VERSION = "p6-activity-master-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _optional_iso(value: date | datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


def _dto(item: ActivityMaster) -> dict[str, Any]:
    return {
        "contract_version": P6_ACTIVITY_MASTER_API_VERSION,
        "kind": "p6_activity_master",
        "scope": _scope_dto(item.scope),
        "activity": {
            "activity_id": item.activity_id,
            "name": item.name,
            "short_name": item.short_name,
            "activity_type": item.activity_type.value,
            "status": item.status.value,
            "status_code": item.status_code.value,
            "duration_value": str(item.duration_value),
            "duration_unit": item.duration_unit.value,
            "duration_type": item.duration_type.value,
            "cost_account_id": item.cost_account_id,
            "actual_start": _optional_iso(item.actual_start),
            "actual_finish": _optional_iso(item.actual_finish),
            "remaining_duration": item.remaining_duration,
            "remaining_start": _optional_iso(item.remaining_start),
            "percent_complete": item.percent_complete,
            "percent_complete_type": item.percent_complete_type.value,
            "expected_finish": _optional_iso(item.expected_finish),
            "planned_finish": _optional_iso(item.planned_finish),
            "leveling_priority": item.leveling_priority.value,
            "original_duration": item.original_duration,
            "wbs_id": item.wbs_id,
            "record_revision": item.record_revision,
        },
    }


class _RelationshipStore(Protocol):
    def list(self, scope: BackendScope) -> tuple[Any, ...]: ...
    def save(self, relationship: Any, expected_revision: int | None = None) -> Any: ...
    def delete(self, scope: BackendScope, relationship_id: str, *, expected_revision: int) -> bool: ...


class _AssignmentStore(Protocol):
    def list(self, scope: BackendScope, activity_id: str | None = None, resource_id: str | None = None) -> tuple[Any, ...]: ...


class _ChildrenStore(Protocol):
    def list_codes(self, scope: BackendScope, activity_id: str) -> tuple[Any, ...]: ...
    def list_topics(self, scope: BackendScope, activity_id: str) -> tuple[Any, ...]: ...


class _StepStore(Protocol):
    def list(self, scope: BackendScope, activity_id: str | None = None) -> tuple[Any, ...]: ...


class _DocumentStore(Protocol):
    def list_all(self, *, tenant_id: str | None = None, project_id: str | None = None) -> tuple[Any, ...]: ...


@dataclass(frozen=True)
class P6ActivityMasterAPI:
    """Authenticated application boundary over authoritative Activity Master persistence."""

    repository: ActivityMasterRepository
    authorization_policy: AuthorizationPolicy
    checkout_lease: ProjectCheckoutLease | None = None
    relationship_repository: _RelationshipStore | None = None
    assignment_repository: _AssignmentStore | None = None
    children_repository: _ChildrenStore | None = None
    step_repository: _StepStore | None = None
    document_store: _DocumentStore | None = None

    def create(
        self,
        activity: ActivityMaster,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(activity.scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
            raise AuthorizationError("authorization denied for permission=project.write")
        require_project_write_ownership(self.checkout_lease, activity.scope, auth_context)
        return _dto(self.repository.save(activity, expected_revision=0))

    def update(
        self,
        activity: ActivityMaster,
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(activity.scope, auth_context)
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 1
        ):
            raise ValueError("EXPECTED_REVISION_REQUIRED")
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
            raise AuthorizationError("authorization denied for permission=project.write")
        require_project_write_ownership(self.checkout_lease, activity.scope, auth_context)
        return _dto(self.repository.save(activity, expected_revision=expected_revision))

    def renumber(
        self,
        scope: BackendScope,
        entries: tuple[tuple[str, str, int], ...],
        *,
        renumber_baselines: bool,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        """Renumber activity IDs in one project, preserving every reference.

        Reference: P6 Professional Help G57535-02, "Renumber activity IDs in
        the Activity Table" and "Renumber Activity IDs dialog box". Baselines
        are renumbered only when the operator leaves the checkbox marked; when
        cleared, the renamed activities are disconnected from the baseline,
        exactly as the reference describes.
        """
        self._require_write(scope, auth_context)
        if not isinstance(renumber_baselines, bool):
            raise ActivityPersistenceError("INVALID_RENUMBER_BASELINES")
        result = self.repository.renumber(
            scope, entries, include_baselines=renumber_baselines
        )
        return {
            "contract_version": P6_ACTIVITY_MASTER_API_VERSION,
            "kind": "p6_activity_renumber",
            "scope": _scope_dto(scope),
            **result,
        }

    def get(
        self,
        scope: BackendScope,
        activity_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("authorization denied for permission=project.read")
        item = self.repository.get(scope, activity_id)
        return None if item is None else _dto(item)

    def list(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("authorization denied for permission=project.read")
        return tuple(_dto(item) for item in self.repository.list(scope))

    def _require_write(self, scope: BackendScope, auth_context: AuthorizationContext) -> None:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
            raise AuthorizationError("authorization denied for permission=project.write")
        require_project_write_ownership(self.checkout_lease, scope, auth_context)

    def _dependent_records(self, scope: BackendScope, activity_id: str) -> list[str]:
        """Names of child records that would be orphaned by removing the activity."""
        found: list[str] = []
        if self.children_repository is not None:
            if self.children_repository.list_codes(scope, activity_id):
                found.append("CODES")
            if self.children_repository.list_topics(scope, activity_id):
                found.append("NOTEBOOK")
        if self.step_repository is not None and self.step_repository.list(scope, activity_id):
            found.append("STEPS")
        if self.assignment_repository is not None and self.assignment_repository.list(scope, activity_id=activity_id):
            found.append("RESOURCE_ASSIGNMENTS")
        if self.document_store is not None:
            for stored in self.document_store.list_all(tenant_id=scope.tenant_id, project_id=scope.project_id):
                document = getattr(stored, "document", stored)
                refs = tuple(getattr(document, "linked_entity_refs", ()) or ())
                if activity_id in refs:
                    found.append("DOCUMENTS")
                    break
        return found

    def delete(
        self,
        scope: BackendScope,
        activity_id: str,
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        """Delete an activity only when no child record or logic would be orphaned."""
        self._require_write(scope, auth_context)
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise ActivityPersistenceError("INVALID_EXPECTED_REVISION")
        existing = self.repository.get(scope, activity_id)
        if existing is None:
            raise ActivityPersistenceError("ACTIVITY_NOT_FOUND")
        if existing.record_revision != expected_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        if self.relationship_repository is not None:
            linked = [
                item for item in self.relationship_repository.list(scope)
                if item.predecessor_id == activity_id or item.successor_id == activity_id
            ]
            if linked:
                raise ActivityPersistenceError("ACTIVITY_HAS_RELATIONSHIPS")
        dependent = self._dependent_records(scope, activity_id)
        if dependent:
            raise ActivityPersistenceError("ACTIVITY_HAS_CHILD_RECORDS:" + ",".join(dependent))
        deleted = self.repository.delete(scope, activity_id, expected_revision=expected_revision)
        return {
            "contract_version": P6_ACTIVITY_MASTER_API_VERSION,
            "kind": "p6_activity_master_delete",
            "scope": _scope_dto(scope),
            "activity_id": activity_id,
            "deleted": deleted,
        }

    def dissolve(
        self,
        scope: BackendScope,
        activity_id: str,
        *,
        expected_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        """Remove an activity while joining each predecessor to each successor.

        Reference: P6 Professional Help G57535-02, "Dissolve an activity":
        the predecessor's side of its link supplies the new relationship's first
        half and the successor's side supplies the second half. Lag is not
        carried; P6's optional "Retain lag" preference is not modelled here.
        """
        self._require_write(scope, auth_context)
        if self.relationship_repository is None:
            raise ActivityPersistenceError("DISSOLVE_UNAVAILABLE")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise ActivityPersistenceError("INVALID_EXPECTED_REVISION")
        existing = self.repository.get(scope, activity_id)
        if existing is None:
            raise ActivityPersistenceError("ACTIVITY_NOT_FOUND")
        if existing.record_revision != expected_revision:
            raise ActivityPersistenceError("REVISION_CONFLICT")
        dependent = self._dependent_records(scope, activity_id)
        if dependent:
            raise ActivityPersistenceError("DISSOLVE_ACTIVITY_HAS_CHILD_RECORDS:" + ",".join(dependent))
        relationships = tuple(self.relationship_repository.list(scope))
        predecessors = [item for item in relationships if item.successor_id == activity_id]
        successors = [item for item in relationships if item.predecessor_id == activity_id]
        if not predecessors or not successors:
            raise ActivityPersistenceError("DISSOLVE_REQUIRES_PREDECESSOR_AND_SUCCESSOR")
        existing_pairs = {(item.predecessor_id, item.successor_id) for item in relationships}
        created: list[dict[str, str]] = []
        for predecessor in predecessors:
            for successor in successors:
                if predecessor.predecessor_id == successor.successor_id:
                    continue
                if (predecessor.predecessor_id, successor.successor_id) in existing_pairs:
                    continue
                relationship_type = RelationshipType(
                    predecessor.relationship_type.value[0] + successor.relationship_type.value[1]
                )
                saved = self.relationship_repository.save(
                    RelationshipMaster(
                        scope=scope,
                        relationship_id=f"REL-DISSOLVE-{uuid4().hex[:16].upper()}",
                        predecessor_id=predecessor.predecessor_id,
                        successor_id=successor.successor_id,
                        relationship_type=relationship_type,
                        lag_value=Decimal("0"),
                        lag_unit=DurationUnit.WORKING_DAY,
                    ),
                    expected_revision=0,
                )
                created.append({
                    "relationship_id": saved.relationship_id,
                    "predecessor_id": saved.predecessor_id,
                    "successor_id": saved.successor_id,
                    "relationship_type": saved.relationship_type.value,
                })
                existing_pairs.add((saved.predecessor_id, saved.successor_id))
        removed: list[str] = []
        for item in [*predecessors, *successors]:
            self.relationship_repository.delete(scope, item.relationship_id, expected_revision=item.record_revision)
            removed.append(item.relationship_id)
        deleted = self.repository.delete(scope, activity_id, expected_revision=expected_revision)
        return {
            "contract_version": P6_ACTIVITY_MASTER_API_VERSION,
            "kind": "p6_activity_dissolve",
            "scope": _scope_dto(scope),
            "activity_id": activity_id,
            "deleted": deleted,
            "created_relationships": created,
            "removed_relationship_ids": removed,
        }


__all__ = ["P6_ACTIVITY_MASTER_API_VERSION", "P6ActivityMasterAPI"]
