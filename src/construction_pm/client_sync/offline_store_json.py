import json
from pathlib import Path

from .offline_mutation import OfflineMutation
from .offline_store import OfflineMutationStore


class JsonFileOfflineMutationStore:
    """Portable local persistence adapter; business semantics stay outside storage."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _read(self) -> list[dict[str, object]]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("INVALID_OFFLINE_STORE")
        return raw

    def _write(self, items: list[dict[str, object]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(items, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def append(self, mutation: OfflineMutation) -> None:
        items = self._read()
        if any(item.get("mutation_id") == mutation.mutation_id for item in items):
            raise ValueError("DUPLICATE_MUTATION_ID")
        if any(item.get("idempotency_key") == mutation.idempotency_key for item in items):
            raise ValueError("DUPLICATE_IDEMPOTENCY_KEY")
        items.append({
            "mutation_id": mutation.mutation_id,
            "tenant_id": mutation.tenant_id,
            "project_id": mutation.project_id,
            "expected_revision": mutation.expected_revision,
            "operation": mutation.operation,
            "payload": dict(mutation.payload),
            "idempotency_key": mutation.idempotency_key,
        })
        self._write(items)

    def pending(self) -> tuple[OfflineMutation, ...]:
        return tuple(OfflineMutation(
            mutation_id=str(item["mutation_id"]),
            tenant_id=str(item["tenant_id"]),
            project_id=str(item["project_id"]),
            expected_revision=int(item["expected_revision"]),
            operation=str(item["operation"]),
            payload=dict(item["payload"]),
            idempotency_key=str(item["idempotency_key"]),
        ) for item in self._read())

    def acknowledge(self, mutation_id: str) -> None:
        self._write([
            item for item in self._read()
            if item.get("mutation_id") != mutation_id
        ])
