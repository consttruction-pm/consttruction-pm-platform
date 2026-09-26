from .revision_limits import MAX_SAFE_PROJECT_REVISION
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class OfflineMutation:
    mutation_id: str
    tenant_id: str
    project_id: str
    expected_revision: int
    operation: str
    payload: Mapping[str, object]
    idempotency_key: str

    def __post_init__(self) -> None:
        if not self.mutation_id or not self.tenant_id or not self.project_id:
            raise ValueError("INVALID_MUTATION_IDENTITY")
        if (isinstance(self.expected_revision, bool) or not isinstance(self.expected_revision, int) or self.expected_revision < 0 or self.expected_revision > MAX_SAFE_PROJECT_REVISION):
            raise ValueError("INVALID_EXPECTED_REVISION")
        if not self.operation or not self.idempotency_key:
            raise ValueError("INVALID_MUTATION_METADATA")
