from dataclasses import dataclass
from typing import Protocol

from .offline_mutation import OfflineMutation


class OfflineMutationStore(Protocol):
    def append(self, mutation: OfflineMutation) -> None: ...
    def pending(self) -> tuple[OfflineMutation, ...]: ...
    def acknowledge(self, mutation_id: str) -> None: ...


@dataclass
class InMemoryOfflineMutationStore:
    _items: list[OfflineMutation]

    def __init__(self) -> None:
        self._items = []

    def append(self, mutation: OfflineMutation) -> None:
        if any(item.mutation_id == mutation.mutation_id for item in self._items):
            raise ValueError("DUPLICATE_MUTATION_ID")
        if any(item.idempotency_key == mutation.idempotency_key for item in self._items):
            raise ValueError("DUPLICATE_IDEMPOTENCY_KEY")
        self._items.append(mutation)

    def pending(self) -> tuple[OfflineMutation, ...]:
        return tuple(self._items)

    def acknowledge(self, mutation_id: str) -> None:
        self._items = [item for item in self._items if item.mutation_id != mutation_id]
