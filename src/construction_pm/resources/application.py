from __future__ import annotations

from dataclasses import dataclass

from .context import ProjectContext
from .errors import (
    ApplicationError,
    context_error,
    not_found_error,
    validation_error,
)
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

    def register_resource(
        self, resource: Resource, idempotency_key: str | None = None
    ) -> Resource:
        try:
            self.context.validate()
        except ValueError as exc:
            raise context_error("INVALID_PROJECT_CONTEXT", str(exc)) from exc
        _raise_if_invalid(validate_resource(resource))

        def mutation() -> Resource:
            with self.transaction_manager.transaction():
                return self.repository.save_resource(self.context, resource)

        if self.idempotency_store is None:
            return mutation()
        return self.idempotency_store.execute(
            self.context,
            key=idempotency_key or "",
            operation="register_resource",
            fingerprint=resource_fingerprint(resource),
            mutation=mutation,
        )

    def assign_resource(
        self, assignment: ResourceAssignment, idempotency_key: str | None = None
    ) -> ResourceAssignment:
        try:
            self.context.validate()
        except ValueError as exc:
            raise context_error("INVALID_PROJECT_CONTEXT", str(exc)) from exc
        _raise_if_invalid(validate_assignment(assignment))

        def mutation() -> ResourceAssignment:
            with self.transaction_manager.transaction():
                if self.repository.get_resource(self.context, assignment.resource_id) is None:
                    raise not_found_error(
                        "RESOURCE_NOT_FOUND",
                        f"Unknown resource: {assignment.resource_id}",
                    )
                return self.repository.save_assignment(self.context, assignment)

        if self.idempotency_store is None:
            return mutation()
        return self.idempotency_store.execute(
            self.context,
            key=idempotency_key or "",
            operation="assign_resource",
            fingerprint=assignment_fingerprint(assignment),
            mutation=mutation,
        )

    def get_resource(self, resource_id: str) -> Resource | None:
        return self.repository.get_resource(self.context, resource_id)

    def list_assignments(self, activity_id: str | None = None) -> list[ResourceAssignment]:
        return self.repository.list_assignments(self.context, activity_id)
