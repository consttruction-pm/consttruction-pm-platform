from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Tuple

from .contracts import ControlScope, ProposedAction, SourceReference, require_enum


class ScheduleQueryKind(str, Enum):
    FACT = "fact"
    EXPLANATION = "explanation"
    FILTER = "filter"
    SCENARIO = "scenario"


@dataclass(frozen=True)
class ScheduleQueryRequest:
    query_id: str
    scope: ControlScope
    requested_by: str
    query_text: str
    kind: ScheduleQueryKind = ScheduleQueryKind.FACT
    language: str = "en"
    constraints: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.query_id, str) or not self.query_id.strip() or not isinstance(self.requested_by, str) or not self.requested_by.strip() or not isinstance(self.query_text, str) or not self.query_text.strip():
            raise ValueError("INVALID_SCHEDULE_QUERY")
        if not isinstance(self.scope, ControlScope):
            raise ValueError("INVALID_SCHEDULE_QUERY_SCOPE")
        require_enum(self.kind, ScheduleQueryKind, "INVALID_SCHEDULE_QUERY_KIND")
        if not isinstance(self.language, str) or not self.language.strip():
            raise ValueError("INVALID_QUERY_LANGUAGE")


def _require_source_scope(source_refs: Tuple[SourceReference, ...], scope: ControlScope, error_code: str) -> None:
    for source in source_refs:
        if source.revision != scope.project_revision:
            raise ValueError(error_code)


@dataclass(frozen=True)
class ScheduleQueryAnswer:
    query_id: str
    scope: ControlScope
    answer_key: str
    data: Mapping[str, object] = field(default_factory=dict)
    source_refs: Tuple[SourceReference, ...] = ()
    proposed_actions: Tuple[ProposedAction, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.query_id, str) or not self.query_id.strip() or not isinstance(self.answer_key, str) or not self.answer_key.strip():
            raise ValueError("INVALID_SCHEDULE_QUERY_ANSWER")
        if not isinstance(self.scope, ControlScope):
            raise ValueError("INVALID_SCHEDULE_QUERY_ANSWER_SCOPE")
        if not self.source_refs:
            raise ValueError("SCHEDULE_QUERY_SOURCE_REQUIRED")
        _require_source_scope(self.source_refs, self.scope, "SCHEDULE_QUERY_SOURCE_REVISION_MISMATCH")
