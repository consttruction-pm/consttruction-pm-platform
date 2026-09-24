from dataclasses import dataclass
from typing import Protocol

from .conflict import ConflictContext


class ConflictStore(Protocol):
    def save(self, mutation_id: str, tenant_id: str, project_id: str, context: ConflictContext) -> None: ...
    def get(self, mutation_id: str) -> ConflictContext | None: ...


@dataclass
class InMemoryConflictStore:
    _items: dict[tuple[str, str, str], ConflictContext]

    def __init__(self) -> None:
        self._items = {}

    def save(self, mutation_id: str, tenant_id: str, project_id: str, context: ConflictContext) -> None:
        self._items[(tenant_id, project_id, mutation_id)] = context

    def get(self, mutation_id: str, tenant_id: str, project_id: str) -> ConflictContext | None:
        return self._items.get((tenant_id, project_id, mutation_id))
