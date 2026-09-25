from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
from typing import Any


@dataclass(frozen=True)
class CalculationContext:
    """Immutable context carried across Shared Core calculations.

    The context is part of calculation identity: the same input snapshot
    evaluated under the same context must produce the same calculation result.
    """

    project_id: str
    project_version: int
    calendar_id: str
    calendar_version: str
    rules_version: str
    engine_version: str
    timezone: str
    calculation_timestamp: str
    input_snapshot_id: str
    tenant_id: str | None = None
    actor_id: str | None = None
    request_id: str | None = None
    idempotency_key: str | None = None

    def __post_init__(self) -> None:
        for field in (
            "project_id",
            "calendar_id",
            "calendar_version",
            "rules_version",
            "engine_version",
            "timezone",
            "calculation_timestamp",
            "input_snapshot_id",
        ):
            if not getattr(self, field):
                raise ValueError(f"{field} is required")
        if self.project_version < 0:
            raise ValueError("project_version must be non-negative")
        try:
            parsed = datetime.fromisoformat(self.calculation_timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("calculation_timestamp must be ISO-8601") from exc
        if parsed.tzinfo is None:
            raise ValueError("calculation_timestamp must include a timezone offset")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    @property
    def calculation_identity(self) -> str:
        return self.sha256()
