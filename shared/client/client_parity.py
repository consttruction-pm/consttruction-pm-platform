from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ClientKind(str, Enum):
    WEB = "web"
    DESKTOP = "desktop"
    MOBILE = "mobile"


@dataclass(frozen=True)
class ClientCapabilities:
    scheduling: str = "shared-core"
    progress_evm: str = "shared-core"
    resource_cost: str = "shared-core"
    offline: bool = False
