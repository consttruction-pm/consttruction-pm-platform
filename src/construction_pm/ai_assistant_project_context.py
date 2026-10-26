"""Permission-scoped, bounded project context for the CUBI assistant.

The assistant may only answer project questions from facts that the authenticated
application layer already read for the current tenant/project/revision. This
module never derives schedule, cost, progress or EVM values itself: calculated
facts come from the Shared Core through an injected read-only provider.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Mapping, Protocol

from .activity_master_repository import ActivityMaster, ActivityMasterRepository
from .ai_action_runtime import AIActionRuntimeContext
from .application.authorization import (
    AuthorizationContext,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .relationship_master_repository import (
    RelationshipMaster,
    RelationshipMasterRepository,
)


PROJECT_CONTEXT_CONTRACT_VERSION = "ai-assistant-project-context.v1"
MAX_CONTEXT_ACTIVITIES = 50
MAX_CONTEXT_RELATIONSHIPS = 100
MAX_CONTEXT_SCHEDULE_ACTIVITIES = 50
MAX_CONTEXT_JSON_BYTES = 48_000
MAX_CONTEXT_NAME_CHARS = 200
MAX_CONTEXT_ID_CHARS = 120
_STABLE_REASON = re.compile(r"^[A-Z][A-Z0-9_]{2,79}$")

ScheduleFactsReader = Callable[
    [BackendScope, AuthorizationContext],
    Mapping[str, object] | None,
]


class AIAssistantProjectContextError(RuntimeError):
    """Safe, stable failure of a server-side project read; never contains row data."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class AIAssistantProjectContextProvider(Protocol):
    def read(self, context: AIActionRuntimeContext) -> Mapping[str, object]: ...


def _revision(scope_text: object) -> int:
    if not isinstance(scope_text, str) or not scope_text.strip():
        raise AIAssistantProjectContextError("AI_ASSISTANT_PROJECT_CONTEXT_SCOPE_INVALID")
    try:
        revision = int(scope_text, 10)
    except (TypeError, ValueError) as exc:
        raise AIAssistantProjectContextError(
            "AI_ASSISTANT_PROJECT_CONTEXT_SCOPE_INVALID"
        ) from exc
    if revision < 0 or str(revision) != scope_text:
        raise AIAssistantProjectContextError("AI_ASSISTANT_PROJECT_CONTEXT_SCOPE_INVALID")
    return revision


def _bounded_text(value: object, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)] + "…"


def _iso(value: object) -> str | None:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return None


def _json_size(value: object) -> int:
    try:
        return len(
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
    except (TypeError, ValueError) as exc:
        raise AIAssistantProjectContextError(
            "AI_ASSISTANT_PROJECT_CONTEXT_NOT_SERIALIZABLE"
        ) from exc


def _activity_row(activity: ActivityMaster) -> dict[str, object]:
    return {
        "activity_id": _bounded_text(activity.activity_id, MAX_CONTEXT_ID_CHARS),
        "name": _bounded_text(activity.name, MAX_CONTEXT_NAME_CHARS),
        "duration": {
            "value": str(activity.duration_value),
            "unit": activity.duration_unit.value,
        },
        "activity_type": activity.activity_type.value,
        "status": activity.status.value,
        "status_code": activity.status_code.value,
        "percent_complete_type": activity.percent_complete_type.value,
        "percent_complete": activity.percent_complete,
        "leveling_priority": activity.leveling_priority.value,
        "record_revision": activity.record_revision,
        "planned_finish": _iso(activity.planned_finish),
        "expected_finish": _iso(activity.expected_finish),
        "actual_start": _iso(activity.actual_start),
        "actual_finish": _iso(activity.actual_finish),
    }


def _relationship_row(relationship: RelationshipMaster) -> dict[str, object]:
    return {
        "relationship_id": _bounded_text(
            relationship.relationship_id, MAX_CONTEXT_ID_CHARS
        ),
        "predecessor_id": _bounded_text(
            relationship.predecessor_id, MAX_CONTEXT_ID_CHARS
        ),
        "successor_id": _bounded_text(
            relationship.successor_id, MAX_CONTEXT_ID_CHARS
        ),
        "type": relationship.relationship_type.value,
        "lag": {
            "value": str(relationship.lag_value),
            "unit": relationship.lag_unit.value,
        },
        "record_revision": relationship.record_revision,
    }


def _safe_reason_code(exc: Exception) -> str:
    text = str(exc).strip()
    return text if _STABLE_REASON.fullmatch(text) else "SCHEDULE_CALCULATION_UNAVAILABLE"


@dataclass(frozen=True)
class PersistedProjectAssistantContextProvider:
    """Read the current revision's persisted facts and Shared Core projection.

    ``activity_repository`` and ``relationship_repository`` are the same
    authoritative repositories used by the project screens. ``schedule_facts``
    must be the read-only Shared Core adapter; this class never calculates.
    """

    activity_repository: ActivityMasterRepository
    authorization_policy: AuthorizationPolicy
    relationship_repository: RelationshipMasterRepository | None = None
    schedule_facts: ScheduleFactsReader | None = None

    def read(self, context: AIActionRuntimeContext) -> Mapping[str, object]:
        context.validate()
        revision = _revision(context.project_revision_id)
        auth = AuthorizationContext(
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            user_id=context.subject_id,
            roles=context.roles,
        )
        try:
            auth.validate()
            allowed = self.authorization_policy.is_allowed(auth, Permission.PROJECT_READ)
        except Exception as exc:
            raise AIAssistantProjectContextError(
                "AI_ASSISTANT_PROJECT_CONTEXT_NOT_AUTHORIZED"
            ) from exc
        if not allowed:
            raise AIAssistantProjectContextError(
                "AI_ASSISTANT_PROJECT_CONTEXT_NOT_AUTHORIZED"
            )

        scope = BackendScope(context.tenant_id, context.project_id, revision)
        try:
            activities = tuple(self.activity_repository.list(scope))
            relationships = (
                ()
                if self.relationship_repository is None
                else tuple(self.relationship_repository.list(scope))
            )
        except AIAssistantProjectContextError:
            raise
        except Exception as exc:
            raise AIAssistantProjectContextError(
                "AI_ASSISTANT_PROJECT_CONTEXT_UNAVAILABLE"
            ) from exc

        ordered_activities = sorted(
            activities, key=lambda item: (item.activity_id, item.record_revision)
        )
        ordered_relationships = sorted(
            relationships, key=lambda item: item.relationship_id
        )
        activity_items = [
            _activity_row(item)
            for item in ordered_activities[:MAX_CONTEXT_ACTIVITIES]
        ]
        relationship_items = [
            _relationship_row(item)
            for item in ordered_relationships[:MAX_CONTEXT_RELATIONSHIPS]
        ]
        payload: dict[str, object] = {
            "contract_version": PROJECT_CONTEXT_CONTRACT_VERSION,
            "project_id": context.project_id,
            "project_revision": revision,
            "activities": {
                "total": len(ordered_activities),
                "returned": len(activity_items),
                "truncated": len(ordered_activities) > len(activity_items),
                "items": activity_items,
            },
            "relationships": {
                "source_available": self.relationship_repository is not None,
                "total": len(ordered_relationships),
                "returned": len(relationship_items),
                "truncated": len(ordered_relationships) > len(relationship_items),
                "items": relationship_items,
            },
            "schedule_calculation": self._schedule_calculation(scope, auth),
        }
        self._fit_budget(payload)
        return payload

    def _schedule_calculation(
        self, scope: BackendScope, auth: AuthorizationContext
    ) -> dict[str, object]:
        if self.schedule_facts is None:
            return {
                "available": False,
                "reason_code": "SCHEDULE_FACTS_NOT_CONFIGURED",
            }
        try:
            facts = self.schedule_facts(scope, auth)
        except AIAssistantProjectContextError:
            raise
        except Exception as exc:
            return {"available": False, "reason_code": _safe_reason_code(exc)}
        if facts is None:
            return {
                "available": False,
                "reason_code": "NO_PUBLISHED_SCHEDULE_SNAPSHOT",
            }
        if not isinstance(facts, Mapping):
            return {
                "available": False,
                "reason_code": "SCHEDULE_CALCULATION_UNAVAILABLE",
            }
        raw_activities = facts.get("activities")
        rows: list[dict[str, object]] = []
        if isinstance(raw_activities, Mapping):
            ordered = sorted(raw_activities)
            for activity_id in ordered[:MAX_CONTEXT_SCHEDULE_ACTIVITIES]:
                fact = raw_activities[activity_id]
                if not isinstance(fact, Mapping):
                    continue
                row: dict[str, object] = {
                    "activity_id": _bounded_text(activity_id, MAX_CONTEXT_ID_CHARS)
                }
                for key in (
                    "start",
                    "finish",
                    "duration",
                    "critical",
                    "early_start",
                    "early_finish",
                    "late_start",
                    "late_finish",
                    "total_float",
                    "free_float",
                ):
                    value = fact.get(key)
                    if isinstance(value, (str, int, float, bool)) or value is None:
                        row[key] = value
                rows.append(row)
            total = len(ordered)
        else:
            total = 0
        project_finish = facts.get("project_finish")
        calculation_identity = facts.get("calculation_run_identity")
        activity_count = facts.get("activity_count")
        return {
            "available": True,
            "project_finish": project_finish if isinstance(project_finish, str) else None,
            "calculation_run_identity": (
                calculation_identity if isinstance(calculation_identity, str) else None
            ),
            "total_activities": (
                activity_count
                if isinstance(activity_count, int) and not isinstance(activity_count, bool)
                else total
            ),
            "returned": len(rows),
            "truncated": total > len(rows),
            "activities": rows,
        }

    @staticmethod
    def _fit_budget(payload: dict[str, object]) -> None:
        """Deterministically trim context to its byte budget and disclose truncation."""

        def items_block(key: str) -> dict[str, object]:
            block = payload[key]
            if not isinstance(block, dict):  # pragma: no cover - internal invariant
                raise AIAssistantProjectContextError(
                    "AI_ASSISTANT_PROJECT_CONTEXT_INVALID"
                )
            return block

        for key in ("activities", "relationships"):
            block = items_block(key)
            items = block.get("items")
            if not isinstance(items, list):  # pragma: no cover - internal invariant
                raise AIAssistantProjectContextError(
                    "AI_ASSISTANT_PROJECT_CONTEXT_INVALID"
                )
            while _json_size(payload) > MAX_CONTEXT_JSON_BYTES and items:
                items.pop()
                block["returned"] = len(items)
                block["truncated"] = True

        schedule = payload.get("schedule_calculation")
        if isinstance(schedule, dict):
            rows = schedule.get("activities")
            if isinstance(rows, list):
                while _json_size(payload) > MAX_CONTEXT_JSON_BYTES and rows:
                    rows.pop()
                    schedule["returned"] = len(rows)
                    schedule["truncated"] = True
        if _json_size(payload) > MAX_CONTEXT_JSON_BYTES:
            # The fixed envelope is small; this protects against pathological
            # project identifiers while still failing closed.
            raise AIAssistantProjectContextError(
                "AI_ASSISTANT_PROJECT_CONTEXT_TOO_LARGE"
            )


__all__ = [
    "AIAssistantProjectContextError",
    "AIAssistantProjectContextProvider",
    "PersistedProjectAssistantContextProvider",
    "PROJECT_CONTEXT_CONTRACT_VERSION",
    "MAX_CONTEXT_ACTIVITIES",
    "MAX_CONTEXT_RELATIONSHIPS",
    "MAX_CONTEXT_SCHEDULE_ACTIVITIES",
    "MAX_CONTEXT_JSON_BYTES",
]
