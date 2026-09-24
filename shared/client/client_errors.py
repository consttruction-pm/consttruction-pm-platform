from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ClientError:
    code: str
    retryable: bool
    message_key: str
    available_actions: Tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.code or not self.message_key:
            raise ValueError("error code and message key are required")
