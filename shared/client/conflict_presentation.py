from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class ClientConflictView:
    client: str
    error_code: str
    message_key: str
    available_actions: tuple[str, ...]
    context: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.client not in {"web", "desktop", "mobile"}:
            raise ValueError("INVALID_CLIENT")
        if not self.error_code:
            raise ValueError("INVALID_ERROR_CODE")
        if not self.message_key:
            raise ValueError("INVALID_MESSAGE_KEY")
        if not self.available_actions:
            raise ValueError("AVAILABLE_ACTIONS_REQUIRED")


def build_conflict_view(
    client: str,
    *,
    error_code: str,
    available_actions: Sequence[str],
    expected_revision: int,
    actual_revision: int | None = None,
    details: Mapping[str, object] | None = None,
) -> ClientConflictView:
    if expected_revision < 0:
        raise ValueError("INVALID_EXPECTED_REVISION")
    if actual_revision is not None and actual_revision < 0:
        raise ValueError("INVALID_ACTUAL_REVISION")
    return ClientConflictView(
        client=client,
        error_code=error_code,
        message_key=f"sync.error.{error_code}",
        available_actions=tuple(available_actions),
        context={
            "expected_revision": expected_revision,
            "actual_revision": actual_revision,
            "details": dict(details or {}),
        },
    )
