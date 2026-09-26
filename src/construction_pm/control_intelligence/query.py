from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Tuple

from .contracts import ControlScope, ProposedAction, SourceReference

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
        if not self.query_id or not self.requested_by or not self.query_text.strip():
            raise ValueError("INVALID_SCHEDULE_QUERY")
        if not self.language.strip():
            raise ValueError("INVALID_QUERY_LANGUAGE")

@dataclass(frozen=True)
class ScheduleQueryAnswer:
    query_id: str
    scope: ControlScope
    answer_key: str
    data: Mapping[str, object] = field(default_factory=dict)
    source_refs: Tuple[SourceReference, ...] = ()
    proposed_actions: Tuple[ProposedAction, ...] = ()

    def __post_init__(self) -> None:
        if not self.query_id or not self.answer_key:
            raise ValueError("INVALID_SCHEDULE_QUERY_ANSWER")
        if not self.source_refs:
            raise ValueError("SCHEDULE_QUERY_SOURCE_REQUIRED")
