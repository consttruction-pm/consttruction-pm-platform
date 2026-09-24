from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .adapter import ClientMutationRequest


@dataclass(frozen=True)
class CallableMutationTransport:
    """Small framework-neutral transport for injecting HTTP/IPC/application callers.

    The callable owns the actual transport. This class only converts the typed
    request into the authoritative payload and does not perform business logic.
    """

    sender: Callable[[dict[str, object]], object]

    def send(self, request: ClientMutationRequest) -> object:
        return self.sender(request.to_payload())
