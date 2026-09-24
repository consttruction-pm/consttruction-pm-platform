from typing import Protocol

from .offline_mutation import OfflineMutation
from .sync_outcome import SyncOutcome


class SyncTransport(Protocol):
    def submit(self, mutation: OfflineMutation) -> SyncOutcome: ...
