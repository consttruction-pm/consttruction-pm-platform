from __future__ import annotations

from dataclasses import dataclass

from .authorization import AllowAllAuthorizationPolicy, AuthorizationPolicy
from .context import ProjectContext
from .errors import (
    ApplicationError,
    context_error,
    not_found_error,
    validation_error,
)
from .persistence import OptimisticLockError
from .idempotency import (
    MutationIdempotencyStore,
    assignment_fingerprint,
    resource_fingerprint,
)
from .models import Resource, ResourceAssignment
from .repository import ResourceRepository
from .transactions import TransactionManager
from .validation import validate_assignment, validate_resource


def _raise_if_invalid(errors: list[str]) -> None:
    if errors:
        raise validation_error("INVALID_INPUT", ";".join(errors))


@dataclass(frozen=True)
class ResourceApplicationService:
    repository: ResourceRepository
    context: ProjectContext
    transaction_manager: TransactionManager
    idempotency_store: MutationIdempotencyStore | None = None
    authorization_policy: AuthorizationPolicy | None = None

    def register_resource(
        self,
        resource: Resource,
        idempotency_key: str | None = None,
        expected_revision: int | None = None,
    ) -> Resource:
        try:
            self.context.validate()
        except ValueError as exc:
            raise context_error("INVALID_PROJECT_CONTEXT", str(exc)) from exc
        _raise_if_invalid(validate_resource(resource))
        (self.authorization_policy or AllowAllAuthorizationPolicy()).authorize(
            self.context, "register_resource"
        )

        def mutation() -> Resource:
            with self.transaction_manager.transaction():
                return self.repository.save_resource(self.context, resource, expected_revision)

        if self.idempotency_store is None:
            try:
                return mutation()
            except OptimisticLockError as exc:
                raise conflict_error("STALE_REVISION", str(exc)) from exc
        return self.idempotency_store.execute(
            self.context,
            key=idempotency_key or "",
            operation="register_resource",
            fingerprint=resource_fingerprint(resource),
            mutation=mutation,
            replay=lambda: self.repository.get_resource(self.context, resource.id) or resource,
        )

    def assign_resource(
        self,
        assignment: ResourceAssignment,
        idempotency_key: str | None = None,
        expected_revision: int | None = None,
    ) -> ResourceAssignment:
        try:
            self.context.validate()
        except ValueError as exc:
            raise context_error("INVALID_PROJECT_CONTEXT", str(exc)) from exc
        _raise_if_invalid(validate_assignment(assignment))
        (self.authorization_policy or AllowAllAuthorizationPolicy()).authorize(
            self.context, "assign_resource"
        )

        def mutation() -> ResourceAssignment:
            with self.transaction_manager.transaction():
                if self.repository.get_resource(self.context, assignment.resource_id) is None:
                    raise not_found_error(
                        "RESOURCE_NOT_FOUND",
                        f"Unknown resource: {assignment.resource_id}",
                    )
                return self.repository.save_assignment(self.context, assignment, expected_revision)

        if self.idempotency_store is None:
            try:
                return mutation()
            except OptimisticLockError as exc:
                raise conflict_error("STALE_REVISION", str(exc)) from exc
        return self.idempotency_store.execute(
            self.context,
            key=idempotency_key or "",
            operation="assign_resource",
            fingerprint=assignment_fingerprint(assignment),
            mutation=mutation,
            replay=lambda: next(
                (
                    item
                    for item in self.repository.list_assignments(self.context, assignment.activity_id)
                    if item.resource_id == assignment.resource_id
                ),
                assignment,
            ),
        )

    def get_resource(self, resource_id: str) -> Resource | None:
        return self.repository.get_resource(self.context, resource_id)

    def list_assignments(self, activity_id: str | None = None) -> list[ResourceAssignment]:
        return self.repository.list_assignments(self.context, activity_id)
