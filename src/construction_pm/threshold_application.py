from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .api_errors import (
    APIError,
    authorization_error,
    conflict_error,
    validation_error,
)
from .application.authorization import (
    AuthorizationContext,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_issue_repository import P6Issue
from .threshold_persistence import (
    StoredThreshold,
    Threshold,
    ThresholdAuditEvent,
    ThresholdIdempotencyReuse,
    ThresholdPersistenceError,
    ThresholdRevisionConflict,
    ThresholdRun,
    ThresholdStore,
    evaluate_threshold_level,
    threshold_number_text,
)


class ThresholdAuthorizationError(ValueError):
    pass


class ThresholdIssueWriter(Protocol):
    def __call__(
        self,
        issue: P6Issue,
        *,
        context: AuthorizationContext,
        occurred_at: str,
    ) -> str: ...


class ThresholdMetricSource(Protocol):
    def observe(
        self,
        *,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        parameter: str,
        currency: str | None = None,
    ): ...


@dataclass(frozen=True)
class MonitoringResult:
    threshold: StoredThreshold
    run: ThresholdRun


@dataclass(frozen=True)
class ThresholdApplicationService:
    """Authorization boundary and monitoring engine over stored thresholds."""

    store: ThresholdStore
    authorization_policy: AuthorizationPolicy
    transaction_manager: object
    metric_source: ThresholdMetricSource
    issue_writer: ThresholdIssueWriter

    # -- reads ------------------------------------------------------------
    def list_thresholds(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
        monitoring_subject: str | None = None,
        parameter: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[StoredThreshold, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.list_thresholds(
            tenant_id,
            project_id,
            monitoring_subject=monitoring_subject,
            parameter=parameter,
            status=status,
            search=search,
        )

    def read_threshold(
        self,
        *,
        tenant_id: str,
        project_id: str,
        threshold_id: str,
        context: AuthorizationContext,
    ) -> StoredThreshold:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.get_threshold(tenant_id, project_id, threshold_id)

    def threshold_history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        threshold_id: str,
        context: AuthorizationContext,
    ) -> tuple[ThresholdAuditEvent, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        self.store.get_threshold(tenant_id, project_id, threshold_id)
        return self.store.threshold_history(tenant_id, project_id, threshold_id)

    def runs(
        self,
        *,
        tenant_id: str,
        project_id: str,
        threshold_id: str,
        context: AuthorizationContext,
    ) -> tuple[ThresholdRun, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        self.store.get_threshold(tenant_id, project_id, threshold_id)
        return self.store.runs(tenant_id, project_id, threshold_id)

    # -- writes -----------------------------------------------------------
    def create_threshold(
        self,
        threshold: Threshold,
        *,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredThreshold:
        self._authorize_write(threshold.tenant_id, threshold.project_id, context, actor_id)
        with self.transaction_manager.transaction():
            return self.store.create_threshold(
                threshold,
                idempotency_key=idempotency_key,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def update_threshold(
        self,
        threshold: Threshold,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredThreshold:
        self._authorize_write(threshold.tenant_id, threshold.project_id, context, actor_id)
        with self.transaction_manager.transaction():
            return self.store.update_threshold(
                threshold,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def delete_threshold(
        self,
        *,
        tenant_id: str,
        project_id: str,
        threshold_id: str,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> None:
        self._authorize_write(tenant_id, project_id, context, actor_id)
        with self.transaction_manager.transaction():
            self.store.delete_threshold(
                tenant_id=tenant_id,
                project_id=project_id,
                threshold_id=threshold_id,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
                reason=reason,
            )

    def monitor(
        self,
        *,
        tenant_id: str,
        project_id: str,
        project_revision: int,
        threshold_id: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> MonitoringResult:
        """Read the authoritative metric, evaluate and append one immutable run."""
        self._authorize_write(tenant_id, project_id, context, actor_id)
        with self.transaction_manager.transaction():
            stored = self.store.get_threshold(tenant_id, project_id, threshold_id)
            threshold = stored.threshold
            if threshold.status != "active":
                raise ValueError("THRESHOLD_INACTIVE")
            previous = self.store.runs(tenant_id, project_id, threshold_id)
            previous_level = previous[-1].level if previous else "normal"
            observed = self.metric_source.observe(
                tenant_id=tenant_id,
                project_id=project_id,
                project_revision=project_revision,
                parameter=threshold.parameter,
                currency=threshold.currency,
            )
            level = evaluate_threshold_level(threshold, observed)
            sequence = self.store.next_run_sequence(tenant_id, project_id, threshold_id)
            issue_id: str | None = None
            if level == "issue" and previous_level != "issue":
                issue_id = self._raise_issue(
                    threshold,
                    observed=observed,
                    project_revision=project_revision,
                    sequence=sequence,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            run = self.store.record_run(
                ThresholdRun(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    threshold_id=threshold_id,
                    run_sequence=sequence,
                    observed_value=observed,
                    level=level,
                    currency=threshold.currency,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                    generated_issue_id=issue_id,
                )
            )
            return MonitoringResult(stored, run)

    # -- helpers ----------------------------------------------------------
    def _raise_issue(
        self,
        threshold: Threshold,
        *,
        observed,
        project_revision: int,
        sequence: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> str:
        issue_id = f"THR-{threshold.threshold_id}-R{sequence}"
        owner = threshold.responsible_manager or actor_id
        bounds = []
        if threshold.lower_threshold is not None:
            bounds.append(f"lower {threshold_number_text(threshold.lower_threshold)}")
        if threshold.upper_threshold is not None:
            bounds.append(f"upper {threshold_number_text(threshold.upper_threshold)}")
        description = (
            f"Threshold {threshold.threshold_id} ({threshold.parameter}) observed "
            f"{threshold_number_text(observed)} against {' and '.join(bounds)}; "
            f"level {evaluate_threshold_level(threshold, observed)}."
        )
        issue = P6Issue(
            scope=BackendScope(threshold.tenant_id, threshold.project_id, project_revision),
            issue_id=issue_id,
            title=f"Threshold breached: {threshold.name}",
            description=description,
            issue_type=threshold.monitoring_subject,
            status="open",
            priority="high",
            owner=owner,
            responsible_manager=threshold.responsible_manager,
            date_identified=occurred_at.date().isoformat(),
        )
        issue.validate()
        return self.issue_writer(issue, context=context, occurred_at=occurred_at.isoformat())

    def _check(
        self,
        context: AuthorizationContext,
        tenant_id: str,
        project_id: str,
        permission: Permission,
    ) -> None:
        if tenant_id != context.tenant_id or project_id != context.project_id:
            raise ThresholdAuthorizationError("THRESHOLD_CROSS_SCOPE_ACCESS")
        if not self.authorization_policy.is_allowed(context, permission):
            raise ThresholdAuthorizationError("THRESHOLD_PERMISSION_DENIED")

    def _authorize_write(
        self,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
        actor_id: str,
    ) -> None:
        if actor_id != context.user_id:
            raise ThresholdAuthorizationError("THRESHOLD_ACTOR_MISMATCH")
        self._check(context, tenant_id, project_id, Permission.PROJECT_WRITE)

    @staticmethod
    def error_dto(exc: Exception) -> APIError:
        if isinstance(exc, KeyError):
            code = str(exc.args[0]) if exc.args else "THRESHOLD_NOT_FOUND"
            return validation_error(code, code)
        if isinstance(exc, ThresholdRevisionConflict):
            return conflict_error("THRESHOLD_REVISION_CONFLICT", str(exc), retryable=True)
        if isinstance(exc, ThresholdIdempotencyReuse):
            return conflict_error("THRESHOLD_IDEMPOTENCY_KEY_REUSE", str(exc))
        if isinstance(exc, ThresholdAuthorizationError):
            return authorization_error(str(exc), str(exc))
        if isinstance(exc, ThresholdPersistenceError):
            return validation_error(str(exc), str(exc))
        if isinstance(exc, ValueError):
            code = str(exc) or type(exc).__name__
            if code.endswith("_ALREADY_EXISTS") or code == "THRESHOLD_RUN_ALREADY_RECORDED":
                return conflict_error(code, code)
            return validation_error(code, code)
        return validation_error(type(exc).__name__, str(exc))


__all__ = [
    "MonitoringResult",
    "ThresholdApplicationService",
    "ThresholdAuthorizationError",
    "ThresholdIssueWriter",
    "ThresholdMetricSource",
]
