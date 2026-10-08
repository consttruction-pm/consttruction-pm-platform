from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
from typing import Any


CALCULATION_IDENTITY_VERSION = "2"

SEMANTIC_IDENTITY_FIELDS = (
    "project_id",
    "project_version",
    "calendar_id",
    "calendar_version",
    "rules_version",
    "engine_version",
    "timezone",
    "input_snapshot_id",
    "tenant_id",
)

PROVENANCE_FIELDS = (
    "calculation_timestamp",
    "actor_id",
    "request_id",
    "idempotency_key",
)


@dataclass(frozen=True)
class CalculationContext:
    """Immutable context carried across Shared Core calculations.

    Calculation identity contains only deterministic scheduling inputs and
    execution-scope fields. Request/provenance metadata is retained in the
    context and full-context hash for auditability, but never changes the
    semantic calculation identity.

    Identity policy (v2):
    - Semantic: project_id, project_version, calendar_id, calendar_version,
      rules_version, engine_version, timezone, input_snapshot_id, tenant_id.
    - Provenance/audit: calculation_timestamp, actor_id, request_id,
      idempotency_key.
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

    def provenance_dict(self) -> dict[str, Any]:
        """Return request/audit metadata that must not affect calculation semantics."""
        return {field: getattr(self, field) for field in PROVENANCE_FIELDS}

    def semantic_identity_dict(self) -> dict[str, Any]:
        """Return the versioned deterministic inputs that define calculation identity."""
        return {
            "identity_version": CALCULATION_IDENTITY_VERSION,
            **{field: getattr(self, field) for field in SEMANTIC_IDENTITY_FIELDS},
        }

    def calculation_identity_json(self) -> str:
        return json.dumps(
            self.semantic_identity_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def sha256(self) -> str:
        """Hash the complete context, including provenance, for legacy/audit use."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    @property
    def legacy_calculation_identity(self) -> str:
        """Pre-v2 identity hash retained for explicit snapshot migration."""
        return self.sha256()

    @property
    def calculation_identity(self) -> str:
        """Deterministic identity for semantically identical scheduling inputs."""
        return hashlib.sha256(self.calculation_identity_json().encode("utf-8")).hexdigest()
