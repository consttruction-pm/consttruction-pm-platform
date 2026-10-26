from __future__ import annotations

"""Latest immutable snapshot -> Shared Core FACT projection for workspace reads."""

from dataclasses import dataclass
from typing import Mapping

from construction_pm.application.authorization import AuthorizationContext
from construction_pm.control_intelligence.contracts import ControlScope
from construction_pm.control_intelligence.query import ScheduleQueryKind, ScheduleQueryRequest
from construction_pm.schedule_input_snapshot_repository import ScheduleInputSnapshotRepository

from .authoritative_schedule_query import AuthoritativeScheduleQueryProvider
from .models import BackendScope


@dataclass(frozen=True)
class PublishedScheduleFactsProvider:
    """Resolve the newest published snapshot and evaluate it through Shared Core.

    No caller-supplied snapshot id or client-side calculation participates in
    reading the workspace. The selected snapshot is immutable and scoped by
    tenant/project/revision.
    """

    snapshot_repository: ScheduleInputSnapshotRepository
    query_provider: AuthoritativeScheduleQueryProvider

    def latest_snapshot_id(self, scope: BackendScope) -> str | None:
        snapshots = self.snapshot_repository.list(scope)
        if not snapshots:
            return None
        latest = max(
            snapshots,
            key=lambda item: (str(item.created_at), item.snapshot_id),
        )
        return latest.snapshot_id

    def __call__(
        self,
        scope: BackendScope,
        auth_context: AuthorizationContext | None,
    ) -> Mapping[str, object] | None:
        snapshot_id = self.latest_snapshot_id(scope)
        if snapshot_id is None:
            return None
        request = ScheduleQueryRequest(
            query_id=f"workspace-read:{snapshot_id}",
            scope=ControlScope(scope.tenant_id, scope.project_id, scope.project_revision),
            requested_by=(
                auth_context.user_id if auth_context is not None else "system-workspace-read"
            ),
            query_text="workspace read calculated schedule facts",
            kind=ScheduleQueryKind.FACT,
            language="en",
            constraints={"snapshot_id": snapshot_id},
        )
        answer = self.query_provider.execute(request, auth_context=auth_context)
        return answer.data


__all__ = ["PublishedScheduleFactsProvider"]
