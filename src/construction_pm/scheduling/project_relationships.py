from __future__ import annotations

from typing import Iterable, Mapping

from .relationships import Relationship


class ExternalProjectRelationshipError(ValueError):
    """Raised when multi-project relationship semantics are not safely resolvable."""


def resolve_project_relationships(
    relationships: Iterable[Relationship],
    *,
    activity_project_ids: Mapping[str, str],
    scheduled_project_id: str,
    ignore_other_project_relationships: bool,
) -> tuple[Relationship, ...]:
    """Resolve relationships at the P6 multi-project scheduling boundary.

    Cross-project relationships are ignored only when the P6 option is enabled.
    Missing endpoint project identity is rejected rather than guessed.
    """
    if not isinstance(activity_project_ids, Mapping):
        raise ExternalProjectRelationshipError("INVALID_ACTIVITY_PROJECT_MAP")
    if not isinstance(scheduled_project_id, str) or not scheduled_project_id.strip():
        raise ExternalProjectRelationshipError("INVALID_SCHEDULED_PROJECT_ID")
    if not isinstance(ignore_other_project_relationships, bool):
        raise ExternalProjectRelationshipError(
            "INVALID_IGNORE_OTHER_PROJECT_RELATIONSHIPS"
        )

    resolved: list[Relationship] = []
    for relationship in relationships:
        predecessor_project = activity_project_ids.get(relationship.predecessor_id)
        successor_project = activity_project_ids.get(relationship.successor_id)
        if predecessor_project is None or successor_project is None:
            raise ExternalProjectRelationshipError(
                "MISSING_PROJECT_ID_FOR_RELATIONSHIP_ENDPOINT"
            )
        is_external = predecessor_project != successor_project
        if is_external and ignore_other_project_relationships:
            continue
        if predecessor_project != scheduled_project_id and successor_project != scheduled_project_id:
            continue
        resolved.append(relationship)

    return tuple(resolved)
