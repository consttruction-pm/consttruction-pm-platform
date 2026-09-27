from __future__ import annotations

import json
from dataclasses import dataclass

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationPolicy,
    Permission,
)

from .errors import BackendApplicationError, ErrorCategory, OptimisticLockError
from ..field_assurance_workflow import FieldAssuranceTransitionError, assert_transition
from .idempotency import IdempotencyStore, fingerprint
from .models import Record, record_id, resource_type
from .persistence import _record_from_payload
from .repository import BackendP0Repository, StoredRecord
from .transactions import TransactionManager


@dataclass(frozen=True)
class BackendP0ApplicationService:
    repository: BackendP0Repository
    transaction_manager: TransactionManager
    authorization_policy: AuthorizationPolicy
    idempotency_store: IdempotencyStore | None = None

    def save(
        self,
        record: Record,
        *,
        auth_context: AuthorizationContext,
        idempotency_key: str | None = None,
        expected_revision: int | None = None,
    ) -> StoredRecord:
        record.validate()
        self._authorize(record, auth_context)
        operation = f"save:{resource_type(record)}"
        fp = fingerprint({
            "operation": operation,
            "record": record.as_dict(),
            "expected_revision": expected_revision,
        })

        def mutation() -> StoredRecord:
            current = self.repository.get(
                record.scope.tenant_id,
                record.scope.project_id,
                resource_type(record),
                record_id(record),
            )
            if current is not None and expected_revision is not None and expected_revision != current.record_revision:
                raise OptimisticLockError(
                    f"Stale record revision: expected {expected_revision}, current {current.record_revision}"
                )
            if current is not None:
                assert_transition(current.record, record)
            return self.repository.save(record, expected_revision=expected_revision)

        try:
            with self.transaction_manager.transaction():
                if self.idempotency_store is None:
                    return mutation()
                return self.idempotency_store.execute(
                    record.scope.tenant_id,
                    record.scope.project_id,
                    operation,
                    idempotency_key or "",
                    fp,
                    mutation,
                    serialize=lambda stored: json.dumps(
                        {
                            "record": stored.record.as_dict(),
                            "record_revision": stored.record_revision,
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                        default=str,
                    ),
                    deserialize=self._deserialize_stored_record,
                )
        except FieldAssuranceTransitionError as exc:
            raise BackendApplicationError(
                ErrorCategory.VALIDATION, str(exc), str(exc)
            ) from exc
        except OptimisticLockError as exc:
            raise BackendApplicationError(
                ErrorCategory.CONFLICT, "STALE_REVISION", str(exc), retryable=True
            ) from exc

    def get(self, record: Record, *, auth_context: AuthorizationContext) -> StoredRecord | None:
        record.scope.validate()
        if auth_context.tenant_id != record.scope.tenant_id or auth_context.project_id != record.scope.project_id:
            raise BackendApplicationError(
                ErrorCategory.AUTHORIZATION,
                "CROSS_SCOPE_ACCESS",
                "Authorization context does not match the resource scope",
            )
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise BackendApplicationError(
                ErrorCategory.AUTHORIZATION,
                "FORBIDDEN",
                "Operation is not authorized",
            )
        return self.repository.get(
            record.scope.tenant_id,
            record.scope.project_id,
            resource_type(record),
            record_id(record),
        )

    def _authorize(self, record: Record, auth_context: AuthorizationContext) -> None:
        if auth_context.tenant_id != record.scope.tenant_id or auth_context.project_id != record.scope.project_id:
            raise BackendApplicationError(
                ErrorCategory.AUTHORIZATION,
                "CROSS_SCOPE_MUTATION",
                "Authorization context does not match the resource scope",
            )
        allowed = self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_WRITE)
        if not allowed:
            raise BackendApplicationError(
                ErrorCategory.AUTHORIZATION,
                "FORBIDDEN",
                "Operation is not authorized",
            )

    @staticmethod
    def _deserialize_stored_record(payload: str) -> StoredRecord:
        snapshot = json.loads(payload)
        return StoredRecord(
            _record_from_payload(snapshot["record"]),
            int(snapshot["record_revision"]),
        )
