from dataclasses import dataclass, field

from .offline_mutation import OfflineMutation


@dataclass
class OfflineMutationQueue:
    _items: list[OfflineMutation] = field(default_factory=list)

    def enqueue(self, mutation: OfflineMutation) -> None:
        if any(item.mutation_id == mutation.mutation_id for item in self._items):
            raise ValueError("DUPLICATE_MUTATION_ID")
        if any(item.idempotency_key == mutation.idempotency_key for item in self._items):
            raise ValueError("DUPLICATE_IDEMPOTENCY_KEY")
        self._items.append(mutation)

    def pending(self) -> tuple[OfflineMutation, ...]:
        return tuple(self._items)

    def acknowledge(self, mutation_id: str) -> None:
        self._items = [item for item in self._items if item.mutation_id != mutation_id]
